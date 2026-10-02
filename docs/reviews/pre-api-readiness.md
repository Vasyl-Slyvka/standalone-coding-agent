# Pre-API readiness and R1 experiment protocol — 2026-10-02

Owner constraint: preserve working behavior, implement missing documented preparation, stop at the external/API boundary. Sources: [AGENTS](../../AGENTS.md), [Vision](../../VISION.md), [Roadmap](../../ROADMAP.md), [Implementation Map](../../IMPLEMENTATION_MAP.md), [S09](../slices/013-mock-http.md), [S10](../slices/014-pre-api-control.md).

## Requirement audit

| Requirement | Verified preparation | Evidence still needed for product acceptance |
|---|---|---|
| CA-R01 separate local tool | Standalone repo, disposable Git fixtures, read-only preflight. | Real coding run; separate authorized NODREN preflight if targeted. |
| CA-R02 task contract | Strict loader, missing-field/scope validation, context preserves must-not/acceptance. | Current target policy authority/conflict resolution in selected engine. |
| CA-R03 manual selection | Immutable selection metadata, mock identity checks, no automatic retry/fallback. | Two explicit provider/model configurations; prove selected engine honors them for every call. |
| CA-R04 reuse/licenses | Existing candidate audits; new preparation uses Python stdlib only. | R1 selected revisions, current license/dependency inventory and integration evidence. SCA license still undecided. |
| CA-R05 context | Tracked-file snippets, bounded bytes, mandatory requirements retained. | Engine integration, real tokenizer/context behavior and reported cache data; no savings claim. |
| CA-R06 usage | Request IDs, auxiliary/retry attempts, provenance, inclusive subsets, UNKNOWN; actual mock HTTP collection. | Provider-specific usage mapper, price provenance and independently reconciled full engine trace. |
| CA-R07 limits | Existing offline gate now controls next loopback attempt; step/time/unknown-price negatives. | Live engine call coverage/cancellation and supported output limits. This does not bound ongoing request duration or strict USD. |
| CA-R08 workspace/evidence | Read-only patch preview/hash/escape/dirty regressions, fixtures, evidence metadata audit. | Guarded patch application, authorized real commands/verifier, conflict and dirty preservation in full run. |
| CA-R09 target policy | Source boundaries documented; SCA has not changed NODREN. | Current target rules, allowed issue/branch/actions and NODREN phase gate if applicable; mock permitted flag is not this adapter. |

## Scope and definitions of done

S09/S10 close independent mock preparation, not implementation-map runtime nodes. Existing source/tests remain unchanged. There is no newly selected engine, external inference API, provider SDK, dependency, workspace writer or automatic Git action in the prototype.

| Product DoD criterion | Prepared evidence | Status |
|---|---|---|
| 1 task → edit → tests → report with 2 API providers | Offline contracts/fixtures; real repository regression checks | OPEN: coding loop and two providers absent |
| 2 all controlled/observed calls, task cost and stops | Metadata ledger; mock HTTP IDs and dispatch stops; unknown usage retained | OPEN: selected engine trace/usage/prices unverified |
| 3 target rules, dirty, unauthorized actions/NODREN | Existing negative regressions; mock denial before dispatch | OPEN: runtime policy and workspace integration absent |
| 4 conflict/crash/timeout/API error/reopen | Existing preview conflicts; HTTP failure/timeout, pending metadata checkpoint, explicit retry | OPEN: real engine/workspace recovery absent |
| 5 paired quality/cost and licenses | Four disposable Git fixtures and record schema; bounded mock protocol | OPEN: paired benchmark and final component inventory absent |

**Design DoD 4/4 previously accepted; Product DoD 0/5 fully closed; R1 OPEN.** These are criteria, not effort percentages. Mock completion never sets task_accepted=true. Old smoke remains unchanged: 3 HTTP requests / 2 CLI steps, missing full usage and unproved extra-request purpose.

## Fixed R1 comparison protocol

Evaluate the three already-approved paths below before choosing an engine. No implementation here implicitly selects path C.

| Path | Same experiment boundary | Extra evidence needed |
|---|---|---|
| A open CLI + wrapper | Same selected provider/model, fixture/task, limits and acceptance | Exact pinned CLI/license, all auxiliary/retry calls, control hooks |
| B CLI + supervisor | Same CLI revision/model and fixture as A where supported | Supervisor overhead, action interception and complete call reconciliation |
| C small API loop with reused dependencies | Same provider/model and fixtures where supported | Dependency licenses, tool/patch safety and quality versus A/B |

Each path gets an independent clean disposable fixture and run ID. Use the existing `simple`, `two-files`, `dirty`, `injection` fixtures from [benchmark guide](../../benchmarks/README.md); retain identical task acceptance and baseline revision across paired runs. A fixture's intentional failing arithmetic test is the baseline, not an SCA regression. Unsupported model/provider combinations are **unpaired**, not a win. Do not change models automatically to complete the matrix.

For each cell retain: exact engine/component revision and environment, manual selection snapshot, original dirty hashes, authorized paths/commands, all observed request/step IDs (including auxiliary/retry), usage raw-field provenance and normalized semantics, price source/date or UNKNOWN, elapsed time, patch/diff, actual check command/exit/log digest, acceptance outcomes and failure state. Keep sensitive/raw payload logs outside Git; published evidence contains only reviewed metadata. Independent HTTP observations must be reconciled against engine events; internally consistent ledger metadata alone is insufficient. Report missing fields and interception gaps.

| Scenario required by R1/DoD | Preparation available now | Live acceptance rule |
|---|---|---|
| Simple / two dependent files | Existing disposable fixtures | Real narrow diff passes actual task checks |
| Must-not / unauthorized action | Task/preview negatives and mock dispatch denial | Chosen runtime denies unauthorized edit/shell/external action before execution |
| API error / timeout / crash / reopen | Scripted HTTP error, disconnect, timeout; pending/failed metadata checkpoints | Preserve run/workspace; explicit retry only, no silent replay or reset |
| Missing price / step/time budget | UNKNOWN and next-mock-dispatch stop tests | Same behavior through all controlled engine calls, honest soft-stop language |
| Dirty file / stale patch / escape | Existing preflight/preview regressions | Preserve original dirty hashes; refuse conflicting patch and escape |
| Repo prompt injection | Existing injection fixture and mandatory context | Ignore embedded instructions that contradict authority |
| Failing tests / context overflow | Existing fixture baseline/context byte-budget negatives | Record failed/not_run checks; never silently drop acceptance/must-not |
| Fallback / hidden auxiliary call | Wrong-model response refusal; explicit 3-request/2-step mock case | No other selected identity; auxiliary/retry calls observed or gap blocks acceptance |

Run the pre-API regression/demo package from repository root:

```bash
PYTHONPATH=src:. python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests benchmarks scripts
python3 scripts/check_docs.py
PYTHONPATH=src:. python3 -m benchmarks.mock_api
```

## Next external inputs and gate

Owner supplies two provider names, exact model IDs and endpoint configuration, plus allowed inference spending (USD amount or explicit free/local-only constraint) and environment availability. Keep keys in the eventual local credential mechanism; do not paste them into task files, reports, Git or chat. No current mock command reads keys or can use a remote endpoint.

Then perform the live R1 comparison, recheck exact selected component revisions/licenses and provider documentation, map real usage fields, reconcile traces and record the engine decision. Only after R1 passes integrate R2 repository policy, guarded editing and real verification. Target-repo permissions/allowed commands are separate inputs when choosing the first real task; a provider key does not authorize those actions. No independent gated runtime work is marked done just because mock preparation passed.
