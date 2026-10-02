# Standalone Coding Agent

**Work in progress · experimental Python prototype · engine selection open**

A local coding-agent project built around explicit tasks, manual model choice, reviewable changes and honest usage accounting. The goal is one repository and one task per run, with the developer choosing the provider, model and permitted actions.

Today this repository contains **working offline components and a documented local engine experiment**. The complete task → edit → test → report loop is still ahead. Python components use the standard library; the final coding engine has not been selected.

Українська документація: [бачення та критерії готовності](VISION.md) · [план](ROADMAP.md) · [карта реалізації](IMPLEMENTATION_MAP.md).

## What works today

| Component | Implemented behavior | Current boundary |
|---|---|---|
| [Task and Git preflight](src/sca/preflight.py) | Parse task constraints; inspect branch, HEAD, dirty paths and scope conflicts. | Read-only structural inspection; repository policy is not evaluated. |
| [Manual selection snapshot](src/sca/selection.py) | Validate and freeze explicit provider/model/endpoint-alias metadata. | No endpoint resolution, credentials or engine invocation. |
| [Trace audit](src/sca/trace_audit.py) | Parse supported Codex/OpenCode event formats; reject ambiguous sessions and conflicting steps. | Step events do not prove that every model request was observed. |
| [Request/usage ledger](src/sca/request_ledger.py) | Correlate supplied request/step IDs; retain auxiliary calls and retries; show unknown usage and token semantics. | Offline metadata validation; no live interception, verified trace completeness or pricing. |
| [Loopback HTTP/control](docs/slices/014-pre-api-control.md) | Collect mock HTTP IDs/estimated usage; stop next dispatch; reopen metadata with explicit retries. | Local mock only; no provider/engine integration, workspace recovery or strict cap. |
| [Usage gate](src/sca/usage_gate.py) | Evaluate supplied usage records, limits and a soft stop before the next controlled step. | Offline decision; no live engine cancellation or strict spending cap. |
| [Patch preview](src/sca/patch_preview.py) | Check one-file replacement against scope, HEAD and SHA-256; display differences. | Review display only; no file writes or applicable patch guarantee. |
| [Context pack](src/sca/context_pack.py) | Preserve task fields and select snippets from explicitly listed tracked files within a UTF-8 byte budget. | No tokenizer, source-authority resolver or measured savings. |
| [Evidence audit](src/sca/evidence_audit.py) | Compare supplied check/acceptance metadata with the task contract. | Does not execute checks or validate logs; `task_accepted=false`. |
| [Benchmark foundation](benchmarks/README.md) | Generate four disposable Git fixtures; validate metric records with provenance and `UNKNOWN`. | No model calls or completed comparative benchmark. |

## Try it offline

Requires **Python 3.10+ and Git**. Run from the repository root on Linux/macOS or a compatible shell. No API key, package installation or model download is required.

```bash
git clone https://github.com/Vasyl-Slyvka/standalone-coding-agent.git
cd standalone-coding-agent

# Run the actual unit and regression tests.
PYTHONPATH=src:. python3 -m unittest discover -s tests -v

# Create a new disposable repository and inspect its task without editing it.
fixture_parent="$(mktemp -d)"
python3 -m benchmarks.fixtures simple "$fixture_parent/repo"
PYTHONPATH=src python3 -m sca "$fixture_parent/repo" examples/simple-task.md --json

# Validate a deliberately unmeasured example record.
PYTHONPATH=src:. python3 -m sca.benchmark benchmarks/example-record.json

# Exercise actual local HTTP, stops and metadata recovery (no API key).
PYTHONPATH=src:. python3 -m benchmarks.mock_api

# Correlate invented request metadata: three requests, two CLI steps.
PYTHONPATH=src python3 -m sca.request_ledger examples/request-ledger.json
```

The preflight should return `INSPECTED` with `policy_status=not_evaluated`. The benchmark example retains unknown totals and `task_accepted=false`. The fixture's arithmetic bug is intentional: its own tests are a failing baseline for a future editing engine. Preflight reads the `Checks` field but does not run it. Temporary fixtures remain available for inspection.

