"""Audit the completeness of externally supplied results; never run checks.

The audit cannot establish that supplied logs, hashes, tests or usage are real.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

from .task import Task, TaskError, parse_task


class EvidenceError(ValueError):
    """The record cannot be matched to this task contract."""


_ROOT = {"schema_version", "task_id", "checks", "acceptance", "diff", "usage"}
_CHECK = {"name", "status", "exit_code", "log_sha256"}
_CRITERION = {"criterion", "status", "evidence_ids"}
_DIFF = {"kind", "sha256"}
_USAGE = {"cost_usd", "provenance", "trace_completeness"}
_STATES = {"passed", "failed", "not_run", "blocked"}
_COST_SOURCES = {"provider_reported", "engine_reported", "estimate"}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_USD = re.compile(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,9})?\Z")


def _object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise EvidenceError(f"{label} needs exactly {', '.join(sorted(fields))}")
    return value


def _digest(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError(f"Duplicate field: {key}")
        result[key] = value
    return result


def _ordered_rows(rows: Any, expected: tuple[str, ...], key: str, fields: set[str],
                  label: str) -> list[dict[str, Any]]:
    if len(expected) != len(set(expected)):
        raise EvidenceError(f"Duplicate {label} entries in task contract")
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise EvidenceError(f"{label} must contain every task entry exactly once")
    values = [_object(row, fields, label) for row in rows]
    if [row[key] for row in values] != list(expected):
        raise EvidenceError(f"{label} names/order differ from task; omissions and duplicates block")
    return values


def audit(task: Task, record: dict[str, Any]) -> dict[str, Any]:
    """Classify reported evidence completeness without asserting task acceptance."""
    record = _object(record, _ROOT, "record")
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise EvidenceError("Only schema_version 1 is supported")
    if record["task_id"] != task.identifier:
        raise EvidenceError("task_id differs from task contract")
    checks = _ordered_rows(record["checks"], task.checks, "name", _CHECK, "checks")
    acceptance = _ordered_rows(record["acceptance"], task.acceptance,
                               "criterion", _CRITERION, "acceptance")
    for row in checks:
        status, code, digest = row["status"], row["exit_code"], row["log_sha256"]
        if not isinstance(status, str) or status not in _STATES:
            raise EvidenceError("Invalid check status")
        if status in ("passed", "failed"):
            if type(code) is not int or (code == 0) != (status == "passed") or not _digest(digest):
                raise EvidenceError("Reported run needs matching exit code and log SHA-256")
        elif code is not None or digest is not None:
            raise EvidenceError("Unrun or blocked check cannot have exit code or log digest")
    for row in acceptance:
        if not isinstance(row["status"], str) or row["status"] not in _STATES:
            raise EvidenceError("Invalid acceptance status")
        ids = row["evidence_ids"]
        if not isinstance(ids, list) or (row["status"] == "passed" and not ids) \
                or any(not isinstance(item, str) or not item.strip() or item != item.strip()
                       for item in ids) or len(ids) != len(set(ids)):
            raise EvidenceError("Acceptance evidence_ids must be unique nonempty identifiers")
    diff = _object(record["diff"], _DIFF, "diff")
    if diff["kind"] not in ("preview_only", "working_tree", "not_available") \
            or (diff["kind"] == "not_available" and diff["sha256"] is not None) \
            or (diff["kind"] != "not_available" and not _digest(diff["sha256"])):
        raise EvidenceError("Diff kind and digest disagree")
    usage = _object(record["usage"], _USAGE, "usage")
    cost, provenance = usage["cost_usd"], usage["provenance"]
    if usage["trace_completeness"] != "unverified" \
            or (cost == "UNKNOWN" and provenance != "unknown") \
            or (cost != "UNKNOWN" and (not isinstance(cost, str) or not _USD.fullmatch(cost)
                                           or not isinstance(provenance, str)
                                           or provenance not in _COST_SOURCES)):
        raise EvidenceError("Usage must keep unknown cost or labelled reported/estimated USD")

    statuses = [row["status"] for row in checks + acceptance]
    if "blocked" in statuses:
        outcome = "BLOCKED_REPORTED"
    elif "failed" in statuses:
        outcome = "REWORK_REQUIRED_REPORTED"
    elif "not_run" in statuses or diff["kind"] != "working_tree":
        outcome = "INCOMPLETE_REPORTED"
    else:
        outcome = "STRUCTURALLY_COMPLETE_UNVERIFIED"
    return {
        "outcome": outcome,
        "task_id": task.identifier,
        "check_counts": {status: sum(row["status"] == status for row in checks)
                         for status in sorted(_STATES)},
        "acceptance_counts": {status: sum(row["status"] == status for row in acceptance)
                              for status in sorted(_STATES)},
        "diff_kind": diff["kind"],
        "cost_usd": cost,
        "cost_provenance": provenance,
        "trace_completeness": "unverified",
        "task_accepted": False,
        "evidence_trust": "externally supplied metadata; log/diff bytes and execution not verified",
        "note": "No checks executed, no repo policy evaluated, no model calls observed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit reported results against a task contract")
    parser.add_argument("task", type=Path)
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    try:
        if args.record.stat().st_size > 65_536:
            raise EvidenceError("Record exceeds 64 KiB")
        task = parse_task(args.task)
        record = json.loads(args.record.read_text(encoding="utf-8"),
                            object_pairs_hook=_unique_pairs)
        result = audit(task, record)
    except (OSError, UnicodeError, json.JSONDecodeError, TaskError, EvidenceError) as exc:
        print(f"INVALID EVIDENCE RECORD: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
