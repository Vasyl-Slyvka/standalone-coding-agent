"""Offline post-step soft-stop decision over visible usage observations.

This module cannot intercept model requests or prove that the trace is complete.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sys
from typing import Any


class GateError(ValueError):
    """A record cannot safely drive the next-step decision."""


_ROOT = {"schema_version", "selection", "limits", "elapsed_ms", "steps"}
_SELECTION = {"provider", "model", "endpoint_alias"}
_LIMITS = {"max_steps", "max_elapsed_ms", "soft_cost_usd"}
_STEP = {"step_id", "provider", "model", "endpoint_alias", "input_tokens",
         "output_tokens", "cost_usd", "cost_provenance", "price_source"}
_COST_SOURCES = {"provider_reported", "engine_reported", "estimate"}
_USD = re.compile(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,9})?\Z")


def _object(data: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(data, dict) or set(data) != keys:
        raise GateError(f"{label}: expected exactly {', '.join(sorted(keys))}")
    return data


def _integer(data: Any, label: str, minimum: int = 0) -> int:
    if type(data) is not int or data < minimum:
        raise GateError(f"{label} must be an integer >= {minimum}")
    return data


def _money(data: Any, label: str) -> Decimal:
    if not isinstance(data, str) or not _USD.fullmatch(data):
        raise GateError(f"{label} must be a decimal string in USD")
    try:
        amount = Decimal(data)
    except InvalidOperation as exc:
        raise GateError(f"{label} must be a decimal string in USD") from exc
    if not amount.is_finite() or amount < 0:
        raise GateError(f"{label} must be finite and nonnegative")
    return amount


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GateError(f"Duplicate field: {key}")
        result[key] = value
    return result


def decide(record: dict[str, Any]) -> dict[str, Any]:
    """Decide whether another *controlled* step may begin after visible steps."""
    record = _object(record, _ROOT, "record")
    _integer(record["schema_version"], "schema_version", 1)
    if record["schema_version"] != 1:
        raise GateError("Only schema_version 1 is supported")
    selection = _object(record["selection"], _SELECTION, "selection")
    if any(not isinstance(value, str) or not value.strip() or value != value.strip()
           for value in selection.values()):
        raise GateError("Selection needs explicit nonempty identifiers")
    if any(selection[field].lower() in ("auto", "default") for field in ("provider", "model")):
        raise GateError("Selection cannot use auto/default provider or model")
    limits = _object(record["limits"], _LIMITS, "limits")
    max_steps = _integer(limits["max_steps"], "max_steps", 1)
    max_elapsed = _integer(limits["max_elapsed_ms"], "max_elapsed_ms", 1)
    elapsed = _integer(record["elapsed_ms"], "elapsed_ms")
    cap = None if limits["soft_cost_usd"] is None else _money(
        limits["soft_cost_usd"], "soft_cost_usd")
    steps = record["steps"]
    if not isinstance(steps, list):
        raise GateError("steps must be a list")

    ids: set[str] = set()
    token_totals = {"input_tokens": 0, "output_tokens": 0}
    token_unknown = {key: False for key in token_totals}
    cost = Decimal("0")
    cost_unknown = False
    provenances: set[str] = set()
    for index, raw in enumerate(steps):
        step = _object(raw, _STEP, f"step {index}")
        step_id = step["step_id"]
        if not isinstance(step_id, str) or not step_id.strip() or step_id != step_id.strip() \
                or step_id in ids:
            raise GateError(f"step {index}: missing or duplicate step_id")
        ids.add(step_id)
        if any(step[field] != selection[field] for field in _SELECTION):
            raise GateError(f"step {index}: provider/model/endpoint differs from selection")
        for key in token_totals:
            value = step[key]
            if value is None:
                token_unknown[key] = True
            else:
                token_totals[key] += _integer(value, f"step {index} {key}")
        value = step["cost_usd"]
        if value is None:
            cost_unknown = True
            if step["cost_provenance"] != "unknown" or step["price_source"] is not None:
                raise GateError(f"step {index}: unknown cost needs unknown provenance and null source")
        else:
            cost += _money(value, f"step {index} cost_usd")
            source = step["cost_provenance"]
            if not isinstance(source, str) or source not in _COST_SOURCES \
                    or not isinstance(step["price_source"], str) \
                    or not step["price_source"].strip():
                raise GateError(f"step {index}: known cost needs provenance and price_source")
            provenances.add(source)

    reasons = []
    if len(steps) >= max_steps:
        reasons.append("MAX_STEPS_REACHED")
    if elapsed >= max_elapsed:
        reasons.append("MAX_ELAPSED_REACHED")
    if cap is not None and steps:
        if cost_unknown:
            reasons.append("COST_UNKNOWN_UNDER_SOFT_CAP")
        elif cost >= cap:
            reasons.append("SOFT_COST_REACHED")
    return {
        "decision": "SOFT_STOP" if reasons else "ALLOW_NEXT_CONTROLLED_STEP",
        "reasons": reasons,
        "visible_steps": len(steps),
        "input_tokens": "UNKNOWN" if not steps or token_unknown["input_tokens"]
                        else token_totals["input_tokens"],
        "output_tokens": "UNKNOWN" if not steps or token_unknown["output_tokens"]
                         else token_totals["output_tokens"],
        "cost_usd": "UNKNOWN" if not steps or cost_unknown else str(cost),
        "cost_provenance": sorted(provenances),
        "cost_basis": "visible observations only; not an invoice or subscription balance",
        "stop_kind": "post-step soft stop; no pre-call guarantee",
        "trace_completeness": "unverified",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess offline usage before the next controlled step")
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    try:
        if args.record.stat().st_size > 65_536:
            raise GateError("Record exceeds 64 KiB")
        record = json.loads(args.record.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs)
        result = decide(record)
    except (OSError, UnicodeError, json.JSONDecodeError, GateError) as exc:
        print(f"INVALID USAGE RECORD: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
