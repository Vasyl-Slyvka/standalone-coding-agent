"""Offline validation of observations from candidate coding engines.

This cannot prove that an engine disclosed every hidden call. Independent
provider or gateway logs are needed for that separate comparison.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class RecordError(ValueError):
    """The observed run record is incomplete or contradicts its model choice."""


def _nonnegative_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise RecordError(f"{field} must be a nonnegative integer")
    return value


def _list(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise RecordError(f"{field} must be a list of objects")
    return value


def assess(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize recorded metrics without substituting estimates for observed use."""
    if not isinstance(record, dict):
        raise RecordError("The record must be a JSON object")
    for field in ("run_id", "case_id", "candidate", "strategy", "provider", "model",
                  "endpoint_alias", "base_head", "context_mode"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise RecordError(f"Missing nonempty {field}")
    if record["strategy"] not in ("cli_wrapper", "hybrid", "api_loop"):
        raise RecordError("Unknown strategy")
    if record["context_mode"] not in ("baseline", "selective"):
        raise RecordError("Unknown context_mode")
    if record.get("acceptance") not in ("passed", "failed", "not_evaluated"):
        raise RecordError("acceptance must be passed, failed or not_evaluated")
    elapsed = record.get("elapsed_ms")
    if elapsed is not None:
        _nonnegative_int(elapsed, "elapsed_ms")
    calls = _list(record.get("calls"), "calls")
    actions = _list(record.get("actions"), "actions")
    checks = _list(record.get("checks"), "checks")
    if record.get("trace_completeness") not in ("unverified", "correlated"):
        raise RecordError("trace_completeness must be unverified or correlated")
    if record["trace_completeness"] == "correlated" and not record.get("trace_basis"):
        raise RecordError("A correlated trace needs a documented independent basis")

    totals = {"input_tokens": 0, "output_tokens": 0}
    unknown = {"input_tokens": False, "output_tokens": False}
    cost = 0.0
    cost_unknown = False
    for index, call in enumerate(calls):
        if (call.get("provider"), call.get("model"), call.get("endpoint_alias")) != (
                record["provider"], record["model"], record["endpoint_alias"]):
            raise RecordError(f"call {index}: provider/model/endpoint differs from the manual selection")
        if call.get("usage_source") not in ("provider_reported", "engine_reported", "estimate", "unknown"):
            raise RecordError(f"call {index}: unknown usage_source")
        for field in totals:
            value = call.get(field)
            if value is None:
                unknown[field] = True
            else:
                totals[field] += _nonnegative_int(value, f"call {index} {field}")
        if call["usage_source"] == "unknown" and any(call.get(f) is not None for f in totals):
            raise RecordError(f"call {index}: token counts need a stated provenance")
        usd = call.get("cost_usd")
        if usd is None:
            cost_unknown = True
        elif (type(usd) not in (float, int) or usd < 0
              or not isinstance(call.get("price_source"), str) or not call["price_source"].strip()
              or call.get("cost_provenance") not in ("provider_reported", "engine_reported", "estimate")):
            raise RecordError(f"call {index}: cost needs a nonnegative value, price_source and cost_provenance")
        else:
            cost += usd
        # Cache/reasoning counters are informational subsets unless a provider
        # documents otherwise. They are deliberately not added to totals.
        for optional in ("cache_read_tokens", "cache_write_tokens", "reasoning_tokens"):
            if call.get(optional) is not None:
                _nonnegative_int(call[optional], f"call {index} {optional}")

    for index, check in enumerate(checks):
        if check.get("status") not in ("passed", "failed", "not_run", "blocked"):
            raise RecordError(f"check {index}: invalid status")
        if not isinstance(check.get("name"), str) or not check["name"]:
            raise RecordError(f"check {index}: missing name")
        exit_code = check.get("exit_code")
        if check["status"] in ("passed", "failed"):
            _nonnegative_int(exit_code, f"check {index} exit_code")
            if (check["status"] == "passed") != (exit_code == 0):
                raise RecordError(f"check {index}: status contradicts exit_code")
        elif exit_code is not None:
            raise RecordError(f"check {index}: a check not run has no exit_code")

    observed = bool(calls)
    return {
        "run_id": record["run_id"],
        "case_id": record["case_id"],
        "candidate": record["candidate"],
        "selected_provider": record["provider"],
        "selected_model": record["model"],
        "endpoint_alias": record["endpoint_alias"],
        "context_mode": record["context_mode"],
        "acceptance": record["acceptance"],
        "elapsed_ms": "UNKNOWN" if elapsed is None else elapsed,
        "visible_calls": len(calls),
        "trace_completeness_claim": record["trace_completeness"],
        "trace_basis": record.get("trace_basis"),
        "input_tokens": "UNKNOWN" if not observed or unknown["input_tokens"] else totals["input_tokens"],
        "output_tokens": "UNKNOWN" if not observed or unknown["output_tokens"] else totals["output_tokens"],
        "cost_usd": "UNKNOWN" if not observed or cost_unknown else round(cost, 6),
        "cost_provenance": "UNKNOWN" if not observed or cost_unknown else sorted(
            {c["cost_provenance"] for c in calls}),
        "actions_recorded": len(actions),
        "checks": {"passed": sum(c["status"] == "passed" for c in checks),
                   "failed": sum(c["status"] == "failed" for c in checks),
                   "not_run": sum(c["status"] == "not_run" for c in checks),
                   "blocked": sum(c["status"] == "blocked" for c in checks)},
        "note": "Recorded observations only; undisclosed calls/actions cannot be inferred from this file.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess a candidate engine's recorded evidence offline")
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    try:
        result = assess(json.loads(args.record.read_text(encoding="utf-8")))
    except (OSError, ValueError, RecordError) as exc:
        parser.exit(2, f"INVALID RECORD: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
