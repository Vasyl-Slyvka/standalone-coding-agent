# S09 — loopback HTTP IDs and mock usage

[Task](../../tasks/task-S09-MOCK-HTTP.md) · [adapter](../../src/sca/mock_http.py) · [scripted server/demo](../../benchmarks/mock_api.py) · [tests](../../tests/test_mock_http.py).

The new stdlib adapter sends a metadata-only pending attempt once to literal `127.0.0.1:<port>/sca/mock-completion`. There is no arbitrary host/URL, environment proxy, credential path, redirect, model inference or automatic retry. The existing request-ledger validates records before dispatch and normalized responses afterward; old modules remain unchanged.

Mock protocol v1 request fields are schema_version, run_id, request_id, model, category, step_id, retry_of. Response fields are schema_version, run_id, request_id, model, usage. IDs/model/version must agree; unknown keys, duplicate fields, nonfinite/deep/malformed JSON and invalid usage are refused. Usage is nullable or the existing ledger usage schema with source=estimate. This is intentionally a synthetic wire protocol, not OpenAI/Anthropic compatibility or a provider-format mapper.

Response reads retain at most 64 KiB + one sentinel byte. Declared Content-Length truncation is detected. HTTP 3xx/4xx/5xx is a failed attempt; transport/protocol problems remain incomplete with unknown usage. Diagnostics are fixed labels without raw exceptions/bodies/headers. Socket inactivity timeout is >0 and <=10 seconds; it is not a strict total wall-time limit. The server is disposable test tooling, not a production HTTP service or security boundary against hostile local processes.

Tests exercise real sockets: successful IDs/estimated inclusive usage, missing usage, wrong run/request/model, extra payload, fake provider provenance, negative counters, duplicate/nonfinite/malformed/deep JSON, oversized/truncated response, timeout/disconnect, HTTP error/redirect, invalid selection/arguments and completed-attempt replay refusal. Cache/reasoning are not added to input/output.

Verification and publication evidence are retained in the [shared validation](../reviews/validation-2026-10-02-pre-api.json) and [test log](../reviews/unit-tests-2026-10-02-pre-api.txt). [S10](014-pre-api-control.md) exercises controlled stop/reopen behavior. No engine trace completeness, verified provider usage, price, accepted coding task, closed R1 or Product DoD claim follows from a mock response.

Local verification: **106/106 tests PASS** (80 existing + 26 new), compilation/whitespace exit 0, **127 local Markdown path targets / 0 broken**, existing quickstart clean and all **22 existing source/test files byte-identical**. Mock demo passes 8 independent checks. No existing fixture is edited. GitHub publication/readback and remote CI status are recorded in the shared validation JSON.
