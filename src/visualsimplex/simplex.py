from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from itertools import chain
from visualsimplex.initialization import BalinskiGomoryInitializer, InitializationPivotStep, InitializationStatus, InitializationStrategy
from visualsimplex.lp_problem import CanonicalFormLPProblem, LPProblem
from visualsimplex.rules import EnteringCandidate, EnteringVariableRule, LeavingCandidate, LeavingVariableRule, bland_rule, minimum_ratio_rule
from visualsimplex.steps import PivotStep
from visualsimplex.tableau import Tableau
from visualsimplex.value_objects import Variable


class SimplexStatus(Enum):
    '''Mathematical outcome reached by a complete simplex execution.'''

    OPTIMAL = 'optimal'
    UNBOUNDED = 'unbounded'
    INFEASIBLE = 'infeasible'


class SimplexPivotStep(PivotStep):
    '''Description of one pivot performed during primal-simplex optimization.'''

    @property
    def description(self) -> str:
        return 'primal-simplex pivot step'


@dataclass(frozen=True)
class SimplexReport:
    '''Structured report of initialization, optimization and the final mathematical outcome.

    Iterating over the report yields initialization pivot steps followed by primal-simplex pivot steps, preserving
    their execution order. The two phases remain separately available for clients that present them differently.
    '''

    original_problem : LPProblem
    canonical_problem : CanonicalFormLPProblem
    initial_tableau : Tableau
    initialization_steps : tuple[InitializationPivotStep, ...]
    optimization_steps : tuple[SimplexPivotStep, ...]
    status : SimplexStatus
    termination_reason : str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'initialization_steps', tuple(self.initialization_steps))
        object.__setattr__(self, 'optimization_steps', tuple(self.optimization_steps))

    @property
    def steps(self) -> Iterator[PivotStep]:
        return chain(self.initialization_steps, self.optimization_steps)

    @property
    def final_tableau(self) -> Tableau:
        if self.optimization_steps:
            return self.optimization_steps[-1].after
        if self.initialization_steps:
            return self.initialization_steps[-1].after
        return self.initial_tableau

    def __iter__(self) -> Iterator[PivotStep]:
        return self.steps

    def __str__(self) -> str:
        lines = ['Initial tableau:', str(self.initial_tableau)]
        for index, step in enumerate(self, start=1):
            lines.extend(('', f'Step {index}: {step}', str(step.after)))
        lines.extend(('', f'Status: {self.status.value}', self.termination_reason))
        return '\n'.join(lines)


class SimplexAlgorithm:
    '''Run simplex automatically with configurable rules while keeping direct pivot execution permissive.'''

    def __init__(self, entering_rule : EnteringVariableRule = bland_rule, leaving_rule : LeavingVariableRule = minimum_ratio_rule, initialization_strategy : InitializationStrategy | None = None):
        self._entering_rule = entering_rule
        self._leaving_rule = leaving_rule
        self._initialization_strategy = initialization_strategy if initialization_strategy is not None else BalinskiGomoryInitializer(entering_rule=self._entering_rule, leaving_rule=self._leaving_rule)

    def solve_inequality_form(self, problem : LPProblem) -> SimplexReport:
        '''Solve an LP problem whose constraints are all inequalities and report every performed pivot.'''
        if not problem.is_in_inequality_form():
            raise ValueError('solve_inequality_form requires every constraint to be an inequality')

        canonical_problem = problem.from_inequality_form_to_canonical_form()
        initial_tableau = Tableau(canonical_problem)
        current = initial_tableau
        initialization_steps : tuple[InitializationPivotStep, ...] = ()

        if not current.is_feasible_basis():
            initialization = current.initialize(self._initialization_strategy)
            initialization_steps = initialization.steps
            if initialization.status is InitializationStatus.INFEASIBLE:
                return SimplexReport(problem, canonical_problem, initial_tableau, initialization_steps, (), SimplexStatus.INFEASIBLE, initialization.termination_reason)
            current = initialization.final_tableau

        optimization_steps : list[SimplexPivotStep] = []
        while not current.is_optimal_basis():
            if current.is_unbounded_problem():
                return SimplexReport(problem, canonical_problem, initial_tableau, initialization_steps, optimization_steps, SimplexStatus.UNBOUNDED, 'an improving variable has no eligible leaving variable')
            entering_candidates = current.entering_candidates()
            entering = current.entering_variable(self._entering_rule)
            leaving_candidates = current.leaving_candidates(entering)
            leaving = current.leaving_variable(entering, self._leaving_rule)
            step = self.perform_pivot(current, entering, leaving.var, entering_candidates=entering_candidates, leaving_candidates=leaving_candidates)
            optimization_steps.append(step)
            current = step.after

        return SimplexReport(problem, canonical_problem, initial_tableau, initialization_steps, optimization_steps, SimplexStatus.OPTIMAL, 'an optimal feasible basis has been reached')

    def perform_pivot(self, tableau : Tableau, entering : Variable, leaving : Variable, *, entering_candidates : tuple[EnteringCandidate, ...] = (), leaving_candidates : tuple[LeavingCandidate, ...] = ()) -> SimplexPivotStep:
        '''Perform and describe any algebraically valid pivot without requiring the selection rules to choose it.

        The candidate tuples describe the alternatives the pivot was chosen among and default to empty, which is the
        honest record for a pivot performed directly: no rule selected it, so it competed against nothing.
        '''
        after = tableau.pivot(entering, leaving)
        entering_index = tableau.get_var_index(entering)
        pivot = next(row.coefficients[entering_index] for row in tableau.rows if row.basic_var == leaving)
        return SimplexPivotStep(tableau, entering_candidates, entering, leaving_candidates, leaving, pivot, after)
