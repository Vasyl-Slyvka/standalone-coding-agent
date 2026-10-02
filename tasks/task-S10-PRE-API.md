# S10 bounded mock control and API experiment pack
Task ID: SCA-S10-PRE-API
Branch: main

## Sources
- Owner 2026-10-02: preserve working behavior; finish independent preparation before API involvement.
- AGENTS.md; VISION.md CA-R03/06/07 and Product DoD error/recovery; ROADMAP.md R1; IMPLEMENTATION_MAP.md.

## Scope
- src/sca/mock_run.py
- tests/test_mock_run.py
- tasks/task-S10-PRE-API.md
- docs/slices/014-pre-api-control.md
- docs/reviews/pre-api-readiness.md
- docs/reviews/validation-2026-10-02-pre-api.json
- docs/reviews/unit-tests-2026-10-02-pre-api.txt
- README.md
- ROADMAP.md
- .github/workflows/checks.yml

## Must do
- Reuse unchanged usage_gate/request_ledger. Count each controlled attempt, including auxiliary/retry, while preserving unknown cost.
- Block next mock HTTP dispatch at step/time limits, unknown price under a soft cap and explicit denial; denial is not a repo policy adapter.
- Validate metadata checkpoints; pending/crashed/failed attempts require an explicit new retry ID. Reopen never sends HTTP or silently resumes.
- Prepare the R1 three-path/two-provider experiment protocol and requirement/DoD readiness matrix; keep engine and R2 decisions gated.
- Review, commit and publish only scoped additions/navigation/evidence to the same public WIP GitHub repository; observe remote CI and read back changes.

## Must not
- Modify old source/tests/fixtures, call model APIs, choose an engine/provider/license, add V2 resume/dashboard or production gateway/provider mapper, execute arbitrary commands/patches, touch NODREN or rewrite history.
- Invent prices/usage, claim strict spending caps, full engine trace, closed R1 or complete MVP. Caller-owned checkpoints are metadata claims, not a durable transaction or permission grant.

## Acceptance
- Independent mock server counts prove no extra dispatch after stops/denial or reopen; explicit retries remain separate attempts.
- Frozen identity/limits, duplicate IDs, model drift, failed/incomplete recovery and exported-state isolation are verified.
- All regression checks pass; existing source/tests are byte-identical. Reports separate verified preparation from blocked live-engine/MVP criteria.

## Checks
- PYTHONPATH=src:. python3 -m unittest discover -s tests -v
- python3 -m compileall -q src tests benchmarks scripts
- python3 scripts/check_docs.py
- PYTHONPATH=src:. python3 -m benchmarks.mock_api
- Existing offline quickstart; git diff --check; source/test hashes; scope/privacy review; remote readback and GitHub CI.

## Stop rule
- Stop dependent work for unresolved scope/policy conflict, failed checks, secrets or unrelated changes. Next external inputs are two explicit provider/model configurations and spending limit; live engine comparison and R2 remain gated.
