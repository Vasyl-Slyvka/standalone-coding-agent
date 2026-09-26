# S03b offline usage and post-step soft stop
Task ID: SCA-S03B-USAGE-GATE
Branch: main

## Sources
- VISION.md CA-R03, CA-R06, CA-R07; AGENTS.md; ROADMAP.md R1/R2.4.
- IMPLEMENTATION_MAP.md usage/budget modes; docs/slices/006-selection-snapshot.md.

## Scope
- src/sca/usage_gate.py
- tests/test_usage_gate.py
- docs/slices/007-usage-gate.md
- README.md
- ROADMAP.md
- tasks/task-S03B-USAGE-GATE.md

## Must do
- Process only explicit, visible post-step usage records for one manual provider/model/endpoint selection.
- Preserve unknown costs and tokens; require provenance for known cost; use decimal USD strings rather than float arithmetic.
- Return a conservative next-controlled-step soft stop on reached step/time/cost limits or unknown cost under a configured cost cap.
- State that unseen model calls, invoices and pre-call protection cannot be inferred from these synthetic records.

## Must not
- Choose a provider, perform inference, connect an engine, bill an account or claim a hard spend cap.
- Modify NODREN, execute tool commands or treat local tests as live telemetry proof.

## Acceptance
- The offline CLI distinguishes allow from soft stop with explicit reasons, with no engine/API traffic.
- Duplicate steps, model mismatch, malformed cost, missing price provenance and boolean token/limit values fail closed.
- Existing tests and links pass; S02b/R1 and full S03 remain open.

## Checks
- PYTHONPATH=src:. python3 -m unittest discover -s tests -v
- Python compilation; git diff --check; Markdown relative links.

## Stop rule
- Do not wire this gate to a real backend or describe it as a cost guarantee before practical S02b and an independent trace check.
