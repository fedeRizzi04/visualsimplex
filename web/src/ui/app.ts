import type { ProblemSpec, Report, Rules } from '../model/types'
import { highlightFor, lastCursor, pendingStep, tableauAt } from '../model/walkthrough'
import type { SimplexEngine } from '../runtime/engine'
import { el, replaceChildren } from './dom'
import { problemForm } from './problemForm'
import { outcomePanel, stepPanel } from './stepPanel'
import { basisSummary, tableauView } from './tableauView'

type View =
  | { kind: 'idle' }
  | { kind: 'failed'; error: string }
  | { kind: 'solved'; report: Report; cursor: number }

const DEFAULT_PROBLEM: ProblemSpec = {
  sense: 'max',
  variables: ['x1', 'x2'],
  objective: ['3', '2'],
  constraints: [
    { coefficients: ['1', '1'], sense: '<=', rhs: '4' },
    { coefficients: ['1', '3'], sense: '<=', rhs: '6' },
  ],
  entering_rule: 'bland',
  leaving_rule: 'minimum_ratio',
}

/** Wire the form, the walkthrough and the engine together, and re-render the results on every state change. */
export function mountApp(host: HTMLElement, engine: SimplexEngine): void {
  let view: View = { kind: 'idle' }
  const results = el('div', { class: 'results' })

  function show(next: View): void {
    view = next
    renderResults()
  }

  function move(delta: number): void {
    if (view.kind !== 'solved') return
    show({ ...view, cursor: clamp(view.cursor + delta, 0, lastCursor(view.report)) })
  }

  function renderResults(): void {
    if (view.kind === 'idle') {
      replaceChildren(
        results,
        el('p', { class: 'note placeholder', text: 'Enter a problem and press “Solve” to walk through the pivot steps.' }),
      )
      return
    }
    if (view.kind === 'failed') {
      replaceChildren(
        results,
        el('section', { class: 'panel error' }, [
          el('h3', { text: 'The problem was rejected' }),
          el('p', { text: view.error }),
        ]),
      )
      return
    }
    replaceChildren(results, ...walkthrough(view.report, view.cursor, move))
  }

  const form = problemForm({
    rules: engine.rules,
    initial: defaultProblemFor(engine.rules),
    onSolve: (spec) => {
      const outcome = engine.solve(spec)
      show(outcome.ok ? { kind: 'solved', report: outcome.report, cursor: 0 } : { kind: 'failed', error: outcome.error })
    },
  })

  replaceChildren(host, form, results)
  renderResults()
}

function walkthrough(report: Report, cursor: number, move: (delta: number) => void): HTMLElement[] {
  const tableau = tableauAt(report, cursor)
  const step = pendingStep(report, cursor)
  const total = lastCursor(report)

  return [
    el('section', { class: 'panel tableau-panel' }, [
      el('header', { class: 'panel-header' }, [
        el('h2', { text: cursor === 0 ? 'Initial tableau' : `Tableau after step ${cursor}` }),
        navigation(cursor, total, move),
      ]),
      tableauView(tableau, step ? highlightFor(tableau, step) : null, report.sense),
      basisSummary(tableau, report.sense),
    ]),
    step ? stepPanel(step, cursor + 1, total) : outcomePanel(report),
  ]
}

function navigation(cursor: number, total: number, move: (delta: number) => void): HTMLElement {
  return el('nav', { class: 'navigation' }, [
    navButton('‹ Back', () => move(-1), cursor === 0),
    el('span', { class: 'counter', text: `${cursor} / ${total}` }),
    navButton('Next ›', () => move(1), cursor === total),
  ])
}

function navButton(text: string, onClick: () => void, disabled: boolean): HTMLButtonElement {
  const button = el('button', { class: 'secondary', text, onClick })
  button.type = 'button'
  button.disabled = disabled
  return button
}

/** Fall back to whatever rules the bridge actually offers, so a renamed rule cannot leave the form unsolvable. */
function defaultProblemFor(rules: Rules): ProblemSpec {
  return { ...DEFAULT_PROBLEM, entering_rule: rules.defaults.entering, leaving_rule: rules.defaults.leaving }
}

function clamp(value: number, low: number, high: number): number {
  return Math.min(Math.max(value, low), high)
}
