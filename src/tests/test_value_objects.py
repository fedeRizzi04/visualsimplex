from fractions import Fraction

import pytest

from visualsimplex import Constraint, ConstraintSense, Expression, Objective, OptimizationSense, Term, VarDomain, VarKind, Variable


def term(name: str, coeff: Fraction = Fraction(1), kind: VarKind = VarKind.ORIGINAL):
    return Term(Variable(kind, name), coeff) 
    

def test_variable_rejects_empty_and_whitespace_only_names():
    with pytest.raises(ValueError):
        Variable(VarKind.ORIGINAL, "")
    with pytest.raises(ValueError):
        Variable(VarKind.ORIGINAL, " \t\n")


def test_variables_are_ordered_by_kind_then_symbol():
    variables = (
        Variable(VarKind.ORIGINAL, "x2"),
        Variable(VarKind.SLACK, "s1"),
        Variable(VarKind.ORIGINAL, "z"),
        Variable(VarKind.ORIGINAL, "x1"),
    )

    assert sorted(variables) == [
        Variable(VarKind.ORIGINAL, "x1"),
        Variable(VarKind.ORIGINAL, "x2"),
        Variable(VarKind.ORIGINAL, "z"),
        Variable(VarKind.SLACK, "s1"),
    ]


def test_variables_with_same_symbol_are_compatible_only_with_same_metadata():
    original = Variable(VarKind.ORIGINAL, "x")
    same = Variable(VarKind.ORIGINAL, "x")
    free = Variable(VarKind.ORIGINAL, "x", VarDomain.FREE)
    slack = Variable(VarKind.SLACK, "x")

    assert original.is_compatible_with(same)
    assert not original.is_compatible_with(free)
    assert not original.is_compatible_with(slack)
    assert original.is_compatible_with(Variable(VarKind.SLACK, "y"))


def test_terms_are_ordered_by_their_variables():
    expression = Expression(
        (
            term("x2", Fraction(2)),
            term("s1", Fraction(3), VarKind.SLACK),
            term("z", Fraction(4)),
            term("x1", Fraction(1)),
        )
    )

    ordered = Expression(sorted(expression))

    assert tuple(ordered) == (
        term("x1", Fraction(1)),
        term("x2", Fraction(2)),
        term("z", Fraction(4)),
        term("s1", Fraction(3), VarKind.SLACK),
    )


def test_zero_expression():
    e = Expression([])
    assert str(e) == '0'



def test_expression_preserves_term_order_and_is_iterable():
    terms = (term("x", Fraction(1, 2)), term("y", Fraction(-3)))

    expression = Expression(terms)

    assert tuple(expression) == terms


def test_expression_scalar_multiplication_scales_all_terms():
    expression = Expression((term("x", Fraction(2)), term("y", Fraction(-3))))

    assert tuple(expression * Fraction(-2)) == (
        term("x", Fraction(-4)),
        term("y", Fraction(6)),
    )
    assert tuple(Fraction(3) * expression) == (
        term("x", Fraction(6)),
        term("y", Fraction(-9)),
    )


def test_expression_coefficient_lookup_returns_a_fraction_and_zero_when_absent():
    x = Variable(VarKind.ORIGINAL, "x")
    expression = Expression((Term(x, Fraction(3, 2)),))

    assert expression.coefficient_of(x) == Fraction(3, 2)
    assert expression.coefficient_of(Variable(VarKind.ORIGINAL, "y")) == Fraction(0)


def test_free_term_is_replaced_by_positive_and_negative_non_negative_terms():
    free = Term(Variable(VarKind.ORIGINAL, "x", VarDomain.FREE), Fraction(3))

    assert tuple(free.to_non_negative()) == (
        Term(Variable(VarKind.ORIGINAL, "x_plus"), Fraction(3)),
        Term(Variable(VarKind.ORIGINAL, "x_minus"), Fraction(-3)),
    )


def test_non_negative_variable_is_left_unchanged_by_conversion():
    variable = Variable(VarKind.ORIGINAL, "x")

    assert variable.to_non_negative() == (variable,)


def test_term_multiplication_preserves_variable_and_kind():
    original = term("x", Fraction(2, 3), VarKind.SLACK)

    result = original * Fraction(-3, 2)

    assert result == Term(original.var, Fraction(-1))


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

    result = constraint.to_equality_form("s")

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
        equality.to_equality_form("s")

    inequality = Constraint(
        Expression((term("x"),)), Fraction(5), ConstraintSense.LE
    )
    with pytest.raises(ValueError, match="at most one term"):
        inequality.to_equality_form("x")


def test_scalar_multiplication_is_symmetric():
    original = term("x", Fraction(2, 3), VarKind.SLACK)

    assert Fraction(-3, 2) * original == original * Fraction(-3, 2)


@pytest.mark.parametrize(
    ("sense", "opposite"),
    [
        (ConstraintSense.LE, ConstraintSense.GE),
        (ConstraintSense.GE, ConstraintSense.LE),
        (ConstraintSense.EQ, ConstraintSense.EQ),
    ],
)
def test_constraint_sense_opposite(sense, opposite):
    assert sense.opposite() is opposite


def test_change_sense_negates_expression_and_rhs():
    constraint = Constraint(
        Expression((term("x", Fraction(2)),)), Fraction(5), ConstraintSense.GE
    )

    result = constraint.change_sense()

    assert result.sense is ConstraintSense.LE
    assert result.rhs == Fraction(-5)
    assert tuple(result.expr) == (term("x", Fraction(-2)),)


def test_change_sense_leaves_equality_unchanged():
    constraint = Constraint(
        Expression((term("x"),)), Fraction(5), ConstraintSense.EQ
    )

    assert constraint.change_sense() is constraint
