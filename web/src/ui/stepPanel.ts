import type { EnteringCandidate, LeavingCandidate, Report, Step } from '../model/types'
import { classes, el } from './dom'

const PHASE_LABEL: Record<Step['phase'], string> = {
  initialization: 'Initialization (Balinski-Gomory)',
  optimization: 'Optimization',
}

const STATUS_LABEL: Record<Report['status'], string> = {
  optimal: 'Optimal solution found',
  unbounded: 'Unbounded problem',
  infeasible: 'Infeasible problem',
}

/** Describe the pivot about to be performed: who may enter, who may leave, and which pair the rules picked. */
export function stepPanel(step: Step, stepNumber: number, totalSteps: number): HTMLElement {
  return el('section', { class: 'panel step-panel' }, [
    el('header', { class: 'panel-header' }, [
      el('span', { class: classes('phase', `phase-${step.phase}`), text: PHASE_LABEL[step.phase] }),
      el('span', { class: 'counter', text: `Step ${stepNumber} of ${totalSteps}` }),
    ]),
    step.violated_row_basic_var
      ? el('p', { class: 'note', text: `Repairing the row of ${step.violated_row_basic_var.symbol}, whose right-hand side is negative.` })
      : null,
    el('div', { class: 'candidate-columns' }, [
      candidateTable(
        'Can enter the basis',
        ['Variable', 'Reduced cost'],
        step.entering_candidates,
        (candidate) => [candidate.var.symbol, candidate.reduced_cost.text],
        (candidate) => candidate.var.symbol === step.entering.symbol,
      ),
      candidateTable(
        'Can leave the basis',
        ['Variable', 'Pivot', 'b', 'Ratio b/pivot'],
        step.leaving_candidates,
        (candidate) => [candidate.var.symbol, candidate.pivot.text, candidate.rhs.text, candidate.ratio.text],
        (candidate) => candidate.var.symbol === step.leaving.symbol,
      ),
    ]),
    el('p', { class: 'outcome' }, [
      el('strong', { text: step.entering.symbol }),
      ' enters the basis, ',
      el('strong', { text: step.leaving.symbol }),
      ' leaves it. The pivot is ',
      el('strong', { text: step.pivot.text }),
      '.',
    ]),
  ])
}

function candidateTable<T extends EnteringCandidate | LeavingCandidate>(
  title: string,
  headers: string[],
  candidates: T[],
  cells: (candidate: T) => string[],
  isChosen: (candidate: T) => boolean,
): HTMLElement {
  if (candidates.length === 0) {
    return el('div', { class: 'candidates' }, [el('h3', { text: title }), el('p', { class: 'note', text: 'No candidates.' })])
  }
  return el('div', { class: 'candidates' }, [
    el('h3', { text: title }),
    el('table', { class: 'candidate-table' }, [
      el('thead', {}, [el('tr', {}, headers.map((header) => el('th', { text: header })))]),
      el(
        'tbody',
        {},
        candidates.map((candidate) =>
          el(
            'tr',
            {
              class: classes(isChosen(candidate) && 'is-chosen'),
              title: isChosen(candidate) ? 'Selected by the rule' : undefined,
            },
            cells(candidate).map((value) => el('td', { text: value })),
          ),
        ),
      ),
    ]),
  ])
}

/** Shown once every step has been performed: the mathematical outcome of the run. */
export function outcomePanel(report: Report): HTMLElement {
  return el('section', { class: classes('panel', 'outcome-panel', `status-${report.status}`) }, [
    el('h3', { text: STATUS_LABEL[report.status] }),
    el('p', { class: 'note', text: report.termination_reason }),
    report.status === 'optimal'
      ? el('p', {}, [
          `Optimal value (${report.sense}): `,
          el('strong', { text: report.final_tableau.original_objective_value.text }),
        ])
      : null,
    report.status === 'unbounded'
      ? el('p', {}, [
          report.unbounded_directions.length === 1 ? 'Unbounded column: ' : 'Unbounded columns: ',
          el('strong', { text: report.unbounded_directions.map((variable) => variable.symbol).join(', ') }),
          ', highlighted above in red.',
        ])
      : null,
  ])
}
