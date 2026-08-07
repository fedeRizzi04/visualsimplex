from fractions import Fraction

import pytest

from visualsimplex import Constraint, ConstraintSense, Expression, LPProblem, Objective, OptimizationSense, Term, VarKind, Variable
from visualsimplex.lp_problem import CanonicalFormLPProblem
from visualsimplex.rules import LeavingCandidate, bland_rule, dantzig_rule, minimum_ratio_rule
from visualsimplex.tableau import Tableau, TableauRow, get_basic_var


def var(symbol, kind=VarKind.ORIGINAL):
    return Variable(kind, symbol)


def test_get_basic_var_returns_the_variable_and_not_its_term():
    x, s = var("x"), var("s", VarKind.SLACK)
    expression = Expression((Term(x, Fraction(2)), Term(s, Fraction(1))))

    assert get_basic_var(expression, frozenset((s,))) == s


@pytest.mark.parametrize(
    ("expression", "basic_vars"),
    [
        (Expression((Term(var("x"), Fraction(1)),)), frozenset((var("s", VarKind.SLACK),))),
        (Expression((Term(var("s1", VarKind.SLACK), Fraction(1)), Term(var("s2", VarKind.SLACK), Fraction(1)))), frozenset((var("s1", VarKind.SLACK), var("s2", VarKind.SLACK)))),
    ],
)
def test_get_basic_var_rejects_missing_or_ambiguous_basic_variables(expression, basic_vars):
    with pytest.raises(ValueError):
        get_basic_var(expression, basic_vars)


def test_tableau_builds_coefficients_from_mocked_problem_dependencies(mocker):
    x, s = var("x"), var("s", VarKind.SLACK)
    objective_expr = mocker.MagicMock()
    objective_expr.coefficient_of.side_effect = {x: Fraction(-2), s: Fraction(0)}.__getitem__
    row_expr = mocker.MagicMock()
    row_expr.coefficient_of.side_effect = {x: Fraction(3), s: Fraction(1)}.__getitem__
    row_expr.__iter__.return_value = iter((Term(x, Fraction(3)), Term(s, Fraction(1))))
    constraint = mocker.Mock(expr=row_expr, rhs=Fraction(6))
    problem = mocker.MagicMock()
    problem.objective.expr = objective_expr
    problem.__iter__.return_value = iter((constraint,))
    canonical = mocker.Mock(problem=problem, basic_vars=frozenset((s,)), non_basic_vars=frozenset((x,)))

    tableau = Tableau(canonical, Fraction(7, 2))

    assert tuple(tableau.variables) == (x, s)
    assert tuple(tableau.basic_variables) == (s,)
    assert tuple(tableau.non_basic_variables) == (x,)
    assert tableau._reduced_cost_coefficients == (Fraction(-2), Fraction(0))
    assert tableau._rows == (TableauRow((Fraction(3), Fraction(1)), Fraction(6), s),)
    assert tableau.objective_value == Fraction(-7, 2)
    assert tableau.get_value_for_basic_var(s) == Fraction(6)
    with pytest.raises(ValueError, match="not a basic var"):
        tableau.get_value_for_basic_var(x)


def test_get_var_index_returns_the_column_and_rejects_unknown_variables():
    x, s = var("x"), var("s", VarKind.SLACK)
    tableau = Tableau.__new__(Tableau)
    tableau._basic_vars = frozenset((s,))
    tableau._variables = (x, s)
    tableau._objective_tableau_coeff, tableau._reduced_cost_coefficients = Fraction(0), (Fraction(0), Fraction(0))
    tableau._rows = (TableauRow((Fraction(0), Fraction(1)), Fraction(0), s),)

    with pytest.raises(ValueError, match="unknown"):
        tableau.get_var_index(var("unknown"))
    assert tableau.get_var_index(x) == 0
    assert tableau.get_var_index(s) == 1


