# Architecture Refactor Report

## Current Grade

After this pass: C+.

The application now has a clearer path toward MVC, packaged Qt Designer `.ui`
files, a representation layer, and a runnable GUI entry point. It is still not a
clean MVC application: `mainwindow.py` and several view classes continue to
coordinate too much, some backend controllers retain legacy assumptions, and a
number of widgets still build detailed layout in Python.

## Direction

- Keep layout in `src/gambitpairing/ui/*.ui`.
- Keep visual behavior and signal wiring in `src/gambitpairing/gui`.
- Keep tournament state in model classes under `src/gambitpairing/models`.
- Keep orchestration and pairing/result logic in `src/gambitpairing/controllers`.
- Keep serialization in `src/gambitpairing/representation`.
- Keep style in QSS resources.

## Boundary Rule

Never put behavior in `.ui` and never put layout in Python. Designer `.ui`
files own static layout, Python owns behavior/signal wiring/runtime state, and
QSS owns styling. Models hold data only; representation/persistence handle
serialization/save-load; Qt-free logic should not live in GUI code; GUI code
should not leak into domain logic. Main window code should stay thin and talk to
views/widgets through intent-level APIs such as `reset_display()`.

## Improvements Made

- Added a runtime UI loader for packaged Qt Designer `.ui` files.
- Added Designer shells for the main window and major views.
- Moved save/load JSON document handling into `gambitpairing.representation`.
- Kept model `to_dict`/`from_dict` compatibility wrappers while delegating to
  representation logic.
- Standardized visible reset behavior around `reset_display()` for the major
  views used by the main window.
- Restored an importable, runnable application path through
  `gambitpairing.__main__`.
- Fixed focused result recording behavior for black forfeit wins and double
  forfeits.
- Added regression tests for representation persistence, round clearing, and
  result edge cases.

## Remaining Risks

- `mainwindow.py` should continue shrinking into setup, wiring, and high-level
  user interaction only.
- View classes should gradually move more layout into Designer files instead of
  creating tables, controls, and containers in Python.
- Tournament model/controller boundaries need another pass; some controller
  behavior is still shaped around legacy mutable model internals.
- The misspelled `repersentation` package remains as a compatibility shim and
  should be removed after callers migrate to `representation`.
- Pairing engines need deeper domain tests, especially around color history,
  duplicate pair avoidance, byes, and round-robin edge cases.
- Pyright still reports many legacy typing issues; the useful short-term target
  is reducing actual errors before pursuing warning cleanup.
