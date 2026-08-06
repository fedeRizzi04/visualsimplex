from __future__ import annotations
from collections.abc import Iterable
from dataclasses import dataclass, field
from visualsimplex.value_objects import Constraint, ConstraintSense, Objective, OptimizationSense, VarDomain, Variable, VarKind

def problem_variables(objective : Objective, constraints : Iterable[Constraint]) -> Iterable[Variable]:
    '''returns all different variables in a problem (Varaible instances)'''
    return (term.var for expression in (objective.expr, *(constraint.expr for constraint in constraints)) for term in expression)


@dataclass(frozen=True)
class CanonicalFormLPProblem:
    problem : LPProblem # guaranteed that all variables are compatible with all the others
    basic_vars : frozenset[Variable] = field(default_factory=frozenset)
    non_basic_vars : frozenset[Variable] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        objective = self.problem.objective
        constraints = tuple(self.problem)
        n_constraints = len(constraints)
        variables = self.basic_vars | self.non_basic_vars
        problem_vars = frozenset(problem_variables(objective, constraints))

        if objective.opt_sense is not OptimizationSense.MINIMIZE:
            raise ValueError("a canonical-form problem must minimize its objective")
        if variables != problem_vars or not self.basic_vars.isdisjoint(self.non_basic_vars):
            raise ValueError("basic and non-basic variables must partition the problem variables")
        if len(self.basic_vars) != n_constraints:
            raise ValueError("the number of basic variables must equal the number of constraints")
        if sum(var.kind is VarKind.SLACK for var in variables) != n_constraints:
            raise ValueError("a canonical-form problem must have one slack variable per constraint")
        
        rows = tuple({term.var: term.coeff for term in constraint.expr} for constraint in constraints)
        basic_columns = {tuple(row.get(var, 0) for row in rows) for var in self.basic_vars}
        identity_columns = {tuple(int(row == column) for row in range(n_constraints)) for column in range(n_constraints)}
        if basic_columns != identity_columns:
            raise ValueError("basic-variable columns must form the identity matrix")
        if not self.basic_vars.isdisjoint(term.var for term in objective.expr):
            raise ValueError("basic variables must not appear in the objective expression")


class LPProblem:

    def __init__(self, objective : Objective, constraints : Iterable[Constraint]):
        constraints = tuple(constraints)
        variables = tuple(problem_variables(objective, constraints))
        for i, variable in enumerate(variables):
            if any(not variable.is_compatible_with(other) for other in variables[i + 1:]):
                raise ValueError(f"incompatible variables with symbol {variable.symbol!r}")
        self._objective = objective
        self._constraints = constraints


    def opt_sense(self) -> OptimizationSense:
        return self._objective.opt_sense

    def n_constraints(self) -> int:
        return len(self._constraints)

    def is_in_inequality_form(self) -> bool:
        return all(c.is_in_inequality_form() for c in self._constraints)

    def from_inequality_form_to_standard_form(self) -> LPProblem:
        """Convert an inequality-form problem to the current standard-form convention."""
        if not self.is_in_inequality_form():
            raise RuntimeError("the LP problem is not in inequality form")

        non_negative_problem = self.from_free_variables_to_non_negative() # all non negative variables now
        # to_equality_form cannot raise RuntimeError because all constraints are NOT in EQ form
        new_constraints = (c.change_sense().to_equality_form(f"sl{i}") if c.sense is not ConstraintSense.LE else c.to_equality_form(f"sl{i}")
                           for i, c in enumerate(non_negative_problem._constraints))
        
        new_obj = (non_negative_problem._objective if non_negative_problem._objective.opt_sense is OptimizationSense.MINIMIZE
                   else non_negative_problem._objective.swap_sense())
        return LPProblem(new_obj, new_constraints)

    def from_free_variables_to_non_negative(self):
        objective = Objective(self._objective.expr.to_non_negative(), self._objective.opt_sense)
        constraints = (Constraint(constraint.expr.to_non_negative(), constraint.rhs, constraint.sense) for constraint in self._constraints)
        return LPProblem(objective, constraints)

    def from_inequality_form_to_canonical_form(self) -> CanonicalFormLPProblem:
        standard_form_problem = self.from_inequality_form_to_standard_form()
        sf_variables = frozenset(standard_form_problem.get_variables())
        basic_variables = frozenset(variable for variable in sf_variables if variable.kind is VarKind.SLACK)
        non_basic_variables = sf_variables - basic_variables
        return CanonicalFormLPProblem(standard_form_problem, basic_variables, non_basic_variables)

    def get_variables(self) -> Iterable[Variable]:
        return problem_variables(self._objective, self._constraints)

    @property
    def objective(self) -> Objective:
        return self._objective

    def __iter__(self) -> Iterable[Constraint]:
        return iter(self._constraints) # Constraint is immutable

    def __str__(self) -> str:
        lines = [str(self._objective), "s.t."]
        lines.extend(map(str, self._constraints))
        
        variables = {term.var.symbol: term.var for term in self._objective.expr}
        for constraint in self._constraints:
            variables.update({term.var.symbol: term.var for term in constraint.expr})

        for domain in VarDomain:
            symbols = sorted(variable.symbol for variable in variables.values() if variable.domain is domain)
            if symbols:
                lines.append(f"{', '.join(symbols)} {domain}")

        return "\n".join(lines)
