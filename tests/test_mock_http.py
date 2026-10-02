import copy
import json
import unittest

from benchmarks.mock_api import LIMITS, SELECTION, mock_server
from sca.mock_http import exchange
from sca.mock_run import MockRun
from sca.request_ledger import assess, LedgerError


class MockHTTPTests(unittest.TestCase):
    def pending(self):
        run = MockRun("run", SELECTION, LIMITS)
        run.begin("r1", "task", "s1")
        return run.ledger

    def test_actual_http_ids_and_inclusive_usage(self):
        ledger = self.pending()
        original = copy.deepcopy(ledger)
        with mock_server() as (port, received):
            request, diagnostic = exchange(ledger, port)
        self.assertEqual(diagnostic, "MOCK_COMPLETED")
        self.assertEqual(received, [{"run_id": "run", "request_id": "r1", "model": "mock-model"}])
        self.assertEqual(ledger, original)
        ledger["requests"][-1] = request
        result = assess(ledger)
        self.assertEqual(result["observed_totals"]["input_tokens"], 10)
        self.assertEqual(result["observed_totals"]["output_tokens"], 2)
        self.assertEqual(result["usage_sources"], ["estimate"])
        self.assertEqual(result["api_call_count"], "UNKNOWN")

    def test_protocol_failures_retain_unknown_usage(self):
        for mode in ("wrong_model", "wrong_run", "wrong_id", "extra", "provider_usage",
                     "negative_usage", "duplicate", "nonfinite", "malformed", "deep"):
            with self.subTest(mode=mode), mock_server((mode,)) as (port, received):
                request, diagnostic = exchange(self.pending(), port)
                self.assertEqual(diagnostic, "PROTOCOL_INVALID")
                self.assertEqual(request["status"], "incomplete")
                self.assertIsNone(request["usage"])
                self.assertEqual(len(received), 1)
                self.assertNotIn("untrusted response", json.dumps(request))

    def test_transport_failures_never_retry(self):
        for mode in ("disconnect", "truncated", "timeout"):
            with self.subTest(mode=mode), mock_server((mode,)) as (port, received):
                request, diagnostic = exchange(self.pending(), port, timeout=0.03)
                self.assertEqual(diagnostic, "TRANSPORT_INCOMPLETE")
                self.assertEqual(request["status"], "incomplete")
                self.assertIsNone(request["usage"])
                self.assertEqual(len(received), 1)

    def test_oversized_response(self):
        with mock_server(("oversized",)) as (port, received):
            request, diagnostic = exchange(self.pending(), port)
        self.assertEqual(diagnostic, "RESPONSE_TOO_LARGE")
        self.assertIsNone(request["usage"])
        self.assertEqual(len(received), 1)

    def test_http_errors_and_redirects_not_followed(self):
        for mode, status in (("http_error", 503), ("redirect", 307)):
            with self.subTest(mode=mode), mock_server((mode,)) as (port, received):
                request, diagnostic = exchange(self.pending(), port)
                self.assertEqual(diagnostic, "HTTP_FAILED")
                self.assertEqual(request["http_status"], status)
                self.assertEqual(request["status"], "failed")
                self.assertIsNone(request["usage"])
                self.assertEqual(len(received), 1)

    def test_missing_usage_is_completed_with_gap(self):
        ledger = self.pending()
        with mock_server(("missing_usage",)) as (port, received):
            ledger["requests"][-1], diagnostic = exchange(ledger, port)
        self.assertEqual(diagnostic, "MOCK_COMPLETED")
        self.assertEqual(assess(ledger)["status"], "GAPS")
        self.assertEqual(assess(ledger)["observed_totals"]["input_tokens"], "UNKNOWN")

    def test_invalid_metadata_sends_nothing(self):
        for field, value in (("model", "other"), ("request_id", "bad id"), ("body", "secret")):
            with self.subTest(field=field), mock_server() as (port, received):
                ledger = self.pending()
                ledger["requests"][-1][field] = value
                with self.assertRaises(LedgerError):
                    exchange(ledger, port)
                self.assertEqual(received, [])

    def test_only_loopback_port_and_bounded_timeout(self):
        for port, timeout in ((True, 1), (0, 1), (65536, 1), ("https://example.com", 1),
                              (1, True), (1, 0), (1, -1), (1, 11), (1, float("nan")),
                              (1, float("inf"))):
            with self.subTest(port=port, timeout=timeout), self.assertRaises(ValueError):
                exchange(self.pending(), port, timeout)

    def test_completed_attempt_cannot_be_dispatched(self):
        ledger = self.pending()
        ledger["requests"][-1].update(status="completed", http_status=200)
        with self.assertRaises(ValueError):
            exchange(ledger, 1)


if __name__ == "__main__":
    unittest.main()
