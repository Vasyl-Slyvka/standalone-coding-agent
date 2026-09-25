# S02b.1 offline trace audit
Task ID: SCA-S02B-OFFLINE-TRACE
Branch: main

## Sources
- VISION.md CA-R03, CA-R06, CA-R07; AGENTS.md.
- ROADMAP.md R1; IMPLEMENTATION_MAP.md sections 5 and 8.
- docs/slices/003-static-engine-audit.md; benchmarks/README.md.

## Scope
- src/sca/trace_audit.py; tests/test_trace_audit.py.
- tasks/task-S02B-OFFLINE-TRACE.md; docs/slices/004-offline-trace-audit.md.
- docs/slices/003-static-engine-audit.md (schema correction); README.md; ROADMAP.md.

## Must do
- Audit documented Codex JSONL turn usage and OpenCode SSE step usage without model calls.
- Keep input/output/cache separate, mark API call count unknown, detect explicit model mismatch.
- Never copy raw prompts or tool output to the generated summary.

## Must not
- Claim per-call trace completeness, a real performance comparison, or engine choice.
- Install/run an engine, use an API key or change NODREN.
- Auto-select provider/model or silently convert missing usage to zero.

## Acceptance
- Synthetic event logs demonstrate aggregates versus calls, duplicate part handling, missing values and explicit model mismatch.
- All tests pass, links resolve and diff has no whitespace errors.

## Checks
- PYTHONPATH=src:. python3 -m unittest discover -s tests -v
- git diff --check; manual Markdown link resolution.

## Stop rule
- No live model tests until the owner specifies OS, manually selected provider/model and maximum experiment budget.
