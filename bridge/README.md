# visualsimplex-bridge

Translates `visualsimplex` domain objects into plain JSON for the VisualSimplex web app.

This package exists so that the presentation-shaped decisions — how an exact `Fraction` is rendered, which parts of a
report a client needs — live outside the library. `visualsimplex` never imports this package; the dependency runs one
way only.

It is **not published**: the `Private :: Do Not Upload` classifier makes PyPI reject it. It is built into a wheel
purely so Pyodide can install it in the browser.