@pytest.mark.parametrize(
    (
        "rhs_values",
        "reduced_costs",
        "row_coefficients",
        "expected_feasible",
        "expected_optimal",
        "expected_unbounded",
    ),
    [
        ((), (), (), True, True, False),
        (
            (Fraction(0), Fraction(3, 2)),
            (Fraction(0), Fraction(2, 3)),
            ((Fraction(0), Fraction(1)), (Fraction(1), Fraction(0))),
            True,
            True,
            False,
        ),
        (
            (Fraction(0), Fraction(-1, 3)),
            (Fraction(-1), Fraction(0)),
            ((Fraction(0), Fraction(1)), (Fraction(0), Fraction(1))),
            False,
            False,
            False,
        ),
        (
            (Fraction(0), Fraction(1)),
            (Fraction(-1, 3), Fraction(0)),
            ((Fraction(0), Fraction(1)), (Fraction(2), Fraction(1))),
            True,
            False,
            False,
        ),
        (
            (Fraction(0), Fraction(1)),
            (Fraction(-1, 3), Fraction(0)),
            ((Fraction(0), Fraction(1)), (Fraction(0), Fraction(1))),
            True,
            False,
            True,
        ),
        (
            (Fraction(1), Fraction(2)),
            (Fraction(-1), Fraction(-2), Fraction(0)),
            ((Fraction(1), Fraction(0), Fraction(1)), (Fraction(0), Fraction(-1), Fraction(0))),
            True,
            False,
            True,
        ),
    ],
    ids=(
        "empty",
        "zero-boundaries",
        "negative-rhs",
        "eligible-pivot",
        "zero-pivot-column",
        "one-unbounded-candidate-among-many",
    ),
)
def test_basis_feasibility_and_optimality_edge_cases(
    rhs_values,
    reduced_costs,
    row_coefficients,
    expected_feasible,
    expected_optimal,
    expected_unbounded,
):
    tableau = Tableau.__new__(Tableau)
    tableau._variables = tuple(var(f"x{i}") for i in range(len(reduced_costs)))
    tableau._rows = tuple(
        TableauRow(coefficients, rhs, var(f"s{i}", VarKind.SLACK))
        for i, (rhs, coefficients) in enumerate(zip(rhs_values, row_coefficients))
    )
    tableau._reduced_cost_coefficients = reduced_costs

    assert tableau.is_feasible_basis() is expected_feasible
    assert tableau.is_optimal_basis() is expected_optimal
    assert tableau.is_unbounded_problem() is expected_unbounded


def test_entering_candidate_variables_returns_variables_with_negative_reduced_costs():
    x1, x2, x3, s = var("x1"), var("x2"), var("x3"), var("s", VarKind.SLACK)
    tableau = Tableau.__new__(Tableau)
    tableau._basic_vars = frozenset((s,))
    tableau._variables = (x1, x2, x3, s)
    tableau._reduced_cost_coefficients = (Fraction(-2), Fraction(0), Fraction(-1, 3), Fraction(0))

    assert tuple(tableau.entering_candidate_variables()) == (x1, x3)


def test_entering_variable_delegates_the_choice_to_the_given_rule():
    x1, x2, x3, s = var("x1"), var("x2"), var("x3"), var("s", VarKind.SLACK)
    tableau = Tableau.__new__(Tableau)
    tableau._basic_vars = frozenset((s,))
    tableau._variables = (x1, x2, x3, s)
    tableau._reduced_cost_coefficients = (Fraction(-1), Fraction(0), Fraction(-2), Fraction(0))

    assert tableau.entering_variable(bland_rule) == x1
    assert tableau.entering_variable(dantzig_rule) == x3


