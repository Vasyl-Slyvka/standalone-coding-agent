# S01 — офлайновий task/Git preflight

**Статус:** реалізовано і перевірено локально; подальші слайси ще відкриті. **Тип:** вузький експеримент, не працюючий Coding Agent і не дозвіл редагувати NODREN.

## Scope

- Python standard-library CLI `python -m sca <repo> <task.md> [--json]`.
- Строгий Markdown task contract: Task ID, Branch, Scope, Must do, Must not, Acceptance, Checks, Stop rule, optional Sources.
- Git read-only branch/HEAD/status; відмова на неправильній гілці, небезпечному scope, symlink або dirty file в заявленому scope.
- Результат `INSPECTED` чи `BLOCKED` з JSON-полями, зокрема `policy_status=not_evaluated`.

## Не реалізовано в S01

Вибір API/моделі, model calls, оцінка токенів, перевірка NODREN issue/AGENTS/phase, автоматичний запуск Checks, edit, shell execution чи strict budget. `INSPECTED` означає, що task/Git-секція придатна для **подальшого** policy review, а не авторизацію дії.

## Перевірка

`PYTHONPATH=src python3 -m unittest discover -s tests -v` — 9 unit/negative tests PASS: чистий Git, dirty в scope і поза ним, wrong branch, traversal/абсолютні/glob/.git шляхи, symlink, malformed/duplicate Markdown, не-Git каталог, відсутність виконання Checks. Тести використовують тимчасові Git-репозиторії, не NODREN.

## Відомі обмеження й наступний крок

Контракт task-файла наразі навмисно вузький: literal relative scope paths і прості `- ` пункти. Готовий CLI/SDK engine, policy adapter та ціна виклику залишаються предметом S02–S03. Перед платним spike зафіксувати платформу тесту, синтетичні задачі й бюджет; результати порівняти з DoD в [Vision](../../VISION.md).

## Уточнення рев’ю S06 (26.09.2026)

Усі фіксовані Git-виклики очищають успадковані `GIT_*` змінні, встановлюють `GIT_OPTIONAL_LOCKS=0`, вимикають `core.fsmonitor` та знайдені `filter.*.clean/smudge/process/required` без зміни конфігурації repo. Регресійні тести перевіряють відсутність запуску контрольних скриптів. Без content filters файл із перетвореннями може консервативно виглядати dirty — автоматично дозволяти запис за такого статусу не можна. Scope допускає один буквальний відносний шлях на пункт; керівні символи відхиляються.

Це не повний sandbox: довіра до встановленого Git/ОС, обмеження ресурсів, repo policy та гонки файлової системи залишаються окремими питаннями.
