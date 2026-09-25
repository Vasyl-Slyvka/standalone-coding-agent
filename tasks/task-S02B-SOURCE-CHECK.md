# S02b.2 source-validated free test path
Task ID: SCA-S02B-SOURCE-CHECK
Branch: main

## Sources
- VISION.md CA-R03, CA-R04, CA-R06, CA-R07; AGENTS.md.
- ROADMAP.md R1; docs/slices/003-static-engine-audit.md; docs/slices/004-offline-trace-audit.md.
- Pinned upstream OpenCode/Codex sources and current official Ollama integration docs in slice report.

## Scope
- src/sca/trace_audit.py; tests/test_trace_audit.py; docs/slices/004-offline-trace-audit.md.
- tasks/task-S02B-SOURCE-CHECK.md; docs/slices/005-free-test-path.md; README.md; ROADMAP.md.

## Must do
- Correct OpenCode `run --format json` decoding from pinned CLI source, and retain separate SSE parsing.
- Distinguish unknown CLI model identity from proven mismatch; avoid merging unrelated sessions.
- State concrete €0 local-model experiment path for the owner's possible Windows 10/Kubuntu setup.

## Must not
- Spend money, choose a model for the owner, install on the owner's computer or claim a live engine comparison.
- Claim that offline CLI events prove complete per-call telemetry, safe shell or two-provider MVP.

## Acceptance
- Synthetic tests covering the upstream CLI envelope, SSE envelope, duplicate steps, unknown identity, cache counters and invalid mixed sessions pass.
- Documentation shows the corrected semantics and links to pinned source.
- `git diff --check` and relative-link verification pass.

## Checks
- PYTHONPATH=src:. python3 -m unittest discover -s tests -v
- git diff --check; Markdown relative-link check.

## Stop rule
- No actual inference until a local model is available or an explicitly chosen provider/model and budget are provided.
