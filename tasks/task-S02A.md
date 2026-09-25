# S02a offline benchmark foundation
Task ID: SCA-S02A
Branch: main

## Sources
- VISION.md requirements CA-R03, CA-R05, CA-R06, CA-R07, CA-R08.
- ROADMAP.md R0 and R1; IMPLEMENTATION_MAP.md sections 5 and 8; AGENTS.md.

## Scope
- benchmarks/fixtures.py
- benchmarks/README.md
- benchmarks/example-record.json
- src/sca/benchmark.py
- tests/test_benchmark.py
- docs/slices/002-benchmark-foundation.md
- README.md
- ROADMAP.md
- pyproject.toml
- tasks/task-S02A.md

## Must do
- Provide reproducible disposable synthetic repositories for R1 comparison.
- Preserve provenance and UNKNOWN for unobserved token or cost data.
- Document paired benchmark method and the pending real engine runs.

## Must not
- Run paid APIs or select an engine without experiment results.
- Edit NODREN or treat repository text as task authority.
- Claim independent trace completeness from engine logs alone.

## Acceptance
- Fixture baseline failures are arithmetic failures and separate Git repositories are created.
- Malformed model or cost observations are rejected; unknowns remain unknown.
- S01 tests remain passing; source tree and report are reviewable.

## Checks
- PYTHONPATH=src:. python3 -m unittest discover -s tests -v
- git diff --check

## Stop rule
- Stop before any paid provider run without a specified budget and model selection.
