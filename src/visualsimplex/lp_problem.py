from collections.abc import Iterable
from visualsimplex.value_objects import Constraint, Objective, OptimizationSense, VarDomain


class LPProblem:

    def __init__(self, objective : Objective, constraints : Iterable[Constraint]):
        self._objective = objective
        self._constraints = tuple(constraints)

    def opt_sense(self) -> OptimizationSense:
        return self._objective.opt_sense

    def n_constraints(self) -> int:
        return len(self._constraints)



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
