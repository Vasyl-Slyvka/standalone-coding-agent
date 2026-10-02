"""Bounded loopback-only mock wire protocol; not a provider API adapter."""
from __future__ import annotations

from copy import deepcopy
import http.client
import json
import math

from sca.request_ledger import assess

MAX_RESPONSE_BYTES = 65_536
ROUTE = "/sca/mock-completion"


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("Nonfinite JSON number")


def exchange(ledger: dict, port: int, timeout: float = 1.0) -> tuple[dict, str]:
    """Dispatch the final pending metadata attempt once. Never follow/retry."""
    assess(ledger)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Invalid loopback port")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 10:
        raise ValueError("Socket inactivity timeout must be >0 and <=10 seconds")
    if not ledger["requests"]:
        raise ValueError("A pending request is required")
    request = deepcopy(ledger["requests"][-1])
    if (request["status"], request["http_status"], request["usage"]) != ("incomplete", None, None):
        raise ValueError("Only a new pending request can be dispatched")
    payload = {"schema_version": 1, **{key: request[key] for key in (
        "run_id", "request_id", "model", "category", "step_id", "retry_of")}}
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    diagnostic = "TRANSPORT_INCOMPLETE"
    try:
        connection.request("POST", ROUTE, json.dumps(payload).encode("utf-8"),
                           {"Content-Type": "application/json"})
        response = connection.getresponse()
        if not 100 <= response.status <= 599:
            return request, "PROTOCOL_INVALID"
        request["http_status"] = response.status
        if not 200 <= response.status <= 299:
            request["status"] = "failed"
            return request, "HTTP_FAILED"
        length = response.getheader("Content-Length")
        if length is not None and (not length.isascii() or not length.isdecimal()):
            return request, "PROTOCOL_INVALID"
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            return request, "RESPONSE_TOO_LARGE"
        if length is not None and len(raw) != int(length):
            return request, "TRANSPORT_INCOMPLETE"
        diagnostic = "PROTOCOL_INVALID"
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=_constant)
        if not isinstance(data, dict) or set(data) != {
                "schema_version", "run_id", "request_id", "model", "usage"}:
            raise ValueError("Invalid mock response fields")
        if type(data["schema_version"]) is not int or data["schema_version"] != 1 \
                or any(data[key] != request[key] for key in ("run_id", "request_id", "model")):
            raise ValueError("Mock identity mismatch")
        if data["usage"] is not None and (not isinstance(data["usage"], dict)
                                          or data["usage"].get("source") != "estimate"):
            raise ValueError("Mock usage must be explicitly estimated")
        candidate = {**request, "status": "completed", "usage": data["usage"]}
        checked = deepcopy(ledger)
        checked["requests"][-1] = candidate
        assess(checked)
        return candidate, "MOCK_COMPLETED"
    except (OSError, http.client.HTTPException, UnicodeError, ValueError, RecursionError):
        # Deliberately do not retain a response body, header or exception text.
        return request, diagnostic
    finally:
        connection.close()
