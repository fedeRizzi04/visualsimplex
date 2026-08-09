import type { OptimizationSense, Tableau } from '../model/types'
import type { Highlight } from '../model/walkthrough'
import { classes, el } from './dom'

/**
 * Render a tableau in the shape used on the blackboard: the value column on the left, separated by a vertical rule
 * from the coefficients, the variable names above their own columns, and the basic variable of each row on the right.
 * A horizontal rule under the objective row separates it from the constraints.
 *
 * Highlighting works on three levels: eligible alternatives are tinted, the selected row and column are outlined, and
 * only their intersection — the pivot — is filled. A student should see at a glance what could have been chosen and
 * what actually was. On the tableau where an unbounded run stopped there is no pivot to show instead: the columns of
 * `unboundedColumns` are marked with their own (danger-toned) style, distinct from a merely eligible alternative.
 */
export function tableauView(tableau: Tableau, highlight: Highlight | null, sense: OptimizationSense): HTMLElement {
  return el('div', { class: 'tableau-scroll' }, [
    el('table', { class: 'tableau' }, [
      el('thead', {}, [headerRow(tableau)]),
      el('tbody', {}, [
        objectiveRow(tableau, highlight, sense),
        ...tableau.rows.map((_, index) => constraintRow(tableau, index, highlight)),
      ]),
    ]),
  ])
}

function headerRow(tableau: Tableau): HTMLElement {
  return el('tr', {}, [
    // One cell labels the whole left column, which holds two different quantities: the tableau's objective value on
    // the row right below (always the "-w" convention, see objectiveCellTitle), and the right-hand sides on the rows
    // under the rule.
    el('th', { class: 'value-header' }, [
      el('span', { class: 'label-z', text: '-w' }),
      el('span', { class: 'label-b', text: 'b' }),
    ]),
    ...tableau.variables.map((variable) =>
      el('th', {
        class: classes('variable', `kind-${variable.kind}`),
        text: variable.symbol,
        title: `${variable.kind} variable`,
      }),
    ),
    el('th', { class: 'basis-header', text: 'basis' }),
  ])
}

function objectiveRow(tableau: Tableau, highlight: Highlight | null, sense: OptimizationSense): HTMLElement {
  return el('tr', { class: 'objective' }, [
    el('td', {
      class: 'value',
      text: tableau.objective_tableau_value.text,
      title: objectiveCellTitle(sense),
    }),
    ...tableau.reduced_costs.map((cost, column) =>
      el('td', { class: classes('coefficient', columnClasses(column, highlight)), text: cost.text }),
    ),
    el('td', { class: 'basis' }),
  ])
}

function constraintRow(tableau: Tableau, rowIndex: number, highlight: Highlight | null): HTMLElement {
  const row = tableau.rows[rowIndex]!
  const isLeaving = highlight?.leavingRow === rowIndex
  const rowClass = classes(
    isLeaving && 'is-leaving',
    highlight?.candidateRows.has(rowIndex) && 'is-candidate-row',
    highlight?.violatedRow === rowIndex && 'is-violated',
    row.rhs.numerator < 0 && 'is-infeasible',
  )
  return el('tr', { class: rowClass }, [
    el('td', { class: 'value', text: row.rhs.text }),
    ...row.coefficients.map((coefficient, column) =>
      el('td', {
        class: classes(
          'coefficient',
          columnClasses(column, highlight),
          isLeaving && highlight?.enteringColumn === column && 'is-pivot',
        ),
        text: coefficient.text,
      }),
    ),
    el('th', { class: 'basis', text: row.basic_var.symbol }),
  ])
}

function objectiveCellTitle(sense: OptimizationSense): string {
  return sense === 'max'
    ? 'Value literally held by the tableau (the "-w" convention): w = -this value, and since the problem maximizes, z = this value.'
    : 'Value literally held by the tableau (the "-w" convention): w = -this value.'
}

function columnClasses(column: number, highlight: Highlight | null): string {
  return classes(
    highlight?.enteringColumn === column && 'is-entering',
    highlight?.candidateColumns.has(column) && 'is-candidate-column',
    highlight?.unboundedColumns?.has(column) && 'is-unbounded-column',
  )
}

/**
 * The current vertex in words: which variables are in the basis, at what value, and what the solution is worth.
 *
 * For a maximization, w (the canonical minimum the tableau works with) and z (what the user actually asked to
 * maximize) are shown as separate lines with their relation spelled out, rather than silently reporting only z —
 * that would leave w's value, printed in the tableau above, unexplained.
 */
export function basisSummary(tableau: Tableau, sense: OptimizationSense): HTMLElement {
  return el('dl', { class: 'summary' }, [
    entry('Basis', tableau.basis.map(({ var: variable, value }) => `${variable.symbol} = ${value.text}`).join(',  ') || '—'),
    ...objectiveEntries(tableau, sense),
    entry('Basis status', basisState(tableau)),
  ])
}

function objectiveEntries(tableau: Tableau, sense: OptimizationSense): HTMLElement[] {
  if (sense === 'max') {
    return [entry('w', tableau.objective_value.text), entry('z = -w', tableau.original_objective_value.text, 'objective-value')]
  }
  return [entry('Objective value (min)', tableau.original_objective_value.text, 'objective-value')]
}

function entry(term: string, description: string, className?: string): HTMLElement {
  return el('div', {}, [el('dt', { text: term }), el('dd', { class: className, text: description })])
}

function basisState(tableau: Tableau): string {
  if (!tableau.is_feasible) return 'infeasible'
  return tableau.is_optimal ? 'feasible and optimal' : 'feasible'
}
