import pytest
from simplexlab.expressions import VarName

def test_empty_varname():
    with pytest.raises(ValueError):
        VarName('')