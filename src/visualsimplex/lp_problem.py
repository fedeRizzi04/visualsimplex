from __future__ import annotations
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from fractions import Fraction
from visualsimplex.value_objects import Constraint, ConstraintSense, Expression, Objective, OptimizationSense, Term, VarDomain, Variable, VarKind
from visualsimplex.utils import problem_variables

CoefficientType = int | float | Fraction
'''Numeric type accepted wherever LPProblemBuilder/LPProblem.from_coefficients expect a raw coefficient or right-hand side.
Values are converted to Fraction; floats go through str() first (Fraction(str(x))), so e.g. 0.1 becomes exactly 1/10
instead of the binary approximation Fraction(0.1) would produce.'''


ConstraintRow = tuple[Iterable[CoefficientType], ConstraintSense | str, CoefficientType]
'''Shape of one row of the `constraints` argument to LPProblem.from_coefficients: a coefficients vector
(aligned with the variable order induced by objective_coeffs), a comparison sense and a right-hand side.
A plain tuple such as ((1, 1), "<=", 4) is enough; there is no type to construct.'''


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
        if any(variable.domain is not VarDomain.NON_NEGATIVE for variable in variables):
            raise ValueError("all variables in a canonical-form problem must be non-negative")
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

    @classmethod
    def builder(cls, opt_sense: OptimizationSense | str) -> LPProblemBuilder:
        '''Start building an LPProblem one variable/constraint at a time; see LPProblemBuilder.'''
        return LPProblemBuilder(opt_sense)

    @classmethod
    def from_coefficients(cls, opt_sense: OptimizationSense | str, objective_coeffs: Iterable[CoefficientType], constraints: Iterable[ConstraintRow], *, var_prefix: str = "x") -> LPProblem:
        '''Build an LPProblem from dense coefficient vectors, auto-naming variables var_prefix1, var_prefix2, ... (all non-negative).

        Convenience wrapper around LPProblemBuilder for the common case where variable names/domains don't matter.
        Use LPProblem.builder() directly for custom variable names or free variables.

        Every variable position must be given a coefficient in objective_coeffs and in each constraint's coeffs,
        even variables that a given expression does not actually use: put a 0 in their position instead of omitting it,
        otherwise the remaining coefficients would silently shift onto the wrong variables.

        Args:
            opt_sense: "min"/"max" or an OptimizationSense member.
            objective_coeffs: one coefficient per variable; also determines how many variables the problem has.
            constraints: iterable of (coeffs, sense, rhs) rows (see ConstraintRow), each coeffs aligned with objective_coeffs.
            var_prefix: prefix used for the generated variable symbols (default "x" -> x1, x2, ...).

        Example:
            LPProblem.from_coefficients("max", (3, 2), [((1, 1), "<=", 4), ((1, 3), "<=", 6)])
        '''
        builder = cls.builder(opt_sense)
        for index, coeff in enumerate(objective_coeffs, start=1):
            builder.add_variable(f"{var_prefix}{index}", coeff)
        for coeffs, sense, rhs in constraints:
            builder.add_constraint(coeffs, sense, rhs)
        return builder.build()

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

    def get_variables(self) -> Iterator[Variable]:
        return problem_variables(self._objective, self._constraints)

    @property
    def objective(self) -> Objective:
        return self._objective

    def __iter__(self) -> Iterator[Constraint]:
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


def _coerce_enum(enum_cls, value):
    '''Return value if it is already an enum_cls member, otherwise look it up by its value (e.g. "max" -> OptimizationSense.MAXIMIZE).'''
    # useful when users pass 'max' or 'min' as parameter. With _coerce_enum(OptimizationSens, 'min') we ca get OptimizationSense.MINIMIZE thanks to OptimizationSense('min')
    return value if isinstance(value, enum_cls) else enum_cls(value)


def _to_fraction(value: CoefficientType) -> Fraction:
    '''Convert a raw coefficient/rhs to Fraction. Floats go through str() to preserve their decimal meaning
    (0.1 -> 1/10) instead of Fraction's binary-exact conversion (Fraction(0.1) -> 3602879701896397/36028797018963968).'''
    return Fraction(str(value)) if isinstance(value, float) else Fraction(value)


class LPProblemBuilder:
    '''Incrementally builds an LPProblem from raw coefficients, one variable and one constraint at a time.

    Variables are declared in order via add_variable(), each paired with its own objective coefficient
    and domain. Every add_constraint() call must then supply exactly one coefficient per declared variable,
    in that same order: if a variable does not appear in a given constraint (or in the objective), pass 0
    for it instead of omitting it, otherwise the remaining coefficients would silently shift onto the wrong
    variables. build() translates the accumulated data into Variable/Term/Expression/Objective/Constraint
    instances and constructs the resulting LPProblem, reusing all of its invariant checks (e.g. variable
    compatibility) instead of duplicating them.

    Example:
        problem = (
            LPProblemBuilder(OptimizationSense.MAXIMIZE)
            .add_variable("x", 3)
            .add_variable("y", 2, VarDomain.FREE)
            .add_constraint((1, 1), "<=", 4)
            .add_constraint((1, 3), "<=", 6)
            .build()
        )
    '''

    def __init__(self, opt_sense: OptimizationSense | str):
        self._opt_sense = _coerce_enum(OptimizationSense, opt_sense)
        self._variables: list[Variable] = []
        self._objective_terms: list[Term] = []
        self._constraints: list[Constraint] = []

    def add_variable(self, symbol: str, obj_coeff: CoefficientType, domain: VarDomain = VarDomain.NON_NEGATIVE) -> LPProblemBuilder:
        '''Declare a new variable together with its objective coefficient and domain, in the order add_constraint() coefficients must follow.'''
        if any(variable.symbol == symbol for variable in self._variables):
            raise ValueError(f"a variable with symbol {symbol!r} has already been declared")
        variable = Variable(VarKind.ORIGINAL, symbol, domain)
        self._variables.append(variable)
        self._objective_terms.append(Term(variable, _to_fraction(obj_coeff)))
        return self

    def add_constraint(self, coeffs: Iterable[CoefficientType], sense: ConstraintSense | str, rhs: CoefficientType) -> LPProblemBuilder:
        '''Add a constraint. coeffs must supply exactly one coefficient per declared variable, in add_variable() order;
        use 0 for variables absent from this constraint instead of omitting them.'''
        coeffs = tuple(coeffs)
        if len(coeffs) != len(self._variables):
            raise ValueError(f"expected {len(self._variables)} coefficients (one per declared variable), got {len(coeffs)}")
        terms = (Term(variable, _to_fraction(coeff)) for variable, coeff in zip(self._variables, coeffs))
        self._constraints.append(Constraint(Expression(terms), _to_fraction(rhs), _coerce_enum(ConstraintSense, sense)))
        return self

    def build(self) -> LPProblem:
        '''Construct the LPProblem from the declared variables and constraints.'''
        if not self._variables:
            raise ValueError("cannot build an LPProblem without at least one variable")
        objective = Objective(Expression(self._objective_terms), self._opt_sense)
        return LPProblem(objective, self._constraints)
