from dataclasses import dataclass, field
from fractions import Fraction

@dataclass(frozen=True)
class VarName:
    s : str 
    def __post_init__(self):
        if self.s.strip() == '': 
            raise ValueError('variable cannot be empty')


@dataclass(frozen=True)
class Variable:
    _coeff : Fraction
    _var : VarName


@dataclass(frozen=True)
class Expression:
    _vars : frozenset[Variable] = field(default_factory=frozenset)

    def __post_init__(self):
        if len(self._vars) == 0:
            raise ValueError('empty expression not allowed')

    def __iter__(self):
        return iter(self._vars)