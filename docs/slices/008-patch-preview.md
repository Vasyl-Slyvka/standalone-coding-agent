# S04a — офлайнове прев’ю правки

**Стан:** реалізовано перевірку однієї запропонованої заміни текстового файлу без запису. Це лише підготовка до S04: живий S02b/R1 і повний S03/S04 не завершено. [Task spec](../../tasks/task-S04A-PATCH-PREVIEW.md).

## Вхід і запуск

Потрібні локальний синтетичний Git-репозиторій, чинний Markdown task contract із S01 та JSON candidate до 256 KiB. У candidate рівно чотири поля: `path` (шлях від кореня repo), `expected_head` (повний Git commit hash), `expected_sha256` (SHA-256 **поточних байтів** файлу) і `replacement` (повний бажаний UTF-8 текст). Наприклад, заміна `src/app.py` з вмістом `print('hello')\n` на `print('goodbye')\n` має такий формат:

```json
{
  "path": "src/app.py",
  "expected_head": "<повний hash HEAD із локального Git>",
  "expected_sha256": "<64 шістнадцяткові символи SHA-256 старого файлу>",
  "replacement": "print('goodbye')\n"
}
```

```bash
PYTHONPATH=src python3 -m sca.patch_preview /path/to/test-repo /path/to/task.md /path/to/candidate.json
```

Exit `0` означає лише `PREVIEW_ONLY`, exit `2` — `BLOCKED PREVIEW`. Перед diff програма перевіряє branch/HEAD/scope/dirty через S01, відхиляє вихід за scope, symlink, нетекстові/завеликі файли (межа 128 KiB), незареєстрований у Git файл і невідповідний SHA-256. Diff показує рядкові зміни, а окремі прапорці фіксують наявність кінцевого newline, зокрема коли **лише** він змінився. Прев’ю ніколи не виконує заявлені в task команди і не застосовує заміну.

## Докази й межі

На синтетичному Git-репозиторії тести звіряють diff, незмінний файл та чистий Git index/worktree після прев’ю; негативні випадки HEAD/hash, dirty, path escape, symlink, untracked, malformed candidate і некоректного UTF-8 блокуються. Ніяких model/API calls, рахунків чи витрат немає.

Результат прямо позначає `policy_status: not_evaluated`: S01 не розбирає чинні правила цільового repo, nested `AGENTS.md`, issue/dependencies або NODREN phase gate. Це **не дозвіл на редагування** і не захист майбутнього запису від гонок, shell, прав доступу чи сторонніх процесів. До виконання правки потрібні окремо перевірені policy adapter, ізоляція, безпечний запис і повторна перевірка стану безпосередньо перед ним.

## Перевірка

`PYTHONPATH=src:. python3 -m unittest discover -s tests -v`, компіляція Python, `git diff --check`, локальні Markdown-посилання. Перевірки доводять лише поведінку цього офлайнового прототипу.
