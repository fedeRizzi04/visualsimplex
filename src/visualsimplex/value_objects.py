from __future__ import annotations
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from fractions import Fraction
from itertools import chain

# variables, terms and expressions

class ComparableEnum(Enum):
    def __lt__(self, other):
        return self.value < other.value

class VarKind(ComparableEnum):
    ORIGINAL = (0, 'original')
    SLACK = (1, 'slack')
    SURPLUS = (2, 'surplus')

class VarDomain(ComparableEnum):
    NON_NEGATIVE = (0, 'non negative')
    FREE = (1, 'free')


@dataclass(frozen=True, order=True)
class Variable:
    kind: VarKind # first the kind because in the tableau and in expressions I want slack and surplus variables to be on the tail
    symbol: str
    domain: VarDomain = VarDomain.NON_NEGATIVE

    def __post_init__(self):
        if self.symbol.strip() == "":
            raise ValueError("variable cannot be empty")
        object.__setattr__(self, "symbol", self.symbol.strip())


@dataclass(frozen=True, order=True)
class Term:
    var: Variable
    coeff: Fraction

    def __mul__(self, scalar: Fraction) -> Term:
        return Term(self.var, self.coeff * scalar)

    def __rmul__(self, scalar : Fraction): # called when we have x * term and x does not support __mul__ with a term
        return self * scalar # calling __mul__


class Expression:
    def __init__(self, terms: Iterable[Term]):
        terms = sorted(tuple(terms))
        if not terms:
            raise ValueError("empty expression not allowed")
        if len({term.var.symbol for term in terms}) != len(terms):
            raise ValueError("an expression must have at most one term for a given Variable name")
        self._terms = terms

    def __iter__(self) -> Iterator[Term]:
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
        term = Term(Variable(var_kind, var.symbol), coeff)

        terms = chain(iter(self.expr), (term,))
        return Constraint(Expression(terms), self.rhs, ConstraintSense.EQ)
