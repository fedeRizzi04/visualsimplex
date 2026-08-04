from __future__ import annotations
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from itertools import chain

# variables, terms and expressions

class VarKind(Enum):
    ORIGINAL = "original"
    SLACK = "slack"
    SURPLUS = "surplus"


@dataclass(frozen=True)
class Variable:
    s: str

    def __post_init__(self):
        if self.s.strip() == "":
            raise ValueError("variable cannot be empty")
        object.__setattr__(self, "s", self.s.strip())


@dataclass(frozen=True)
class Term:
    coeff: Fraction
    var: Variable
    kind: VarKind

    def same_var(self, other: Term) -> bool:
        return self.var == other.var

    def __mul__(self, scalar: Fraction) -> Term:
        return Term(self.coeff * scalar, self.var, self.kind)

    def __rmul__(self, scalar : Fraction): # called when we have x * term and x does not support __mul__ with a term
        return self * scalar # calling __mul__


class Expression:
    def __init__(self, terms: Iterable[Term]):
        terms = tuple(terms)
        if not terms:
            raise ValueError("empty expression not allowed")
        if len({term.var for term in terms}) != len(terms):
            raise ValueError("an expression must have at most one term for a given Variable name")
        self._terms = terms

    def __iter__(self):
        return iter(self._terms)


# objective function

class OptimizationSense(Enum):
    MAXIMIZE = "max"
    MINIMIZE = "min"

    def swap(self) -> OptimizationSense:
        return OptimizationSense.MINIMIZE if self is OptimizationSense.MAXIMIZE else OptimizationSense.MAXIMIZE



@dataclass(frozen=True)
class Objective:
    expr: Expression
    opt_sense: OptimizationSense

    def swap_sense(self) -> Objective:
        terms = (term * -1 for term in self.expr)
        return Objective(Expression(terms), self.opt_sense.swap())


# constraints

class ConstraintSense(Enum):
    LE = "<="
    GE = ">="
    EQ = "="


@dataclass(frozen=True)
class Constraint:
    expr: Expression
    rhs: Fraction
    sense: ConstraintSense

    def is_in_inequality_form(self) -> bool:
        return self.sense in (ConstraintSense.LE, ConstraintSense.GE)

    def to_equality_form(self, var: Variable) -> Constraint:
        """Add a slack/surplus variable and return the equality constraint."""
        if not self.is_in_inequality_form():
            raise RuntimeError("the expression is already in equality form")
        
        var_kind = VarKind.SLACK if self.sense is ConstraintSense.LE else VarKind.SURPLUS
        coeff = Fraction(1) if var_kind is VarKind.SLACK else Fraction(-1)
        term = Term(coeff, var, var_kind)

        terms = chain(iter(self.expr), (term,))
        return Constraint(Expression(terms), self.rhs, ConstraintSense.EQ)
