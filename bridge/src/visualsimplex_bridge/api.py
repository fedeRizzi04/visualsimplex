import json
from collections.abc import Mapping, Sequence
from fractions import Fraction
from typing import Any
from visualsimplex import LPProblem, SimplexAlgorithm, bland_rule, dantzig_rule, minimum_ratio_rule
from visualsimplex_bridge.encoding import Json, encode_report

ENTERING_RULES = {
    'bland': ('Bland', bland_rule),
    'dantzig': ('Dantzig', dantzig_rule),
}
'''Entering-variable rules a client may choose from, keyed by the identifier it sends back in a spec.'''

LEAVING_RULES = {
    'minimum_ratio': ('Minimum ratio', minimum_ratio_rule),
}
'''Leaving-variable rules a client may choose from, keyed by the identifier it sends back in a spec.'''

DEFAULT_ENTERING_RULE = 'bland'
DEFAULT_LEAVING_RULE = 'minimum_ratio'


def available_rules() -> Json:
    '''Describe the selectable rules so that a client can populate its pickers without hardcoding them.'''
    return {
        'entering': [{'id': identifier, 'label': label} for identifier, (label, _) in ENTERING_RULES.items()],
        'leaving': [{'id': identifier, 'label': label} for identifier, (label, _) in LEAVING_RULES.items()],
        'defaults': {'entering': DEFAULT_ENTERING_RULE, 'leaving': DEFAULT_LEAVING_RULE},
    }


def solve(spec : Mapping[str, Any]) -> Json:
    '''Solve the problem described by spec and return its encoded report.

    The spec shape is:
        {
          "sense": "max" | "min",
          "objective": [coefficient, ...],
          "constraints": [{"coefficients": [...], "sense": "<=" | ">=" , "rhs": value}, ...],
          "variables": ["x1", ...],          # optional, defaults to x1, x2, ...
          "entering_rule": "bland",          # optional
          "leaving_rule": "minimum_ratio"    # optional
        }
    Coefficients accept integers, decimals and exact rationals written as text such as "1/3".
    '''
    problem = _build_problem(spec)
    algorithm = SimplexAlgorithm(
        entering_rule=_rule(ENTERING_RULES, spec.get('entering_rule') or DEFAULT_ENTERING_RULE, 'entering'),
        leaving_rule=_rule(LEAVING_RULES, spec.get('leaving_rule') or DEFAULT_LEAVING_RULE, 'leaving'),
    )
    return encode_report(algorithm.solve_inequality_form(problem))


def solve_json(spec_json : str) -> str:
    '''Solve a JSON-encoded spec and return a JSON-encoded outcome.

    This is the boundary the browser calls: strings cross it in both directions, so no JavaScript value is ever
    converted into a Python object implicitly. A rejected problem is reported as data rather than raised, because an
    exception crossing into JavaScript loses the message a student needs to read.
    '''
    try:
        return json.dumps({'ok': True, 'report': solve(json.loads(spec_json))})
    except (ValueError, TypeError, KeyError, RuntimeError) as error:
        return json.dumps({'ok': False, 'error': str(error)})


def _build_problem(spec : Mapping[str, Any]) -> LPProblem:
    objective = _sequence(spec, 'objective')
    symbols = spec.get('variables') or [f'x{index}' for index in range(1, len(objective) + 1)]
    if len(symbols) != len(objective):
        raise ValueError(f'expected {len(objective)} variable names (one per objective coefficient), got {len(symbols)}')

    builder = LPProblem.builder(spec['sense'])
    for symbol, coefficient in zip(symbols, objective):
        builder.add_variable(symbol, _to_fraction(coefficient))
    for constraint in _sequence(spec, 'constraints'):
        coefficients = tuple(_to_fraction(coefficient) for coefficient in constraint['coefficients'])
        builder.add_constraint(coefficients, constraint['sense'], _to_fraction(constraint['rhs']))
    return builder.build()


def _rule(registry : Mapping[str, Any], identifier : str, kind : str):
    if identifier not in registry:
        raise ValueError(f'unknown {kind} rule {identifier!r}, available: {", ".join(sorted(registry))}')
    return registry[identifier][1]


def _sequence(spec : Mapping[str, Any], key : str) -> Sequence[Any]:
    value = spec.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str) or not value:
        raise ValueError(f'{key!r} must be a non-empty list')
    return value


def _to_fraction(value : Any) -> Fraction:
    '''Parse a coefficient arriving from JSON.

    JavaScript has a single number type, so integers reach Python as floats: routing them through str() keeps 0.1
    meaning one tenth instead of its binary approximation. Text is accepted too, which is how a client sends an exact
    rational such as "1/3".
    '''
    if isinstance(value, bool):
        raise ValueError(f'{value!r} is not a valid coefficient')
    if isinstance(value, float):
        return Fraction(str(value))
    if isinstance(value, (int, str)):
        return Fraction(value)
    raise ValueError(f'{value!r} is not a valid coefficient')
