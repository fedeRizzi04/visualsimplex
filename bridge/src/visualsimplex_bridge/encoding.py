from fractions import Fraction
from typing import Any
from visualsimplex import EnteringCandidate, InitializationPivotStep, LeavingCandidate, OptimizationSense, PivotStep, SimplexReport, Tableau, TableauRow, Variable

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


def encode_tableau(tableau : Tableau, opt_sense : OptimizationSense) -> Json:
    '''Encode a tableau. Coefficient lists follow the order of `variables`, exactly as they do in the tableau itself.

    Two objective values are reported because they answer two different questions. `objective_value` is the quantity
    the tableau actually holds, always a minimization since that is the canonical form the algorithm works in, and it
    is the one consistent with the reduced costs shown alongside it. `original_objective_value` is the same solution
    measured in the problem the user wrote: for a maximization the two differ by a sign, and showing the canonical one
    would tell a student their maximum is negative.
    '''
    basic_variables = frozenset(tableau.basic_variables)
    return {
        'variables': [{**encode_variable(variable), 'is_basic': variable in basic_variables} for variable in tableau.variables],
        'reduced_costs': [encode_fraction(reduced_cost) for _, reduced_cost in tableau.reduced_costs],
        'rows': [encode_row(row) for row in tableau.rows],
        'basis': [{'var': encode_variable(variable), 'value': encode_fraction(tableau.get_value_for_basic_var(variable))}
                  for variable in tableau.basic_variables],
        'objective_value': encode_fraction(tableau.objective_value),
        'original_objective_value': encode_fraction(_in_original_sense(tableau.objective_value, opt_sense)),
        'is_feasible': tableau.is_feasible_basis(),
        'is_optimal': tableau.is_optimal_basis(),
        'text': str(tableau),
    }


def _in_original_sense(objective_value : Fraction, opt_sense : OptimizationSense) -> Fraction:
    '''Undo the negation that turned a maximization into the minimization the canonical form requires.'''
    return -objective_value if opt_sense is OptimizationSense.MAXIMIZE else objective_value


def encode_step(step : PivotStep, phase : str, opt_sense : OptimizationSense) -> Json:
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
        'after': encode_tableau(step.after, opt_sense),
        'text': str(step),
    }


def encode_report(report : SimplexReport) -> Json:
    '''Encode a complete run: the starting tableau, every pivot in execution order and the final outcome.'''
    opt_sense = report.original_problem.opt_sense()
    return {
        'problem': str(report.original_problem),
        'canonical_problem': str(report.canonical_problem.problem),
        'sense': opt_sense.value,
        'initial_tableau': encode_tableau(report.initial_tableau, opt_sense),
        'steps': [
            *(encode_step(step, INITIALIZATION_PHASE, opt_sense) for step in report.initialization_steps),
            *(encode_step(step, OPTIMIZATION_PHASE, opt_sense) for step in report.optimization_steps),
        ],
        'final_tableau': encode_tableau(report.final_tableau, opt_sense),
        'status': report.status.value,
        'termination_reason': report.termination_reason,
    }
