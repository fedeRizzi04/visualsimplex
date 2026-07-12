import pytest
from simplexlab.expressions import VarName, Expression

def test_empty_varname():
    with pytest.raises(ValueError):
        VarName('')

def test_empty_expression():
    with pytest.raises(ValueError):
        Expression()

def test_ok_expression():
    s = frozenset([VarName('x'), VarName('y')])
    e = Expression(s)
    assert e.vars == s