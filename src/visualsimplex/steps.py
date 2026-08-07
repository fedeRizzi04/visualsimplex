from abc import ABC, abstractmethod
from dataclasses import dataclass
from fractions import Fraction

from visualsimplex.tableau import Tableau
from visualsimplex.value_objects import Variable


@dataclass(frozen=True)
class PivotStep(ABC):
    '''Common description of a pivot and of the tableau transformation it produces.'''

    before : Tableau
    entering : Variable
    leaving : Variable
    pivot : Fraction
    after : Tableau

    @property
    @abstractmethod
    def description(self) -> str:
        '''Returns a description of the pivot step'''

    def __str__(self) -> str:
        return f'{self.description}: {self.entering} enters the basis, {self.leaving} leaves the basis. The pivot value is: {self.pivot}'
