from abc import ABC, abstractmethod
from dataclasses import dataclass
from fractions import Fraction
from visualsimplex.rules import EnteringCandidate, LeavingCandidate
from visualsimplex.tableau import Tableau
from visualsimplex.value_objects import Variable


@dataclass(frozen=True)
class PivotStep(ABC):
    '''Common description of a pivot and of the tableau transformation it produces.

    Each selection is recorded together with the candidates it was chosen among, so that a client can present which
    pivots were eligible and not only which one was performed. Both candidate tuples are empty when the pivot was
    performed directly rather than chosen by the selection rules.
    '''

    before : Tableau
    entering_candidates : tuple[EnteringCandidate, ...]
    entering : Variable
    leaving_candidates : tuple[LeavingCandidate, ...]
    leaving : Variable
    pivot : Fraction
    after : Tableau

    @property
    @abstractmethod
    def description(self) -> str:
        '''Returns a description of the pivot step'''

    def __str__(self) -> str:
        return f'{self.description}: {self.entering} enters the basis, {self.leaving} leaves the basis. The pivot value is: {self.pivot}'
