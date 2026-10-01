# S07 — публічний work in progress і повторна перевірка

**01.10.2026 · локальні перевірки PASS; публікація виконується.** [Task S07](../../tasks/task-S07-PUBLIC.md). Авторизація власника: продовжити, повторно перевірити та зробити саме Standalone Coding Agent публічним WIP на GitHub. Локальна база — `5e05e13`; віддалена база — `d294403`. Історії різні через попередні вебкоміти; remote history не переписується.

## Scope

Англомовний README показує реалізовані компоненти, межі й наступні кроки; українські дизайн і звіти збережено. Додано офлайновий приклад задачі, перевірку локальних Markdown-шляхів та CI для Python 3.10/3.13. CI має `contents: read`, офіційні actions із pinned commit SHA, `persist-credentials: false`, 10-хвилинний timeout і не використовує model API keys. Перед public change перевіряються tracked файли та доступна локальна історія; raw logs, binaries і weights не входять у публікацію.

## Перевірки та публікація

- [Повторний unittest log](unit-tests-2026-10-01.txt): **62/62 PASS**, exit 0, Python 3.12.14.
- [Машинозчитувана перевірка](validation-2026-10-01.json): compilation, README preflight і benchmark example — exit 0; усі байти fixture включно з Git-файлами незмінні.
- **93 local Markdown path target, 0 broken**; додатково перевірено позитивний і missing-target випадки самого checker. Зовнішні URL, anchors і reference-style links не оцінено.
- `git diff --check` — exit 0; YAML workflow parsed; read-only permissions і matrix перевірено.
- **112 унікальних reachable local Git blobs** і working-tree project files перевірено п'ятьма credential patterns; hits 0, binary/large assets 0. Два GitHub UI списки показують усі 69 попередніх комітів цього проєкту; повний remote-history byte scan до відкриття недоступний. Це не повний аудит секретів чи безпеки.
- Ліцензії й notices стороннього коду не підміняються: S07 не копіює engine code та не додає runtime dependencies. CI використовує офіційні actions/checkout і actions/setup-python; обидва v6 refs перевірено через GitHub API 01.10.2026 та pinned у workflow. [Checkout revision](https://github.com/actions/checkout/commit/d23441a48e516b6c34aea4fa41551a30e30af803), [setup-python revision](https://github.com/actions/setup-python/commit/ece7cb06caefa5fff74198d8649806c4678c61a1).
- GitHub visibility/content verification і CI run ще виконуються. Наявність workflow-файла сама не означає успішний GitHub Actions run.

## Scope і Definitions of Done

| Рівень | Стан |
|---|---|
| Слайси S01–S06 | Повторна перевірка наявного scope; їхні обмеження збережено у [повному рев’ю](2026-09-26-full-review.md). |
| S07 | Публічне оформлення, перевірки та publication verification; завершення лише після підтвердження remote. |
| Design DoD | 4/4 прийнято власником 25.09.2026. |
| Product DoD | 0/5 повністю закритих критеріїв; не відсоток роботи. |
| R1 / engine | OPEN; engine не обрано. |
| Ліцензія SCA | Рішення власника відкрите; public не означає open-source grant. |

Наступний технічний слайс — кореляція локальних HTTP requests і usage, потім permission/failure/recovery та парне порівняння. Два реальні API-провайдери й inference budget лишаються відкладеними. Під час S07 модельні API не викликаються; NODREN не редагується.
