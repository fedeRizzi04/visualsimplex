from collections.abc import Iterable
from visualsimplex.value_objects import Constraint, ConstraintSense, Objective, OptimizationSense, VarDomain, Variable


def _variables(objective : Objective, constraints : Iterable[Constraint]) -> tuple[Variable, ...]:
    '''returns all different variables in a problem (Varaible instances)'''
    return tuple(term.var for expression in (objective.expr, *(constraint.expr for constraint in constraints))
                          for term in expression)

class LPProblem:

    def __init__(self, objective : Objective, constraints : Iterable[Constraint]):
        constraints = tuple(constraints)
        variables = _variables(objective, constraints)
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

    def from_inequality_form_to_standard_form(self):
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

    def get_objective(self) -> Objective:
        return self._objective

    def __iter__(self):
        return iter(self._constraints) # constraint is immutable

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
