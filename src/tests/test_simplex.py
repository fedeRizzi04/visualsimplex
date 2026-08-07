from fractions import Fraction

import pytest

from visualsimplex import BalinskiGomoryInitializer, Constraint, ConstraintSense, Expression, LPProblem, Objective, OptimizationSense, PivotStep, SimplexAlgorithm, SimplexStatus, Term, VarKind, Variable
from visualsimplex.tableau import Tableau


def var(symbol, kind=VarKind.ORIGINAL):
    return Variable(kind, symbol)


def problem(objective_terms, constraints):
    return LPProblem(Objective(Expression(objective_terms), OptimizationSense.MINIMIZE), constraints)


def test_solve_inequality_form_rejects_a_problem_with_equality_constraints():
    x = var('x')
    equality_problem = problem((Term(x, Fraction(-1)),), (Constraint(Expression((Term(x, Fraction(1)),)), Fraction(4), ConstraintSense.EQ),))

    with pytest.raises(ValueError):
        SimplexAlgorithm().solve_inequality_form(equality_problem)


def test_simplex_algorithm_uses_the_configured_entering_and_leaving_rules():
    x1, x2 = var('x1'), var('x2')
    lp_problem = problem(
        (Term(x1, Fraction(-1)), Term(x2, Fraction(-2))),
        (Constraint(Expression((Term(x1, Fraction(1)), Term(x2, Fraction(1)))), Fraction(4), ConstraintSense.LE),),
    )
    choices = []

    def choose_first_entering(candidates):
        candidates = tuple(candidates)
        choices.append(candidates)
        return candidates[0].var

    def choose_first_leaving(candidates):
        candidates = tuple(candidates)
        choices.append(candidates)
        return candidates[0]

    report = SimplexAlgorithm(choose_first_entering, choose_first_leaving).solve_inequality_form(lp_problem)
    step = next(iter(report.optimization_steps))

    assert report.status is SimplexStatus.OPTIMAL
    assert step.entering == x1
    assert step.leaving.symbol == 'sl0'
    assert len(choices) == 4
    assert tuple(step.entering for step in report.optimization_steps) == (x1, x2)
    assert tuple(report.initialization_steps) == ()
    assert tuple(report.steps) == tuple(report.optimization_steps)


def test_simplex_report_contains_initialization_steps_before_optimization_steps():
    x = var('x')
    lp_problem = problem(
        (Term(x, Fraction(1)),),
        (
            Constraint(Expression((Term(x, Fraction(1)),)), Fraction(2), ConstraintSense.GE),
            Constraint(Expression((Term(x, Fraction(1)),)), Fraction(5), ConstraintSense.LE),
        ),
    )
    initializer = BalinskiGomoryInitializer()

    report = SimplexAlgorithm(initialization_strategy=initializer).solve_inequality_form(lp_problem)

    assert report.status is SimplexStatus.OPTIMAL
    assert len(tuple(report.initialization_steps)) == 1
    assert len(tuple(report.optimization_steps)) == 1
    assert tuple(report) == (*report.initialization_steps, *report.optimization_steps)
    assert all(isinstance(step, PivotStep) for step in report)
    assert report.final_tableau.is_optimal_basis()
    assert str(report.initial_tableau) in str(report)
    assert all(str(step) in str(report) for step in report)
    assert report.termination_reason in str(report)


def test_simplex_algorithm_reports_an_unbounded_problem():
    x = var('x')
    lp_problem = problem(
        (Term(x, Fraction(-1)),),
        (Constraint(Expression((Term(x, Fraction(-1)),)), Fraction(0), ConstraintSense.LE),),
    )

    report = SimplexAlgorithm().solve_inequality_form(lp_problem)

    assert report.status is SimplexStatus.UNBOUNDED
    assert tuple(report.steps) == ()
    assert report.final_tableau is report.initial_tableau
    assert not report.final_tableau.is_optimal_basis()


def test_simplex_algorithm_reports_an_infeasible_problem_and_uses_the_initial_tableau_when_no_pivots_were_performed():
    x = var('x')
    lp_problem = problem(
        (Term(x, Fraction(1)),),
        (Constraint(Expression((Term(x, Fraction(1)),)), Fraction(-1), ConstraintSense.LE),),
    )

    report = SimplexAlgorithm().solve_inequality_form(lp_problem)

    assert report.status is SimplexStatus.INFEASIBLE
    assert tuple(report.steps) == ()
    assert report.final_tableau is report.initial_tableau
    assert report.termination_reason


def test_perform_pivot_does_not_require_the_entering_variable_to_be_a_simplex_candidate():
    x = var('x')
    lp_problem = problem(
        (Term(x, Fraction(1)),),
        (Constraint(Expression((Term(x, Fraction(1)),)), Fraction(4), ConstraintSense.LE),),
    )
    tableau = Tableau(lp_problem.from_inequality_form_to_canonical_form())
    leaving = next(iter(tableau.basic_variables))

    step = SimplexAlgorithm().perform_pivot(tableau, x, leaving)

    assert step.entering == x
    assert step.leaving == leaving
    assert step.pivot == Fraction(1)
    assert step.after.is_basic_variable(x)
    assert not tableau.is_basic_variable(x)
    assert all(value in str(step) for value in (str(step.entering), str(step.leaving), str(step.pivot)))
