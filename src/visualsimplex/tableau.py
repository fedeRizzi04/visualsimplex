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

class Tableau:


    # Tuples for reduced costs and for constraint expressions must follow the variable ordering. Enfact
    # the property variable must return an Iterable that produces variables accordingly to this ordering.
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

    def get_value_for_basic_var(self, var : Variable) -> Fraction:
        if var not in self._basic_vars:
            raise ValueError(f'{var} is not a basic var in the following tableau: \n{self}')
        return next(r.rhs for r in self._rows if r.basic_var == var)

    def is_feasible_basis(self) -> bool:
        return all(r.rhs >= 0 for r in self._rows)

    def is_optimal_basis(self) -> bool:
        return self.is_feasible_basis() and all(c >= Fraction(0) for c in self._reduced_cost_coefficients)


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
