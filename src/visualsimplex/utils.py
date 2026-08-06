from collections.abc import Set
from fractions import Fraction
from typing import Iterable
from visualsimplex.value_objects import Constraint, Expression, Objective, Variable


def problem_variables(objective : Objective, constraints : Iterable[Constraint]) -> Iterable[Variable]:
    '''returns all different variables in a problem (Varaible instances)'''
    return (term.var for expression in (objective.expr, *(constraint.expr for constraint in constraints)) for term in expression)


def get_basic_var(expr : Expression, basic_vars : Set[Variable]) -> Variable: 
    '''given an Expression instance (related to a constraint) and a set of basic vars in a canonical form of a problem 
       (that comprises the constraint having the expression as a parameter, 
        this function returns the basic var (if exists) in the expression'''
    
    basic_vars_in_expr = {t.var for t in expr if t.var in basic_vars and t.coeff == Fraction(1)}
    if len(basic_vars_in_expr) == 0:
        raise ValueError(f'The expression {expr}, given this set of basic vars: {basic_vars}, does not have a basic var with unitary coefficient')
    if len(basic_vars_in_expr) > 1:
        raise ValueError(f'an expression must have only one basic variable with unitary coefficient. \
                           The expression {expr}, given this set of basic vars: {basic_vars}, does not satisfy the previous constraint')
    return next(iter(basic_vars_in_expr))
