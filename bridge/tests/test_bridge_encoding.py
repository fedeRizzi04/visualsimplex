from fractions import Fraction
from visualsimplex import LPProblem, OptimizationSense, SimplexAlgorithm, Tableau, VarKind, Variable
from visualsimplex.rules import EnteringCandidate, LeavingCandidate
from visualsimplex_bridge.encoding import encode_entering_candidate, encode_fraction, encode_leaving_candidate, encode_report, encode_tableau, encode_variable


def problem():
    return LPProblem.from_coefficients("max", (3, 2), [((1, 1), "<=", 4), ((1, 3), "<=", 6)])


def test_encode_fraction_keeps_the_exact_rational_and_its_rendered_text():
    assert encode_fraction(Fraction(-1, 3)) == {'numerator': -1, 'denominator': 3, 'text': '-1/3'}
    assert encode_fraction(Fraction(4)) == {'numerator': 4, 'denominator': 1, 'text': '4'}


def test_encode_variable_reports_the_kind_as_a_plain_lowercase_name():
    assert encode_variable(Variable(VarKind.SLACK, "sl0")) == {'symbol': 'sl0', 'kind': 'slack'}


def test_encode_candidates_carry_the_numbers_a_client_shows_next_to_each_option():
    x = Variable(VarKind.ORIGINAL, "x")

    entering = encode_entering_candidate(EnteringCandidate(x, Fraction(-3)))
    leaving = encode_leaving_candidate(LeavingCandidate(x, Fraction(2), Fraction(8)))

    assert entering == {'var': {'symbol': 'x', 'kind': 'original'}, 'reduced_cost': encode_fraction(Fraction(-3))}
    assert leaving['ratio'] == encode_fraction(Fraction(4))
    assert (leaving['pivot'], leaving['rhs']) == (encode_fraction(Fraction(2)), encode_fraction(Fraction(8)))


def test_encode_tableau_aligns_every_coefficient_list_with_the_variable_order():
    tableau = Tableau(problem().from_inequality_form_to_canonical_form())

    encoded = encode_tableau(tableau, OptimizationSense.MAXIMIZE)

    assert [variable['symbol'] for variable in encoded['variables']] == [str(variable) for variable in tableau.variables]
    assert len(encoded['reduced_costs']) == len(encoded['variables'])
    assert all(len(row['coefficients']) == len(encoded['variables']) for row in encoded['rows'])
    assert [variable['is_basic'] for variable in encoded['variables']] == [tableau.is_basic_variable(variable) for variable in tableau.variables]
    assert encoded['is_feasible'] and not encoded['is_optimal']


def test_encode_report_lists_initialization_steps_before_optimization_steps():
    lp_problem = LPProblem.from_coefficients("min", (1,), [((1,), ">=", 2), ((1,), "<=", 5)])

    encoded = encode_report(SimplexAlgorithm().solve_inequality_form(lp_problem))

    assert [step['phase'] for step in encoded['steps']] == ['initialization', 'optimization']
    assert encoded['status'] == 'optimal'
    assert encoded['termination_reason']


def test_a_maximization_reports_its_value_in_the_sense_the_user_wrote():
    '''The canonical form minimizes, so the tableau of a max problem holds the opposite of the value the user expects.'''
    encoded = encode_report(SimplexAlgorithm().solve_inequality_form(problem()))

    assert encoded['sense'] == 'max'
    assert encoded['final_tableau']['objective_value']['text'] == '-12'
    assert encoded['final_tableau']['original_objective_value']['text'] == '12'


def test_a_minimization_reports_the_same_value_in_both_senses():
    lp_problem = LPProblem.from_coefficients("min", (1,), [((1,), ">=", 2), ((1,), "<=", 5)])

    encoded = encode_report(SimplexAlgorithm().solve_inequality_form(lp_problem))

    assert encoded['sense'] == 'min'
    assert encoded['final_tableau']['original_objective_value'] == encoded['final_tableau']['objective_value']


def test_encode_report_carries_only_the_resulting_tableau_of_each_step():
    encoded = encode_report(SimplexAlgorithm().solve_inequality_form(problem()))

    assert 'before' not in encoded['steps'][0]
    assert encoded['steps'][0]['after']['text']
    assert encoded['steps'][-1]['after'] == encoded['final_tableau']


def test_encode_report_records_the_candidates_of_every_step():
    encoded = encode_report(SimplexAlgorithm().solve_inequality_form(problem()))
    step = encoded['steps'][0]

    assert [candidate['var']['symbol'] for candidate in step['entering_candidates']] == ['x1', 'x2']
    assert step['entering']['symbol'] == 'x1'
    assert [candidate['var']['symbol'] for candidate in step['leaving_candidates']] == ['sl0', 'sl1']
    assert step['leaving']['symbol'] in [candidate['var']['symbol'] for candidate in step['leaving_candidates']]
    assert step['violated_row_basic_var'] is None
