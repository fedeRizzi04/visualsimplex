// Minimal element helper.
//
// Everything user-supplied reaches the page as a text node, never as markup, so a variable named `<script>` is shown
// and not executed.

type Child = Node | string | null | false

interface ElementOptions {
  class?: string
  text?: string
  title?: string
  onClick?: () => void
}

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  options: ElementOptions = {},
  children: Child[] = [],
): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag)
  if (options.class) element.className = options.class
  if (options.text !== undefined) element.textContent = options.text
  if (options.title) element.title = options.title
  if (options.onClick) element.addEventListener('click', options.onClick)
  for (const child of children) {
    if (child === null || child === false) continue
    element.append(typeof child === 'string' ? document.createTextNode(child) : child)
  }
  return element
}

export function replaceChildren(host: HTMLElement, ...children: Child[]): void {
  host.replaceChildren(...children.filter((child): child is Node | string => child !== null && child !== false))
}

export function classes(...names: (string | false | null | undefined)[]): string {
  return names.filter(Boolean).join(' ')
}
