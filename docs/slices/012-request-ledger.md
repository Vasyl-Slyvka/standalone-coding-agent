# S08 — офлайновий request/usage ledger

**02.10.2026 · S08 DONE: реалізовано, перевірено й опубліковано; CI PASS.** [Task S08](../../tasks/task-S08-REQUEST-LEDGER.md). Це незалежний контракт до gate R1, без вибору engine, мережі, proxy або model calls. Наявний `trace_audit` правильно рахує кроки, але не має request IDs; `usage_gate` приймає post-step спостереження. Вузький ledger заповнює цю прогалину на нормалізованих metadata, не додаючи CLI/framework dependency.

## Запуск і результат

```bash
PYTHONPATH=src python3 -m sca.request_ledger examples/request-ledger.json
```

[Приклад](../../examples/request-ledger.json) **повністю синтетичний**, не перетворений із smoke logs: 3 request IDs, 2 step IDs, 1 явно анотований auxiliary request поза steps. Вигадані estimate counters дають observed input 21/output 10, зокрема auxiliary 7/3. Усі 3 запити обліковуються; step count не підміняє request count. `api_call_count=UNKNOWN`, `trace_completeness=unverified`, `task_accepted=false` і `cost_usd=UNKNOWN` залишаються навіть для internally consistent запису.

CLI: exit **0** — `CONSISTENT_OBSERVATIONS`; **1** — `GAPS` із JSON та причинами; **2** — invalid/contradictory input, stderr без JSON-результату. Це результат аудиту supplied metadata, не прийняття задачі чи дозвіл наступного model call. `failed_requests` може бути непорожнім навіть за consistent metadata.

## Контракт v1

Вхід — JSON object з точними полями `schema_version: 1`, `run_id`, `selection`, `steps`, `requests`. CLI читає максимум **1 MiB**; collections до **1000** елементів, загалом до 1000 linked requests. Duplicate JSON keys і nonfinite numbers відхиляються. Ідентифікатори — до 128 ASCII символів `[A-Za-z0-9][A-Za-z0-9._:/-]*`; endpoint alias — назва, не URL/path. Provider/model мають бути явними, без `auto/default`.

| Об’єкт | Точні поля / значення |
|---|---|
| `selection` | `provider`, `model`, `endpoint_alias` — ті самі в кожному request. Snapshot є заявленим вибором, не доказом використаної моделі. |
| `steps[]` | Унікальний `step_id`, `request_ids[]`. Посилання перевіряються в обидва боки; порожній step — gap. |
| `requests[]` | Унікальний `request_id`, `run_id`, `provider`, `model`, `endpoint_alias`, `category`, `category_source`, `step_id`, `retry_of`, `status`, `http_status`, `usage`. |
| `category` | `task`, `auxiliary`, `retry`, `unknown`; жодного автоматичного висновку з кількості/порядку steps. |
| `category_source` | Для відомої category — `adapter_reported` або `operator_annotation`; для `unknown` — лише `unknown`. Це provenance твердження, не підтвердження призначення запиту. |
| `step_id` | ID відомого step або `null`. Task без step лишається gap; auxiliary може бути поза steps. |
| `retry_of` | Для retry — ID раніше записаного request у тому самому step, включно з auxiliary поза steps; інакше `null`. Кожна спроба обліковується окремо. |
| `status` / `http_status` | `completed` потребує HTTP 2xx; `failed` і `incomplete` можуть мати HTTP integer 100–599 або `null`. HTTP 200 не означає коректну відповідь чи завершену задачу. |
| `usage` | `null` або object із `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens`, `source`, `token_semantics`. Counters — `null` або integer 0…2⁶³−1; source — `provider_reported`, `engine_reported`, `estimate`. |
| `token_semantics` | `inclusive` означає, що input/output вже включають їхні відповідні cache/reasoning subsets; `unspecified` зберігає counters, але не дозволяє нормалізований total. |

Requests мають бути в порядку запису спроб: retry посилається лише назад. Це контракт входу, не незалежна атестація часу. У виході `purpose` retry успадковує **заявлений** task/auxiliary/unknown purpose свого parent; unknown origin не стає відомим лише через retry. `by_category` та `by_purpose` — два різні зрізи того самого списку, їх не додавати один до одного.

Cache read/write і reasoning **не додаються** до input/output. За `inclusive` кожний наявний subset не перевищує свій наявний total; cache read/write не вважаються взаємно неперетинними. Для raw OpenCode input/cache зі старого smoke не слід ставити `inclusive` без окремого перевіреного mapper. Цей слайс provider-format mapper не реалізує.

Якщо хоча б один request не має потрібного inclusive counter, відповідний observed total — `UNKNOWN`. `known_*_subtotal` показує лише відомий subtotal; нульовий subtotal за відсутніх даних не означає нуль використання. Unknown classification, missing usage, unspecified semantics, incomplete request, task без step або відсутність requests лишаються явними gaps. Counts зі failed/retry attempts не губляться й не підміняються нулем.

Unknown keys відхиляються на кожному рівні, довільний payload не проходить у вивід. Prompts, response bodies, headers, URL та credentials не є полями схеми. Це **не** secret scanner: у дозволені identifier fields також не можна записувати секрети.

## Перевірка й межі

- **80/80 unittest PASS**: 62 попередні + 18 request-ledger tests; локально Python 3.12.14 і повторно з повної опублікованої копії. Compilation та `git diff --check` — exit 0.
- **101 local Markdown path target, 0 broken**; external URLs/anchors/reference-style links не перевірено. Demo exit 0, байти вхідного JSON незмінні.
- **71/71 remote files прочитано назад і байтово звірено**, Git blob SHA-1 кожного перевірено; remote `fa2f92071fa0e82693932b3e285385b08915c6fb`. Змінені рівно 10 scope paths; видалених чи сторонніх змін немає.
- [GitHub Actions run 37027660848](https://github.com/Vasyl-Slyvka/standalone-coding-agent/actions/runs/37027660848) — **success**; `offline (3.10)` і `offline (3.13)` виконали тести, compilation, docs, offline quickstart з ledger та whitespace check.
- Після цієї звірки оновлено лише цей звіт і JSON-докази. Звірка 71 файлу стосується зазначеного SHA до фінального evidence update; executable code, workflow, example і tests не змінено.

[Unittest log](../reviews/unit-tests-2026-10-02-S08.txt) і [машинозчитувані результати](../reviews/validation-2026-10-02-S08.json) фіксують фактичні команди, exits і publication verification. Негативні тести покривають відсутні/суперечливі links, duplicates, cross-run/model drift, task/auxiliary retries, retry parent order/cycles, unknown usage/purpose, cache semantics, malformed JSON, oversized input і заборонені payload fields.

[Старий live smoke](010-local-engine-smoke.md) залишається незмінним: 3 HTTP requests/2 CLI steps підтверджено, але повний request/usage trace й призначення додаткового запиту **не встановлено**. Синтетичний приклад не є повторним engine run. Ledger не перехоплює HTTP, не перевіряє достовірність annotation, не знаходить невидимі calls, не нормалізує конкретний provider, не рахує ціну й не інтегрований із live stop.

**Scope S08:** офлайнова валідація й кореляція. **R1 OPEN; Design DoD 4/4 раніше прийнято; Product DoD 0/5 повністю закритих критеріїв.** Під час S08 не викликали inference API, не додавали dependency і не редагували NODREN. Наступний крок — вузький adapter для збору наскрізних request IDs і provider usage, спочатку з локальним mock server і негативними сценаріями; живий повтор окремо потребуватиме точних weights/engine та дозволених ресурсів.
