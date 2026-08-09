from visualsimplex.value_objects import Variable
from fractions import Fraction
from dataclasses import dataclass
from typing import Callable, Iterable

# entering variable rules (from non basic to basic)

@dataclass(frozen=True)
class EnteringCandidate:
    var : Variable
    reduced_cost : Fraction

EnteringVariableRule = Callable[[Iterable[EnteringCandidate]], Variable]
'''Rule for choosing which candidate variable enters the basis according to its coefficient in a reference row. The reference row is the objective row during primal-simplex optimization or a violated-constraint row during initialization. The rule must return the variable of one of the provided candidates.'''

def bland_rule(candidates : Iterable[EnteringCandidate]) -> Variable: 
    '''Bland rule: the first candidate with negative reduced cost'''
    try: 
        return next(c.var for c in candidates if c.reduced_cost < Fraction(0))
    except StopIteration as e:
        raise ValueError('no candidates provided with negative reduced costs') from e

def dantzig_rule(candidates : Iterable[EnteringCandidate]) -> Variable:
    '''Dantzig rule: the candidate with the minimum reduced cost from ones with negative reduced cost'''
    try: 
        return min((c for c in candidates if c.reduced_cost < Fraction(0)), key=lambda c: c.reduced_cost).var
    except ValueError as e :
        raise ValueError('no candidates provided with negative reduced costs') from e

# leaving variable rules (from basic to non basic)

@dataclass(frozen=True)
class LeavingCandidate:
    var : Variable
    pivot : Fraction
    rhs : Fraction

    @property
    def ratio(self) -> Fraction:
        return self.rhs / self.pivot


LeavingVariableRule = Callable[[Iterable[LeavingCandidate]], LeavingCandidate]
'''Rule for choosing which basic variable leaves the basis for a fixed entering variable. Each candidate identifies an eligible pivot row through its basic variable and contains the pivot coefficient and the row right-hand side. The rule must return one of the provided candidates.'''

def minimum_ratio_rule(candidates : Iterable[LeavingCandidate]) -> LeavingCandidate:
    '''Choose the candidate with the minimum rhs/pivot ratio, keeping input order to break ties.'''
    try:
        return min(candidates, key=lambda candidate: candidate.ratio)
    except ValueError as e:
        raise ValueError('no eligible leaving candidates provided') from e

# violated constraint rules

@dataclass(frozen=True)
class ViolatedConstraintCandidate:
    basic_var : Variable # basic var of the violated constraint
    rhs : Fraction


ViolatedConstraintRule = Callable[[Iterable[ViolatedConstraintCandidate]], ViolatedConstraintCandidate]
'''Rule for choosing which violated constraint to repair next during initialization. Each candidate identifies a violated constraint row through its basic variable and contains its negative right-hand side. The rule must return one of the provided candidates.'''

def first_violated_constraint_rule(candidates : Iterable[ViolatedConstraintCandidate]) -> ViolatedConstraintCandidate:
    '''Choose the first violated constraint, preserving tableau row order.'''
    try:
        return next(candidate for candidate in candidates if candidate.rhs < 0)
    except StopIteration as e:
        raise ValueError('no violated constraint candidates provided') from e
