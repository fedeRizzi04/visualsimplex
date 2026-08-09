# VisualSimplex

> VisualSimplex is an early-stage educational project under development. Its API and features may change frequently, and its results may be incomplete or incorrect. Always verify them independently before relying on them.

VisualSimplex has been created to help students understand the simplex algorithm by showing how a solution evolves one pivot at a time, instead of presenting only the final result. The long-term goal is to provide a Python library for exploring and visualizing every step of the algorithm. The library is not yet published on PyPI.

The current version supports feasible-basis initialization with the Balinski–Gomory method and the optimization phase of the primal simplex method. Entering and leaving variables are selected through configurable rules chosen from those currently implemented.

## Project structure

- **`visualsimplex`** is the core Python library. It models linear programming problems, runs the algorithm through the tableau representation and records each pivot step.
- **`visualsimplex-bridge`** is a small adapter for the web app. It exposes a JSON-based interface, builds the corresponding Python objects and translates the results back into JSON.
- **`web`** is a static application that runs the library directly in the browser through the bridge, providing a ready-to-use visual walkthrough without a backend.

The web app currently presents the steps selected by the configured rules. Students cannot choose the next pivot themselves yet, although the Python library can perform any valid pivot. Interactive pivot selection is planned for a future version.