def test_leaving_variable_uses_the_minimum_ratio_and_ignores_non_positive_pivots():
    x = var("x")
    s1, s2, s3, s4 = (var(f"s{i}", VarKind.SLACK) for i in range(1, 5))
    tableau = Tableau.__new__(Tableau)
    tableau._basic_vars = frozenset((s1, s2, s3, s4))
    tableau._variables = (x, s1, s2, s3, s4)
    tableau._reduced_cost_coefficients = (Fraction(-1), Fraction(0), Fraction(0), Fraction(0), Fraction(0))
    tableau._rows = (
        TableauRow((Fraction(2), Fraction(1), Fraction(0), Fraction(0), Fraction(0)), Fraction(8), s1),
        TableauRow((Fraction(1), Fraction(0), Fraction(1), Fraction(0), Fraction(0)), Fraction(3), s2),
        TableauRow((Fraction(0), Fraction(0), Fraction(0), Fraction(1), Fraction(0)), Fraction(0), s3),
        TableauRow((Fraction(-2), Fraction(0), Fraction(0), Fraction(0), Fraction(1)), Fraction(1), s4),
    )

    assert tableau.leaving_variable(x, minimum_ratio_rule) == LeavingCandidate(s2, Fraction(1), Fraction(3))


def test_leaving_variable_delegates_the_choice_among_eligible_rows_to_the_given_rule():
    x, s1, s2 = var("x"), var("s1", VarKind.SLACK), var("s2", VarKind.SLACK)
    tableau = Tableau.__new__(Tableau)
    tableau._basic_vars = frozenset((s1, s2))
    tableau._variables = (x, s1, s2)
    tableau._reduced_cost_coefficients = (Fraction(-1), Fraction(0), Fraction(0))
    tableau._rows = (
        TableauRow((Fraction(1), Fraction(1), Fraction(0)), Fraction(4), s1),
        TableauRow((Fraction(1), Fraction(0), Fraction(1)), Fraction(2), s2),
    )

    def choose_first(candidates):
        return next(iter(candidates))

    assert tableau.leaving_variable(x, choose_first) == LeavingCandidate(s1, Fraction(1), Fraction(4))


def test_leaving_variable_accepts_a_degenerate_pivot_and_breaks_ratio_ties_by_row_order():
    x, s1, s2 = var("x"), var("s1", VarKind.SLACK), var("s2", VarKind.SLACK)
    tableau = Tableau.__new__(Tableau)
    tableau._basic_vars = frozenset((s1, s2))
    tableau._variables = (x, s1, s2)
    tableau._reduced_cost_coefficients = (Fraction(-1), Fraction(0), Fraction(0))
    tableau._rows = (
        TableauRow((Fraction(2), Fraction(1), Fraction(0)), Fraction(0), s1),
        TableauRow((Fraction(1), Fraction(0), Fraction(1)), Fraction(0), s2),
    )

    assert tableau.leaving_variable(x, minimum_ratio_rule) == LeavingCandidate(s1, Fraction(2), Fraction(0))


def test_leaving_variable_ignores_negative_rhs_rows_without_requiring_a_feasible_basis():
    x, s1, s2 = var("x"), var("s1", VarKind.SLACK), var("s2", VarKind.SLACK)
    tableau = Tableau.__new__(Tableau)
    tableau._basic_vars = frozenset((s1, s2))
    tableau._variables = (x, s1, s2)
    tableau._reduced_cost_coefficients = (Fraction(-1), Fraction(0), Fraction(0))
    tableau._rows = (
        TableauRow((Fraction(2), Fraction(1), Fraction(0)), Fraction(-4), s1),
        TableauRow((Fraction(1), Fraction(0), Fraction(1)), Fraction(3), s2),
    )

    assert tableau.leaving_variable(x, minimum_ratio_rule) == LeavingCandidate(s2, Fraction(1), Fraction(3))


def test_leaving_variable_reports_unboundedness_only_for_a_feasible_basis():
    x, s = var("x"), var("s", VarKind.SLACK)
    tableau = Tableau.__new__(Tableau)
    tableau._basic_vars = frozenset((s,))
    tableau._variables = (x, s)
    tableau._reduced_cost_coefficients = (Fraction(-1), Fraction(0))
    tableau._rows = (TableauRow((Fraction(0), Fraction(1)), Fraction(1), s),)

    with pytest.raises(ValueError, match="unbounded"):
        tableau.leaving_variable(x, minimum_ratio_rule)

    tableau._rows = (TableauRow((Fraction(0), Fraction(1)), Fraction(-1), s),)
    with pytest.raises(ValueError, match="no eligible pivot") as error:
        tableau.leaving_variable(x, minimum_ratio_rule)
    assert "unbounded" not in str(error.value)


