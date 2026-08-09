// Boots CPython in the browser and exposes the bridge as a plain async function.
//
// Everything Python-specific is confined to this file: the rest of the app only ever sees TypeScript values. Strings
// cross the boundary in both directions, so no JavaScript object is implicitly converted into a Python one.

import type { ProblemSpec, Rules, SolveOutcome } from '../model/types'

const PYODIDE_VERSION = '0.28.3'
const PYODIDE_INDEX = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`

interface WheelManifest {
  library: string
  bridge: string
}

interface Pyodide {
  loadPackage(name: string): Promise<void>
  runPython(code: string): unknown
  runPythonAsync(code: string): Promise<unknown>
}

export type BootProgress = (message: string) => void

export class SimplexEngine {
  private constructor(
    private readonly solveJson: (spec: string) => string,
    readonly rules: Rules,
  ) {}

  static async boot(onProgress: BootProgress): Promise<SimplexEngine> {
    onProgress('Loading the Python interpreter…')
    const { loadPyodide } = (await import(/* @vite-ignore */ `${PYODIDE_INDEX}pyodide.mjs`)) as {
      loadPyodide(options: { indexURL: string }): Promise<Pyodide>
    }
    const pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX })

    onProgress('Installing VisualSimplex…')
    const wheels = await resolveWheelUrls()
    await pyodide.loadPackage('micropip')
    await pyodide.runPythonAsync(`
import micropip
await micropip.install(${quote(wheels.library)})
await micropip.install(${quote(wheels.bridge)}, deps=False)
`)

    const solveJson = pyodide.runPython(`
from visualsimplex_bridge import solve_json
solve_json
`) as (spec: string) => string
    const rules = JSON.parse(
      pyodide.runPython(`
import json
from visualsimplex_bridge import available_rules
json.dumps(available_rules())
`) as string,
    ) as Rules

    onProgress('Ready')
    return new SimplexEngine(solveJson, rules)
  }

  /** Solve a problem. A rejected problem comes back as `{ ok: false }` rather than throwing. */
  solve(spec: ProblemSpec): SolveOutcome {
    return JSON.parse(this.solveJson(JSON.stringify(spec))) as SolveOutcome
  }
}

async function resolveWheelUrls(): Promise<WheelManifest> {
  const directory = new URL('wheels/', new URL(import.meta.env.BASE_URL, location.href))
  const response = await fetch(new URL('manifest.json', directory))
  if (!response.ok) {
    throw new Error('Wheel manifest not found: run "npm run wheels".')
  }
  const manifest = (await response.json()) as WheelManifest
  return {
    library: new URL(manifest.library, directory).toString(),
    bridge: new URL(manifest.bridge, directory).toString(),
  }
}

/** Embed a URL in generated Python source as a literal that cannot terminate the string early. */
function quote(value: string): string {
  return JSON.stringify(value)
}
