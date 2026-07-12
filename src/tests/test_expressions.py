import pytest
from fractions import Fraction
from simplexlab.expressions import VarName, Expression, Variable

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