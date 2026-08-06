from fractions import Fraction

import pytest

from visualsimplex import CanonicalFormLPProblem, Constraint, ConstraintSense, Expression, LPProblem, Objective, OptimizationSense, Term, VarDomain, VarKind, Variable


def variable(symbol, domain=VarDomain.NON_NEGATIVE):
    return Variable(VarKind.ORIGINAL, symbol, domain)


def term(symbol, coeff=Fraction(1), domain=VarDomain.NON_NEGATIVE):
    return Term(variable(symbol, domain), coeff)


def slack(symbol, coeff=Fraction(1)):
    return Term(Variable(VarKind.SLACK, symbol), coeff)


def make_canonical_problem(*, objective=None, constraints=None, basic_vars=None):
    x1 = variable("x1")
    x2 = variable("x2")
    s1 = Variable(VarKind.SLACK, "s1")
    s2 = Variable(VarKind.SLACK, "s2")
    if objective is None:
        objective = Objective(Expression((Term(x1, Fraction(2)), Term(x2, Fraction(3)))), OptimizationSense.MINIMIZE)
    if constraints is None:
        constraints = (
            Constraint(
                Expression((Term(x1, Fraction(1)), Term(s1, Fraction(1)))),
                Fraction(4),
                ConstraintSense.EQ,
            ),
            Constraint(
                Expression((Term(x2, Fraction(1)), Term(s2, Fraction(1)))),
                Fraction(5),
                ConstraintSense.EQ,
            ),
        )
    if basic_vars is None:
        basic_vars = (s1, s2)
    return CanonicalFormLPProblem(LPProblem(objective, constraints), frozenset(basic_vars), frozenset((x1, x2)))


def test_lp_problem_string():
    problem = LPProblem(
        Objective(
            Expression((term("x2"), term("x1", Fraction(2)))),
            OptimizationSense.MAXIMIZE,
        ),
        (
            Constraint(
                Expression((term("x1"), term("x2"))),
                Fraction(5),
                ConstraintSense.LE,
            ),
            Constraint(
                Expression((term("x3", domain=VarDomain.FREE),)),
                Fraction(2),
                ConstraintSense.EQ,
            ),
        ),
    )

    assert str(problem) == (
        "maximize z = 2x1 + x2\n"
        "s.t.\n"
        "x1 + x2 <= 5\n"
        "x3 = 2\n"
        "x1, x2 >= 0\n"
        "x3 free"
    )


def test_lp_problem_is_in_inequality_form_only_when_all_constraints_are_inequalities():
    objective = Objective(Expression((term("x"),)), OptimizationSense.MAXIMIZE)
    inequality = Constraint(Expression((term("x"),)), Fraction(3), ConstraintSense.LE)
    equality = Constraint(Expression((term("x"),)), Fraction(3), ConstraintSense.EQ)

    assert LPProblem(objective, (inequality,)).is_in_inequality_form()
    assert not LPProblem(objective, (inequality, equality)).is_in_inequality_form()


def test_from_inequality_form_normalizes_sense_and_minimizes_objective():
    problem = LPProblem(
        Objective(Expression((term("x", Fraction(2)),)), OptimizationSense.MAXIMIZE),
        (
            Constraint(Expression((term("x"),)), Fraction(5), ConstraintSense.GE),
            Constraint(Expression((term("y"),)), Fraction(4), ConstraintSense.LE),
        ),
    )

    result = problem.from_inequality_form_to_standard_form()

    assert result.opt_sense() is OptimizationSense.MINIMIZE
    assert str(result) == (
        "minimize z = -2x\n"
        "s.t.\n"
        "-x + sl0 = -5\n"
        "y + sl1 = 4\n"
        "sl0, sl1, x, y >= 0"
    )


def test_from_inequality_form_rejects_equality_constraints():
    problem = LPProblem(
        Objective(Expression((term("x"),)), OptimizationSense.MINIMIZE),
        (Constraint(Expression((term("x"),)), Fraction(1), ConstraintSense.EQ),),
    )

    with pytest.raises(RuntimeError, match="not in inequality form"):
        problem.from_inequality_form_to_standard_form()


def test_lp_problem_rejects_same_symbol_with_different_kind_or_domain():
    problem_objective = Objective(
        Expression((term("x"),)), OptimizationSense.MINIMIZE
    )
    free_x_constraint = Constraint(
        Expression((term("x", domain=VarDomain.FREE),)),
        Fraction(1),
        ConstraintSense.LE,
    )

    with pytest.raises(ValueError, match="incompatible variables"):
        LPProblem(problem_objective, (free_x_constraint,))


def test_free_variables_are_split_before_inequality_conversion():
    problem = LPProblem(
        Objective(
            Expression((term("x", Fraction(2), VarDomain.FREE),)),
            OptimizationSense.MAXIMIZE,
        ),
        (
            Constraint(
                Expression((term("x", domain=VarDomain.FREE),)),
                Fraction(1),
                ConstraintSense.GE,
            ),
        ),
    )

    result = problem.from_inequality_form_to_standard_form()

    assert str(result) == (
        "minimize z = 2x_minus - 2x_plus\n"
        "s.t.\n"
        "x_minus - x_plus + sl0 = -1\n"
        "sl0, x_minus, x_plus >= 0"
    )


