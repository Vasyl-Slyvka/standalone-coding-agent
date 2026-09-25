# S02b.1 — офлайновий аудит подій рушіїв

**Статус: підготовчий слайс до практичного S02b.** Контракт у [`task-S02B-OFFLINE-TRACE.md`](../../tasks/task-S02B-OFFLINE-TRACE.md). Не встановлювали Codex/OpenCode, не викликали моделі та не порівнювали якість, вартість або ізоляцію.

## Що зроблено

[`sca.trace_audit`](../../src/sca/trace_audit.py) читає існуючий JSONL локально. Користувач передає engine, provider і model вручну. Для Codex документовані [`turn.completed.usage`](https://developers.openai.com/codex/noninteractive) записуються як **turn observation**; назва моделі в цій події відсутня. Для OpenCode [CLI JSON format](https://dev.opencode.ai/docs/cli/) й [внутрішні SDK event types](https://github.com/anomalyco/opencode/blob/34aa427434b054afcce7184764aa681159b5d769/packages/sdk/js/src/gen/types.gen.ts) є **різними потоками**: точний [`run.ts`](https://github.com/anomalyco/opencode/blob/34aa427434b054afcce7184764aa681159b5d769/packages/opencode/src/cli/cmd/run.ts) видає `step_finish` із `part`, а SSE видає `message.updated` і `message.part.updated`. У CLI-потоці модель не виводиться окремою подією; її ідентичність лишається `unresolved`. SSE може зіставити її лише за повних полів. Однаковий `part.id` обліковується один раз.

```bash
PYTHONPATH=src python3 -m sca.trace_audit codex /path/to/events.jsonl --provider PROVIDER --model MODEL
PYTHONPATH=src python3 -m sca.trace_audit opencode /path/to/events.jsonl --provider PROVIDER --model MODEL
```

Результат містить типи/кількість подій, usage observations, виявлені явні розбіжності моделі та error events. `api_call_count` завжди `UNKNOWN`, `trace_completeness=unverified`, відсутні токени — `null`. OpenCode `cost` позначено як `engine_reported_cost_usd`, без прирівнювання до рахунка API. Cache/reasoning не додаються до input/output. Це **не** нормалізований `calls[]` стенда S02a і не його per-call proof. Вихід не містить тексту prompt, tool output чи ключів. Сирий локальний JSONL може містити чутливі дані: не комітити/не надсилати його.

## Перевірка та обмеження

Тести використовують **синтетичні**, не записані з engine, події. Вони перевіряють turn проти API-call, dedup step, явний mismatch, пропущене usage, зламаний JSON і суперечливий message ID. `PYTHONPATH=src:. python3 -m unittest discover -s tests -v` та `git diff --check` — обов'язкові. Під час реального spike треба перевірити точну версію engine і фактичний stream, незалежно зіставити модельні запити з provider/gateway logs, а також виміряти дозволи на дії та перевірити diff/tests на S02a фікстурах. Інструмент не бачить прихованих викликів, не контролює shell/network і не обмежує витрати.

У [попередньому аудиті](003-static-engine-audit.md) виправлено `trace_completeness=uncorrelated` на чинне значення схеми `unverified`. **Практичний S02b/R1 залишається відкритим** до ручного вибору OS, двох provider/model та бюджету експерименту.
