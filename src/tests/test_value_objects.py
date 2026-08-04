from fractions import Fraction

import pytest

from visualsimplex import (
    Constraint,
    ConstraintSense,
    Expression,
    Objective,
    OptimizationSense,
    Term,
    VarKind,
    Variable,
)


def term(name: str, coeff: Fraction = Fraction(1), kind: VarKind = VarKind.ORIGINAL):
    return Term(coeff, Variable(name), kind)


def test_variable_rejects_empty_and_whitespace_only_names():
    with pytest.raises(ValueError):
        Variable("")
    with pytest.raises(ValueError):
        Variable(" \t\n")


def test_expression_requires_terms_and_rejects_duplicate_variables():
    with pytest.raises(ValueError, match="empty expression"):
        Expression(())

    with pytest.raises(ValueError, match="at most one term"):
        Expression((term("x"), term("x", Fraction(2))))


def test_expression_preserves_term_order_and_is_iterable():
    terms = (term("x", Fraction(1, 2)), term("y", Fraction(-3)))

    expression = Expression(terms)

    assert tuple(expression) == terms


def test_term_multiplication_preserves_variable_and_kind():
    original = term("x", Fraction(2, 3), VarKind.SLACK)

    result = original * Fraction(-3, 2)

    assert result == Term(Fraction(-1), original.var, VarKind.SLACK)


@pytest.mark.parametrize(
    ("sense", "swapped"),
    [
        (OptimizationSense.MAXIMIZE, OptimizationSense.MINIMIZE),
        (OptimizationSense.MINIMIZE, OptimizationSense.MAXIMIZE),
    ],
)
def test_objective_swap_sense_negates_terms(sense, swapped):
    objective = Objective(
        Expression((term("x", Fraction(2)), term("y", Fraction(-1)))), sense
    )

    result = objective.swap_sense()

    assert result.opt_sense is swapped
    assert tuple(result.expr) == (
        term("x", Fraction(-2)),
        term("y", Fraction(1)),
    )


@pytest.mark.parametrize(
    ("sense", "kind", "coeff"),
    [
        (ConstraintSense.LE, VarKind.SLACK, Fraction(1)),
        (ConstraintSense.GE, VarKind.SURPLUS, Fraction(-1)),
    ],
)
def test_inequality_is_converted_to_equality_with_expected_variable_kind_and_coefficient(
    sense, kind, coeff
):
    constraint = Constraint(Expression((term("x"),)), Fraction(5), sense)

    result = constraint.to_equality_form(Variable("s"))

    assert result.sense is ConstraintSense.EQ
    assert result.rhs == Fraction(5)
    assert tuple(result.expr) == (
        term("x"),
        term("s", coeff=coeff, kind=kind),
    )


def test_equality_cannot_be_converted_again_and_duplicate_added_variable_is_rejected():
    equality = Constraint(
        Expression((term("x"),)), Fraction(5), ConstraintSense.EQ
    )
    with pytest.raises(RuntimeError, match="already in equality"):
        equality.to_equality_form(Variable("s"))

    inequality = Constraint(
        Expression((term("x"),)), Fraction(5), ConstraintSense.LE
    )
    with pytest.raises(ValueError, match="at most one term"):
        inequality.to_equality_form(Variable("x"))


def test_scalar_multiplication_is_symmetric():
    original = term("x", Fraction(2, 3), VarKind.SLACK)

    assert Fraction(-3, 2) * original == original * Fraction(-3, 2)