def test_inequality_problem_is_converted_to_a_valid_canonical_problem():
    problem = LPProblem(
        Objective(Expression((term("x1"),)), OptimizationSense.MAXIMIZE),
        (
            Constraint(Expression((term("x1"),)), Fraction(4), ConstraintSense.LE),
            Constraint(Expression((term("x2"),)), Fraction(5), ConstraintSense.GE),
        ),
    )

    result = problem.from_inequality_form_to_canonical_form()

    assert result.problem.opt_sense() is OptimizationSense.MINIMIZE
    assert {variable.symbol for variable in result.basic_vars} == {"sl0", "sl1"}
    assert {variable.symbol for variable in result.non_basic_vars} == {"x1", "x2"}


def test_canonical_form_requires_minimization_and_excludes_basic_variables_from_objective():
    maximum = Objective(Expression((term("x1"),)), OptimizationSense.MAXIMIZE)
    with pytest.raises(ValueError, match="must minimize"):
        make_canonical_problem(objective=maximum)

    s1 = Variable(VarKind.SLACK, "s1")
    objective_with_zero_cost_basic_var = Objective(Expression((term("x1"), Term(s1, Fraction(0)))), OptimizationSense.MINIMIZE)
    with pytest.raises(ValueError, match="must not appear"):
        make_canonical_problem(objective=objective_with_zero_cost_basic_var)


def test_canonical_form_rejects_declared_variables_not_present_in_the_problem():
    canonical = make_canonical_problem()
    undeclared = variable("undeclared")

    with pytest.raises(ValueError, match="must partition"):
        CanonicalFormLPProblem(canonical.problem, canonical.basic_vars, canonical.non_basic_vars | frozenset((undeclared,)))


def test_canonical_form_requires_all_variables_to_be_non_negative():
    free_x = variable("x", domain=VarDomain.FREE)
    slack_var = Variable(VarKind.SLACK, "s")
    problem = LPProblem(
        Objective(Expression((Term(free_x, Fraction(1)),)), OptimizationSense.MINIMIZE),
        (
            Constraint(
                Expression((Term(free_x, Fraction(1)), Term(slack_var, Fraction(1)))),
                Fraction(1),
                ConstraintSense.EQ,
            ),
        ),
    )

    with pytest.raises(ValueError, match="must be non-negative"):
        CanonicalFormLPProblem(problem, frozenset((slack_var,)), frozenset((free_x,)))


@pytest.mark.parametrize("invalid_partition", ("missing", "overlapping"))
def test_basic_and_non_basic_variables_partition_all_problem_variables(invalid_partition):
    canonical = make_canonical_problem()
    variable_to_move = next(iter(canonical.non_basic_vars if invalid_partition == "missing" else canonical.basic_vars))
    basic_vars = canonical.basic_vars
    non_basic_vars = canonical.non_basic_vars - frozenset((variable_to_move,)) if invalid_partition == "missing" else canonical.non_basic_vars | frozenset((variable_to_move,))

    with pytest.raises(ValueError, match="must partition"):
        CanonicalFormLPProblem(canonical.problem, basic_vars, non_basic_vars)


def test_canonical_form_requires_one_distinct_slack_and_one_basic_variable_per_constraint():
    x1 = variable("x1")
    x2 = variable("x2")
    repeated_slack = Variable(VarKind.SLACK, "s")
    constraints = (
        Constraint(Expression((Term(x1, Fraction(1)), Term(repeated_slack, Fraction(1)))), Fraction(1), ConstraintSense.EQ),
        Constraint(Expression((Term(x2, Fraction(1)), Term(repeated_slack, Fraction(1)))), Fraction(2), ConstraintSense.EQ),
    )
    with pytest.raises(ValueError, match="one slack variable per constraint"):
        CanonicalFormLPProblem(LPProblem(Objective(Expression(()), OptimizationSense.MINIMIZE), constraints), frozenset((x1, x2)), frozenset((repeated_slack,)))

    canonical = make_canonical_problem()
    retained_basic_var = next(iter(canonical.basic_vars))
    with pytest.raises(ValueError, match="number of basic variables"):
        CanonicalFormLPProblem(canonical.problem, frozenset((retained_basic_var,)), canonical.non_basic_vars | (canonical.basic_vars - frozenset((retained_basic_var,))))


@pytest.mark.parametrize(
    "constraints",
    [
        # A basic column has a 2 where the identity matrix requires a 1.
        (
            Constraint(Expression((term("x1"), slack("s1", Fraction(2)))), Fraction(4), ConstraintSense.EQ),
            Constraint(Expression((term("x2"), slack("s2"))), Fraction(5), ConstraintSense.EQ),
        ),
        # A basic column has two non-zero entries.
        (
            Constraint(Expression((term("x1"), slack("s1"))), Fraction(4), ConstraintSense.EQ),
            Constraint(Expression((term("x2"), slack("s1"), slack("s2"))), Fraction(5), ConstraintSense.EQ),
        ),
        # Both unit columns have their 1 on the same row.
        (
            Constraint(Expression((term("x1"), slack("s1"), slack("s2"))), Fraction(4), ConstraintSense.EQ),
            Constraint(Expression((term("x2"),)), Fraction(5), ConstraintSense.EQ),
        ),
    ],
)
def test_canonical_form_requires_basic_columns_to_form_the_identity_matrix(constraints):
    basic_vars = (Variable(VarKind.SLACK, "s1"), Variable(VarKind.SLACK, "s2"))

    with pytest.raises(ValueError, match="columns must"):
        make_canonical_problem(constraints=constraints, basic_vars=basic_vars)