def test_get_constraints_coefficient_returns_the_column_and_rejects_unknown_variables():
    x1, x2 = var("x1"), var("x2")
    tableau = Tableau.__new__(Tableau)
    tableau._variables = (x1, x2)
    tableau._rows = (
        TableauRow((Fraction(2), Fraction(0)), Fraction(1), var("s1", VarKind.SLACK)),
        TableauRow((Fraction(-1, 3), Fraction(4)), Fraction(2), var("s2", VarKind.SLACK)),
    )

    assert tuple(tableau.get_constraints_coefficient(x1)) == (Fraction(2), Fraction(-1, 3))
    assert tuple(tableau.get_constraints_coefficient(x2)) == (Fraction(0), Fraction(4))
    with pytest.raises(ValueError, match="not part of this tableau variables"):
        tableau.get_constraints_coefficient(var("unknown"))


def test_pivot_returns_the_transformed_tableau_without_mutating_the_original():
    x1, x2, s1, s2 = var("x1"), var("x2"), var("s1", VarKind.SLACK), var("s2", VarKind.SLACK)
    tableau = Tableau.__new__(Tableau)
    tableau._basic_vars = frozenset((s1, s2))
    tableau._objective_tableau_coeff = Fraction(0)
    tableau._variables = (x1, x2, s1, s2)
    tableau._reduced_cost_coefficients = (Fraction(-3), Fraction(-2), Fraction(0), Fraction(0))
    tableau._rows = (
        TableauRow((Fraction(1), Fraction(1), Fraction(1), Fraction(0)), Fraction(4), s1),
        TableauRow((Fraction(2), Fraction(1), Fraction(0), Fraction(1)), Fraction(5), s2),
    )

    result = tableau.pivot(x1, s2)

    assert result._basic_vars == frozenset((x1, s1))
    assert result._objective_tableau_coeff == Fraction(15, 2)
    assert result._reduced_cost_coefficients == (Fraction(0), Fraction(-1, 2), Fraction(0), Fraction(3, 2))
    assert result._rows == (
        TableauRow((Fraction(0), Fraction(1, 2), Fraction(1), Fraction(-1, 2)), Fraction(3, 2), s1),
        TableauRow((Fraction(1), Fraction(1, 2), Fraction(0), Fraction(1, 2)), Fraction(5, 2), x1),
    )
    assert tableau._basic_vars == frozenset((s1, s2))
    assert tableau._objective_tableau_coeff == Fraction(0)
    assert tableau._rows[1].basic_var == s2
    assert tableau.pivot(x1, s1)._rows[1].rhs == Fraction(-3)


@pytest.mark.parametrize(
    ("entering", "leaving", "expected_error"),
    [
        ("x2", "s1", "not a candidate entering variable"),
        ("x1", "x2", "not a basic variable"),
        ("x1", "s1", "not a positive value"),
        ("x1", "s2", "right hand side.*negative"),
    ],
)
def test_pivot_rejects_invalid_variables_and_ineligible_pivots(entering, leaving, expected_error):
    variables = {symbol: var(symbol, VarKind.SLACK if symbol.startswith("s") else VarKind.ORIGINAL) for symbol in ("x1", "x2", "s1", "s2")}
    tableau = Tableau.__new__(Tableau)
    tableau._basic_vars = frozenset((variables["s1"], variables["s2"]))
    tableau._objective_tableau_coeff = Fraction(0)
    tableau._variables = tuple(variables.values())
    tableau._reduced_cost_coefficients = (Fraction(-1), Fraction(0), Fraction(0), Fraction(0))
    tableau._rows = (
        TableauRow((Fraction(0), Fraction(1), Fraction(1), Fraction(0)), Fraction(1), variables["s1"]),
        TableauRow((Fraction(1), Fraction(0), Fraction(0), Fraction(1)), Fraction(-1), variables["s2"]),
    )

    with pytest.raises(ValueError, match=expected_error):
        tableau.pivot(variables[entering], variables[leaving])


