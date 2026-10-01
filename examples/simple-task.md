# Inspect the synthetic arithmetic task
Task ID: SCA-DEMO-SIMPLE
Branch: main

## Sources
- src/math_utils.py and tests/test_math_utils.py in the generated simple benchmark fixture.

## Scope
- src/math_utils.py

## Must do
- Identify the intended arithmetic correction: add(2, 3) must return 5.
- Use only read-only inspection for this demo; report branch, HEAD and scope conflicts.

## Must not
- Edit files, run task checks, commit, push, contact a model API or change provider/model.
- Treat INSPECTED as repository-policy authorization or task acceptance.

## Acceptance
- The preflight reports INSPECTED on a clean simple fixture on main.
- The report retains policy_status=not_evaluated and the fixture remains unchanged.

## Checks
- python3 -m unittest discover -s tests -v

## Stop rule
- Stop on malformed task, a different branch, dirty scope overlap or unsafe scope paths.
