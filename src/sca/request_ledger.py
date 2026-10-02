"""Correlate supplied request/step/usage metadata offline, without model calls.

An internally consistent record does not prove that an engine disclosed every
request, used the claimed model or reported accurate usage. No live interception,
price lookup, budget enforcement or provider-format conversion is performed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


class LedgerError(ValueError):
    """Supplied metadata is malformed or contradicts its own identities."""


_ROOT = {"schema_version", "run_id", "selection", "steps", "requests"}
_IDENTITY = {"provider", "model", "endpoint_alias"}
_STEP = {"step_id", "request_ids"}
_REQUEST = {"request_id", "run_id", *_IDENTITY, "category", "category_source",
            "step_id", "retry_of", "status", "http_status", "usage"}
_TOKENS = ("input_tokens", "output_tokens", "cache_read_tokens",
           "cache_write_tokens", "reasoning_tokens")
_USAGE = {*_TOKENS, "source", "token_semantics"}
_CATEGORIES = ("task", "auxiliary", "retry", "unknown")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")
_MAX_ITEMS = 1000
_MAX_BYTES = 1_048_576


def _object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise LedgerError(f"{label}: fields do not match the metadata schema")
    return value


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise LedgerError(f"{label}: expected a bounded identifier")
    return value


def _choice(value: Any, options: tuple[str, ...], label: str) -> str:
    if not isinstance(value, str) or value not in options:
        raise LedgerError(f"{label}: unsupported value")
    return value


def _items(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list) or len(value) > _MAX_ITEMS:
        raise LedgerError(f"{label}: expected a list with at most {_MAX_ITEMS} items")
    return value


def _usage(value: Any, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    usage = _object(value, _USAGE, label)
    source = _choice(usage["source"], ("provider_reported", "engine_reported", "estimate"),
                     f"{label} source")
    semantics = _choice(usage["token_semantics"], ("inclusive", "unspecified"),
                        f"{label} token_semantics")
    result: dict[str, Any] = {"source": source, "token_semantics": semantics}
    for field in _TOKENS:
        count = usage[field]
        if count is not None and (type(count) is not int or not 0 <= count <= 2**63 - 1):
            raise LedgerError(f"{label} {field}: expected null or a nonnegative 63-bit integer")
        result[field] = count
    if semantics == "inclusive":
        for subset, total in (("cache_read_tokens", "input_tokens"),
                              ("cache_write_tokens", "input_tokens"),
                              ("reasoning_tokens", "output_tokens")):
            if result[subset] is not None and result[total] is not None \
                    and result[subset] > result[total]:
                raise LedgerError(f"{label}: subset counter exceeds its inclusive total")
    return result


def _totals(requests: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"requests": len(requests)}
    for field in ("input_tokens", "output_tokens"):
        counts = [item["usage"][field] if item["usage"] is not None
                  and item["usage"]["token_semantics"] == "inclusive" else None
                  for item in requests]
        result[field] = sum(counts) if counts and all(x is not None for x in counts) else "UNKNOWN"
        result[f"known_{field}_subtotal"] = sum(x for x in counts if x is not None)
        result[f"unknown_{field}_requests"] = sum(x is None for x in counts)
    return result


def assess(record: dict[str, Any]) -> dict[str, Any]:
    """Validate ID relationships and summarize only the supplied observations."""
    record = _object(record, _ROOT, "record")
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise LedgerError("Only schema_version 1 is supported")
    run_id = _id(record["run_id"], "run_id")
    selection = _object(record["selection"], _IDENTITY, "selection")
    for field in sorted(_IDENTITY):
        _id(selection[field], f"selection {field}")
        if field in ("provider", "model") and selection[field].lower() in ("auto", "default"):
            raise LedgerError("Selection must be explicit")
    if "/" in selection["endpoint_alias"] or "://" in selection["endpoint_alias"]:
        raise LedgerError("endpoint_alias must be a name, not a URL/path")

    steps: dict[str, list[str]] = {}
    linked: set[str] = set()
    for index, raw in enumerate(_items(record["steps"], "steps")):
        step = _object(raw, _STEP, f"step {index}")
        step_id = _id(step["step_id"], f"step {index} step_id")
        if step_id in steps:
            raise LedgerError("Duplicate step_id")
        ids = [_id(value, f"step {index} request_id")
               for value in _items(step["request_ids"], f"step {index} request_ids")]
        if len(set(ids)) != len(ids) or linked.intersection(ids):
            raise LedgerError("A request is linked more than once")
        linked.update(ids)
        if len(linked) > _MAX_ITEMS:
            raise LedgerError("Too many linked requests")
        steps[step_id] = ids

    requests: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, str]] = []
    for index, raw in enumerate(_items(record["requests"], "requests")):
        request = _object(raw, _REQUEST, f"request {index}")
        request_id = _id(request["request_id"], f"request {index} request_id")
        if request_id in by_id:
            raise LedgerError("Duplicate request_id")
        if request["run_id"] != run_id:
            raise LedgerError("Request belongs to another run")
        if any(request[field] != selection[field] for field in _IDENTITY):
            raise LedgerError("Request provider/model/endpoint differs from selection")
        category = _choice(request["category"], _CATEGORIES, f"request {index} category")
        source = _choice(request["category_source"],
                         ("adapter_reported", "operator_annotation", "unknown"),
                         f"request {index} category_source")
        if (category == "unknown") != (source == "unknown"):
            raise LedgerError("Category and classification provenance disagree")
        step_id = request["step_id"]
        if step_id is not None:
            _id(step_id, f"request {index} step_id")
            if step_id not in steps or request_id not in steps[step_id]:
                raise LedgerError("Request-to-step link is absent or contradictory")
        elif request_id in linked:
            raise LedgerError("Step lists a request that declares no step")

        parent_id = request["retry_of"]
        if category == "retry":
            _id(parent_id, f"request {index} retry_of")
            parent = by_id.get(parent_id)
            if parent is None or parent["step_id"] != step_id:
                raise LedgerError("Retry needs an earlier request in the same step")
            purpose = parent["purpose"]
        elif parent_id is not None:
            raise LedgerError("Only a retry can have retry_of")
        else:
            purpose = category

        status = _choice(request["status"], ("completed", "failed", "incomplete"),
                         f"request {index} status")
        http = request["http_status"]
        if http is not None and (type(http) is not int or not 100 <= http <= 599):
            raise LedgerError("http_status must be null or an integer from 100 to 599")
        if status == "completed" and (http is None or not 200 <= http <= 299):
            raise LedgerError("Completed request needs a successful HTTP status")
        usage = _usage(request["usage"], f"request {index} usage")
        # Construct a detached, allowlisted result; arbitrary payloads never pass through.
        normalized = {**{field: request[field] for field in _REQUEST - {"usage"}},
                      "usage": usage, "purpose": purpose}
        requests.append(normalized)
        by_id[request_id] = normalized
        for condition, code in (
                (purpose == "unknown", "CLASSIFICATION_UNKNOWN"),
                (purpose == "task" and step_id is None, "TASK_REQUEST_WITHOUT_STEP"),
                (status == "incomplete", "REQUEST_INCOMPLETE"),
                (usage is None or usage["input_tokens"] is None or usage["output_tokens"] is None,
                 "USAGE_MISSING"),
                (usage is not None and usage["token_semantics"] != "inclusive",
                 "TOKEN_SEMANTICS_UNSPECIFIED")):
            if condition:
                issues.append({"request_id": request_id, "code": code})

    if linked - by_id.keys():
        raise LedgerError("Step refers to an unobserved request")
    for step_id, ids in steps.items():
        if any(by_id[request_id]["step_id"] != step_id for request_id in ids):
            raise LedgerError("Step-to-request link is contradictory")
        if not ids:
            issues.append({"step_id": step_id, "code": "STEP_WITHOUT_REQUEST"})
    if not requests:
        issues.append({"code": "NO_REQUESTS_OBSERVED"})

    return {
        "schema_version": 1,
        "run_id": run_id,
        "selection": dict(selection),
        "status": "GAPS" if issues else "CONSISTENT_OBSERVATIONS",
        "observed_requests": len(requests),
        "declared_steps": len(steps),
        "requests_without_step": [item["request_id"] for item in requests if item["step_id"] is None],
        "requests": requests,
        "issues": issues,
        "observed_totals": _totals(requests),
        "by_category": {category: _totals([item for item in requests if item["category"] == category])
                        for category in _CATEGORIES},
        "by_purpose": {purpose: _totals([item for item in requests if item["purpose"] == purpose])
                       for purpose in ("task", "auxiliary", "unknown")},
        "usage_sources": sorted({item["usage"]["source"] for item in requests if item["usage"] is not None}),
        "failed_requests": [item["request_id"] for item in requests if item["status"] == "failed"],
        "api_call_count": "UNKNOWN",
        "trace_completeness": "unverified",
        "task_accepted": False,
        "cost_usd": "UNKNOWN",
        "note": "Supplied metadata only; classification, model identity and usage are claims. "
                "No inference of unseen calls, verified provider totals, prices or enforced limits. "
                "Inclusive input/output totals never add cache/reasoning subsets.",
    }


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LedgerError("Duplicate JSON field")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise LedgerError("Non-finite JSON number")


def main() -> int:
    parser = argparse.ArgumentParser(description="Correlate supplied HTTP request metadata offline")
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    try:
        with args.record.open("rb") as stream:
            raw = stream.read(_MAX_BYTES + 1)
        if len(raw) > _MAX_BYTES:
            raise LedgerError("Record exceeds 1 MiB")
        result = assess(json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                                   parse_constant=_invalid_constant))
    except (OSError, ValueError, RecursionError) as exc:
        parser.exit(2, f"INVALID REQUEST LEDGER: {exc}\n")
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 1 if result["status"] == "GAPS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
