from fractions import Fraction
from typing import Any
from visualsimplex import EnteringCandidate, InitializationPivotStep, LeavingCandidate, PivotStep, SimplexReport, Tableau, TableauRow, Variable

Json = dict[str, Any]

INITIALIZATION_PHASE = 'initialization'
OPTIMIZATION_PHASE = 'optimization'


def encode_fraction(value : Fraction) -> Json:
    '''Encode an exact rational.

    Numerator and denominator are kept apart so a client can typeset a real fraction, while the ready-made text spares
    every client from reimplementing the "1" denominator case.
    '''
    return {'numerator': value.numerator, 'denominator': value.denominator, 'text': str(value)}


def encode_variable(variable : Variable) -> Json:
    return {'symbol': variable.symbol, 'kind': variable.kind.name.lower()}


def encode_entering_candidate(candidate : EnteringCandidate) -> Json:
    return {'var': encode_variable(candidate.var), 'reduced_cost': encode_fraction(candidate.reduced_cost)}


def encode_leaving_candidate(candidate : LeavingCandidate) -> Json:
    return {
        'var': encode_variable(candidate.var),
        'pivot': encode_fraction(candidate.pivot),
        'rhs': encode_fraction(candidate.rhs),
        'ratio': encode_fraction(candidate.ratio),
    }


def encode_row(row : TableauRow) -> Json:
    return {
        'basic_var': encode_variable(row.basic_var),
        'coefficients': [encode_fraction(coefficient) for coefficient in row.coefficients],
        'rhs': encode_fraction(row.rhs),
    }


def encode_tableau(tableau : Tableau) -> Json:
    '''Encode a tableau. Coefficient lists follow the order of `variables`, exactly as they do in the tableau itself.'''
    basic_variables = frozenset(tableau.basic_variables)
    return {
        'variables': [{**encode_variable(variable), 'is_basic': variable in basic_variables} for variable in tableau.variables],
        'reduced_costs': [encode_fraction(reduced_cost) for _, reduced_cost in tableau.reduced_costs],
        'rows': [encode_row(row) for row in tableau.rows],
        'basis': [{'var': encode_variable(variable), 'value': encode_fraction(tableau.get_value_for_basic_var(variable))}
                  for variable in tableau.basic_variables],
        'objective_value': encode_fraction(tableau.objective_value),
        'is_feasible': tableau.is_feasible_basis(),
        'is_optimal': tableau.is_optimal_basis(),
        'text': str(tableau),
    }


def encode_step(step : PivotStep, phase : str) -> Json:
    '''Encode a pivot step together with the candidates each choice was made among.

    Only the resulting tableau is carried: the tableau a step starts from is the previous step's `after`, or the
    report's `initial_tableau` for the first one, so embedding it again would double the payload for nothing.
    '''
    return {
        'phase': phase,
        'description': step.description,
        'entering_candidates': [encode_entering_candidate(candidate) for candidate in step.entering_candidates],
        'entering': encode_variable(step.entering),
        'leaving_candidates': [encode_leaving_candidate(candidate) for candidate in step.leaving_candidates],
        'leaving': encode_variable(step.leaving),
        'pivot': encode_fraction(step.pivot),
        'violated_row_basic_var': encode_variable(step.violated_row_basic_var) if isinstance(step, InitializationPivotStep) else None,
        'after': encode_tableau(step.after),
        'text': str(step),
    }


def encode_report(report : SimplexReport) -> Json:
    '''Encode a complete run: the starting tableau, every pivot in execution order and the final outcome.'''
    return {
        'problem': str(report.original_problem),
        'canonical_problem': str(report.canonical_problem.problem),
        'initial_tableau': encode_tableau(report.initial_tableau),
        'steps': [
            *(encode_step(step, INITIALIZATION_PHASE) for step in report.initialization_steps),
            *(encode_step(step, OPTIMIZATION_PHASE) for step in report.optimization_steps),
        ],
        'final_tableau': encode_tableau(report.final_tableau),
        'status': report.status.value,
        'termination_reason': report.termination_reason,
    }
