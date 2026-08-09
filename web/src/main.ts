import './styles.css'
import { SimplexEngine } from './runtime/engine'
import { el, replaceChildren } from './ui/dom'
import { mountApp } from './ui/app'

const host = document.querySelector<HTMLElement>('#app')
if (!host) throw new Error('missing #app host element')

const status = el('p', { class: 'boot-status', text: 'Starting…' })
replaceChildren(host, el('div', { class: 'boot' }, [el('div', { class: 'spinner' }), status]))

// Booting downloads a few megabytes of WebAssembly the first time, so the page says what it is waiting for instead
// of showing an empty frame. The browser caches it, and later visits start almost immediately.
SimplexEngine.boot((message) => {
  status.textContent = message
}).then(
  (engine) => mountApp(host, engine),
  (error: unknown) => {
    replaceChildren(
      host,
      el('section', { class: 'panel error' }, [
        el('h3', { text: 'Startup failed' }),
        el('p', { text: error instanceof Error ? error.message : String(error) }),
      ]),
    )
  },
)
