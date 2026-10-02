# S08 offline request and usage correlation
Task ID: SCA-S08-REQUEST-LEDGER
Branch: main

## Sources
- Owner continuation on 2026-10-02, following the S07 summary and its next telemetry slice.
- AGENTS.md; VISION.md CA-R03/06/07; ROADMAP.md R1; IMPLEMENTATION_MAP.md usage ledger.
- docs/slices/010-local-engine-smoke.md and the retained sanitized evidence: three HTTP requests versus two CLI steps, without complete request/usage IDs.

## Scope
- src/sca/request_ledger.py
- tests/test_request_ledger.py
- examples/request-ledger.json
- docs/slices/012-request-ledger.md
- docs/reviews/validation-2026-10-02-S08.json
- docs/reviews/unit-tests-2026-10-02-S08.txt
- tasks/task-S08-REQUEST-LEDGER.md
- README.md
- ROADMAP.md
- .github/workflows/checks.yml

## Must do
- Define a strict, bounded metadata-only record with run/request/step identities, explicit task/auxiliary/retry classification and usage provenance.
- Correlate supplied records by IDs in both directions; count every observed request once, including retries and requests outside CLI steps.
- Preserve unknown usage, unresolved classification and unspecified token semantics; never infer full engine trace completeness from an internally consistent record.
- Test missing, contradictory, duplicate, cross-run, model-drift, retry and malformed/oversized input cases.
- Keep stdlib only; reuse the existing offline components and fill their demonstrated request-ID gap without choosing an engine or adding a gateway.
- Review scope/diff, retain actual checks, publish the reviewed slice to the existing public WIP repository, and observe remote CI.

## Must not
- Call a model, download weights, run a live proxy, change NODREN, select an engine/provider or add dependencies/licenses.
- Reclassify the old smoke request as a proven auxiliary call or fabricate its missing usage/request IDs.
- Retain prompts, response bodies, headers, endpoint URLs, credentials or raw private logs.
- Claim a live interceptor, enforced stop, complete task cost, strict spending cap, closed R1 or completed Product DoD.
- Rewrite remote history or discard unrelated changes.

## Acceptance
- A synthetic record with three requests/two steps retains all three requests and includes explicitly annotated auxiliary usage in observed totals.
- An incomplete record remains visibly incomplete; contradictory correlations and identities are rejected.
- Retry attempts are separately counted and linked; cache/reasoning subsets are not added to input/output totals.
- CLI reads at most 1 MiB, rejects duplicate JSON keys/nonfinite numbers, prints only schema metadata, and returns nonzero for invalid records or unresolved gaps.
- Existing regression suite and new meaningful negative cases pass; documentation and published text agree with the reviewed files; CI succeeds.

## Checks
- PYTHONPATH=src:. python3 -m unittest discover -s tests -v
- python3 -m compileall -q src tests benchmarks scripts
- python3 scripts/check_docs.py
- PYTHONPATH=src python3 -m sca.request_ledger examples/request-ledger.json
- git diff --check; scope/privacy review; remote readback and GitHub CI.

## Stop rule
- Stop dependent publication on unresolved authority/scope conflict, failed mandatory checks, unexpected sensitive data or unrelated remote changes. Preserve evidence; do not overwrite or reset work.
