from fractions import Fraction

from visualsimplex import (
    Constraint,
    ConstraintSense,
    Expression,
    LPProblem,
    Objective,
    OptimizationSense,
    Term,
    VarDomain,
    VarKind,
    Variable,
)


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
