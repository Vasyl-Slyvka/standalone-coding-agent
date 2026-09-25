"""Audit reports are self-reported metadata, never a real test-run attestation."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from sca.evidence_audit import EvidenceError, audit
from sca.task import parse_task


TASK = """# Synthetic evidence
Task ID: EXP-005
Branch: main

## Scope
- src/app.py

## Must do
- Change a greeting.

## Must not
- Modify other files.

## Acceptance
- Greeting is correct.
- Tests are green.

## Checks
- python -m unittest
- git diff --check

## Stop rule
- Stop on missing evidence.
"""


def example() -> dict:
    digest = "a" * 64
    return {
        "schema_version": 1,
        "task_id": "EXP-005",
        "checks": [
            {"name": "python -m unittest", "status": "passed", "exit_code": 0,
             "log_sha256": digest},
            {"name": "git diff --check", "status": "passed", "exit_code": 0,
             "log_sha256": digest},
        ],
        "acceptance": [
            {"criterion": "Greeting is correct.", "status": "passed",
             "evidence_ids": ["review-1"]},
            {"criterion": "Tests are green.", "status": "passed",
             "evidence_ids": ["log-1"]},
        ],
        "diff": {"kind": "working_tree", "sha256": digest},
        "usage": {"cost_usd": "UNKNOWN", "provenance": "unknown",
                  "trace_completeness": "unverified"},
    }


class EvidenceAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.task_path = self.root / "task.md"
        self.task_path.write_text(TASK, encoding="utf-8")
        self.task = parse_task(self.task_path)

    def test_all_reported_passes_never_accept_task(self) -> None:
        report = audit(self.task, example())
        self.assertEqual(report["outcome"], "STRUCTURALLY_COMPLETE_UNVERIFIED")
        self.assertFalse(report["task_accepted"])
        self.assertEqual(report["cost_usd"], "UNKNOWN")
        self.assertEqual(report["trace_completeness"], "unverified")
        self.assertEqual(report["check_counts"]["passed"], 2)

    def test_failure_missing_and_blocked_are_distinct(self) -> None:
        failed = example()
        failed["checks"][0].update(status="failed", exit_code=1)
        self.assertEqual(audit(self.task, failed)["outcome"], "REWORK_REQUIRED_REPORTED")
        missing = example()
        missing["checks"][0].update(status="not_run", exit_code=None, log_sha256=None)
        self.assertEqual(audit(self.task, missing)["outcome"], "INCOMPLETE_REPORTED")
        preview_only = example()
        preview_only["diff"]["kind"] = "preview_only"
        self.assertEqual(audit(self.task, preview_only)["outcome"], "INCOMPLETE_REPORTED")
        blocked = example()
        blocked["acceptance"][1].update(status="blocked", evidence_ids=[])
        self.assertEqual(audit(self.task, blocked)["outcome"], "BLOCKED_REPORTED")

    def test_missing_duplicate_or_extra_task_entries_fail(self) -> None:
        base = example()
        for checks in (base["checks"][:1], base["checks"] + [base["checks"][0]],
                       [base["checks"][0], base["checks"][0]],
                       [base["checks"][1], base["checks"][0]]):
            with self.subTest(checks=checks), self.assertRaises(EvidenceError):
                audit(self.task, {**base, "checks": checks})
        base["acceptance"] = base["acceptance"][:1]
        with self.assertRaises(EvidenceError):
            audit(self.task, base)
        self.task_path.write_text(TASK.replace("- git diff --check", "- python -m unittest"))
        with self.assertRaisesRegex(EvidenceError, "Duplicate checks"):
            audit(parse_task(self.task_path), example())

    def test_invalid_codes_claims_and_cost_provenance_fail(self) -> None:
        base = example()
        variants = [
            {**base, "checks": [{**base["checks"][0], "exit_code": True}, base["checks"][1]]},
            {**base, "checks": [{**base["checks"][0], "exit_code": 3}, base["checks"][1]]},
            {**base, "checks": [{**base["checks"][0], "log_sha256": None}, base["checks"][1]]},
            {**base, "checks": [{**base["checks"][0], "status": []}, base["checks"][1]]},
            {**base, "acceptance": [{**base["acceptance"][0], "evidence_ids": []},
                                    base["acceptance"][1]]},
            {**base, "diff": {"kind": "working_tree", "sha256": None}},
            {**base, "usage": {**base["usage"], "provenance": "estimate"}},
            {**base, "usage": {**base["usage"], "cost_usd": "0.10"}},
            {**base, "usage": {**base["usage"], "trace_completeness": "verified"}},
            {**base, "schema_version": True},
            {**base, "task_id": "OTHER"},
        ]
        for record in variants:
            with self.subTest(record=record), self.assertRaises(EvidenceError):
                audit(self.task, record)

    def test_cli_never_runs_checks_and_rejects_duplicate_json(self) -> None:
        marker = self.root / "created-by-check"
        self.task_path.write_text(TASK.replace("python -m unittest", f"touch {marker}"))
        record = example()
        record["checks"][0]["name"] = f"touch {marker}"
        path = self.root / "record.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        command = [sys.executable, "-m", "sca.evidence_audit", str(self.task_path), str(path)]
        good = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(good.returncode, 0)
        self.assertFalse(marker.exists())
        self.assertFalse(json.loads(good.stdout)["task_accepted"])
        path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        bad = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(bad.returncode, 2)
        self.assertIn("Duplicate field", bad.stderr)


if __name__ == "__main__":
    unittest.main()
