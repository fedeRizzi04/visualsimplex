import pytest
from fractions import Fraction
from visualsimplex.expressions import VarName, Expression, Variable

def test_empty_varname():
    with pytest.raises(ValueError):
        VarName('')

def test_empty_expression():
    with pytest.raises(ValueError):
        Expression()

def test_ok_expression():
    s = frozenset([Variable(Fraction(1,1), VarName('x')), Variable(Fraction(2, 3), VarName('y'))])
    e = Expression(s)
    assert e.vars == s

def test_expression_returns_iterator():
    variables = frozenset({
        Variable(Fraction(1, 1), VarName("x")),
    })

    expression = Expression(variables)
    iterator = iter(expression)

    assert list(iterator) == list(variables)