For other modules, follow the input formats in the [slice reports](docs/slices/001-preflight.md) and [benchmark guide](benchmarks/README.md). Validate documentation paths with `python3 scripts/check_docs.py`.

## Evidence and progress

- **106 unit/regression tests passed** for [S09/S10](docs/slices/014-pre-api-control.md), including actual local HTTP, stop and failure/reopen checks. The [pre-API audit](docs/reviews/pre-api-readiness.md) identifies the remaining live-engine/API inputs.

- **80 unit/regression tests passed** in the [S08 checks](docs/slices/012-request-ledger.md): the original 62 plus 18 request-ledger cases. The [S06 review](docs/reviews/2026-09-26-full-review.md) records the earlier fixes to Git hook/filter suppression, dirty files, path escapes, malformed usage, trace conflicts and newline differences.
- A [local OpenCode + llama.cpp/Qwen smoke test](docs/slices/010-local-engine-smoke.md) observed **3 HTTP model requests but only 2 CLI steps**. This is a telemetry gap to resolve; the experiment did not produce a valid final answer or demonstrate agent quality.
- [Sanitized experiment metadata](benchmarks/evidence/local-smoke-2026-09-25.json) preserves counts and hashes without raw model messages, private logs or model weights.
- [S07 verification](docs/reviews/2026-10-01-public-readiness.md) records the repeat checks and publication scope. [GitHub Actions](https://github.com/Vasyl-Slyvka/standalone-coding-agent/actions) runs the offline suite on Python 3.10 and 3.13 using pinned official actions.

**Design DoD: 4/4 accepted. Product DoD: 0/5 fully completed criteria.** These are acceptance criteria, not a percentage of development effort. [VISION.md](VISION.md) defines both; the [review matrix](docs/reviews/2026-09-26-full-review.md) explains the missing evidence. R1 remains open.

## Next milestones

1. Use the tested [pre-API experiment pack](docs/reviews/pre-api-readiness.md) to compare CLI wrapper, supervisor and a small API loop on the same fixtures. Loopback collection/stop/reopen preparation is complete; live engine permission and recovery still need verification.
2. Capture provider-specific usage and all live request IDs. The old smoke's additional request remains unclassified and its total usage unknown.
3. Verify two manually chosen API providers when access and an inference budget are available; make the R1 engine decision from evidence.
4. Integrate repository policy, guarded edits, real verification and recovery; complete paired quality/cost benchmarks and the Product DoD.

The tool is being designed to preserve user changes, obey target-repository rules and avoid hidden model fallback. These are requirements; the offline prototype does not yet enforce a complete runtime policy or sandbox. Unknown usage/cost remains `UNKNOWN`; token savings and strict monetary caps have not been demonstrated.

## Project map

| Path | Purpose |
|---|---|
| [src/sca](src/sca) | Implemented offline modules and CLI entry points. |
| [tests](tests) | Executable unit and regression cases. |
| [benchmarks](benchmarks) | Synthetic fixtures, record example and sanitized local evidence. |
| [examples/simple-task.md](examples/simple-task.md) | Runnable task for the offline quickstart. |
| [tasks](tasks) / [docs/slices](docs/slices) | Slice contracts, commands, results and limitations. |
| [VISION.md](VISION.md) / [ROADMAP.md](ROADMAP.md) | Approved scope, non-goals, acceptance and remaining milestones. |
| [IMPLEMENTATION_MAP.md](IMPLEMENTATION_MAP.md) / [AGENTS.md](AGENTS.md) | Candidate architecture and task rules. |

SCA is a separate project for Git repositories. NODREN is a potential target with its own authorization rules; this project does not change its runtime or phase gates.

## License and contributions

**Project license decision pending.** Public visibility does not grant an open-source license. No MIT/Apache license has been selected for SCA. Third-party tools referenced in experiments retain their own licenses; the final dependency/license inventory remains part of Product DoD.

Read [AGENTS.md](AGENTS.md) before proposing changes. Keep contributions tied to a small task with acceptance and negative checks; report actual evidence and preserve the current WIP boundaries.
