# S05a — офлайновий аудит метаданих доказів

**Стан:** реалізовано локальний аудит уже наданих результатів для task contract S01. Це не запуск verifier та не прийняття задачі. Практичний S02b/R1 і повний S05 лишаються відкритими. [Task spec](../../tasks/task-S05A-EVIDENCE-AUDIT.md).

## Контракт

Команда `PYTHONPATH=src python3 -m sca.evidence_audit /path/to/task.md /path/to/record.json` читає JSON до 64 KiB. Схема версії `1`: `task_id`, масив `checks` із **точними** назвами й порядком пунктів `## Checks`, масив `acceptance` із точними пунктами `## Acceptance`, `diff` і `usage`. Інші/пропущені/повторені пункти блокуються. Для кожного `check` потрібно `name`, `status` (`passed`, `failed`, `not_run`, `blocked`), `exit_code` і `log_sha256`: для повідомленого запуску код цілий (`0` на passed, ненульовий на failed) і SHA-256 у форматі 64 символів; для not_run/blocked обидва `null`. Для criterion — `criterion`, `status`, `evidence_ids`; reported passed потребує принаймні одного ID. ID не доводить існування файла.

`diff` має `kind` (`preview_only`, `working_tree`, `not_available`) та заявлений `sha256` або `null`, коли diff відсутній. `usage` має `cost_usd` (`UNKNOWN` або десятковий USD-рядок), `provenance` (`unknown`, `provider_reported`, `engine_reported`, `estimate`) і `trace_completeness: unverified`. Не записувати в record секретів, prompt, сирих відповідей, журналів або приватних файлів.

## Результат і значення

| Outcome | Значення *повідомлених* даних |
|---|---|
| `BLOCKED_REPORTED` | Є пункт зі статусом blocked. |
| `REWORK_REQUIRED_REPORTED` | Є failed, якщо blocked немає. |
| `INCOMPLETE_REPORTED` | Є not_run або diff відсутній чи є лише прев’ю, якщо вищих статусів немає. |
| `STRUCTURALLY_COMPLETE_UNVERIFIED` | Усі пункти позначені passed і заявлено working-tree diff. |

За будь-якого outcome `task_accepted=false`, `trace_completeness=unverified`. Модуль не читає log/diff bytes, не перевіряє їхні hash незалежно, не виконує команд, не встановлює справжність exit code, не перевіряє repo policy та не бачить model calls. Навіть останній рядок таблиці засвідчує тільки внутрішню повноту **самозаявлених метаданих**. Реальний verifier має запускати дозволені перевірки, прив’язувати журнали й diff до поточного Git-стану та повторно звіряти правила цільового репозиторію.

## Перевірка

Синтетичні тести охоплюють повний запис, failed/not_run/blocked, пропуски, дублікати, невідповідні коди, неправильну provenance і спробу приховати команду в task: CLI її не запускає. `PYTHONPATH=src:. python3 -m unittest discover -s tests -v`, компіляція Python, `git diff --check`, локальні Markdown-посилання.
