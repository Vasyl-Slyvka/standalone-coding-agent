"""Offline policy checks for the next controlled step; no engine involved."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from sca.usage_gate import GateError, decide


def example() -> dict:
    return {
        "schema_version": 1,
        "selection": {"provider": "manual-provider", "model": "manual-model",
                      "endpoint_alias": "local"},
        "limits": {"max_steps": 3, "max_elapsed_ms": 60_000, "soft_cost_usd": "0.30"},
        "elapsed_ms": 100,
        "steps": [{"step_id": "s1", "provider": "manual-provider", "model": "manual-model",
                   "endpoint_alias": "local", "input_tokens": 10, "output_tokens": 5,
                   "cost_usd": "0.10", "cost_provenance": "estimate",
                   "price_source": "example-price-table"}],
    }


class UsageGateTests(unittest.TestCase):
    def test_cost_threshold_stops_only_before_next_step(self) -> None:
        record = example()
        self.assertEqual(decide(record)["decision"], "ALLOW_NEXT_CONTROLLED_STEP")
        record["steps"].append({**record["steps"][0], "step_id": "s2", "cost_usd": "0.20"})
        result = decide(record)
        self.assertEqual(result["decision"], "SOFT_STOP")
        self.assertEqual(result["reasons"], ["SOFT_COST_REACHED"])
        self.assertEqual(result["cost_usd"], "0.30")
        self.assertIn("post-step", result["stop_kind"])

    def test_unknown_cost_is_not_zero_or_a_safe_soft_budget(self) -> None:
        record = example()
        record["steps"][0].update(cost_usd=None, cost_provenance="unknown", price_source=None)
        record["steps"][0]["input_tokens"] = None
        result = decide(record)
        self.assertEqual(result["cost_usd"], "UNKNOWN")
        self.assertEqual(result["input_tokens"], "UNKNOWN")
        self.assertIn("COST_UNKNOWN_UNDER_SOFT_CAP", result["reasons"])
        record["limits"]["soft_cost_usd"] = None
        self.assertEqual(decide(record)["decision"], "ALLOW_NEXT_CONTROLLED_STEP")
        self.assertEqual(decide(record)["cost_usd"], "UNKNOWN")

    def test_step_and_time_limits_do_not_depend_on_price(self) -> None:
        record = example()
        record["limits"]["max_steps"] = 1
        record["elapsed_ms"] = 60_000
        self.assertEqual(decide(record)["reasons"],
                         ["MAX_STEPS_REACHED", "MAX_ELAPSED_REACHED"])

    def test_first_step_is_not_a_pre_call_cost_guarantee(self) -> None:
        record = example()
        record["steps"] = []
        record["limits"]["soft_cost_usd"] = "0"
        result = decide(record)
        self.assertEqual(result["decision"], "ALLOW_NEXT_CONTROLLED_STEP")
        self.assertEqual(result["cost_usd"], "UNKNOWN")
        self.assertEqual(result["trace_completeness"], "unverified")

    def test_duplicate_identity_price_and_token_errors_are_blocked(self) -> None:
        base = example()
        variants = [
            {**base, "steps": [base["steps"][0], base["steps"][0]]},
            {**base, "steps": [{**base["steps"][0], "model": "unexpected"}]},
            {**base, "steps": [{**base["steps"][0], "cost_usd": None}]},
            {**base, "steps": [{**base["steps"][0], "cost_usd": 0.0}]},
            {**base, "steps": [{**base["steps"][0], "cost_usd": "NaN"}]},
            {**base, "steps": [{**base["steps"][0], "cost_usd": "1e99999999"}]},
            {**base, "steps": [{**base["steps"][0], "step_id": "s1 "}]},
            {**base, "steps": [{**base["steps"][0], "input_tokens": True}]},
            {**base, "steps": [{**base["steps"][0], "price_source": ""}]},
            {**base, "steps": [{**base["steps"][0], "cost_provenance": []}]},
            {**base, "limits": {**base["limits"], "max_steps": True}},
        ]
        for record in variants:
            with self.subTest(record=record):
                with self.assertRaises(GateError):
                    decide(record)

    def test_cli_reports_offline_decision_and_rejects_duplicate_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usage.json"
            command = [sys.executable, "-m", "sca.usage_gate", str(path)]
            path.write_text(json.dumps(example()), encoding="utf-8")
            good = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(good.returncode, 0)
            self.assertEqual(json.loads(good.stdout)["decision"], "ALLOW_NEXT_CONTROLLED_STEP")
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            bad = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(bad.returncode, 2)
            self.assertFalse(bad.stdout)
            self.assertIn("Duplicate field", bad.stderr)
