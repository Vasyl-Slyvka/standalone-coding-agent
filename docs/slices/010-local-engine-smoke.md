# S02b.3 — живий локальний smoke test OpenCode + llama.cpp

**25.09.2026 · обмежений експеримент на CPU, €0 за API.** Перевірено один локальний endpoint і два OpenCode runs у синтетичному одноразовому Git repo. Це не порівняння трьох архітектур R1, не тест двох незалежних API-провайдерів і не вибір рушія. [Task/межі попереднього слайса](005-free-test-path.md), [R1 gate](../../ROADMAP.md).

## Підготовка й межі

| Компонент | Пін і перевірка |
|---|---|
| OpenCode CLI | Офіційний Linux x64 release `v1.18.32`; SHA-256 архіву `3046e0404fdc60fb80307e7a47824ba07477364178a4d09baa8548496dd6d43b`. [Випуск](https://github.com/anomalyco/opencode/releases/tag/v1.18.32). |
| llama.cpp CPU | Офіційний Linux x64 release `b11177`, commit `1ab7e5ad2`; SHA-256 архіву `9e088583293c4c104953ead0dd8957f4e00dca318c7f241c039198e5eb2e2e54`. [Випуск](https://github.com/ggml-org/llama.cpp/releases/tag/b11177). |
| Локальна модель | `Qwen/Qwen3-0.6B-GGUF`, Q4_K_M, 396 704 416 байтів завантаженого файла, SHA-256 `b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e`. [Файл моделі](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF). |
| Середовище | Linux x86_64, CPU, близько 9,7 GiB RAM, без GPU; `llama-server` на `127.0.0.1:8080`, context 8192, 2 CPU threads. |

Тільки `localqwen/qwen3-0.6b-q4_k_m` у `enabled_providers`, явний `--model`; `small_model` теж локальна модель. Конфіг OpenCode: `share=disabled`, `autoupdate=false`, `compaction.auto=false`, `plugin=[]`, `lsp=false`, `formatter=false`; `permission` за замовчуванням `deny`, дозволені лише `read`, `glob`, `grep`; `edit`, `bash`, `webfetch`, `websearch` і `external_directory` заборонені. CLI `--pure`, без `--auto`. Сервер і CLI жили в одній ізольованій мережевій області. Запуск лише на синтетичних `README.md` та `hello.py`; модель, журнали й session export **не входять до Git**. OpenCode документує [локальний OpenAI-compatible endpoint](https://opencode.ai/docs/providers) і [дозволи](https://opencode.ai/docs/permissions/). Дозволи рушія самі по собі не є sandbox для коду стороннього plugin/runtime.

## Спостереження

- `llama-cli` окремо завершив локальну генерацію з кодом `0`; коротка генерація зупинилася під час thinking, без фінальної відповіді.
- `GET /v1/models` сервера повернув єдину модель `qwen3-0.6b-q4_k_m`; `opencode run --format json` завершився з кодом `0` приблизно за 71 с.
- Потік OpenCode: 2 `step_start`, 1 `tool_use(read hello.py)`, 2 `step_finish`, жодного error event. Перший крок: engine-reported input 3076/output 187/cache read 0; другий: input 81/output 97/cache read 3262. `sca.trace_audit` повернув `model_identity=unresolved` для обох і `api_call_count=UNKNOWN`.
- Локальний `llama-server` зафіксував **три** завершені генерації (`task 0`, `task 2`, `task 197`), а JSONL — **два** `step_finish`. Додаткова генерація почалася раніше за читання файла; вона, імовірно, пов'язана з назвою сесії, але це не встановлено з per-request ідентифікаторів. Її ~549 prompt tokens/~256 output tokens не можна приписати кроку з JSONL. Це конкретний ризик прихованого виклику і неповної task telemetry.
- Session export містить reasoning і `read`, але не фінальний текст відповіді. `hello.py` у Git-статусі лишився незміненим. **Коректну відповідь на задачу не підтверджено.** `cost: 0` у двох кроках — поле OpenCode для локального провайдера, не доказ повного обліку викликів чи грошового рахунку.

### Контрольне повторення з метаданими HTTP

Запущено другу, окрему сесію на тій самій моделі, в тому самому синтетичному repo, із тим самим read-only конфігом. Тимчасовий локальний проксі між OpenCode та llama.cpp записував **тільки** номер запиту, endpoint, вибрану модель, ролі повідомлень, кількість tools, код відповіді й час. Вміст повідомлень, відповіді, заголовки й токени доступу не зберігалися. Всі три `POST /v1/chat/completions` повернули 200:

| Запит | Модель | Ролі; tools | Співвідношення з CLI |
|---|---|---|---|
| 1 | `qwen3-0.6b-q4_k_m` | `system,user,user`; 0 | Стартує перед головним запитом, завершений окремо; у JSONL немає окремого `step_finish`. |
| 2 | та сама | `system,user`; 3 | Перший CLI step; `read hello.py`. |
| 3 | та сама | `system,user,assistant,tool`; 3 | Другий CLI step після `read`. |

Повторний JSONL теж має **2** `step_finish`, **1** `read` і жодного error event. У повторі сервер показав ~549 input/~256 output tokens для запиту 1, тоді як engine step usage відображає лише запити 2 і 3. Отже **додатковий модельний запит підтверджено**, і явний `small_model` не вимикає його. Те, що це генерація назви сесії, є обґрунтованим висновком із форми запиту та [документації OpenCode про `small_model`](https://opencode.ai/docs/config/), а не доведеним призначенням запиту з його вмісту. Сирі журнали й експериментальний проксі лишилися поза Git.

**Рішення gate:** `S02b/R1 OPEN`. На цій ревізії CLI-події недостатні для доказу всіх model calls. Наступний етап має точно прив’язати всі HTTP-запити до task/auxiliary категорій і їх provider usage, підтвердити призначення третього виклику та спосіб вимкнути або врахувати його, після чого провести парні сценарії та два API-провайдери. Проксі тут був разовим експериментальним інструментом, не production adapter. Слабкий Qwen 0.6B не дає підстав оцінювати загальну якість OpenCode. Жодного платного виклику не робили.

## Повторна звірка S06 (26.09.2026)

[Очищений машинозчитуваний evidence](../../benchmarks/evidence/local-smoke-2026-09-25.json) заново отримано з двох JSONL, server timing logs і proxy metadata. Перераховано 5 CLI-подій / 2 завершені кроки в кожному запуску та 3 завершені HTTP-запити у повторенні. `hello.py` байтово дорівнює HEAD. Поточний `opencode.json` dirty через ручну зміну endpoint 8080 → 8081 для проксі; це не встановлена дія engine. Сирі повідомлення, відповіді, session IDs і приватний session export не включено. Хеші журналів дозволяють звірити збережені входи, але не є незалежною атестацією запуску. Первісні архіви й GGUF уже відсутні за записаними шляхами завантаження: їхні хеші збережено з первісного звіту, повторно цього разу не обчислено.

Тимчасовий проксі **буферизував усю відповідь**, перш ніж віддати її клієнту; це може змінити latency/concurrency. Зіставлення запитів 2/3 з CLI-кроками ґрунтується на послідовності та ролях, а не наскрізному request ID. Повного provider usage за кожним запитом немає. Налаштування `deny` саме по собі не замінює негативні тести небезпечних дій.

На точних release commits перевірено top-level LICENSE: [OpenCode — MIT](https://github.com/anomalyco/opencode/blob/545f51d26cc39a907d2867492d498d9607ea5fa4/LICENSE), [llama.cpp — MIT](https://github.com/ggml-org/llama.cpp/blob/1ab7e5ad2d4e7295c94c3b966a3e0b70fa365865/LICENSE). Офіційна [картка Qwen GGUF](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/blob/main/README.md) позначає Apache-2.0; README не pinned, точний завантажений GGUF ідентифіковано записаним SHA-256. Це не аудит усіх bundled/transitive залежностей і не ліцензійне рішення SCA.
