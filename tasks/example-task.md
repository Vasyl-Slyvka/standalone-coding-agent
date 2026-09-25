# Example task for an isolated test repository
Task ID: EXP-001
Branch: main

## Sources
- Repository AGENTS.md and any applicable instructions; reviewed by the operator.

## Scope
- src/app.py

## Must do
- Add a greeting function.

## Must not
- Rewrite unrelated files.

## Acceptance
- A real test verifies the greeting.

## Checks
- python -m unittest discover -s tests

## Stop rule
- Stop when repo instructions, branch, or dirty scope make the task unsafe.
