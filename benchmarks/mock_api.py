"""Disposable loopback mock and pre-API experiment; no inference or provider API."""
from __future__ import annotations

from contextlib import contextmanager
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import time

from sca.mock_http import MAX_RESPONSE_BYTES, ROUTE
from sca.mock_run import MockRun
from sca.request_ledger import assess

SELECTION = {"provider": "mock-provider", "model": "mock-model", "endpoint_alias": "loopback"}
LIMITS = {"max_steps": 10, "max_elapsed_ms": 10_000, "soft_cost_usd": None}
USAGE = {"input_tokens": 10, "output_tokens": 2, "cache_read_tokens": 3,
         "cache_write_tokens": None, "reasoning_tokens": 1, "source": "estimate",
         "token_semantics": "inclusive"}


@contextmanager
def mock_server(modes=("ok",)):
    """A finite scripted responder. Captures allowlisted synthetic IDs only."""
    script = tuple(modes)
    if not script:
        raise ValueError("At least one scripted response is required")
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.connection.settimeout(1)
            if self.path != ROUTE:
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192:
                self.send_error(413)
                return
            payload = json.loads(self.rfile.read(length))
            identity = {key: payload[key] for key in ("run_id", "request_id", "model")}
            received.append(identity)
            index = len(received) - 1
            mode = script[index] if index < len(script) else "http_error"
            if mode == "disconnect":
                self.close_connection = True
                return
            if mode == "timeout":
                time.sleep(0.12)
            status = 503 if mode == "http_error" else 307 if mode == "redirect" else 200
            data = {"schema_version": 1, **identity, "usage": dict(USAGE)}
            if mode == "missing_usage":
                data["usage"] = None
            elif mode in ("wrong_model", "wrong_run", "wrong_id"):
                key = {"wrong_model": "model", "wrong_run": "run_id", "wrong_id": "request_id"}[mode]
                data[key] = "different"
            elif mode == "extra":
                data["body"] = "untrusted response text must not enter evidence"
            elif mode == "provider_usage":
                data["usage"]["source"] = "provider_reported"
            elif mode == "negative_usage":
                data["usage"]["input_tokens"] = -1
            raw = json.dumps(data).encode()
            if mode == "duplicate":
                raw = raw[:-1] + b',"model":"duplicate"}'
            elif mode == "nonfinite":
                raw = raw.replace(b'"input_tokens": 10', b'"input_tokens": NaN')
            elif mode == "malformed":
                raw = b'not-json'
            elif mode == "deep":
                raw = b'[' * 2000 + b'0' + b']' * 2000
            elif mode == "oversized":
                raw = b' ' * (MAX_RESPONSE_BYTES + 1)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw) + (1 if mode == "truncated" else 0)))
            if mode == "redirect":
                self.send_header("Location", "http://127.0.0.1:1/never-follow")
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass
            self.close_connection = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield server.server_port, received
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _blocked(function):
    try:
        function()
    except ValueError:
        return True
    return False


def demo():
    checks = {}
    with mock_server(("ok", "ok", "ok")) as (port, received):
        run = MockRun("demo", SELECTION, {**LIMITS, "max_steps": 3})
        for request_id, category, step in (("r1", "task", "s1"),
                                            ("r2", "auxiliary", None), ("r3", "task", "s2")):
            run.begin(request_id, category, step)
            assert run.dispatch(port) == "MOCK_COMPLETED"
        checks["step_stop_blocks_fourth_http"] = _blocked(lambda: run.begin("r4", "task", "s3")) \
            and len(received) == 3
        summary = assess(run.ledger)
        checks["three_requests_two_cli_steps"] = summary["observed_requests"] == 3 \
            and summary["declared_steps"] == 2
        checks["unknown_cost_retained"] = summary["cost_usd"] == "UNKNOWN"
    with mock_server(("http_error", "ok")) as (port, received):
        run = MockRun("recovery", SELECTION, LIMITS)
        run.begin("r1", "task", "s1")
        assert run.dispatch(port) == "HTTP_FAILED"
        with tempfile.TemporaryDirectory(prefix="sca-mock-checkpoint-") as directory:
            checkpoint_path = Path(directory) / "checkpoint.json"
            checkpoint_path.write_text(json.dumps(run.checkpoint()), encoding="utf-8")
            reopened = MockRun.reopen(json.loads(checkpoint_path.read_text(encoding="utf-8")),
                                      run_id="recovery", selection=SELECTION, limits=LIMITS)
        checks["reopen_has_no_http"] = len(received) == 1
        checks["implicit_replay_blocked"] = _blocked(lambda: reopened.dispatch(port)) \
            and _blocked(lambda: reopened.begin("r2", "task", "s1"))
        reopened.begin("r2", "retry", "s1", "r1")
        checks["explicit_retry_is_separate_attempt"] = reopened.dispatch(port) == "MOCK_COMPLETED" \
            and len(received) == 2 and len(reopened.ledger["requests"]) == 2
    with mock_server() as (port, received):
        run = MockRun("price", SELECTION, {**LIMITS, "soft_cost_usd": "0.01"})
        run.begin("r1", "task", "s1")
        run.dispatch(port)
        checks["unknown_price_blocks_next_http"] = _blocked(lambda: run.begin("r2", "task", "s2")) \
            and len(received) == 1
        denied = MockRun("denied", SELECTION, LIMITS)
        checks["explicit_denial_has_no_http"] = _blocked(
            lambda: denied.begin("r1", "task", "s1", permitted=False)) and len(received) == 1
    assert all(checks.values()), checks
    return {"mock_only": True, "checks": checks, "happy_http_requests": 3,
            "happy_cli_steps": 2, "mock_estimated_totals": summary["observed_totals"],
            "cost_usd": "UNKNOWN", "provider_api_calls": 0, "R1": "OPEN",
            "note": "Loopback mock evidence only; no engine completeness or task acceptance claim."}


if __name__ == "__main__":
    print(json.dumps(demo(), indent=2))
