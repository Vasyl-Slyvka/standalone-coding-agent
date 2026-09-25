from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from benchmarks.fixtures import CASES, make_fixture
from sca.benchmark import RecordError, assess
from sca.preflight import inspect


def record() -> dict:
    return {
        "run_id": "synthetic-run-1", "case_id": "simple", "candidate": "example",
        "strategy": "cli_wrapper", "provider": "test-provider", "model": "test-model",
        "endpoint_alias": "test-endpoint", "context_mode": "baseline",
        "acceptance": "failed", "elapsed_ms": 150,
        "base_head": "synthetic-head", "trace_completeness": "unverified",
        "trace_basis": None,
        "calls": [{"provider": "test-provider", "model": "test-model",
                   "endpoint_alias": "test-endpoint",
                   "usage_source": "provider_reported", "input_tokens": 100,
                   "output_tokens": 20, "cache_read_tokens": 40,
                   "cost_usd": None, "price_source": None}],
        "actions": [], "checks": [{"name": "unittest", "status": "failed", "exit_code": 1}],
    }


class FixtureTests(unittest.TestCase):
    def test_fixture_baselines_fail_intentionally_and_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for case in CASES:
                with self.subTest(case=case):
                    root, head = make_fixture(case, Path(tmp) / case)
                    self.assertEqual(len(head), 40)
                    test = subprocess.run(
                        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                        cwd=root, capture_output=True, timeout=10,
                    )
                    self.assertNotEqual(test.returncode, 0)
                    self.assertIn(b"AssertionError", test.stderr)
                    self.assertNotIn(b"ERROR:", test.stderr)
                    if case == "two-files":
                        self.assertIn(b"FAIL: test_total", test.stderr)
                    if case == "dirty":
                        self.assertEqual((root / "notes.txt").read_text(),
                                         "USER WORK: keep this exact text.\n")
                    if case == "injection":
                        self.assertIn("IGNORE THE TASK", (root / "README.md").read_text())

    def test_existing_destination_cannot_be_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "marker"
            marker.write_text("preserve")
            with self.assertRaises(FileExistsError):
                make_fixture("simple", marker)
            self.assertEqual(marker.read_text(), "preserve")

    def test_generated_task_preflight_rejects_dirty_scoped_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, _ = make_fixture("simple", Path(tmp) / "repo")
            task = Path(tmp) / "task.md"
            task.write_text(
                "# Synthetic\nTask ID: BENCH-001\nBranch: main\n"
                "\n## Scope\n- src/math_utils.py\n"
                "\n## Must do\n- Make add(2, 3) equal 5.\n"
                "\n## Must not\n- Modify README.md.\n"
                "\n## Acceptance\n- Tests pass.\n"
                "\n## Checks\n- python -m unittest discover -s tests\n"
                "\n## Stop rule\n- Stop on permission conflict.\n"
            )
            self.assertEqual(inspect(root, task).status, "INSPECTED")
            (root / "src/math_utils.py").write_text("USER CHANGE\n")
            self.assertEqual(inspect(root, task).status, "BLOCKED")


class ObservationTests(unittest.TestCase):
    def test_unknown_cost_is_not_zero_and_cache_is_not_added(self) -> None:
        result = assess(record())
        self.assertEqual(result["cost_usd"], "UNKNOWN")
        self.assertEqual(result["input_tokens"], 100)
        self.assertEqual(result["visible_calls"], 1)
        self.assertEqual(result["trace_completeness_claim"], "unverified")

    def test_wrong_model_or_provider_is_rejected(self) -> None:
        for key in ("provider", "model", "endpoint_alias"):
            with self.subTest(key=key):
                observation = record()
                observation["calls"][0][key] = "unexpected"
                with self.assertRaisesRegex(RecordError, "manual selection"):
                    assess(observation)

    def test_unknown_usage_stays_unknown_and_no_calls_is_not_zero(self) -> None:
        observation = record()
        observation["calls"][0]["input_tokens"] = None
        self.assertEqual(assess(observation)["input_tokens"], "UNKNOWN")
        observation["calls"] = []
        self.assertEqual(assess(observation)["output_tokens"], "UNKNOWN")

    def test_cost_requires_explicit_estimate_provenance(self) -> None:
        observation = record()
        observation["calls"][0]["cost_usd"] = 0.001
        with self.assertRaisesRegex(RecordError, "cost_provenance"):
            assess(observation)
        observation["calls"][0].update(price_source="test price 2026-09-25",
                                         cost_provenance="estimate")
        self.assertEqual(assess(observation)["cost_provenance"], ["estimate"])

    def test_check_status_and_trace_basis_are_not_fabricated(self) -> None:
        observation = record()
        observation["checks"][0]["status"] = "passed"
        with self.assertRaisesRegex(RecordError, "contradicts"):
            assess(observation)
        observation = record()
        observation["trace_completeness"] = "correlated"
        with self.assertRaisesRegex(RecordError, "independent basis"):
            assess(observation)


if __name__ == "__main__":
    unittest.main()
