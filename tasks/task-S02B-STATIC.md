# S02b.0 static engine-interface audit
Task ID: SCA-S02B-STATIC
Branch: main

## Sources
- VISION.md CA-R03–CA-R08 and Product DoD; AGENTS.md.
- ROADMAP.md R0/R1; IMPLEMENTATION_MAP.md sections 5 and 8.
- benchmarks/README.md and tasks/task-S02A.md for paired-run rules.
- Exact upstream revisions and official documentation linked in the slice report.

## Scope
- tasks/task-S02B-STATIC.md
- docs/slices/003-static-engine-audit.md
- README.md and ROADMAP.md: progress links only.

## Must do
- Pin and cite candidate upstream licenses, execution seams, telemetry and permission interfaces.
- Distinguish source facts, engineering inferences, recommendations and unverified gates.
- Define reproducible, security-aware paid comparison without selecting an engine.

## Must not
- Run a paid model, install an engine, make changes to NODREN or claim R1 is complete.
- Equate a turn total with per-call usage; silently assume compatibility with a second provider.
- Treat a Git worktree or a prompt instruction as an execution sandbox.

## Acceptance
- Four candidates have exact revision, license and source references.
- Three architectural approaches have concrete integration and negative-test questions.
- Every proposed cost/permission claim identifies how it would be verified; unknown remains unknown.
- All relative links resolve; whitespace check passes.

## Checks
- git diff --check
- Verify local relative Markdown links and review pinned public URLs.

## Stop rule
- Stop before real inference until the owner specifies OS, test provider/model and a maximum experiment budget.
