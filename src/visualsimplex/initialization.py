from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from visualsimplex.rules import EnteringCandidate, EnteringVariableRule, LeavingCandidate, LeavingVariableRule, ViolatedConstraintCandidate, ViolatedConstraintRule, bland_rule, first_violated_constraint_rule, minimum_ratio_rule
from visualsimplex.steps import PivotStep
from visualsimplex.tableau import Tableau
from visualsimplex.value_objects import Variable


class InitializationStatus(Enum):
    FEASIBLE = 'feasible'
    INFEASIBLE = 'infeasible'


@dataclass(frozen=True)
class InitializationPivotStep(PivotStep):
    violated_row_basic_var : Variable # basic variable used to identify the violated row being repaired

    @property
    def description(self) -> str:
        return 'initialization pivot step'


@dataclass(frozen=True)
class InitializationResult:
    '''Result of an initialization strategy, including every pivot and its mathematical outcome.'''

    initial_tableau : Tableau
    steps : tuple[InitializationPivotStep, ...]
    status : InitializationStatus
    termination_reason : str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'steps', tuple(self.steps))

    @property
    def final_tableau(self) -> Tableau:
        return self.steps[-1].after if self.steps else self.initial_tableau

    def __iter__(self) -> Iterator[InitializationPivotStep]:
        return iter(self.steps)


class InitializationStrategy(ABC):
    '''Strategy that returns its pivot steps together with the resulting initialization status.'''

    def run(self, tableau : Tableau) -> InitializationResult:
        '''Validate and execute the initialization strategy.'''
        if tableau.is_feasible_basis():
            raise ValueError('cannot initialize a tableau whose basis is already feasible')
        return self.initialize(tableau)

    @abstractmethod
    def initialize(self, tableau : Tableau) -> InitializationResult:
        pass


@dataclass(frozen=True)
class BalinskiGomoryInitializer(InitializationStrategy):
    violated_constraint_rule : ViolatedConstraintRule = first_violated_constraint_rule
    entering_rule : EnteringVariableRule = bland_rule
    leaving_rule : LeavingVariableRule = minimum_ratio_rule

    def initialize(self, tableau : Tableau) -> InitializationResult:
        current = tableau
        steps : list[InitializationPivotStep] = []
        while not current.is_feasible_basis():
            violated_constraint = self._choose_violated_constraint(current) # ValueError cannot be raised because the basis is not feasible, so there is at least one violated constraint
            repaired = self._repair_constraint(current, violated_constraint.basic_var, steps)
            if repaired is None:
                reason = f'constraint associated with {violated_constraint.basic_var} remains violated after its infeasibility has been minimized'
                return InitializationResult(tableau, steps, InitializationStatus.INFEASIBLE, reason)
            current = repaired
        return InitializationResult(tableau, steps, InitializationStatus.FEASIBLE, 'a feasible basis has been reached')

    def _choose_violated_constraint(self, tableau : Tableau) -> ViolatedConstraintCandidate:
        '''given a tableau, this method returns the violated constraint to work on minimizing the violation'''
        candidates = tuple(ViolatedConstraintCandidate(row.basic_var, row.rhs) for row in tableau.rows if row.rhs < 0)
        return self.violated_constraint_rule(candidates)

    def _repair_constraint(self, tableau : Tableau, violated_row_basic_var : Variable, steps : list[InitializationPivotStep]) -> Tableau | None:
        current = tableau
        while current.get_value_for_basic_var(violated_row_basic_var) < 0:
            violated_row = next(row for row in current.rows if row.basic_var == violated_row_basic_var)
            entering_candidates = self._entering_candidates(current, violated_row.coefficients)
            if not entering_candidates:
                return None
            entering = self.entering_rule(entering_candidates)
            entering_index = current.get_var_index(entering)
            leaving_candidates = self._leaving_candidates(current, entering_index, violated_row_basic_var)
            if leaving_candidates:
                leaving = self.leaving_rule(leaving_candidates)
            else: # no leaving candidates, then the last possibility is to pivot on the same row
                leaving = LeavingCandidate(violated_row_basic_var, violated_row.coefficients[entering_index], violated_row.rhs)
                leaving_candidates = (leaving,)
            after = current.pivot(entering, leaving.var)
            steps.append(InitializationPivotStep(current, entering_candidates, entering, leaving_candidates, leaving.var, leaving.pivot, after, violated_row_basic_var))
            current = after
            if leaving.var == violated_row_basic_var: # pivot on the same row
                break
        return current

    def _entering_candidates(self, tableau : Tableau, coefficients : tuple[Fraction]) -> tuple[EnteringCandidate, ...]:
        '''Return the candidates the entering rule chooses among: the variables whose coefficient in the violated row is negative.'''
        return tuple(EnteringCandidate(var, coefficient) for var, coefficient in zip(tableau.variables, coefficients) if coefficient < 0)

    def _leaving_candidates(self, tableau : Tableau, entering_index : int, violated_row_basic_var : Variable) -> tuple[LeavingCandidate, ...]:
        '''Return the candidates the leaving rule chooses among: the feasible rows other than the violated one admitting a positive pivot.'''
        return tuple(LeavingCandidate(row.basic_var, row.coefficients[entering_index], row.rhs)
                     for row in tableau.rows if row.basic_var != violated_row_basic_var and row.rhs >= 0 and row.coefficients[entering_index] > 0)
