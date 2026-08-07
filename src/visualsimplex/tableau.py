from visualsimplex.value_objects import Variable, Expression, Constraint
from visualsimplex.lp_problem import CanonicalFormLPProblem
from typing import Iterable
from fractions import Fraction
from dataclasses import dataclass
from visualsimplex.utils import get_basic_var

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


@dataclass(frozen=True)
class LeavingVariableInfo:
    leaving_var : Variable
    pivot : Fraction
    index_of_constraint : int

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

    def candidate_entering_variables(self) -> Iterable[Variable]:
        '''returns the variable that have negative reduced cost coefficients'''
        for var, reduced_cost in zip(self._variables, self._reduced_cost_coefficients):
            if reduced_cost < 0:
                yield var

    def leaving_variable(self, entering : Variable) -> LeavingVariableInfo:
        '''given a candidate entering variable returns a LeavingVariableInfo object. It represent the leaving variable
        from basis, the value of the pivot and the index of the constraint where the pivot is in the tableau (starting from 0)
        '''
        if entering not in self.candidate_entering_variables():
            raise ValueError(f'{entering} is not a candidate entering variable in the following tableau:\n{self}')
        column_index_var = self.get_var_index(entering)
        eligible_rows = ((i, row) for i, row in enumerate(self._rows) if row.rhs >= 0 and row.coefficients[column_index_var] > 0) # rows that have a non-negative rhs and a positive pivot candidate
        try:
            # min on an empty iterable raises ValueError 
            index_constraint, row = min(eligible_rows, key=lambda item: item[1].rhs / item[1].coefficients[column_index_var]) # minimum ratio test on elegible rows
        except ValueError as e:
            problem_status = ', the problem is unbounded!' if self.is_feasible_basis() else ''
            raise ValueError(f'{entering} has a negative reduced cost but no eligible pivot{problem_status}') from e
        return LeavingVariableInfo(row.basic_var, row.coefficients[column_index_var], index_constraint)

    def is_unbounded_problem(self) -> bool:
        '''returns whether the problem represented by this tableau is unbounded. A problem is unbounded
        if exists a tableau where there are possible entering variables but no feasible pivot, meaning that
        all candidates pivot are negative (or equal to 0). In other words there is almost one candidate entering variables
        where all candidates pivot are not elegible. An unbounded problem is feasible'''
        constraints_coeffs : Iterable[Iterable[Fraction]]= (self.get_constraints_coefficient(var) for var in self.candidate_entering_variables())
        return self.is_feasible_basis() and \
               any(all(c <= Fraction(0) for c in coeffs) for coeffs in constraints_coeffs)
    

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
