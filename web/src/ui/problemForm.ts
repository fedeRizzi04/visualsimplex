import type { ConstraintSense, OptimizationSense, ProblemSpec, Rule, Rules } from '../model/types'
import { el, replaceChildren } from './dom'

export interface ProblemFormOptions {
  rules: Rules
  initial: ProblemSpec
  onSolve: (spec: ProblemSpec) => void
}

/**
 * Editor for the problem and the two selection rules.
 *
 * Inputs are uncontrolled: the draft is read out of the DOM before every structural change and before submitting.
 * That keeps a keystroke from triggering a re-render — which would steal focus mid-typing — while still preserving
 * what the user typed when a row or a column is added.
 */
export function problemForm({ rules, initial, onSolve }: ProblemFormOptions): HTMLElement {
  let draft: ProblemSpec = structuredClone(initial)
  const host = el('form', { class: 'panel problem-form' })

  let variableInputs: HTMLInputElement[] = []
  let objectiveInputs: HTMLInputElement[] = []
  let constraintInputs: { coefficients: HTMLInputElement[]; sense: HTMLSelectElement; rhs: HTMLInputElement }[] = []
  let senseSelect: HTMLSelectElement
  let enteringSelect: HTMLSelectElement
  let leavingSelect: HTMLSelectElement

  function harvest(): ProblemSpec {
    draft = {
      sense: senseSelect.value as OptimizationSense,
      variables: variableInputs.map((input, index) => input.value.trim() || `x${index + 1}`),
      objective: objectiveInputs.map(coefficientOf),
      constraints: constraintInputs.map((row) => ({
        coefficients: row.coefficients.map(coefficientOf),
        sense: row.sense.value as ConstraintSense,
        rhs: coefficientOf(row.rhs),
      })),
      entering_rule: enteringSelect.value,
      leaving_rule: leavingSelect.value,
    }
    return draft
  }

  function restructure(change: (spec: ProblemSpec) => ProblemSpec): void {
    draft = change(harvest())
    render()
  }

  function addVariable(): void {
    restructure((spec) => ({
      ...spec,
      variables: [...spec.variables, `x${spec.variables.length + 1}`],
      objective: [...spec.objective, '0'],
      constraints: spec.constraints.map((constraint) => ({ ...constraint, coefficients: [...constraint.coefficients, '0'] })),
    }))
  }

  function removeVariable(index: number): void {
    restructure((spec) => ({
      ...spec,
      variables: without(spec.variables, index),
      objective: without(spec.objective, index),
      constraints: spec.constraints.map((constraint) => ({ ...constraint, coefficients: without(constraint.coefficients, index) })),
    }))
  }

  function addConstraint(): void {
    restructure((spec) => ({
      ...spec,
      constraints: [...spec.constraints, { coefficients: spec.variables.map(() => '0'), sense: '<=', rhs: '0' }],
    }))
  }

  function removeConstraint(index: number): void {
    restructure((spec) => ({ ...spec, constraints: without(spec.constraints, index) }))
  }

  function render(): void {
    variableInputs = draft.variables.map((symbol) => textInput(symbol, 'symbol'))
    objectiveInputs = draft.objective.map((coefficient) => textInput(coefficient, 'coefficient'))
    constraintInputs = draft.constraints.map((constraint) => ({
      coefficients: constraint.coefficients.map((coefficient) => textInput(coefficient, 'coefficient')),
      sense: select([{ id: '<=', label: '≤' }, { id: '>=', label: '≥' }], constraint.sense),
      rhs: textInput(constraint.rhs, 'coefficient'),
    }))
    senseSelect = select([{ id: 'max', label: 'max' }, { id: 'min', label: 'min' }], draft.sense)
    enteringSelect = select(rules.entering, draft.entering_rule)
    leavingSelect = select(rules.leaving, draft.leaving_rule)

    replaceChildren(
      host,
      el('h2', { text: 'Problem' }),
      el('div', { class: 'grid-scroll' }, [
        el('table', { class: 'problem-grid' }, [
          el('thead', {}, [
            el('tr', {}, [
              el('th', { text: '' }),
              ...variableInputs.map((input, index) =>
                el('th', {}, [input, iconButton('×', 'Remove variable', () => removeVariable(index), draft.variables.length <= 1)]),
              ),
              el('th', { text: '' }),
              el('th', { text: '' }),
              el('th', { text: '' }),
            ]),
          ]),
          el('tbody', {}, [
            el('tr', { class: 'objective-row' }, [
              el('th', {}, [senseSelect, el('span', { class: 'label', text: ' z =' })]),
              ...objectiveInputs.map((input) => el('td', {}, [input])),
              el('td', { text: '' }),
              el('td', { text: '' }),
              el('td', { text: '' }),
            ]),
            ...constraintInputs.map((row, index) =>
              el('tr', {}, [
                el('th', { class: 'label', text: index === 0 ? 'subject to' : '' }),
                ...row.coefficients.map((input) => el('td', {}, [input])),
                el('td', {}, [row.sense]),
                el('td', {}, [row.rhs]),
                el('td', {}, [iconButton('×', 'Remove constraint', () => removeConstraint(index), draft.constraints.length <= 1)]),
              ]),
            ),
          ]),
        ]),
      ]),
      el('div', { class: 'form-actions' }, [
        secondaryButton('+ variable', addVariable),
        secondaryButton('+ constraint', addConstraint),
      ]),
      el('p', { class: 'note', text: 'All variables are ≥ 0. Coefficients accept decimals (0.5) and exact fractions (1/3).' }),
      el('div', { class: 'rule-pickers' }, [
        labelled('Column rule (entering variable)', enteringSelect),
        labelled('Row rule (leaving variable)', leavingSelect),
      ]),
      el('button', { class: 'primary', text: 'Solve' }),
    )
  }

  host.addEventListener('submit', (event) => {
    event.preventDefault()
    onSolve(harvest())
  })

  render()
  return host
}

function coefficientOf(input: HTMLInputElement): string {
  return input.value.trim() || '0'
}

function without<T>(values: T[], index: number): T[] {
  return values.filter((_, position) => position !== index)
}

function textInput(value: string, className: string): HTMLInputElement {
  const input = el('input', { class: className })
  input.type = 'text'
  input.value = value
  input.spellcheck = false
  return input
}

function select(options: Rule[], selected: string): HTMLSelectElement {
  const element = el('select')
  for (const option of options) {
    const item = el('option', { text: option.label })
    item.value = option.id
    element.append(item)
  }
  element.value = selected
  return element
}

function labelled(text: string, control: HTMLElement): HTMLElement {
  return el('label', { class: 'field' }, [el('span', { text }), control])
}

function iconButton(glyph: string, title: string, onClick: () => void, disabled: boolean): HTMLButtonElement {
  const button = el('button', { class: 'icon', text: glyph, title, onClick })
  button.type = 'button'
  button.disabled = disabled
  return button
}

function secondaryButton(text: string, onClick: () => void): HTMLButtonElement {
  const button = el('button', { class: 'secondary', text, onClick })
  button.type = 'button'
  return button
}
