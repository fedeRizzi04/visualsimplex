// Builds the Python wheels the browser installs and records their exact filenames in a manifest.
//
// The manifest exists because a wheel filename carries its version: without it the app would have to hardcode
// "0.1.0" in TypeScript and would silently load a stale wheel at the first version bump. `npm run build` calls this
// first, so a deploy can never ship a frontend and a wheel that disagree.

import { execFileSync } from 'node:child_process'
import { mkdirSync, readdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const workspaceRoot = resolve(webRoot, '..')
const outputDirectory = join(webRoot, 'public', 'wheels')

function findWheel(prefix) {
  const matches = readdirSync(outputDirectory).filter((name) => name.startsWith(prefix) && name.endsWith('.whl'))
  if (matches.length !== 1) {
    throw new Error(`expected exactly one ${prefix}*.whl in ${outputDirectory}, found ${matches.length}`)
  }
  return matches[0]
}

rmSync(outputDirectory, { recursive: true, force: true })
mkdirSync(outputDirectory, { recursive: true })

execFileSync('uv', ['build', '--all-packages', '--wheel', '--out-dir', outputDirectory], {
  cwd: workspaceRoot,
  stdio: 'inherit',
})

// The bridge is installed with deps=False against this manifest, so the library must be listed first.
const manifest = {
  library: findWheel('visualsimplex-'),
  bridge: findWheel('visualsimplex_bridge-'),
}
writeFileSync(join(outputDirectory, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`)

console.log(`wheels ready: ${manifest.library}, ${manifest.bridge}`)
