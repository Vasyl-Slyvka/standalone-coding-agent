# S09 loopback HTTP evidence
Task ID: SCA-S09-MOCK-HTTP
Branch: main

## Sources
- Owner 2026-10-02: preserve working code; finish documented preparation before API inputs.
- AGENTS.md; VISION.md CA-R03/06/07; ROADMAP.md R1; IMPLEMENTATION_MAP.md.

## Scope
- src/sca/mock_http.py
- benchmarks/mock_api.py
- tests/test_mock_http.py
- tasks/task-S09-MOCK-HTTP.md
- docs/slices/013-mock-http.md

## Must do
- Capture actual loopback HTTP request IDs and explicitly estimated usage through a fixed mock route; reuse unchanged request_ledger.
- Bound response bytes and socket inactivity. Retain unsuccessful attempts and unknown usage, reject malformed/duplicate/nonfinite JSON, extra fields and identity drift.
- Keep stdlib only; use a disposable local server and no implicit retry, redirect, proxy or provider routing.
- Review and publish scoped changes to the same public WIP GitHub repo, with local commits, readback and CI; shared navigation/evidence paths belong to S10.

## Must not
- Modify existing source/tests or fixtures; call inference APIs, download models, choose an engine/license, add dependencies/frameworks, touch NODREN or rewrite Git history.
- Store prompts, response bodies, headers or keys. Mock protocol is not provider compatibility, full engine interception or a strict cost/time guarantee.

## Acceptance
- Actual HTTP echoes run/request/model IDs and retains auxiliary and explicit retry attempts.
- HTTP error/redirect, disconnect, timeout, truncated/oversized/invalid responses preserve unknown usage without replay.
- Existing regression suite and new negatives pass; working source/test hashes remain unchanged.

## Checks
- PYTHONPATH=src:. python3 -m unittest discover -s tests -v
- python3 -m compileall -q src tests benchmarks scripts
- python3 scripts/check_docs.py
- PYTHONPATH=src:. python3 -m benchmarks.mock_api
- git diff --check; scope/privacy audit; old hashes; remote readback and CI.

## Stop rule
- Stop dependent changes/publication on failed checks, authority/scope conflicts, secrets or unrelated remote changes; preserve evidence and user work.
