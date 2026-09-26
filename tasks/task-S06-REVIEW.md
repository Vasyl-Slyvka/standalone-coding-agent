# S06 full review and correction of existing slices
Task ID: SCA-S06-REVIEW
Branch: main

## Sources
- AGENTS.md; VISION.md Design DoD and Product DoD; ROADMAP.md; IMPLEMENTATION_MAP.md.
- Existing slice task contracts, tests and available local S02b.3 evidence.

## Scope
- src/sca
- tests
- benchmarks
- tasks
- docs
- README.md
- ROADMAP.md

## Must do
- Review every existing module and slice against its actual contract; reproduce material defects before fixing them.
- Reject invalid accounting and ambiguous traces; preserve exact task constraints and visible byte-level patch differences.
- Prevent Git inspection from executing configured fsmonitor hooks and prevent inherited Git environment from redirecting fixture writes.
- Recheck live-smoke claims against retained logs, preserve a sanitized evidence summary, and correct stale status text.
- Publish an explicit scope and Design/Product DoD matrix with verified, partial and deferred outcomes.

## Must not
- Start paid API tests, select an engine, bypass R1, modify NODREN, or claim full MVP/security acceptance.
- Commit raw model messages, private logs, binaries, model weights or credentials.

## Acceptance
- Every reproduced defect has a meaningful passing regression test and the full existing test suite passes.
- All task Scope lists use one literal relative path per item; documentation commands and local links are valid.
- Read-only operations preserve target files/index and do not run configured Git fsmonitor commands.
- Available local smoke metadata supports the published counts without claiming complete per-call usage.
- The final report states every open Product DoD criterion and the next dependency-ordered steps.

## Checks
- PYTHONPATH=src:. python3 -m unittest discover -s tests -v
- Python compilation, CLI smoke commands, git diff --check and Markdown relative links.
- Reconcile retained engine JSONL, HTTP metadata and source hashes; review the full changed diff.

## Stop rule
- Stop dependent work on a failed mandatory check, unrelated changes, missing authority or a deferred R1 requirement; record the precise limitation.
