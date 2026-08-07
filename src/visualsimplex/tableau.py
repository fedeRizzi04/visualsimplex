from __future__ import annotations
from visualsimplex.value_objects import Variable, Expression, Constraint
from visualsimplex.lp_problem import CanonicalFormLPProblem
from typing import TYPE_CHECKING, Iterable
from fractions import Fraction
from dataclasses import dataclass
from visualsimplex.rules import EnteringCandidate, EnteringVariableRule, LeavingCandidate, LeavingVariableRule
from visualsimplex.utils import get_basic_var, tableau_to_canonical_form_problem, update_row_coeffs_after_pivot
if TYPE_CHECKING:
    from visualsimplex.initialization import InitializationStrategy

@dataclass(frozen=True)
class TableauRow:
    coefficients : tuple[Fraction]
    rhs : Fraction
    basic_var : Variable

    def __str__(self) -> str:
        return self.format(len(str(self.rhs)), tuple(len(str(coefficient)) for coefficient in self.coefficients))

    def format(self, rhs_width : int, coefficient_widths : tuple[int, ...]) -> str:
        coefficients = "  ".join(f"{coefficient!s:>{width}}" for coefficient, width in zip(self.coefficients, coefficient_widths))
        return f"{self.rhs!s:>{rhs_width}} | {coefficients}"

