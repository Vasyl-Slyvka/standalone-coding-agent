# S06 — повне рев’ю реалізованих слайсів

**26.09.2026 · рев’ю й виправлення завершено; код і докази опубліковано.** Перевірено окремий Standalone Coding Agent, не NODREN. [Task S06](../../tasks/task-S06-REVIEW.md). База локального рев’ю: `551a643`; до початку правок робоча копія була чистою. Критерії взято з [VISION](../../VISION.md), [ROADMAP](../../ROADMAP.md), [IMPLEMENTATION_MAP](../../IMPLEMENTATION_MAP.md) та чинного [AGENTS](../../AGENTS.md).

Автоматична перевірка дозволів тимчасово зупинила відкриття GitHub через ліміт використання. Після продовження роботи доступ відновився, публікацію виконано. Локальний коміт основних виправлень — `3ea0378`; вебкоміти мають іншу історію. [Запис контролю публікації](publication-2026-09-26.json) містить стан remote та результати звірки. Текст файлів прочитано назад із GitHub UI й зіставлено з локальним: інтерфейс прибирає кінцевий LF, тому це перевірка тексту з ігноруванням одного кінцевого LF, не доказ ідентичності завантажених байтів.

## Що перевірено і виправлено

Прочитано всі модулі `src/sca`, генератор фікстур, усі тести, task contracts, звіти слайсів і дизайн. Відтворено дефекти на одноразових синтетичних Git-репозиторіях. Це перевірка наявних контрактів і конкретних ризиків, а не доказ відсутності всіх уразливостей.

| Знахідка | Наслідок до виправлення | Виправлення / доказ |
|---|---|---|
| Git `fsmonitor` у доборі контексту | `git ls-files` запускав налаштований сторонній скрипт під час «лише читання». | Єдиний Git helper вимикає fsmonitor; тест перевіряє, що marker-файл не створено й index не змінено. |
| Git `clean`/`process` filters | `status` міг виконати сторонній фільтр для зміненого файла того самого розміру. | Виявлені content filters вимикаються лише на час команди; регресія відтворює same-size edit і перевіряє відсутність marker. |
| Успадковані `GIT_*` змінні | Inspection або створення фікстури могли звернутися до іншого repo/index. | Helper і генератор фікстур очищають ці змінні; тести з підставленим `GIT_DIR`. |
| Scope у восьми task-файлах | Кілька шляхів через `;` трактувалися як один буквальний шлях, що могло приховати перетин dirty/scope. | Один реальний шлях на пункт; тест усіх опублікованих `task-*.md`. Навчальний `example-task.md` перевіряється окремими тестами parser/preflight. |
| Вартість і повторні calls | `NaN`/infinity проходили; `0.00000001` округлялося до нуля; дубль call міг подвоїти підсумок. | Finite validation, унікальний `call_id`, Decimal aggregation, відомий результат як десятковий рядок; `UNKNOWN` збережено. |
| Неоднозначний trace | Два SSE sessions змішувалися; некоректне usage могло зникнути після наступного update; конфлікт CLI-дублікатів не блокувався. | Перевірка sessions, counters при читанні, completed-step conflict, duplicate JSON keys і nonfinite numbers; bounded CLI input 8 MiB. |
| CRLF → LF у preview | `changed=true`, але рядковий diff міг бути порожнім. | CR збережено й видно в JSON; `diff_applicable=false` прямо відділяє review display від застосовного patch. |
| Неповний mandatory context | Branch, scope, sources і checks не входили в mandatory блок. | Збережено всі поля task; byte cap і UTF-8 перевірені. Sources залишаються посиланнями, не завантаженими правилами. |
| Застарілі статуси і доказ smoke test | Документи одночасно говорили «живих запусків немає» і описували два запуски. | Узгоджено README/Roadmap/звіти, заново перераховано очищені докази, явно позначено непідтверджені твердження. |

Додатково: benchmark CLI обмежено 1 MiB, duplicate JSON keys відхиляються; від’ємний exit code допускається для завершення сигналом; `task_accepted=false` не дозволяє перетворити самозвіт на прийняття задачі. Scope відхиляє керівні символи.

