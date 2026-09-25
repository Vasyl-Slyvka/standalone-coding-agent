# S04b — офлайновий добір контексту

**Стан:** реалізовано read-only прев’ю з явним лімітом **UTF-8 байтів**, не токенів. [Task spec](../../tasks/task-S04B-CONTEXT.md). Цей модуль не інтегрований із backend і не вирішує, які джерела в репозиторії є обов'язковими.

`PYTHONPATH=src python3 -m sca.context_pack tasks/task-S04B-CONTEXT.md . 'context preflight' --file src/sca/task.py --budget-bytes 8192` повертає JSON. `mandatory` містить повні `must_do`, `must_not`, `acceptance`, `stop_rule` task у вихідному порядку. Коли обов'язковий блок плюс метадані не вміщуються — команда припиняється без скорочення. `optional` містить фрагменти лише явно перелічених Git tracked UTF-8 файлів, лексично зіставлені з query, з шляхом і SHA-256 повного файла. `used_bytes` — розмір компактного UTF-8 JSON разом із метаданими; pretty printed CLI результат може займати більше байтів. `omitted` перелічує відкинуті кандидати.

Один файл обмежено 64 KiB, до 64 різних кандидатів, бюджет 256–1 048 576 байтів. Відхиляються absolute/traversal, symlink, untracked, binary, invalid UTF-8 та завеликі файли. Файл може змінитися після читання: digest описує прочитані байти, але не блокує race; інструмент нічого не записує. Сам `git ls-files` є безпечним фіксованим Git викликом, task checks та shell із task не виконуються. Не запускати на приватних файлах без окремого рішення про надсилання контексту до provider.

**Межа:** перед model call ще потрібні перевірені authoritative repo rules, всі обов’язкові sources, інтеграція з фактичним tokenizer/context window, захист від змін між добором і відправленням, а також вимірювання якості й usage. Результат не закриває S02b/R1, S04 чи Product DoD.

**Перевірка:** синтетична Git-фікстура, детермінований фрагмент, точні clauses, ліміт і відкидання optional, негативні path/symlink/binary/large cases, незмінний Git статус; повний набір unittest, компіляція Python, `git diff --check` і перевірка локальних Markdown-посилань.