class Tableau:


    # Tuples for reduced costs and for constraint expressions must follow the variable ordering (self._variables is ordered in natural ordering variables). 
    # Also the property variable must return an Iterable that produces variables accordingly to this ordering.
    # For example, if the variable ordering is (x1, x2, x3, sl1, sl2), then the reduced cost
    # tuple (2, 0, 1, 0, -1) represent a reduced cost of 2 for x1, of 0 for x2, etc...
    # The same must be true even for constraint tuples

    def __init__(self, lp_problem : CanonicalFormLPProblem, objective_tableau_coeff : Fraction = Fraction(0)): 
        self._basic_vars : frozenset[Variable] = lp_problem.basic_vars 
        self._objective_tableau_coeff : Fraction = objective_tableau_coeff 
        self._variables : tuple[Variable] = tuple(sorted(lp_problem.basic_vars | lp_problem.non_basic_vars))

        obj_expr = lp_problem.problem.objective.expr
        self._reduced_cost_coefficients : tuple[Fraction] = tuple(self._build_reduced_costs_coefficients(obj_expr))
        constraints = iter(lp_problem.problem)
        self._rows : tuple[TableauRow] = tuple(self._build_tableau_rows(constraints))

    def _build_reduced_costs_coefficients(self, objective_expr : Expression) -> Iterable[Fraction]:
        return (objective_expr.coefficient_of(var) for var in self._variables)

    def _build_tableau_rows(self, constraints : Iterable[Constraint]) -> Iterable[TableauRow]:
        rows = list() # set is more efficients but I need insertion order :(
        for c in constraints: 
            expr : Expression = c.expr
            rhs : Fraction = c.rhs
            coefficients : tuple[Fraction] = tuple(expr.coefficient_of(v) for v in self._variables)
            basic_var : Variable = get_basic_var(expr, self._basic_vars)
            rows.append(TableauRow(coefficients, rhs, basic_var))
        return iter(rows)


    @property
    def variables(self) -> Iterable[Variable]:
        '''returns the variables of the LP problem represented by this tableau. The order of the variables
        returned by this method defines the order of the reduced costs and constraint coefficients of this tableau
        '''
        return iter(self._variables)
    
    @property
    def basic_variables(self) -> Iterable[Variable]:
        return iter(sorted(self._basic_vars))

    @property
    def non_basic_variables(self) -> Iterable[Variable]:
        return iter(sorted(frozenset(self._variables) - self._basic_vars)) 

    @property
    def objective_value(self) -> Fraction:
        return -self._objective_tableau_coeff

    @property
    def reduced_costs(self) -> Iterable[tuple[Variable, Fraction]]:
        return iter(zip(self._variables, self._reduced_cost_coefficients))

    @property
    def rows(self) -> Iterable[TableauRow]:
        return iter(self._rows)


    def is_basic_variable(self, var : Variable) -> bool:
        return var in self._basic_vars


    def get_value_for_basic_var(self, var : Variable) -> Fraction:
        if not self.is_basic_variable(var):
            raise ValueError(f'{var} is not a basic var in the following tableau: \n{self}')
        return next(r.rhs for r in self._rows if r.basic_var == var)

    def is_feasible_basis(self) -> bool:
        return all(r.rhs >= 0 for r in self._rows)

    def is_optimal_basis(self) -> bool:
        return self.is_feasible_basis() and all(c >= Fraction(0) for c in self._reduced_cost_coefficients)

    def _require_feasible_basis(self) -> None:
        if not self.is_feasible_basis():
            raise ValueError('primal-simplex rules require a feasible basis')

    def entering_candidate_variables(self) -> Iterable[Variable]:
        '''Return the variables with negative reduced costs in a feasible tableau.'''
        self._require_feasible_basis()
        for var, reduced_cost in zip(self._variables, self._reduced_cost_coefficients):
            if reduced_cost < 0:
                yield var

    def entering_variable(self, rule : EnteringVariableRule) -> Variable:
        '''Choose an entering variable for a primal-simplex step on a feasible tableau.'''
        self._require_feasible_basis()
        candidates = tuple(EnteringCandidate(var, reduced_cost) for var, reduced_cost in self.reduced_costs if reduced_cost < 0)
        entering = rule(candidates)
        if entering not in (candidate.var for candidate in candidates):
            raise ValueError('the entering-variable rule returned a variable that is not eligible')
        return entering

    def leaving_variable(self, entering : Variable, rule : LeavingVariableRule) -> LeavingCandidate:
        '''Choose a leaving variable that preserves feasibility during a primal-simplex step.'''
        self._require_feasible_basis()
        if entering not in self.entering_candidate_variables():
            raise ValueError(f'{entering} is not a candidate entering variable in the following tableau:\n{self}')
        column_index_var = self.get_var_index(entering)
        candidates = tuple(LeavingCandidate(row.basic_var, row.coefficients[column_index_var], row.rhs) for row in self._rows if row.rhs >= 0 and row.coefficients[column_index_var] > 0)
        if not candidates:
            raise ValueError(f'{entering} has a negative reduced cost but no eligible pivot, the problem is unbounded!')

        selected = rule(candidates)
        if selected not in candidates:
            raise ValueError('the leaving-variable rule returned a candidate that is not eligible')
        return selected

    def is_unbounded_problem(self) -> bool:
        '''returns whether the problem represented by this tableau is unbounded. A problem is unbounded
        if exists a tableau where there are possible entering variables but no feasible pivot, meaning that
        all candidates pivot are negative (or equal to 0). In other words there is almost one candidate entering variables
        where all candidates pivot are not elegible. An unbounded problem is feasible'''
        self._require_feasible_basis()
        constraints_coeffs : Iterable[Iterable[Fraction]]= (self.get_constraints_coefficient(var) for var in self.entering_candidate_variables())
        return any(all(c <= Fraction(0) for c in coeffs) for coeffs in constraints_coeffs)
    

    def get_constraints_coefficient(self, var : Variable) -> Iterable[Fraction]: 
        '''given a variable returns the coefficients of that variable for every constraint in the tableau'''
        if var not in self._variables:
            raise ValueError(f'{var} is not part of this tableau variables, that are: {self._variables}')
        index = self.get_var_index(var)
        return (row.coefficients[index] for row in self._rows)
            
    def get_var_index(self, var : Variable):
        '''
        Given a variable of the problem that represent this tableau, this method returns its index 
        in the order. For example, if the problem have variables (x1, x2, x3, sl1) in such ordering, then the index of
        sl1 is 3 
        '''
        try:
            index = self._variables.index(var)
        except ValueError as e: 
            raise ValueError(f'{var} is not part of {self}') from e
        return index


    def pivot(self, entering : Variable, leaving : Variable) -> Tableau:
        '''Perform the algebraic pivot selected by entering and leaving and return a new tableau.

        This method deliberately knows nothing about simplex pivot-selection rules or basis feasibility. It only
        requires entering to be non-basic, leaving to be basic and their pivot coefficient to be non-zero. Callers
        such as the primal-simplex algorithm or an initialization strategy are responsible for choosing a pivot
        that satisfies their own mathematical invariants.
        '''
        if entering not in self._variables:
            raise ValueError(f'{entering} is not part of this tableau variables')
        if entering in self._basic_vars:
            raise ValueError(f'{entering} must be a non-basic variable in the following tableau:\n{self}')
        if leaving not in self._basic_vars:
            raise ValueError(f'{leaving} is not a basic variable in the following tableau:\n{self}')

        entering_index = self.get_var_index(entering)
        pivot_row = next(row for row in self._rows if row.basic_var == leaving)
        pivot = pivot_row.coefficients[entering_index]
        if pivot == 0:
            raise ValueError('cannot pivot on a zero coefficient')

        normalized_coefficients = tuple(coefficient / pivot for coefficient in pivot_row.coefficients)
        normalized_rhs = pivot_row.rhs / pivot
        new_pivot_row = TableauRow(normalized_coefficients, normalized_rhs, entering)
        new_rows : list[TableauRow] = []
        for row in self._rows:
            if row.basic_var == leaving:
                new_rows.append(new_pivot_row)
            else:
                factor = row.coefficients[entering_index]
                new_coefficients = tuple(update_row_coeffs_after_pivot(row.coefficients, normalized_coefficients, factor))
                new_rows.append(TableauRow(new_coefficients, row.rhs - factor * normalized_rhs, row.basic_var))

        objective_factor = self._reduced_cost_coefficients[entering_index]
        new_objective_coefficients = tuple(update_row_coeffs_after_pivot(self._reduced_cost_coefficients, normalized_coefficients, objective_factor))
        new_objective_tableau_coeff = self._objective_tableau_coeff - objective_factor * normalized_rhs
        problem = tableau_to_canonical_form_problem(self._variables, new_objective_coefficients, new_rows)
        return Tableau(problem, new_objective_tableau_coeff)

    def to_canonical_form_problem(self) -> CanonicalFormLPProblem:
        return tableau_to_canonical_form_problem(self._variables, self._reduced_cost_coefficients, self._rows)

    def initialize(self, strategy : InitializationStrategy) -> Tableau:
        '''Initialize this tableau using a strategy that returns a feasible tableau or raises InfeasibleProblemError.'''
        if self.is_feasible_basis():
            raise ValueError('cannot initialize a tableau whose basis is already feasible')
        return strategy.run(self) # could raise InfeasibleProblemError



    def __str__(self) -> str:
        objective_coefficient = self._objective_tableau_coeff
        rhs_width = max(len(str(value)) for value in (objective_coefficient, *(row.rhs for row in self._rows)))
        widths = tuple(max(len(str(var)), *(len(str(row.coefficients[i])) for row in self._rows), len(str(self._reduced_cost_coefficients[i]))) for i, var in enumerate(self._variables))
        header = f"{'':>{rhs_width}} | " + "  ".join(f"{var!s:>{width}}" for var, width in zip(self._variables, widths))
        objective = f"{objective_coefficient!s:>{rhs_width}} | " + "  ".join(f"{coefficient!s:>{width}}" for coefficient, width in zip(self._reduced_cost_coefficients, widths))
        basis = ", ".join(f"{var} = {self.get_value_for_basic_var(var)}" for var in self.basic_variables)
        return "\n".join((
            header,
            objective,
            *(row.format(rhs_width, widths) for row in self._rows),
            f"Basis: {basis}",
            f"Objective value: {self.objective_value}",
        ))
