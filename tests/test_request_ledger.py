"""Request IDs, incomplete telemetry and retries, using invented metadata only."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from sca.request_ledger import LedgerError, assess


def example() -> dict:
    path = Path(__file__).resolve().parents[1] / "examples/request-ledger.json"
    return json.loads(path.read_text(encoding="utf-8"))


def retry(record: dict, parent_index: int = 1, request_id: str = "retry-1") -> dict:
    parent = record["requests"][parent_index]
    item = {**deepcopy(parent), "request_id": request_id, "category": "retry",
            "retry_of": parent["request_id"]}
    record["requests"].append(item)
    for step in record["steps"]:
        if step["step_id"] == parent["step_id"]:
            step["request_ids"].append(item["request_id"])
    return item


class RequestLedgerTests(unittest.TestCase):
    def test_three_requests_are_not_collapsed_to_two_steps(self) -> None:
        record = example()
        original = deepcopy(record)
        result = assess(record)
        self.assertEqual(result["status"], "CONSISTENT_OBSERVATIONS")
        self.assertEqual(result["observed_requests"], 3)
        self.assertEqual(result["declared_steps"], 2)
        self.assertEqual(result["requests_without_step"], ["request-1"])
        self.assertEqual(result["observed_totals"]["input_tokens"], 21)
        self.assertEqual(result["observed_totals"]["output_tokens"], 10)
        self.assertEqual(result["by_category"]["auxiliary"]["input_tokens"], 7)
        self.assertEqual(result["usage_sources"], ["estimate"])
        self.assertEqual(result["api_call_count"], "UNKNOWN")
        self.assertEqual(result["trace_completeness"], "unverified")
        self.assertEqual(result["cost_usd"], "UNKNOWN")
        self.assertFalse(result["task_accepted"])
        result["requests"][0]["usage"]["input_tokens"] = 999
        self.assertEqual(record, original)

    def test_missing_auxiliary_usage_keeps_unknown_total_and_known_subtotal(self) -> None:
        record = example()
        record["requests"][0]["usage"] = None
        result = assess(record)
        self.assertEqual(result["status"], "GAPS")
        self.assertEqual(result["observed_totals"]["input_tokens"], "UNKNOWN")
        self.assertEqual(result["observed_totals"]["known_input_tokens_subtotal"], 14)
        self.assertEqual(result["observed_totals"]["unknown_input_tokens_requests"], 1)
        self.assertIn({"request_id": "request-1", "code": "USAGE_MISSING"}, result["issues"])

    def test_partial_usage_and_zero_are_distinct(self) -> None:
        record = example()
        usage = record["requests"][0]["usage"]
        usage.update(input_tokens=None, output_tokens=0)
        result = assess(record)
        self.assertEqual(result["observed_totals"]["input_tokens"], "UNKNOWN")
        self.assertEqual(result["observed_totals"]["output_tokens"], 7)
        self.assertEqual(result["requests"][0]["usage"]["output_tokens"], 0)

    def test_empty_record_has_unknown_totals_and_an_explicit_gap(self) -> None:
        record = example()
        record.update(steps=[], requests=[])
        result = assess(record)
        self.assertEqual(result["status"], "GAPS")
        self.assertEqual(result["observed_totals"]["input_tokens"], "UNKNOWN")
        self.assertEqual(result["issues"], [{"code": "NO_REQUESTS_OBSERVED"}])

    def test_unknown_purpose_is_never_inferred_from_an_unlinked_request(self) -> None:
        record = example()
        record["requests"][0].update(category="unknown", category_source="unknown")
        result = assess(record)
        self.assertEqual(result["requests"][0]["purpose"], "unknown")
        self.assertIn({"request_id": "request-1", "code": "CLASSIFICATION_UNKNOWN"}, result["issues"])
        self.assertEqual(result["by_category"]["auxiliary"]["requests"], 0)

    def test_task_without_step_and_empty_step_remain_gaps(self) -> None:
        record = example()
        record["requests"][0].update(category="task")
        record["steps"].append({"step_id": "empty-step", "request_ids": []})
        codes = {item["code"] for item in assess(record)["issues"]}
        self.assertIn("TASK_REQUEST_WITHOUT_STEP", codes)
        self.assertIn("STEP_WITHOUT_REQUEST", codes)

    def test_duplicate_step_request_and_link_are_rejected(self) -> None:
        for kind in ("request", "step", "link", "shared-link"):
            record = example()
            if kind == "request":
                record["requests"].append(deepcopy(record["requests"][0]))
            elif kind == "step":
                record["steps"].append(deepcopy(record["steps"][0]))
            elif kind == "link":
                record["steps"][0]["request_ids"].append("request-2")
            else:
                record["steps"][1]["request_ids"].append("request-2")
            with self.subTest(kind=kind), self.assertRaises(LedgerError):
                assess(record)

    def test_bidirectional_links_reject_missing_and_contradictory_ids(self) -> None:
        for kind in ("unobserved", "unlisted", "wrong-step", "no-step", "unknown-step"):
            record = example()
            if kind == "unobserved":
                record["steps"][0]["request_ids"].append("absent-request")
            elif kind == "unlisted":
                record["steps"][0]["request_ids"] = []
            elif kind == "wrong-step":
                record["requests"][1]["step_id"] = "step-2"
            elif kind == "no-step":
                record["requests"][1]["step_id"] = None
            else:
                record["requests"][1]["step_id"] = "absent-step"
            with self.subTest(kind=kind), self.assertRaises(LedgerError):
                assess(record)

    def test_cross_run_and_selection_drift_are_rejected(self) -> None:
        for field in ("run_id", "provider", "model", "endpoint_alias"):
            record = example()
            record["requests"][0][field] = "different"
            with self.subTest(field=field), self.assertRaises(LedgerError):
                assess(record)

    def test_retry_counts_separately_even_after_failed_http_attempt(self) -> None:
        record = example()
        record["requests"][1].update(status="failed", http_status=503)
        retry(record).update(status="completed", http_status=200)
        result = assess(record)
        self.assertEqual(result["observed_requests"], 4)
        self.assertEqual(result["observed_totals"]["input_tokens"], 31)
        self.assertEqual(result["failed_requests"], ["request-2"])
        self.assertEqual(result["by_category"]["retry"]["requests"], 1)
        self.assertEqual(result["by_purpose"]["task"]["requests"], 3)
        retry(record, len(record["requests"]) - 1, "retry-2")
        chained = assess(record)
        self.assertEqual(chained["observed_requests"], 5)
        self.assertEqual(chained["by_purpose"]["task"]["input_tokens"], 34)
        self.assertEqual(chained["requests"][-1]["purpose"], "task")

    def test_auxiliary_retry_outside_a_step_is_retained(self) -> None:
        record = example()
        retry(record, 0)
        result = assess(record)
        self.assertEqual(result["status"], "CONSISTENT_OBSERVATIONS")
        self.assertEqual(result["requests_without_step"], ["request-1", "retry-1"])
        self.assertEqual(result["by_purpose"]["auxiliary"]["input_tokens"], 14)

    def test_retry_of_unclassified_request_stays_unclassified(self) -> None:
        record = example()
        record["requests"][0].update(category="unknown", category_source="unknown")
        retry(record, 0).update(category_source="operator_annotation")
        result = assess(record)
        self.assertEqual(result["requests"][-1]["purpose"], "unknown")
        self.assertIn({"request_id": "retry-1", "code": "CLASSIFICATION_UNKNOWN"}, result["issues"])

    def test_invalid_retry_parent_order_step_cycle_and_spurious_parent(self) -> None:
        for kind in ("absent", "forward", "self", "wrong-step", "not-retry"):
            record = example()
            item = retry(record)
            if kind == "absent":
                item["retry_of"] = "absent"
            elif kind == "forward":
                record["requests"].insert(0, record["requests"].pop())
            elif kind == "self":
                item["retry_of"] = "retry-1"
            elif kind == "wrong-step":
                item["retry_of"] = "request-3"
            else:
                item["category"] = "task"
            with self.subTest(kind=kind), self.assertRaises(LedgerError):
                assess(record)

    def test_cache_and_reasoning_subsets_are_not_added(self) -> None:
        record = example()
        record["requests"][1]["usage"].update(cache_read_tokens=8, cache_write_tokens=8,
                                             reasoning_tokens=4, source="provider_reported")
        result = assess(record)
        self.assertEqual(result["observed_totals"]["input_tokens"], 21)
        self.assertEqual(result["observed_totals"]["output_tokens"], 10)
        record["requests"][1]["usage"]["reasoning_tokens"] = 6
        with self.assertRaises(LedgerError):
            assess(record)

    def test_unspecified_token_semantics_preserve_counters_but_not_totals(self) -> None:
        record = example()
        record["requests"][1]["usage"].update(token_semantics="unspecified", cache_read_tokens=99)
        result = assess(record)
        self.assertEqual(result["status"], "GAPS")
        self.assertEqual(result["observed_totals"]["input_tokens"], "UNKNOWN")
        self.assertEqual(result["requests"][1]["usage"]["cache_read_tokens"], 99)

    def test_incomplete_or_failed_transport_is_not_dropped(self) -> None:
        record = example()
        record["requests"][0].update(status="incomplete", http_status=None, usage=None)
        result = assess(record)
        self.assertEqual(result["observed_requests"], 3)
        self.assertIn({"request_id": "request-1", "code": "REQUEST_INCOMPLETE"}, result["issues"])
        record["requests"][0]["status"] = "failed"
        self.assertEqual(assess(record)["failed_requests"], ["request-1"])

    def test_bad_fields_counters_status_classification_and_selection_are_rejected(self) -> None:
        mutations = [
            lambda r: r.update(schema_version=True),
            lambda r: r["selection"].update(model="auto"),
            lambda r: r["selection"].update(endpoint_alias="https://private.example"),
            lambda r: r.update(run_id="line\nbreak"),
            lambda r: r["requests"][0].update(category_source="unknown"),
            lambda r: r["requests"][0].update(status="completed", http_status=500),
            lambda r: r["requests"][0].update(http_status=True),
            lambda r: r["requests"][0].update(category=[]),
            lambda r: r["requests"][0]["usage"].update(input_tokens=True),
            lambda r: r["requests"][0]["usage"].update(output_tokens=-1),
            lambda r: r["requests"][0]["usage"].update(output_tokens=2**63),
            lambda r: r["requests"][0]["usage"].update(source="unknown"),
            lambda r: r["requests"][0]["usage"].update(token_semantics=[]),
            lambda r: r["requests"][0].update(prompt="DO_NOT_ECHO"),
            lambda r: r["requests"][0]["usage"].update(response_body="DO_NOT_ECHO"),
            lambda r: r.update(requests=[r["requests"][0]] * 1001),
        ]
        for index, mutation in enumerate(mutations):
            record = example()
            mutation(record)
            with self.subTest(index=index), self.assertRaises(LedgerError) as error:
                assess(record)
            self.assertNotIn("DO_NOT_ECHO", str(error.exception))

    def test_cli_exit_codes_and_invalid_json_limits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            command = [sys.executable, "-m", "sca.request_ledger", str(path)]
            record = example()
            path.write_text(json.dumps(record), encoding="utf-8")
            valid = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(valid.returncode, 0, valid.stderr)
            self.assertEqual(json.loads(valid.stdout)["observed_requests"], 3)
            record["requests"][0]["usage"] = None
            path.write_text(json.dumps(record), encoding="utf-8")
            gaps = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(gaps.returncode, 1)
            self.assertEqual(json.loads(gaps.stdout)["status"], "GAPS")
            bad_inputs = ['{"schema_version":1,"schema_version":1}', '{"value":NaN}',
                          '{"value":Infinity}', '{"value":1e309}', '[' * 2000,
                          ' ' * 1_048_577, '{"prompt":"DO_NOT_ECHO"}']
            for raw in bad_inputs:
                path.write_text(raw, encoding="utf-8")
                invalid = subprocess.run(command, capture_output=True, text=True, check=False)
                with self.subTest(length=len(raw)):
                    self.assertEqual(invalid.returncode, 2)
                    self.assertFalse(invalid.stdout)
                    self.assertIn("INVALID REQUEST LEDGER", invalid.stderr)
                    self.assertNotIn("DO_NOT_ECHO", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
