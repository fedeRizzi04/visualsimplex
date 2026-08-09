// Reading model over a report.
//
// A walkthrough is a cursor in [0, steps.length]. At cursor k the app shows the tableau reached so far together with
// the step *about to happen*, so a student sees the candidates on the tableau they are looking at and only then
// advances. At cursor steps.length there is nothing left to perform and the run is over.

import type { Report, Step, Tableau, Variable } from './types'

export interface Highlight {
  /** Column of the entering variable, and the columns of every variable that could have entered instead. */
  enteringColumn: number
  candidateColumns: ReadonlySet<number>
  /** Row of the leaving variable, and the rows of every basic variable that could have left instead. */
  leavingRow: number
  candidateRows: ReadonlySet<number>
  /** Row being repaired during initialization, absent during optimization. */
  violatedRow: number | null
  /** Columns of the variables that make the tableau unbounded, present only on the tableau a run stopped at. */
  unboundedColumns?: ReadonlySet<number>
}

export function lastCursor(report: Report): number {
  return report.steps.length
}

export function tableauAt(report: Report, cursor: number): Tableau {
  const previous = report.steps[cursor - 1]
  return previous ? previous.after : report.initial_tableau
}

/** The step performed by advancing from `cursor`, or null once every step has been performed. */
export function pendingStep(report: Report, cursor: number): Step | null {
  return report.steps[cursor] ?? null
}

export function highlightFor(tableau: Tableau, step: Step): Highlight {
  return {
    enteringColumn: columnOf(tableau, step.entering),
    candidateColumns: new Set(step.entering_candidates.map((candidate) => columnOf(tableau, candidate.var))),
    leavingRow: rowOf(tableau, step.leaving),
    candidateRows: new Set(step.leaving_candidates.map((candidate) => rowOf(tableau, candidate.var))),
    violatedRow: step.violated_row_basic_var ? rowOf(tableau, step.violated_row_basic_var) : null,
  }
}

/** Highlight for the tableau an unbounded run stopped at: the columns of `report.unbounded_directions`, with no
 * entering/leaving pivot to show since the run never performed one on this tableau. */
export function unboundedHighlight(tableau: Tableau, report: Report): Highlight {
  return {
    enteringColumn: -1,
    candidateColumns: new Set(),
    leavingRow: -1,
    candidateRows: new Set(),
    violatedRow: null,
    unboundedColumns: new Set(report.unbounded_directions.map((variable) => columnOf(tableau, variable))),
  }
}

/** Column index of a variable, or -1 when the tableau does not contain it. */
export function columnOf(tableau: Tableau, variable: Variable): number {
  return tableau.variables.findIndex((candidate) => candidate.symbol === variable.symbol)
}

/** Index of the row whose basic variable is the given one, or -1 when no row has it in the basis. */
export function rowOf(tableau: Tableau, variable: Variable): number {
  return tableau.rows.findIndex((row) => row.basic_var.symbol === variable.symbol)
}