**Зміни контракту, які треба врахувати інтегратору:** кожен benchmark call тепер потребує `call_id`; відомий aggregate `cost_usd` — рядок; context mandatory більший і може не вміститися в старий byte budget; preview diff призначений лише для читання. Вимкнення Git content filters може консервативно показати dirty для перетворюваних файлів. Конфігурація цільового repo не переписується.

## Scope по слайсах

| Слайс | Фактично готово й перевірено | Що це ще не означає |
|---|---|---|
| S01 | Task parser, branch/HEAD/status, буквальний scope, dirty-overlap, path/symlink checks. | `policy_status=not_evaluated`; дозволи target repo не оцінено. |
| S02a | Чотири синтетичні фікстури й валідатор записаних метрик. | Модель не запускається; acceptance і trace correlation лише заявлені. |
| S02b.0–.2 | Статичний аудит кандидатів, офлайновий event parser, перевірка форматів upstream, €0 маршрут. | Немає парного порівняння трьох технічних підходів. |
| S02b.3 | Два живі локальні досліди; збережені журнали підтверджують додатковий model request. | Немає фінальної відповіді, повної request/usage кореляції чи завершеного R1. |
| S03a | Явний незмінний selection snapshot, digest, відхилення неоднозначного config. | Endpoint alias не вирішується; реальний engine не зобов’язаний використати цей snapshot. |
| S03b | Офлайнове рішення перед наступним контрольованим кроком, Decimal/UNKNOWN, soft limits. | Немає інтегрованої зупинки engine або strict pre-call cap. |
| S04a | Однофайлове read-only preview з HEAD/hash/scope і видимими newline differences. | Немає apply, ізоляції чи захисту запису від race. |
| S04b | Явно перелічені tracked UTF-8 файли, lexical snippets, byte budget, повний task context. | Немає authoritative source loading, tokenizer, інтеграції чи виміряної економії. |
| S05a | Звірка метаданих checks/acceptance з task; статуси reported/unverified. | Команди не запускаються, журнали й істинність доказів не перевіряються. |
| S06 | Виправлені знайдені дефекти, регресії, узгоджені статуси й ця матриця. | Product DoD/R1 усе ще відкриті; публікація не змінює їхніх критеріїв. |

## Звірка вимог CA-R01…09

| Вимога | Стан | Залишок |
|---|---|---|
| CA-R01 — окремий локальний інструмент | Частково | Синтетичний Git repo працює; немає дозволеного NODREN policy-preflight. |
| CA-R02 — task contract | Частково | Структуру перевірено; authoritative sources і семантичні суперечності ще не вирішуються. |
| CA-R03 — ручний API/model | Частково | Snapshot і локальна конфігурація є; немає двох реальних API та end-to-end гарантії без fallback. |
| CA-R04 — вибір відкритих компонентів | Частково | Є pinned досліди і top-level licenses; вибір engine та повний dependency inventory відкриті. |
| CA-R05 — контекст | Частково | Є bounded offline pack; немає provider tokenizer/cache/quality comparison. |
| CA-R06 — usage/cost | Частково | Валідатори з provenance/UNKNOWN працюють; живий trace пропускає додатковий запит у step usage. |
| CA-R07 — limits/stop | Частково | Синтетичні негативні рішення є; живого stop/control loop немає. |
| CA-R08 — workspace/patch/evidence | Частково | Read-only hash/scope/diff та evidence metadata є; apply/verifier/isolation ще немає. |
| CA-R09 — repo policy | Не реалізовано | Немає policy adapter та негативного NODREN gate test; NODREN не змінювався. |

## Definitions of Done

### Design DoD — 4/4 прийнято раніше, не скасовано

| Критерій VISION | Результат рев’ю |
|---|---|
| Узгоджений scope, ручний вибір, cost guarantees, DoD | Збережено; застарілі execution-status твердження виправлено. |
| NODREN-факти відділено від пропозицій, джерела наведено | Збережено як датовані факти. Поточний NODREN gate цього разу не перевірявся: жодна дія над NODREN не виконувалася. |
| Є MVP/non-goals, stages, рішення й негативні сценарії | Є в дизайні; негативні runtime scenarios ще не всі реалізовано. |
| Власник прийняв пакет | Зафіксовано 25.09.2026; це попереднє прийняття дизайну, не нове прийняття MVP. |

### Product DoD — 0/5 повністю закритих критеріїв

