# S03a offline manual selection snapshot
Task ID: SCA-S03A-SELECTION
Branch: main

## Sources
- VISION.md CA-R03/CA-R04/CA-R06; AGENTS.md; ROADMAP.md R1 and R2.2.
- docs/slices/005-free-test-path.md; user's €0 constraint and decision to defer live S02b while away from the laptop.

## Scope
- src/sca/selection.py; tests/test_selection.py.
- docs/slices/006-selection-snapshot.md; README.md; ROADMAP.md; this task.

## Must do
- Accept only an explicit provider, model and endpoint alias from a small local JSON file, with no credentials or fallback config.
- Produce a detached immutable-value snapshot with a reproducible digest; reject ambiguous or invalid inputs.
- State clearly that this is an offline contract, independent of the future engine and not evidence of a successful provider call.
- Mark the live S02b comparison deferred, with the R1 gate still open.

## Must not
- Call a model, silently choose a model or provider, incur charges or select the production engine.
- Modify NODREN, run commands from task files, or claim the Product DoD is satisfied.

## Acceptance
- Offline CLI emits the stated choice and `UNVERIFIED_SELECTION`; invalid/missing/duplicate fields fail closed.
- A prior snapshot does not change when the config file is edited.
- Existing tests and links pass; S02b/R1 remains explicitly open in docs.

## Checks
- PYTHONPATH=src:. python3 -m unittest discover -s tests -v
- git diff --check; Python compilation; Markdown relative links.

## Stop rule
- Do not implement or claim engine integration until practical S02b tests establish its model and telemetry control.
