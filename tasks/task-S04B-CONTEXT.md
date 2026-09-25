# S04b offline context selection
Task ID: SCA-S04B-CONTEXT
Branch: main

## Sources
- VISION.md CA-R02, CA-R05, CA-R09; AGENTS.md; ROADMAP.md R2.3/R2.4.
- IMPLEMENTATION_MAP.md Context selector and context preflight.

## Scope
- src/sca/context_pack.py; tests/test_context_pack.py.
- docs/slices/011-context-pack.md; README.md; ROADMAP.md; this task.

## Must do
- Preserve the complete parsed task must-do, must-not, acceptance and stop rule in an immutable mandatory context block.
- Fail closed when mandatory UTF-8 bytes exceed the explicit budget; reserve output/headroom outside this byte budget.
- Rank only explicitly listed, tracked, regular UTF-8 files under a resolved Git root by lexical relevance; record path and SHA-256.
- Bound file size and returned bytes; label byte accounting as bytes, not exact model tokens.

## Must not
- Call a model, execute task checks, read unlisted files, follow symlinks, edit repository files, or decide repo authorization.
- Claim this selection supplies all authoritative repo sources or a measured token saving.

## Acceptance
- Mandatory clauses remain exact and in task order; optional snippets are deterministic within the budget.
- Missing, untracked, traversal, absolute, symlink, binary and oversize candidates fail; mandatory overflow fails without truncation.
- Synthetic Git fixture remains unchanged; existing tests and Markdown relative links pass.

## Checks
- PYTHONPATH=src:. python3 -m unittest discover -s tests -v
- Python compilation; git diff --check; Markdown relative links.

## Stop rule
- Do not send context to a backend until repo policy, all required sources and a real tokenizer/context limit are integrated and tested.
