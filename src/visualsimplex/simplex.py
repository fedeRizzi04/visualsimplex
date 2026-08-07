from dataclasses import dataclass, field
from enum import Enum
from itertools import chain
from typing import Iterable
from visualsimplex.initialization import BalinskiGomoryInitializer, InfeasibleProblemError, InitializationPivotStep, InitializationStrategy
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


@dataclass(frozen=True)
class SimplexPivotStep(PivotStep):
    '''Description of one pivot performed during primal-simplex optimization.

    The candidate collections describe the choices available before the pivot according to the primal-simplex
    conditions. The selected variables need not belong to them when the step is produced through the permissive
    SimplexAlgorithm.perform_pivot method.
    '''

    _entering_candidates : tuple[EnteringCandidate, ...] = field(repr=False)
    _leaving_candidates : tuple[LeavingCandidate, ...] = field(repr=False)

    @property
    def description(self) -> str:
        return 'primal-simplex pivot step'

    @property
    def entering_candidates(self) -> Iterable[EnteringCandidate]:
        return iter(self._entering_candidates)

    @property
    def leaving_candidates(self) -> Iterable[LeavingCandidate]:
        return iter(self._leaving_candidates)


class SimplexReport:
    '''Structured report of initialization, optimization and the final mathematical outcome.

    Iterating over the report yields initialization pivot steps followed by primal-simplex pivot steps, preserving
    their execution order. The two phases remain separately available for clients that present them differently.
    '''

    def __init__(self, original_problem : LPProblem, canonical_problem : CanonicalFormLPProblem, initial_tableau : Tableau, initialization_steps : Iterable[InitializationPivotStep], optimization_steps : Iterable[SimplexPivotStep], final_tableau : Tableau, status : SimplexStatus, termination_reason : str):
        self._original_problem = original_problem
        self._canonical_problem = canonical_problem
        self._initial_tableau = initial_tableau
        self._initialization_steps = tuple(initialization_steps)
        self._optimization_steps = tuple(optimization_steps)
        self._final_tableau = final_tableau
        self._status = status
        self._termination_reason = termination_reason

    @property
    def original_problem(self) -> LPProblem:
        return self._original_problem

    @property
    def canonical_problem(self) -> CanonicalFormLPProblem:
        return self._canonical_problem

    @property
    def initial_tableau(self) -> Tableau:
        return self._initial_tableau

    @property
    def initialization_steps(self) -> Iterable[InitializationPivotStep]:
        return iter(self._initialization_steps)

    @property
    def optimization_steps(self) -> Iterable[SimplexPivotStep]:
        return iter(self._optimization_steps)

    @property
    def steps(self) -> Iterable[PivotStep]:
        return chain(self._initialization_steps, self._optimization_steps)

    @property
    def final_tableau(self) -> Tableau:
        return self._final_tableau

    @property
    def status(self) -> SimplexStatus:
        return self._status

    @property
    def termination_reason(self) -> str:
        return self._termination_reason

    def __iter__(self) -> Iterable[PivotStep]:
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
            try:
                current = current.initialize(self._initialization_strategy)
            except InfeasibleProblemError as error:
                initialization_steps = tuple(self._initialization_strategy.steps)
                final_tableau = self._last_tableau(initial_tableau, initialization_steps)
                return SimplexReport(problem, canonical_problem, initial_tableau, initialization_steps, (), final_tableau, SimplexStatus.INFEASIBLE, str(error))
            initialization_steps = tuple(self._initialization_strategy.steps)

        optimization_steps : list[SimplexPivotStep] = []
        while not current.is_optimal_basis():
            if current.is_unbounded_problem():
                return SimplexReport(problem, canonical_problem, initial_tableau, initialization_steps, optimization_steps, current, SimplexStatus.UNBOUNDED, 'an improving variable has no eligible leaving variable')
            entering = current.entering_variable(self._entering_rule)
            leaving = current.leaving_variable(entering, self._leaving_rule)
            step = self.perform_pivot(current, entering, leaving.leaving_var)
            optimization_steps.append(step)
            current = step.after

        return SimplexReport(problem, canonical_problem, initial_tableau, initialization_steps, optimization_steps, current, SimplexStatus.OPTIMAL, 'an optimal feasible basis has been reached')

    def perform_pivot(self, tableau : Tableau, entering : Variable, leaving : Variable) -> SimplexPivotStep:
        '''Perform and describe any algebraically valid pivot without requiring the selection rules to choose it.'''
        after = tableau.pivot(entering, leaving)
        entering_index = tableau.get_var_index(entering)
        pivot = next(row.coefficients[entering_index] for row in tableau.rows if row.basic_var == leaving)
        entering_candidates = tuple(EnteringCandidate(var, reduced_cost) for var, reduced_cost in tableau.reduced_costs if reduced_cost < 0)
        leaving_candidates = tuple(LeavingCandidate(row.basic_var, row.coefficients[entering_index], row.rhs) for row in tableau.rows if row.rhs >= 0 and row.coefficients[entering_index] > 0)
        return SimplexPivotStep(tableau, entering, leaving, pivot, after, entering_candidates, leaving_candidates)

    @staticmethod
    def _last_tableau(initial_tableau : Tableau, steps : Iterable[InitializationPivotStep]) -> Tableau:
        current = initial_tableau
        for step in steps:
            current = step.after
        return current
