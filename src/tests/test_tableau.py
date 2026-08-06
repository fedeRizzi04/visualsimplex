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
    assert tableau.objective_value == Fraction(7, 2)


def test_get_var_index_returns_the_column_and_rejects_unknown_variables():
    x, s = var("x"), var("s", VarKind.SLACK)
    tableau = Tableau.__new__(Tableau)
    tableau._basic_vars = tableau._basic_variables = frozenset((s,))
    tableau._non_basic_vars = tableau._non_basic_variables = frozenset((x,))

    with pytest.raises(ValueError, match="unknown"):
        tableau.get_var_index(var("unknown"))
    assert tableau.get_var_index(x) == 0
    assert tableau.get_var_index(s) == 1


def test_lp_problem_to_tableau_integration_preserves_variable_and_constraint_alignment():
    x1, x2 = var("x1"), var("x2")
    problem = LPProblem(
        Objective(Expression((Term(x1, Fraction(2)), Term(x2, Fraction(3)))), OptimizationSense.MAXIMIZE),
        (
            Constraint(Expression((Term(x1, Fraction(1)), Term(x2, Fraction(1)))), Fraction(4), ConstraintSense.LE),
            Constraint(Expression((Term(x1, Fraction(2)), Term(x2, Fraction(1)))), Fraction(5), ConstraintSense.LE),
        ),
    )

    tableau = Tableau(problem.from_inequality_form_to_canonical_form())

    assert tuple(variable.symbol for variable in tableau.variables) == ("x1", "x2", "sl0", "sl1")
    assert tableau._reduced_cost_coefficients == (Fraction(-2), Fraction(-3), Fraction(0), Fraction(0))
    assert tableau._rows == (
        TableauRow((Fraction(1), Fraction(1), Fraction(1), Fraction(0)), Fraction(4), var("sl0", VarKind.SLACK)),
        TableauRow((Fraction(2), Fraction(1), Fraction(0), Fraction(1)), Fraction(5), var("sl1", VarKind.SLACK)),
    )
