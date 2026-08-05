from __future__ import annotations
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from itertools import chain

# variables, terms and expressions

class ComparableEnum(Enum):
    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f'{type(self)} instances cannot be compared (<) with {type(other)} instances')
        return self.value < other.value

class VarKind(ComparableEnum):
    ORIGINAL = (0, 'original')
    SLACK = (1, 'slack')
    SURPLUS = (2, 'surplus')

class VarDomain(ComparableEnum):
    NON_NEGATIVE = (0, 'non negative')
    FREE = (1, 'free')

    def __str__(self):
        return ">= 0" if self is VarDomain.NON_NEGATIVE else "free"


@dataclass(frozen=True, order=True)
class Variable:
    kind: VarKind # first the kind because in the tableau and in expressions I want slack and surplus variables to be on the tail
    symbol: str
    domain: VarDomain = VarDomain.NON_NEGATIVE

    def __post_init__(self):
        if self.symbol.strip() == "":
            raise ValueError("variable cannot be empty")
        object.__setattr__(self, "symbol", self.symbol.strip())

    def __str__(self):
        return self.symbol

    def is_compatible_with(self, other: Variable) -> bool:
        """Return whether two variables with the same symbol have matching metadata."""
        return self.symbol != other.symbol or (
            self.kind is other.kind and self.domain is other.domain)

    def to_non_negative(self) -> tuple[Variable, ...]:
        if self.domain is VarDomain.NON_NEGATIVE:
            return (self,)
        return (Variable(self.kind, f"{self.symbol}_plus"), Variable(self.kind, f"{self.symbol}_minus"))


@dataclass(frozen=True, order=True)
class Term:
    var: Variable
    coeff: Fraction

    def __mul__(self, scalar) -> Term:
        return Term(self.var, self.coeff * scalar)

    def __rmul__(self, scalar): # called when we have x * term and x does not support __mul__ with a term
        return self * scalar # calling __mul__

    def __str__(self):
        coefficient = abs(self.coeff)
        factor = "" if coefficient == 1 else str(coefficient)
        sign = "-" if self.coeff < 0 else ""
        return f"{sign}{factor}{self.var}"

    def unsigned_str(self) -> str:
        return str(Term(self.var, abs(self.coeff)))

    def to_non_negative(self) -> tuple[Term, ...]:
        variables = self.var.to_non_negative()
        if len(variables) == 1:
            return (self,)
        # c * x = c * (x^+  -   x^-) = c * x^+ - c * x^-
        return (Term(variables[0], self.coeff), Term(variables[1], -self.coeff))  # need to flatten (or chaining)


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

    def __mul__(self, scalar):
        terms = (t * scalar for t in self._terms)
        return Expression(terms)

    def __rmul__(self, scalar):
        return self * scalar

    def to_non_negative(self) -> Expression:
        terms = chain.from_iterable(term.to_non_negative() for term in self._terms) # tuple of tuples chained to have one iterable
        return Expression(terms)

    def __str__(self):
        first, *rest = self._terms
        return str(first) + "".join(
            f" {'-' if term.coeff < 0 else '+'} {term.unsigned_str()}"
            for term in rest
        )


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
        return Objective(self.expr * -1, self.opt_sense.swap())

    def __str__(self):
        return f"{self.opt_sense.name.lower()} z = {self.expr}"


# constraints

class ConstraintSense(Enum):
    LE = "<="
    GE = ">="
    EQ = "="

    def is_equality(self):
        return self is ConstraintSense.EQ

    def opposite(self):
        if self.is_equality():
            return self
        return ConstraintSense.LE if self is ConstraintSense.GE else ConstraintSense.GE


@dataclass(frozen=True)
class Constraint:
    expr: Expression
    rhs: Fraction
    sense: ConstraintSense

    def is_in_inequality_form(self) -> bool:
        return self.sense in (ConstraintSense.LE, ConstraintSense.GE)

    def to_equality_form(self, symbol) -> Constraint:
        """Add a slack/surplus variable and return the equality constraint."""
        if not self.is_in_inequality_form():
            raise RuntimeError("the expression is already in equality form")
        
        var_kind = VarKind.SLACK if self.sense is ConstraintSense.LE else VarKind.SURPLUS
        coeff = Fraction(1) if var_kind is VarKind.SLACK else Fraction(-1)
        term = Term(Variable(var_kind, symbol), coeff)

        terms = chain(iter(self.expr), (term,))
        return Constraint(Expression(terms), self.rhs, ConstraintSense.EQ)

    def change_sense(self) -> Constraint:
        if self.sense.is_equality():
            return self
        new_expr = self.expr * -1
        return Constraint(new_expr, self.rhs * -1, self.sense.opposite())

    def __str__(self):
        return f"{self.expr} {self.sense.value} {self.rhs}"
