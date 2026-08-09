from dataclasses import FrozenInstanceError
from fractions import Fraction

import pytest

from visualsimplex.initialization import BalinskiGomoryInitializer, InitializationStatus
from visualsimplex.rules import EnteringCandidate, LeavingCandidate
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


def test_tableau_initialize_returns_the_result_produced_by_the_strategy(mocker):
    x, s = var("x"), var("s", VarKind.SLACK)
    tableau = make_tableau((x, s), (s,), (0, 0), (TableauRow((Fraction(1), Fraction(1)), Fraction(-1), s),))
    expected_result = mocker.sentinel.initialization_result
    strategy = mocker.Mock()
    strategy.run.return_value = expected_result

    assert tableau.initialize(strategy) is expected_result


def test_balinski_gomory_initializer_configuration_is_immutable():
    strategy = BalinskiGomoryInitializer()

    with pytest.raises(FrozenInstanceError):
        strategy.entering_rule = lambda candidates: next(iter(candidates)).var


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

    initialization = tableau.initialize(strategy)
    steps = tuple(initialization)
    result = initialization.final_tableau

    assert initialization.status is InitializationStatus.FEASIBLE
    assert result.is_feasible_basis()
    assert tuple(result.basic_variables) == (x1, x2, s3)
    assert result.get_value_for_basic_var(s3) == Fraction(8)
    assert tuple((step.entering, step.leaving) for step in steps) == ((x1, s1), (x2, s2))
    assert all(step.violated_row_basic_var == s3 for step in steps)


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

    initialization = tableau.initialize(strategy)
    steps = tuple(initialization)
    result = initialization.final_tableau

    assert initialization.status is InitializationStatus.FEASIBLE
    assert result.is_feasible_basis()
    assert tuple(result.basic_variables) == (x, s1)
    assert result.get_value_for_basic_var(x) == Fraction(4)
    assert len(steps) == 1
    step = steps[0]
    assert step.pivot == Fraction(-1)


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

    initialization = tableau.initialize(strategy)
    steps = tuple(initialization)
    result = initialization.final_tableau

    assert result.get_value_for_basic_var(s2) == Fraction(0)
    assert len(steps) == 1


def test_initialization_steps_record_the_candidates_taken_from_the_violated_row():
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

    step = tuple(tableau.initialize(BalinskiGomoryInitializer()))[0]

    assert step.entering_candidates == (EnteringCandidate(x1, Fraction(-1)), EnteringCandidate(x2, Fraction(-1)))
    assert step.entering == x1
    assert step.leaving_candidates == (LeavingCandidate(s1, Fraction(1), Fraction(2)),)
    assert step.leaving == s1


def test_initialization_records_the_pivot_on_the_violated_row_itself_as_its_only_candidate():
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

    step = tuple(tableau.initialize(BalinskiGomoryInitializer()))[0]

    assert step.entering_candidates == (EnteringCandidate(x, Fraction(-1)),)
    assert step.leaving_candidates == (LeavingCandidate(s2, Fraction(-1), Fraction(-4)),)
    assert step.leaving == s2


def test_balinski_gomory_detects_an_infeasible_problem():
    x, s = var("x"), var("s", VarKind.SLACK)
    tableau = make_tableau((x, s), (s,), (0, 0), (TableauRow((Fraction(1), Fraction(1)), Fraction(-1), s),))
    strategy = BalinskiGomoryInitializer()

    initialization = tableau.initialize(strategy)

    assert initialization.status is InitializationStatus.INFEASIBLE
    assert tuple(initialization) == ()
    assert initialization.final_tableau is tableau
    assert initialization.termination_reason


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

    initialization = tableau.initialize(strategy)
    steps = tuple(initialization)
    result = initialization.final_tableau

    assert initialization.status is InitializationStatus.FEASIBLE
    assert result.is_feasible_basis()
    assert tuple(step.violated_row_basic_var for step in steps) == (s2, s1)
