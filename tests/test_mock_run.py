import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmarks.mock_api import LIMITS, SELECTION, demo, mock_server
from sca.mock_run import MockRun
from sca.request_ledger import assess


class MockRunTests(unittest.TestCase):
    def test_step_stop_counts_auxiliary_and_retry_attempts(self):
        limits = {**LIMITS, "max_steps": 3}
        with mock_server(("http_error", "ok", "ok")) as (port, received):
            run = MockRun("run", SELECTION, limits)
            for args in (("r1", "task", "s1"), ("r2", "retry", "s1", "r1"),
                         ("r3", "auxiliary")):
                run.begin(*args)
                run.dispatch(port)
            with self.assertRaisesRegex(ValueError, "SOFT_STOP"):
                run.begin("r4", "task", "s2")
            self.assertEqual(len(received), 3)
            result = assess(run.ledger)
            self.assertEqual(result["declared_steps"], 1)
            self.assertEqual(result["observed_requests"], 3)
            self.assertEqual(run.gate()["visible_steps"], 3)
            self.assertEqual(result["observed_totals"]["input_tokens"], "UNKNOWN")
            self.assertEqual(result["requests"][1]["purpose"], "task")

    def test_unknown_price_stops_after_first_observation(self):
        with mock_server() as (port, received):
            run = MockRun("run", SELECTION, {**LIMITS, "soft_cost_usd": "0.01"})
            run.begin("r1", "task", "s1")
            run.dispatch(port)
            self.assertIn("COST_UNKNOWN_UNDER_SOFT_CAP", run.gate()["reasons"])
            with self.assertRaisesRegex(ValueError, "SOFT_STOP"):
                run.begin("r2", "task", "s2")
            self.assertEqual(len(received), 1)
            self.assertEqual(run.gate()["cost_usd"], "UNKNOWN")

    def test_explicit_denial_precedes_state_and_http(self):
        with mock_server() as (port, received):
            run = MockRun("run", SELECTION, LIMITS)
            for denied in (False, None, 1, "yes"):
                with self.assertRaisesRegex(ValueError, "DENIED"):
                    run.begin("r1", "task", "s1", permitted=denied)
            with self.assertRaises(ValueError):
                run.dispatch(port)
            self.assertEqual(run.ledger["requests"], [])
            self.assertEqual(received, [])

    def test_elapsed_limit_blocks_before_begin(self):
        with patch("sca.mock_run.time.monotonic", return_value=100) as clock, mock_server() as (port, received):
            run = MockRun("run", SELECTION, {**LIMITS, "max_elapsed_ms": 100})
            clock.return_value = 101
            with self.assertRaisesRegex(ValueError, "SOFT_STOP"):
                run.begin("r1", "task", "s1")
            self.assertEqual(received, [])

    def test_elapsed_limit_between_begin_and_dispatch(self):
        with patch("sca.mock_run.time.monotonic", return_value=100) as clock, mock_server() as (port, received):
            run = MockRun("run", SELECTION, {**LIMITS, "max_elapsed_ms": 100})
            run.begin("r1", "task", "s1")
            clock.return_value = 101
            with self.assertRaisesRegex(ValueError, "TIME_STOP"):
                run.dispatch(port)
            self.assertEqual(received, [])
            self.assertEqual(run.ledger["requests"][0]["status"], "incomplete")
            with self.assertRaises(ValueError):
                run.dispatch(port)

    def test_pending_attempt_checkpoint_has_no_implicit_replay(self):
        with mock_server() as (port, received):
            run = MockRun("run", SELECTION, LIMITS)
            run.begin("r1", "task", "s1")
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "checkpoint.json"
                path.write_text(json.dumps(run.checkpoint()), encoding="utf-8")
                reopened = MockRun.reopen(json.loads(path.read_text(encoding="utf-8")),
                                          run_id="run", selection=SELECTION, limits=LIMITS)
            self.assertEqual(received, [])
            with self.assertRaises(ValueError):
                reopened.dispatch(port)
            with self.assertRaisesRegex(ValueError, "EXPLICIT_RETRY"):
                reopened.begin("r2", "task", "s1")
            reopened.begin("r2", "retry", "s1", "r1")
            self.assertEqual(reopened.dispatch(port), "MOCK_COMPLETED")
            self.assertEqual(len(received), 1)
            self.assertEqual(len(reopened.ledger["requests"]), 2)
            self.assertEqual(assess(reopened.ledger)["status"], "GAPS")

    def test_failed_or_incomplete_requires_explicit_retry(self):
        for mode in ("http_error", "disconnect", "wrong_model"):
            with self.subTest(mode=mode), mock_server((mode, "ok")) as (port, received):
                run = MockRun("run", SELECTION, LIMITS)
                run.begin("r1", "auxiliary")
                run.dispatch(port)
                reopened = MockRun.reopen(run.checkpoint(), run_id="run", selection=SELECTION, limits=LIMITS)
                with self.assertRaises(ValueError):
                    reopened.begin("r2", "auxiliary")
                reopened.begin("r2", "retry", None, "r1")
                self.assertEqual(reopened.dispatch(port), "MOCK_COMPLETED")
                self.assertEqual(len(received), 2)
                self.assertEqual(assess(reopened.ledger)["requests"][1]["purpose"], "auxiliary")

    def test_completed_run_reopens_without_network_then_explicit_new_attempt(self):
        with mock_server(("ok", "ok")) as (port, received):
            run = MockRun("run", SELECTION, LIMITS)
            run.begin("r1", "task", "s1")
            run.dispatch(port)
            reopened = MockRun.reopen(run.checkpoint(), run_id="run", selection=SELECTION, limits=LIMITS)
            self.assertEqual(len(received), 1)
            with self.assertRaises(ValueError):
                reopened.dispatch(port)
            reopened.begin("r2", "task", "s2")
            reopened.dispatch(port)
            self.assertEqual(len(received), 2)

    def test_frozen_checkpoint_identity_limits_and_shape(self):
        run = MockRun("run", SELECTION, LIMITS)
        run.begin("r1", "task", "s1")
        baseline = run.checkpoint()
        cases = []
        for field, value in (("mock_only", False), ("schema_version", True), ("elapsed_ms", -1),
                             ("elapsed_ms", True), ("body", "secret")):
            candidate = copy.deepcopy(baseline)
            candidate[field] = value
            cases.append(candidate)
        candidate = copy.deepcopy(baseline)
        candidate["ledger"]["requests"][0]["model"] = "other"
        cases.append(candidate)
        candidate = copy.deepcopy(baseline)
        candidate["limits"]["max_steps"] = 11
        cases.append(candidate)
        for checkpoint in cases:
            with self.subTest(checkpoint=checkpoint), self.assertRaises(ValueError):
                MockRun.reopen(checkpoint, run_id="run", selection=SELECTION, limits=LIMITS)
        for run_id, selection in (("other", SELECTION), ("run", {**SELECTION, "model": "other"})):
            with self.assertRaises(ValueError):
                MockRun.reopen(baseline, run_id=run_id, selection=selection, limits=LIMITS)

    def test_restored_elapsed_and_step_limits_not_reset(self):
        limits = {**LIMITS, "max_steps": 1}
        with mock_server() as (port, received):
            run = MockRun("run", SELECTION, limits)
            run.begin("r1", "task", "s1")
            run.dispatch(port)
            reopened = MockRun.reopen(run.checkpoint(), run_id="run", selection=SELECTION, limits=limits)
            with self.assertRaises(ValueError):
                reopened.begin("r2", "task", "s2")
            self.assertEqual(len(received), 1)
        checkpoint = MockRun("time", SELECTION, LIMITS).checkpoint()
        checkpoint["elapsed_ms"] = LIMITS["max_elapsed_ms"]
        reopened = MockRun.reopen(checkpoint, run_id="time", selection=SELECTION, limits=LIMITS)
        with self.assertRaises(ValueError):
            reopened.begin("r1", "task", "s1")

    def test_pending_and_duplicate_ids_never_dispatch_twice(self):
        with mock_server() as (port, received):
            run = MockRun("run", SELECTION, LIMITS)
            run.begin("r1", "task", "s1")
            with self.assertRaises(ValueError):
                run.begin("r2", "task", "s2")
            run.dispatch(port)
            with self.assertRaises(ValueError):
                run.dispatch(port)
            with self.assertRaises(ValueError):
                run.begin("r1", "task", "s1")
            with self.assertRaises(ValueError):
                run.begin("r2", "retry", "s1", "r1")
            self.assertEqual(len(received), 1)

    def test_bad_dispatch_parameters_leave_incomplete_not_replayable(self):
        run = MockRun("run", SELECTION, LIMITS)
        run.begin("r1", "task", "s1")
        with self.assertRaises(ValueError):
            run.dispatch(0)
        with self.assertRaises(ValueError):
            run.dispatch(1)
        self.assertEqual(run.ledger["requests"][0]["status"], "incomplete")

    def test_input_and_export_are_detached(self):
        selection, limits = copy.deepcopy(SELECTION), copy.deepcopy(LIMITS)
        run = MockRun("run", selection, limits)
        selection["model"] = "different"
        limits["max_steps"] = 1
        run.begin("r1", "task", "s1")
        exported = run.checkpoint()
        exported["ledger"]["selection"]["model"] = "different"
        exported["limits"]["max_steps"] = 1
        self.assertEqual(run.ledger["selection"], SELECTION)
        self.assertEqual(run.checkpoint()["limits"], LIMITS)

    def test_unknown_classification_not_inferred_from_steps(self):
        with mock_server() as (port, received):
            run = MockRun("run", SELECTION, LIMITS)
            run.begin("r1", "unknown")
            run.dispatch(port)
            result = assess(run.ledger)
            self.assertEqual(result["status"], "GAPS")
            self.assertEqual(result["requests"][0]["purpose"], "unknown")
            self.assertEqual(result["trace_completeness"], "unverified")

    def test_reopen_refuses_fabricated_provenance_and_bypassed_failure(self):
        with mock_server(("ok", "ok")) as (port, received):
            run = MockRun("run", SELECTION, LIMITS)
            run.begin("r1", "task", "s1")
            run.dispatch(port)
            run.begin("r2", "task", "s2")
            run.dispatch(port)
        checkpoint = run.checkpoint()
        fake = copy.deepcopy(checkpoint)
        fake["ledger"]["requests"][0]["usage"]["source"] = "provider_reported"
        with self.assertRaisesRegex(ValueError, "estimated"):
            MockRun.reopen(fake, run_id="run", selection=SELECTION, limits=LIMITS)
        fake = copy.deepcopy(checkpoint)
        fake["ledger"]["requests"][0].update(status="failed", http_status=503, usage=None)
        with self.assertRaisesRegex(ValueError, "Unresolved"):
            MockRun.reopen(fake, run_id="run", selection=SELECTION, limits=LIMITS)

    def test_zero_soft_cap_is_still_post_step_not_a_first_call_guarantee(self):
        with mock_server() as (port, received):
            run = MockRun("run", SELECTION, {**LIMITS, "soft_cost_usd": "0"})
            run.begin("r1", "task", "s1")
            run.dispatch(port)
            with self.assertRaisesRegex(ValueError, "SOFT_STOP"):
                run.begin("r2", "task", "s2")
            self.assertEqual(len(received), 1)
            self.assertIn("post-step", run.gate()["stop_kind"])

    def test_demo_proves_server_counts(self):
        result = demo()
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(result["provider_api_calls"], 0)
        self.assertEqual(result["R1"], "OPEN")


if __name__ == "__main__":
    unittest.main()
