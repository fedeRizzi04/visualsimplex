from fractions import Fraction

import pytest

from visualsimplex import Constraint, ConstraintSense, Expression, LPProblem, Objective, OptimizationSense, Term, VarKind, Variable
from visualsimplex.lp_problem import CanonicalFormLPProblem
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
    ("rhs_values", "reduced_costs", "expected_feasible", "expected_optimal"),
    [
        ((), (), True, True),
        ((Fraction(0), Fraction(3, 2)), (Fraction(0), Fraction(2, 3)), True, True),
        ((Fraction(0), Fraction(-1, 3)), (Fraction(0), Fraction(1)), False, False),
        ((Fraction(0), Fraction(1)), (Fraction(0), Fraction(-1, 3)), True, False),
    ],
    ids=("empty", "zero-boundaries", "negative-rhs", "negative-reduced-cost"),
)
def test_basis_feasibility_and_optimality_edge_cases(
    rhs_values, reduced_costs, expected_feasible, expected_optimal
):
    tableau = Tableau.__new__(Tableau)
    tableau._rows = tuple(
        TableauRow((), rhs, var(f"s{i}", VarKind.SLACK))
        for i, rhs in enumerate(rhs_values)
    )
    tableau._reduced_cost_coefficients = reduced_costs

    assert tableau.is_feasible_basis() is expected_feasible
    assert tableau.is_optimal_basis() is expected_optimal


def test_candidate_entering_variables_returns_variables_with_negative_reduced_costs():
    x1, x2, x3, s = var("x1"), var("x2"), var("x3"), var("s", VarKind.SLACK)
    tableau = Tableau.__new__(Tableau)
    tableau._basic_vars = frozenset((s,))
    tableau._variables = (x1, x2, x3, s)
    tableau._reduced_cost_coefficients = (Fraction(-2), Fraction(0), Fraction(-1, 3), Fraction(0))

    assert tuple(tableau.candidate_entering_variables()) == (x1, x3)


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
    assert tuple(tableau.candidate_entering_variables()) == (x1, x2)
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