Це кількість завершених критеріїв, **не відсоток зробленої роботи**.

| Критерій | Що бракує для DONE |
|---|---|
| 1. Реальна task → edit → tests → report; два API-провайдери | Обраний engine/adapter, дозволений write/test цикл, два окремі provider runs і повний model trace. |
| 2. Повний call/usage/cost accounting та stop | Кореляція всіх request IDs з usage, auxiliary/retry accounting і демонстрація реальної контрольованої зупинки. |
| 3. Repo rules, dirty preservation, unauthorized actions, NODREN gate | Policy adapter, ізоляція і живі негативні тести shell/network/write/branch; дозволений NODREN test case. |
| 4. Conflict, crash/timeout/API failure/resume | Runtime safe states/checkpoints, recovery tests, доказ відсутності прихованого commit/push. Hash-conflict preview покриває лише частину. |
| 5. Quality/cost benchmark і dependencies/licenses | Парні прийняті задачі, контроль якості/ціни, frozen dependency inventory, transitive licenses та ліцензійне рішення самого SCA. |

**R1 залишається OPEN, MVP не прийнятий, engine не обраний.** Відкладені два реальні API, платні тести та ноутбучна інтеграція не підмінені синтетичними перевірками.

## Докази перевірки

- [Повний журнал unittest](unit-tests-2026-09-26.txt): **62/62 PASS**, 12 нових регресій до попередніх 50; exit 0.
- [Машинозчитувані результати](validation-2026-09-26.json): Python compilation, benchmark example і README context command — exit 0; `git diff --check` — exit 0. Перевірка локальних Markdown links і scope/diff наведена там само після фінального оформлення.
- Код, повторно прочитаний із GitHub UI: **62/62 PASS** у локальній копії. Це перевірка опублікованого тексту, а не запуск GitHub Actions. Перше перенесення контрольної копії було неповним; його import failure усунуто повним експортом перед повторною перевіркою.
- [Очищений live evidence](../../benchmarks/evidence/local-smoke-2026-09-25.json): 5 CLI events / 2 completed steps у кожному з двох запусків; 3 HTTP requests у повторенні, усі до заданої локальної моделі, усі HTTP 200; фінальної текстової відповіді немає. `hello.py` дорівнює HEAD. Dirty `opencode.json` — зміна endpoint виконавцем експерименту.
- Сирі model messages, приватний session export, credentials, binaries і model weights у diff відсутні. Модельні API під час рев’ю не викликалися.
- Первісні архіви/GGUF відсутні за старими шляхами: збережені раніше release hashes цього разу **не** перераховано. Натомість наявні JSONL/server/proxy журнали заново прочитано й хешовано.
- Top-level LICENSE OpenCode/llama.cpp на точних release commits перевірено; картка Qwen вказує Apache-2.0. Повного bundled/transitive license audit немає; runtime SCA — stdlib, але Python/Git і build `setuptools>=61` не є frozen final toolchain.

Проксі буферизував відповіді й міг змінити затримки. Призначення допоміжного запиту як title generation — висновок, не доведений факт. Локальний smoke не вимірює якість engine чи економію; task totals usage/cost — `UNKNOWN`.

## Що робити далі

1. **Наступний технічний слайс — повний облік локальних HTTP-викликів.** Вузький дослідний adapter із request IDs, provider usage, явною auxiliary-категорією і тестом «3 HTTP requests не губляться в 2 CLI steps». Без API-ключів, без вибору engine, спочатку контракт і synthetic failure tests; живий повтор потребуватиме повернення точних model weights.
2. **Після telemetry — негативні permission/error сценарії і парне порівняння R1.** Зіставні задачі для CLI wrapper / supervisor / малого API loop; не робити висновок про якість із Qwen 0.6B.
3. **Коли доступні дві вручну обрані API-конфігурації та дозволений бюджет — завершити R1.** Тоді рішення про engine, policy/workspace/verifier integration і повний Product DoD. Ноутбук користувача не потрібен для всього дослідження; доступ до provider і прийняті межі витрат усе одно потрібні.

У межах рев’ю наявних слайсів доступні виправлення виконано. Майбутні adapter/apply/runtime роботи не оголошені зробленими й не початі приховано за відкритим R1 gate.
