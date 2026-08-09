import json
from pathlib import Path
import pytest
import visualsimplex
from visualsimplex_bridge.api import available_rules, solve, solve_json


def spec(**overrides):
    base = {
        'sense': 'max',
        'objective': [3, 2],
        'constraints': [
            {'coefficients': [1, 1], 'sense': '<=', 'rhs': 4},
            {'coefficients': [1, 3], 'sense': '<=', 'rhs': 6},
        ],
    }
    return {**base, **overrides}


def test_solve_returns_an_optimal_report_for_a_feasible_problem():
    report = solve(spec())

    assert report['status'] == 'optimal'
    assert report['final_tableau']['is_optimal']
    assert report['steps']


def test_solve_uses_the_requested_rules():
    with_bland = solve(spec(objective=[3, 5], entering_rule='bland'))
    with_dantzig = solve(spec(objective=[3, 5], entering_rule='dantzig'))

    assert with_bland['steps'][0]['entering']['symbol'] == 'x1'
    assert with_dantzig['steps'][0]['entering']['symbol'] == 'x2'


def test_solve_rejects_an_unknown_rule_naming_the_available_ones():
    with pytest.raises(ValueError, match='unknown entering rule'):
        solve(spec(entering_rule='steepest_edge'))


def test_solve_accepts_exact_rationals_written_as_text():
    report = solve(spec(objective=['1/3', 2]))

    assert report['status'] == 'optimal'
    assert '1/3' in report['problem']


def test_solve_keeps_decimal_coefficients_exact():
    report = solve(spec(objective=[0.1, 2]))

    assert '1/10' in report['problem']


def test_solve_names_variables_when_the_spec_provides_them():
    report = solve(spec(variables=['pane', 'vino']))

    assert [variable['symbol'] for variable in report['initial_tableau']['variables'][:2]] == ['pane', 'vino']


def test_solve_rejects_a_variable_list_that_does_not_match_the_objective():
    with pytest.raises(ValueError, match='one per objective coefficient'):
        solve(spec(variables=['solo_una']))


@pytest.mark.parametrize('broken', [{'objective': []}, {'objective': 'x'}, {'constraints': []}])
def test_solve_rejects_a_malformed_spec(broken):
    with pytest.raises(ValueError, match='non-empty list'):
        solve(spec(**broken))


def test_solve_json_reports_success_as_data():
    outcome = json.loads(solve_json(json.dumps(spec())))

    assert outcome['ok']
    assert outcome['report']['status'] == 'optimal'


def test_solve_json_reports_a_rejected_problem_as_data_instead_of_raising():
    outcome = json.loads(solve_json(json.dumps(spec(entering_rule='steepest_edge'))))

    assert not outcome['ok']
    assert 'steepest_edge' in outcome['error']


def test_available_rules_expose_defaults_that_are_themselves_available():
    rules = available_rules()

    assert rules['defaults']['entering'] in [rule['id'] for rule in rules['entering']]
    assert rules['defaults']['leaving'] in [rule['id'] for rule in rules['leaving']]
    assert all(rule['label'] for rule in (*rules['entering'], *rules['leaving']))


def test_the_library_never_depends_on_the_bridge():
    '''The dependency runs web -> bridge -> library only: the library must stay unaware of anything built on top.'''
    sources = Path(visualsimplex.__file__).parent.glob('*.py')

    offenders = [source.name for source in sources if 'visualsimplex_bridge' in source.read_text()]

    assert offenders == []
