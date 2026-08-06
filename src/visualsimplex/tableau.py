from visualsimplex.value_objects import Variable, Expression, Constraint
from visualsimplex.lp_problem import CanonicalFormLPProblem
from typing import Iterable
from fractions import Fraction
from dataclasses import dataclass
from collections.abc import Set

@dataclass(frozen=True)
class TableauRow:
    coefficients : tuple[Fraction]
    rhs : Fraction
    basic_var : Variable

def get_basic_var(expr : Expression, basic_vars : Set[Variable]) -> Variable: 
    basic_vars_in_expr = {t.var for t in expr if t.var in basic_vars and t.coeff == Fraction(1)}
    if len(basic_vars_in_expr) == 0:
        raise ValueError(f'The expression {expr}, given this set of basic vars: {basic_vars}, does not have a basic var with unitary coefficient')
    if len(basic_vars_in_expr) > 1:
        raise ValueError(f'an expression must have only one basic variable with unitary coefficient. \
                           The expression {expr}, given this set of basic vars: {basic_vars}, does not satisfy the previous constraint')
    return next(iter(basic_vars_in_expr))


class Tableau:


    # Tuples for reduced costs and for constraint expressions must follow the variable ordering. Enfact
    # the property variable must return an Iterable that produces variables accordingly to this ordering.
    # For example, if the variable ordering is (x1, x2, x3, sl1, sl2), then the reduced cost
    # tuple (2, 0, 1, 0, -1) represent a reduced cost of 2 for x1, of 0 for x2, etc...
    # The same must be true even for constraint tuples

    def __init__(self, lp_problem : CanonicalFormLPProblem, obj_value : Fraction = Fraction(0)): 
        self._basic_vars : frozenset[Variable] = lp_problem.basic_vars 
        self._non_basic_vars : frozenset[Variable] = lp_problem.non_basic_vars
        self._obj_value : Fraction = obj_value 

        obj_expr = lp_problem.problem.objective.expr
        self._reduced_cost_coefficients : tuple[Fraction] = tuple(self._build_reduced_costs_coefficients(obj_expr))
        constraints = iter(lp_problem.problem)
        self._rows : tuple[TableauRow] = tuple(self._build_tableau_rows(constraints))

    def _build_reduced_costs_coefficients(self, objective_expr : Expression) -> Iterable[Fraction]:
        return (objective_expr.coefficient_of(var) for var in self.variables)

    def _build_tableau_rows(self, constraints : Iterable[Constraint]) -> Iterable[TableauRow]:
        rows = list() # set is more efficients but I need insertion order :(
        for c in constraints: 
            expr : Expression = c.expr
            rhs : Fraction = c.rhs
            coefficients : tuple[Fraction] = tuple(expr.coefficient_of(v) for v in self.variables)
            basic_var : Variable = get_basic_var(expr, self._basic_vars)
            rows.append(TableauRow(coefficients, rhs, basic_var))
        return iter(rows)


    @property
    def variables(self) -> Iterable[Variable]:
        return iter(sorted(tuple(self._basic_vars | self._non_basic_vars)))
    
    @property
    def basic_variables(self) -> Iterable[Variable]:
        return iter(sorted(tuple(self._basic_vars)))

    @property
    def non_basic_variables(self) -> Iterable[Variable]:
        return iter(sorted(tuple(self._non_basic_vars))) 

    @property
    def objective_value(self) -> int:
        return self._obj_value

    def get_var_index(self, var : Variable):
        '''
        Given a variable of the problem that represent this tableau, this method returns its index 
        in the order. For example, if the problem have variables (x1, x2, x3, sl1) in such ordering, then the index of
        sl1 is 3 
        '''
        variables = tuple(self.variables)
        try:
            index = variables.index(var)
        except ValueError as e: 
            raise ValueError(f'{var} is not part of {self}') from e
        return index
        
        



