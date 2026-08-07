from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Iterable
from visualsimplex.rules import EnteringCandidate, EnteringVariableRule, LeavingCandidate, LeavingVariableRule, ViolatedConstraintCandidate, ViolatedConstraintRule, bland_rule, first_violated_constraint_rule, minimum_ratio_rule
from visualsimplex.steps import PivotStep
from visualsimplex.tableau import Tableau
from visualsimplex.value_objects import Variable


class InfeasibleProblemError(ValueError):
    '''Raised when initialization proves that the original problem is infeasible.'''


class InitializationPivotKind(Enum):
    AUXILIARY_OPTIMIZATION = 'auxiliary optimization'
    FEASIBILITY_REPAIR = 'feasibility repair' # no elegible pivots, so pivoting on negative element of the current optimizing violated constraint 


@dataclass(frozen=True)
class InitializationPivotStep(PivotStep):
    violated_row_basic_var : Variable # basic variable used to identify the violated row being repaired
    kind : InitializationPivotKind # reason why this pivot is performed

    @property
    def description(self) -> str:
        return self.kind.value


class InitializationStrategy(ABC):
    def __init__(self):
        self._steps : list[InitializationPivotStep] = []

    @property
    def steps(self) -> Iterable[InitializationPivotStep]:
        return iter(self._steps)

    def run(self, tableau : Tableau) -> Tableau:
        if tableau.is_feasible_basis():
            raise ValueError('cannot initialize a tableau whose basis is already feasible')
        self._steps.clear()
        return self.initialize(tableau)

    @abstractmethod
    def initialize(self, tableau : Tableau) -> Tableau:
        pass


class BalinskiGomoryInitializer(InitializationStrategy):
    def __init__(self, violated_constraint_rule : ViolatedConstraintRule = first_violated_constraint_rule, entering_rule : EnteringVariableRule = bland_rule, leaving_rule : LeavingVariableRule = minimum_ratio_rule):
        super().__init__()
        self._violated_constraint_rule = violated_constraint_rule
        self._entering_rule = entering_rule
        self._leaving_rule = leaving_rule

    def initialize(self, tableau : Tableau) -> Tableau:
        current = tableau
        while not current.is_feasible_basis():
            violated_constraint = self._choose_violated_constraint(current) # ValueError cannot be raised because the basis is not feasible, so there is at least one violated constraint
            current = self._repair_constraint(current, violated_constraint.basic_var)
        return current

    def _choose_violated_constraint(self, tableau : Tableau) -> ViolatedConstraintCandidate:
        '''given a tableau, this method returns the violated constraint to work on minimizing the violation'''
        candidates = tuple(ViolatedConstraintCandidate(row.basic_var, row.rhs) for row in tableau.rows if row.rhs < 0)
        selected = self._violated_constraint_rule(candidates)
        return selected

    def _repair_constraint(self, tableau : Tableau, violated_row_basic_var : Variable) -> Tableau:
        current = tableau
        while current.get_value_for_basic_var(violated_row_basic_var) < 0:
            violated_row = next(row for row in current.rows if row.basic_var == violated_row_basic_var)
            entering = self._choose_entering_variable(current, violated_row.coefficients, violated_row_basic_var)
            entering_index = current.get_var_index(entering)
            candidates = tuple(LeavingCandidate(row.basic_var, row.coefficients[entering_index], row.rhs) for row in current.rows if row.basic_var != violated_row_basic_var and row.rhs >= 0 and row.coefficients[entering_index] > 0)
            if candidates:
                leaving = self._leaving_rule(candidates)
                if leaving not in candidates:
                    raise ValueError('the leaving-variable rule returned a candidate that is not eligible')
                kind = InitializationPivotKind.AUXILIARY_OPTIMIZATION
            else:
                leaving = LeavingCandidate(violated_row_basic_var, violated_row.coefficients[entering_index], violated_row.rhs)
                kind = InitializationPivotKind.FEASIBILITY_REPAIR
            after = current.pivot(entering, leaving.leaving_var)
            self._steps.append(InitializationPivotStep(current, entering, leaving.leaving_var, leaving.pivot, after, violated_row_basic_var, kind))
            current = after
            if kind is InitializationPivotKind.FEASIBILITY_REPAIR:
                break
        return current

    def _choose_entering_variable(self, tableau : Tableau, coefficients : tuple[Fraction], violated_row_basic_var : Variable) -> Variable:
        '''given a row of coefficients, this method returns the entering variable selected from the entering rule of this instance'''
        candidates = tuple(EnteringCandidate(var, coefficient) for var, coefficient in zip(tableau.variables, coefficients) if coefficient < 0)
        if not candidates:
            raise InfeasibleProblemError(f'constraint associated with {violated_row_basic_var} remains violated after its infeasibility has been minimized')
        entering = self._entering_rule(candidates)
        return entering
