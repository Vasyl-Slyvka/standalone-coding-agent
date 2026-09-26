# S05a offline evidence metadata audit
Task ID: SCA-S05A-EVIDENCE-AUDIT
Branch: main

## Sources
- VISION.md CA-R02, CA-R06, CA-R08; AGENTS.md; ROADMAP.md R1/R2.5.
- IMPLEMENTATION_MAP.md verification/report; docs/slices/008-patch-preview.md.

## Scope
- src/sca/evidence_audit.py
- tests/test_evidence_audit.py
- docs/slices/009-evidence-audit.md
- README.md
- ROADMAP.md
- tasks/task-S05A-EVIDENCE-AUDIT.md

## Must do
- Compare every reported check and acceptance criterion with the exact parsed task contract.
- Distinguish reported passed, failed, not_run and blocked with consistent exit codes and digest metadata.
- Keep unknown cost UNKNOWN and label reported/estimated known USD without claiming invoice status.
- Always mark external evidence unverified and task unaccepted; do not present synthetic records as live tests.

## Must not
- Execute task checks, read claimed logs or diff bytes, trust arbitrary evidence IDs, change a repo or call a model.
- Claim that a structurally complete record proves actual execution, policy authorization or Product DoD.

## Acceptance
- Full reported pass yields STRUCTURALLY_COMPLETE_UNVERIFIED with task_accepted=false.
- Missing, duplicate or reordered task entries, inconsistent exit codes and invalid usage provenance fail validation.
- Failed/not_run/blocked entries yield distinct outcomes; no check command executes.
- Existing tests and Markdown links pass; S02b/R1 and full S05 remain open.

## Checks
- PYTHONPATH=src:. python3 -m unittest discover -s tests -v
- Python compilation; git diff --check; Markdown relative links.

## Stop rule
- Do not upgrade reported evidence to verified task completion until real allowed checks, log/diff byte validation and repo-policy gates are integrated and tested.
