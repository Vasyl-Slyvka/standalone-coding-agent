# S07 public work-in-progress presentation and verification
Task ID: SCA-S07-PUBLIC
Branch: main

## Sources
- Owner request on 2026-10-01: continue, recheck, and publish this project on GitHub as public work in progress.
- AGENTS.md; VISION.md; ROADMAP.md; IMPLEMENTATION_MAP.md; S06 review and publication evidence.

## Scope
- README.md
- ROADMAP.md
- examples
- scripts
- .github
- tasks/task-S07-PUBLIC.md
- docs/reviews

## Must do
- Present implemented components, runnable offline commands, evidence, limitations and next milestones clearly.
- Add a network-free demo task; repeat the tests, compilation, documentation and quickstart checks.
- Review tracked content and reachable local Git history for credentials, private logs and unintended assets before publication.
- Publish reviewed files to Vasyl-Slyvka/standalone-coding-agent, update description/topics, and make this repository public as requested.
- Verify remote contents, public visibility and actual workflow outcomes; report limitations rather than invent successful checks.

## Must not
- Call paid model APIs, select the final engine, close R1 or declare Product DoD complete.
- Modify NODREN or publish raw model messages/private logs/credentials/binaries/weights.
- Choose a project license without the Owner's decision, rewrite remote history or discard unrelated changes.

## Acceptance
- README clearly presents WIP status, implemented scope, runnable offline quickstart and evidence.
- The existing 62 tests pass; advertised offline commands and local Markdown links work.
- CI uses read-only permissions, pinned official actions and no model API credentials.
- The repository is public and published text agrees with reviewed files.
- The final summary distinguishes S07 completion from open Product DoD and deferred experiments.

## Checks
- PYTHONPATH=src:. python3 -m unittest discover -s tests -v
- python3 -m compileall -q src tests benchmarks scripts
- python3 scripts/check_docs.py
- README demo commands, git diff --check, credential-pattern and asset review.
- Read back published files; observe repository visibility and workflow results on GitHub.

## Stop rule
- Stop dependent publication on failed mandatory local checks, unexpected sensitive data or unrelated remote changes; preserve evidence and report the exact blocker.
