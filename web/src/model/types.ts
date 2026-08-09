// The contract with visualsimplex-bridge.
//
// Every shape here mirrors one encode_* function in bridge/src/visualsimplex_bridge/encoding.py. This is the single
// file to open when Python and TypeScript disagree, and the single file to change when the encoding changes: nothing
// else in the app is allowed to touch raw JSON.

/** An exact rational. Numerator and denominator allow proper typesetting; `text` is the ready-made rendering. */
export interface Fraction {
  numerator: number
  denominator: number
  text: string
}

export type VariableKind = 'original' | 'slack' | 'surplus'

export interface Variable {
  symbol: string
  kind: VariableKind
}

export interface TableauVariable extends Variable {
  is_basic: boolean
}

export interface TableauRow {
  basic_var: Variable
  coefficients: Fraction[]
  rhs: Fraction
}

export interface BasisEntry {
  var: Variable
  value: Fraction
}

/** All coefficient lists follow the order of `variables`, exactly as they do in the tableau itself. */
export interface Tableau {
  variables: TableauVariable[]
  reduced_costs: Fraction[]
  rows: TableauRow[]
  basis: BasisEntry[]
  /** The value literally held in the tableau's top-left cell (the "-w" convention): -objective_value, always the
   * one consistent with the reduced costs shown alongside it. This is what a tableau rendering should display. */
  objective_tableau_value: Fraction
  /** The resolved canonical-form (minimization) value: -objective_tableau_value. */
  objective_value: Fraction
  /** The same solution measured in the problem the user wrote — the opposite sign for a maximization. */
  original_objective_value: Fraction
  is_feasible: boolean
  is_optimal: boolean
  text: string
}

export interface EnteringCandidate {
  var: Variable
  reduced_cost: Fraction
}

export interface LeavingCandidate {
  var: Variable
  pivot: Fraction
  rhs: Fraction
  ratio: Fraction
}

export type Phase = 'initialization' | 'optimization'

/** A step carries only the tableau it produces: the one it starts from is the previous step's `after`. */
export interface Step {
  phase: Phase
  description: string
  entering_candidates: EnteringCandidate[]
  entering: Variable
  leaving_candidates: LeavingCandidate[]
  leaving: Variable
  pivot: Fraction
  violated_row_basic_var: Variable | null
  after: Tableau
  text: string
}

export type Status = 'optimal' | 'unbounded' | 'infeasible'

export interface Report {
  problem: string
  canonical_problem: string
  /** Sense of the problem the user wrote, which is what `original_objective_value` is expressed in. */
  sense: OptimizationSense
  initial_tableau: Tableau
  steps: Step[]
  final_tableau: Tableau
  status: Status
  termination_reason: string
  /** The variables that can grow without bound in `final_tableau`: negative reduced cost, no positive coefficient
   * in any row. Only non-empty when `status` is 'unbounded'. */
  unbounded_directions: Variable[]
}

export interface Rule {
  id: string
  label: string
}

export interface Rules {
  entering: Rule[]
  leaving: Rule[]
  defaults: { entering: string; leaving: string }
}

export type OptimizationSense = 'max' | 'min'
export type ConstraintSense = '<=' | '>='

/** A coefficient the user typed: a decimal, or text such as "1/3" for an exact rational. */
export type Coefficient = string

export interface ConstraintSpec {
  coefficients: Coefficient[]
  sense: ConstraintSense
  rhs: Coefficient
}

export interface ProblemSpec {
  sense: OptimizationSense
  objective: Coefficient[]
  constraints: ConstraintSpec[]
  variables: string[]
  entering_rule: string
  leaving_rule: string
}

export type SolveOutcome = { ok: true; report: Report } | { ok: false; error: string }
