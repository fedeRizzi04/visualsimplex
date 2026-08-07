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
    leaving_var : Variable
    pivot : Fraction
    rhs : Fraction

    @property
    def ratio(self) -> Fraction:
        return self.rhs / self.pivot


LeavingVariableRule = Callable[[Iterable[LeavingCandidate]], LeavingCandidate]

def minimum_ratio_rule(candidates : Iterable[LeavingCandidate]) -> LeavingCandidate:
    '''Choose the candidate with the minimum rhs/pivot ratio, keeping input order to break ties.'''
    try:
        return min(candidates, key=lambda candidate: candidate.ratio)
    except ValueError as e:
        raise ValueError('no eligible leaving candidates provided') from e
