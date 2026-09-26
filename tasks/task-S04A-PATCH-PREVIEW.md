# S04a offline patch preview
Task ID: SCA-S04A-PATCH-PREVIEW
Branch: main

## Sources
- VISION.md CA-R02, CA-R08, CA-R09; AGENTS.md; ROADMAP.md R1/R2.3.
- IMPLEMENTATION_MAP.md workspace guard; docs/slices/001-preflight.md and 007-usage-gate.md.

## Scope
- src/sca/patch_preview.py
- tests/test_patch_preview.py
- docs/slices/008-patch-preview.md
- README.md
- ROADMAP.md
- tasks/task-S04A-PATCH-PREVIEW.md

## Must do
- Preview one full-file UTF-8 replacement against explicit Git HEAD and source SHA-256.
- Require an inspected task branch and scope, a clean scoped worktree, an existing regular tracked file and no symlink/path traversal.
- Return a reviewable diff and newline metadata; never modify the target repository.
- Distinguish structural checks from repo-policy authorization and workspace isolation.

## Must not
- Apply a patch, run task Checks or arbitrary shell, commit, push, choose an engine or modify NODREN.
- Claim that preview validates nested AGENTS.md, target repo policy, permissions or security of a future write.

## Acceptance
- A clean synthetic Git fixture yields a diff with unchanged working tree and index.
- Wrong HEAD/digest, dirty scoped file, out-of-scope path, traversal, symlink, untracked target and malformed input block.
- Existing tests and Markdown links pass; live S02b/R1 and full S04 remain open.

## Checks
- PYTHONPATH=src:. python3 -m unittest discover -s tests -v
- Python compilation; git diff --check; Markdown relative links.

## Stop rule
- No edit/apply capability before target policy authorization, isolation and race-resistant path/write design are specified and verified.
