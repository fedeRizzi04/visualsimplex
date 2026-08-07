from fractions import Fraction

import pytest

from visualsimplex.initialization import BalinskiGomoryInitializer, InfeasibleProblemError, InitializationPivotKind
from visualsimplex.tableau import Tableau, TableauRow
from visualsimplex.value_objects import VarKind, Variable


def var(symbol, kind=VarKind.ORIGINAL):
    return Variable(kind, symbol)


def make_tableau(variables, basic_variables, reduced_costs, rows):
    tableau = Tableau.__new__(Tableau)
    tableau._basic_vars = frozenset(basic_variables)
    tableau._objective_tableau_coeff = Fraction(0)
    tableau._variables = tuple(variables)
    tableau._reduced_cost_coefficients = tuple(Fraction(value) for value in reduced_costs)
    tableau._rows = tuple(rows)
    return tableau


def test_tableau_initialize_rejects_an_already_feasible_basis(mocker):
    x, s = var("x"), var("s", VarKind.SLACK)
    tableau = make_tableau((x, s), (s,), (0, 0), (TableauRow((Fraction(1), Fraction(1)), Fraction(1), s),))
    strategy = mocker.Mock()

    with pytest.raises(ValueError, match="already feasible"):
        tableau.initialize(strategy)
    strategy.run.assert_not_called()


def test_tableau_initialize_propagates_the_infeasible_problem_error_from_the_strategy(mocker):
    x, s = var("x"), var("s", VarKind.SLACK)
    tableau = make_tableau((x, s), (s,), (0, 0), (TableauRow((Fraction(1), Fraction(1)), Fraction(-1), s),))
    expected_error = InfeasibleProblemError('infeasible problem')
    strategy = mocker.Mock()
    strategy.run.side_effect = expected_error

    with pytest.raises(InfeasibleProblemError) as raised:
        tableau.initialize(strategy)

    assert raised.value is expected_error


def test_balinski_gomory_optimizes_a_violated_constraint_until_it_becomes_feasible():
    x1, x2 = var("x1"), var("x2")
    s1, s2, s3 = var("s1", VarKind.SLACK), var("s2", VarKind.SLACK), var("s3", VarKind.SLACK)
    tableau = make_tableau(
        (x1, x2, s1, s2, s3),
        (s1, s2, s3),
        (2, 3, 0, 0, 0),
        (
            TableauRow((Fraction(1), Fraction(0), Fraction(1), Fraction(0), Fraction(0)), Fraction(2), s1),
            TableauRow((Fraction(0), Fraction(1), Fraction(0), Fraction(1), Fraction(0)), Fraction(10), s2),
            TableauRow((Fraction(-1), Fraction(-1), Fraction(0), Fraction(0), Fraction(1)), Fraction(-4), s3),
        ),
    )
    strategy = BalinskiGomoryInitializer()

    result = tableau.initialize(strategy)

    assert result.is_feasible_basis()
    assert tuple(result.basic_variables) == (x1, x2, s3)
    assert result.get_value_for_basic_var(s3) == Fraction(8)
    assert tuple((step.entering, step.leaving) for step in strategy.steps) == ((x1, s1), (x2, s2))
    assert all(step.violated_row_basic_var == s3 for step in strategy.steps)
    assert all(step.kind is InitializationPivotKind.AUXILIARY_OPTIMIZATION for step in strategy.steps)


def test_balinski_gomory_uses_a_negative_pivot_when_the_auxiliary_problem_is_unbounded():
    x = var("x")
    s1, s2 = var("s1", VarKind.SLACK), var("s2", VarKind.SLACK)
    tableau = make_tableau(
        (x, s1, s2),
        (s1, s2),
        (2, 0, 0),
        (
            TableauRow((Fraction(0), Fraction(1), Fraction(0)), Fraction(6), s1),
            TableauRow((Fraction(-1), Fraction(0), Fraction(1)), Fraction(-4), s2),
        ),
    )
    strategy = BalinskiGomoryInitializer()

    result = tableau.initialize(strategy)

    assert result.is_feasible_basis()
    assert tuple(result.basic_variables) == (x, s1)
    assert result.get_value_for_basic_var(x) == Fraction(4)
    steps = tuple(strategy.steps)
    assert len(steps) == 1
    step = steps[0]
    assert step.pivot == Fraction(-1)
    assert step.kind is InitializationPivotKind.FEASIBILITY_REPAIR


def test_balinski_gomory_stops_optimizing_a_constraint_as_soon_as_its_rhs_is_non_negative():
    x1, x2 = var("x1"), var("x2")
    s1, s2 = var("s1", VarKind.SLACK), var("s2", VarKind.SLACK)
    tableau = make_tableau(
        (x1, x2, s1, s2),
        (s1, s2),
        (0, 0, 0, 0),
        (
            TableauRow((Fraction(1), Fraction(0), Fraction(1), Fraction(0)), Fraction(2), s1),
            TableauRow((Fraction(-1), Fraction(-1), Fraction(0), Fraction(1)), Fraction(-2), s2),
        ),
    )
    strategy = BalinskiGomoryInitializer()

    result = tableau.initialize(strategy)

    assert result.get_value_for_basic_var(s2) == Fraction(0)
    assert len(tuple(strategy.steps)) == 1


def test_balinski_gomory_detects_an_infeasible_problem():
    x, s = var("x"), var("s", VarKind.SLACK)
    tableau = make_tableau((x, s), (s,), (0, 0), (TableauRow((Fraction(1), Fraction(1)), Fraction(-1), s),))
    strategy = BalinskiGomoryInitializer()

    with pytest.raises(InfeasibleProblemError):
        tableau.initialize(strategy)
    assert tuple(strategy.steps) == ()


def test_balinski_gomory_delegates_the_order_of_violated_constraints_to_the_given_rule():
    x1, x2 = var("x1"), var("x2")
    s1, s2 = var("s1", VarKind.SLACK), var("s2", VarKind.SLACK)
    tableau = make_tableau(
        (x1, x2, s1, s2),
        (s1, s2),
        (0, 0, 0, 0),
        (
            TableauRow((Fraction(-1), Fraction(0), Fraction(1), Fraction(0)), Fraction(-1), s1),
            TableauRow((Fraction(0), Fraction(-1), Fraction(0), Fraction(1)), Fraction(-2), s2),
        ),
    )

    def choose_last(candidates):
        return tuple(candidates)[-1]

    strategy = BalinskiGomoryInitializer(violated_constraint_rule=choose_last)

    result = tableau.initialize(strategy)

    assert result.is_feasible_basis()
    assert tuple(step.violated_row_basic_var for step in strategy.steps) == (s2, s1)
    assert all(step.kind is InitializationPivotKind.FEASIBILITY_REPAIR for step in strategy.steps)