def test_to_canonical_form_problem_preserves_tableau_state_in_a_round_trip():
    x, s = var("x"), var("s", VarKind.SLACK)
    problem = LPProblem(
        Objective(Expression((Term(x, Fraction(-2)),)), OptimizationSense.MINIMIZE),
        (Constraint(Expression((Term(x, Fraction(3)), Term(s, Fraction(1)))), Fraction(6), ConstraintSense.EQ),),
    )
    canonical_problem = CanonicalFormLPProblem(problem, frozenset((s,)), frozenset((x,)))
    tableau = Tableau(canonical_problem, Fraction(7, 2))

    rebuilt_tableau = Tableau(tableau.to_canonical_form_problem(), tableau._objective_tableau_coeff)

    assert rebuilt_tableau._basic_vars == tableau._basic_vars
    assert rebuilt_tableau._variables == tableau._variables
    assert rebuilt_tableau._reduced_cost_coefficients == tableau._reduced_cost_coefficients
    assert rebuilt_tableau._rows == tableau._rows
    assert rebuilt_tableau._objective_tableau_coeff == tableau._objective_tableau_coeff


def test_tableau_row_string_contains_rhs_and_coefficients():
    row = TableauRow((Fraction(-1, 2), Fraction(0), Fraction(3)), Fraction(5, 4), var("s", VarKind.SLACK))

    assert str(row) == "5/4 | -1/2  0  3"


def test_lp_problem_to_tableau_integration_preserves_variable_and_constraint_alignment():
    x1, x2 = var("x1"), var("x2")
    problem = LPProblem(
        Objective(Expression((Term(x1, Fraction(10, 3)), Term(x2, Fraction(3)))), OptimizationSense.MAXIMIZE),
        (
            Constraint(Expression((Term(x1, Fraction(1)), Term(x2, Fraction(1)))), Fraction(400), ConstraintSense.LE),
            Constraint(Expression((Term(x1, Fraction(2)), Term(x2, Fraction(1)))), Fraction(5), ConstraintSense.LE),
        ),
    )

    canonical_problem = problem.from_inequality_form_to_canonical_form()
    tableau = Tableau(canonical_problem, Fraction(7, 2))

    assert tuple(variable.symbol for variable in tableau.variables) == ("x1", "x2", "sl0", "sl1")
    assert tableau._reduced_cost_coefficients == (Fraction(-10, 3), Fraction(-3), Fraction(0), Fraction(0))
    assert tableau._rows == (
        TableauRow((Fraction(1), Fraction(1), Fraction(1), Fraction(0)), Fraction(400), var("sl0", VarKind.SLACK)),
        TableauRow((Fraction(2), Fraction(1), Fraction(0), Fraction(1)), Fraction(5), var("sl1", VarKind.SLACK)),
    )
    assert tuple(tableau.entering_candidate_variables()) == (x1, x2)
    assert str(tableau) == (
        "    |    x1  x2  sl0  sl1\n"
        "7/2 | -10/3  -3    0    0\n"
        "400 |     1   1    1    0\n"
        "  5 |     2   1    0    1\n"
        "Basis: sl0 = 400, sl1 = 5\n"
        "Objective value: -7/2"
    )
    assert str(Tableau(canonical_problem)) == (
        "    |    x1  x2  sl0  sl1\n"
        "  0 | -10/3  -3    0    0\n"
        "400 |     1   1    1    0\n"
        "  5 |     2   1    0    1\n"
        "Basis: sl0 = 400, sl1 = 5\n"
        "Objective value: 0"
    )
