from fractions import Fraction

import pytest

from visualsimplex import Constraint, ConstraintSense, Expression, LPProblem, Objective, OptimizationSense, Term, VarDomain, VarKind, Variable


def variable(symbol, domain=VarDomain.NON_NEGATIVE):
    return Variable(VarKind.ORIGINAL, symbol, domain)


def term(symbol, coeff=Fraction(1), domain=VarDomain.NON_NEGATIVE):
    return Term(variable(symbol, domain), coeff)


def test_lp_problem_string():
    problem = LPProblem(
        Objective(
            Expression((term("x2"), term("x1", Fraction(2)))),
            OptimizationSense.MAXIMIZE,
        ),
        (
            Constraint(
                Expression((term("x1"), term("x2"))),
                Fraction(5),
                ConstraintSense.LE,
            ),
            Constraint(
                Expression((term("x3", domain=VarDomain.FREE),)),
                Fraction(2),
                ConstraintSense.EQ,
            ),
        ),
    )

    assert str(problem) == (
        "maximize z = 2x1 + x2\n"
        "s.t.\n"
        "x1 + x2 <= 5\n"
        "x3 = 2\n"
        "x1, x2 >= 0\n"
        "x3 free"
    )


def test_lp_problem_is_in_inequality_form_only_when_all_constraints_are_inequalities():
    objective = Objective(Expression((term("x"),)), OptimizationSense.MAXIMIZE)
    inequality = Constraint(Expression((term("x"),)), Fraction(3), ConstraintSense.LE)
    equality = Constraint(Expression((term("x"),)), Fraction(3), ConstraintSense.EQ)

    assert LPProblem(objective, (inequality,)).is_in_inequality_form()
    assert not LPProblem(objective, (inequality, equality)).is_in_inequality_form()


def test_from_inequality_form_normalizes_sense_and_minimizes_objective():
    problem = LPProblem(
        Objective(Expression((term("x", Fraction(2)),)), OptimizationSense.MAXIMIZE),
        (
            Constraint(Expression((term("x"),)), Fraction(5), ConstraintSense.GE),
            Constraint(Expression((term("y"),)), Fraction(4), ConstraintSense.LE),
        ),
    )

    result = problem.from_inequality_form_to_standard_form()

    assert result.opt_sense() is OptimizationSense.MINIMIZE
    assert str(result) == (
        "minimize z = -2x\n"
        "s.t.\n"
        "-x + sl0 = -5\n"
        "y + sl1 = 4\n"
        "sl0, sl1, x, y >= 0"
    )


def test_from_inequality_form_rejects_equality_constraints():
    problem = LPProblem(
        Objective(Expression((term("x"),)), OptimizationSense.MINIMIZE),
        (Constraint(Expression((term("x"),)), Fraction(1), ConstraintSense.EQ),),
    )

    with pytest.raises(RuntimeError, match="not in inequality form"):
        problem.from_inequality_form_to_standard_form()


def test_lp_problem_rejects_same_symbol_with_different_kind_or_domain():
    problem_objective = Objective(
        Expression((term("x"),)), OptimizationSense.MINIMIZE
    )
    free_x_constraint = Constraint(
        Expression((term("x", domain=VarDomain.FREE),)),
        Fraction(1),
        ConstraintSense.LE,
    )

    with pytest.raises(ValueError, match="incompatible variables"):
        LPProblem(problem_objective, (free_x_constraint,))


def test_free_variables_are_split_before_inequality_conversion():
    problem = LPProblem(
        Objective(
            Expression((term("x", Fraction(2), VarDomain.FREE),)),
            OptimizationSense.MAXIMIZE,
        ),
        (
            Constraint(
                Expression((term("x", domain=VarDomain.FREE),)),
                Fraction(1),
                ConstraintSense.GE,
            ),
        ),
    )

    result = problem.from_inequality_form_to_standard_form()

    assert str(result) == (
        "minimize z = 2x_minus - 2x_plus\n"
        "s.t.\n"
        "x_minus - x_plus + sl0 = -1\n"
        "sl0, x_minus, x_plus >= 0"
    )
