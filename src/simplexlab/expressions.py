from dataclasses import dataclass
from fractions import Fraction

@dataclass(frozen=True)
class VarName:
    s : str 
    def __post_init__(self):
        if self.s.strip() == '': 
            raise ValueError('variable cannot be empty')


@dataclass(frozen=True)
class Variable:
    coeff : Fraction
    var : VarName 
