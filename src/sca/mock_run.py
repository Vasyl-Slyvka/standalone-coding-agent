"""Experimental metadata checkpoints and control for the loopback mock only."""
from __future__ import annotations

from copy import deepcopy
import time

from sca.mock_http import exchange
from sca.request_ledger import assess
from sca.usage_gate import decide


class MockRun:
    """No workspace actions, credentials, provider routing or implicit replay."""

    def __init__(self, run_id: str, selection: dict, limits: dict):
        self._ledger = {"schema_version": 1, "run_id": run_id,
                        "selection": deepcopy(selection), "steps": [], "requests": []}
        self._limits = deepcopy(limits)
        self._elapsed_ms = 0
        self._started = time.monotonic()
        self._pending = False
        assess(self._ledger)
        self.gate()

    @property
    def ledger(self):
        return deepcopy(self._ledger)

    def _elapsed(self):
        return self._elapsed_ms + max(0, int((time.monotonic() - self._started) * 1000))

    def gate(self):
        steps = []
        for request in self._ledger["requests"]:
            usage = request["usage"]
            inclusive = usage is not None and usage["token_semantics"] == "inclusive"
            steps.append({"step_id": request["request_id"], **self._ledger["selection"],
                          "input_tokens": usage["input_tokens"] if inclusive else None,
                          "output_tokens": usage["output_tokens"] if inclusive else None,
                          "cost_usd": None, "cost_provenance": "unknown", "price_source": None})
        return decide({"schema_version": 1, "selection": self._ledger["selection"],
                       "limits": self._limits, "elapsed_ms": self._elapsed(), "steps": steps})

    def begin(self, request_id: str, category: str, step_id=None, retry_of=None,
              *, permitted: bool = True):
        """Record pending BEFORE HTTP; caller must checkpoint before dispatch."""
        if permitted is not True:
            raise ValueError("MOCK_DISPATCH_DENIED")
        if self._pending:
            raise ValueError("PENDING_ATTEMPT_REQUIRES_REOPEN")
        if self.gate()["decision"] != "ALLOW_NEXT_CONTROLLED_STEP":
            raise ValueError("MOCK_SOFT_STOP")
        prior = self._ledger["requests"]
        if prior and prior[-1]["status"] != "completed":
            if category != "retry" or retry_of != prior[-1]["request_id"]:
                raise ValueError("EXPLICIT_RETRY_REQUIRED")
        if category == "retry" and (not prior or retry_of != prior[-1]["request_id"]
                                     or prior[-1]["status"] == "completed"):
            raise ValueError("Retry must reference the latest unsuccessful attempt")
        candidate = deepcopy(self._ledger)
        request = {"request_id": request_id, "run_id": candidate["run_id"],
                   **candidate["selection"], "category": category,
                   "category_source": "unknown" if category == "unknown" else "operator_annotation",
                   "step_id": step_id, "retry_of": retry_of, "status": "incomplete",
                   "http_status": None, "usage": None}
        candidate["requests"].append(request)
        if step_id is not None:
            step = next((s for s in candidate["steps"] if s["step_id"] == step_id), None)
            if step is None:
                step = {"step_id": step_id, "request_ids": []}
                candidate["steps"].append(step)
            step["request_ids"].append(request_id)
        assess(candidate)
        self._ledger = candidate
        self._pending = True
        return self.checkpoint()

    def dispatch(self, port: int, timeout: float = 1.0):
        if not self._pending:
            raise ValueError("NO_NEW_PENDING_ATTEMPT")
        # begin checked before adding this attempt; time may have expired meanwhile.
        if self._elapsed() >= self._limits["max_elapsed_ms"]:
            self._pending = False
            raise ValueError("MOCK_TIME_STOP_BEFORE_DISPATCH")
        try:
            request, diagnostic = exchange(self._ledger, port, timeout)
            self._ledger["requests"][-1] = request
            return diagnostic
        finally:
            # Even bad local parameters do not authorize silently replaying a pending attempt.
            self._pending = False

    def checkpoint(self):
        return {"schema_version": 1, "mock_only": True, "ledger": self.ledger,
                "limits": deepcopy(self._limits), "elapsed_ms": self._elapsed()}

    @classmethod
    def reopen(cls, checkpoint: dict, *, run_id: str, selection: dict, limits: dict):
        """Validate caller-supplied metadata; no HTTP and no automatic resume."""
        if not isinstance(checkpoint, dict) or set(checkpoint) != {
                "schema_version", "mock_only", "ledger", "limits", "elapsed_ms"}:
            raise ValueError("Invalid checkpoint fields")
        if type(checkpoint["schema_version"]) is not int or checkpoint["schema_version"] != 1 \
                or checkpoint["mock_only"] is not True \
                or type(checkpoint["elapsed_ms"]) is not int or checkpoint["elapsed_ms"] < 0:
            raise ValueError("Invalid checkpoint version/time")
        ledger = checkpoint["ledger"]
        assess(ledger)
        if ledger["run_id"] != run_id or ledger["selection"] != selection \
                or checkpoint["limits"] != limits:
            raise ValueError("Frozen checkpoint identity/limits differ")
        for index, item in enumerate(ledger["requests"]):
            if item["usage"] is not None and item["usage"]["source"] != "estimate":
                raise ValueError("Mock checkpoint usage must be estimated")
            previous = ledger["requests"][index - 1] if index else None
            if previous and previous["status"] != "completed":
                if item["category"] != "retry" or item["retry_of"] != previous["request_id"]:
                    raise ValueError("Unresolved earlier unsuccessful attempt")
            elif item["category"] == "retry":
                raise ValueError("Retry has no unsuccessful predecessor")
        result = cls(run_id, selection, limits)
        result._ledger = deepcopy(ledger)
        result._elapsed_ms = checkpoint["elapsed_ms"]
        result._started = time.monotonic()
        result.gate()
        return result
