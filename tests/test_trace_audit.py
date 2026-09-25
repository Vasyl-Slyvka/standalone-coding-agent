from __future__ import annotations

import json
import unittest

from sca.trace_audit import TraceError, audit_events


def jsonl(*events: dict) -> list[str]:
    return [json.dumps(event) for event in events]


class TraceAuditTests(unittest.TestCase):
    def test_codex_turn_is_not_reported_as_api_call(self) -> None:
        result = audit_events("codex", jsonl(
            {"type": "thread.started", "thread_id": "test"},
            {"type": "turn.completed", "usage": {"input_tokens": 200,
              "cached_input_tokens": 120, "cache_write_input_tokens": 3, "output_tokens": 30,
              "reasoning_output_tokens": 10}},
            {"type": "turn.failed"}), "manual-api", "manual-model")
        self.assertEqual(result["api_call_count"], "UNKNOWN")
        self.assertEqual(result["usage_observations"][0]["granularity"], "turn")
        self.assertEqual(result["usage_observations"][0]["tokens"]["input_tokens"], 200)
        self.assertEqual(result["usage_observations"][0]["tokens"]["cache_write_input_tokens"], 3)
        self.assertEqual(result["error_events"], 1)
        self.assertEqual(result["trace_completeness"], "unverified")

    def test_opencode_deduplicates_step_and_detects_unselected_model(self) -> None:
        info = {"role": "assistant", "id": "m1", "providerID": "other", "modelID": "other"}
        step = {"type": "step-finish", "id": "p1", "messageID": "m1",
                "tokens": {"input": 20, "output": 4, "reasoning": 1,
                           "cache": {"read": 5, "write": 0}}}
        result = audit_events("opencode", jsonl(
            {"type": "message.updated", "properties": {"info": info}},
            {"type": "message.part.updated", "properties": {"part": step}},
            {"type": "message.part.updated", "properties": {"part": step}}),
            "manual-api", "manual-model")
        self.assertEqual(len(result["usage_observations"]), 1)
        self.assertEqual(result["model_mismatches"], ["other/other"])
        self.assertEqual(result["usage_observations"][0]["model_identity"], "mismatch")
        self.assertEqual(result["trace_format"], "sse")

    def test_opencode_run_cli_json_uses_step_finish_not_sse_envelope(self) -> None:
        part = {"type": "step-finish", "id": "part-1", "messageID": "msg-1", "cost": 0.005,
                "tokens": {"input": 40, "output": 7, "reasoning": 2,
                           "cache": {"read": 8, "write": 1}}}
        result = audit_events("opencode", jsonl(
            {"type": "step_start", "sessionID": "session-1", "part": {"type": "step-start"}},
            {"type": "step_finish", "sessionID": "session-1", "part": part},
            {"type": "step_finish", "sessionID": "session-1", "part": part},
            {"type": "error", "sessionID": "session-1", "error": {"name": "test"}}),
            "ollama", "manual-model")
        self.assertEqual(result["trace_format"], "cli_json")
        self.assertEqual(result["event_count"], 4)
        self.assertEqual(len(result["usage_observations"]), 1)
        self.assertEqual(result["usage_observations"][0]["tokens"]["cache_read"], 8)
        self.assertEqual(result["usage_observations"][0]["engine_reported_cost_usd"], 0.005)
        self.assertEqual(result["usage_observations"][0]["model_identity"], "unresolved")
        self.assertEqual(result["model_mismatches"], [])
        self.assertEqual(result["api_call_count"], "UNKNOWN")

    def test_no_events_or_missing_usage_does_not_become_zero(self) -> None:
        empty = audit_events("codex", [], "p", "m")
        self.assertEqual(empty["usage_observations"], [])
        self.assertEqual(empty["api_call_count"], "UNKNOWN")
        missing = audit_events("codex", jsonl({"type": "turn.completed"}), "p", "m")
        self.assertIsNone(missing["usage_observations"][0]["tokens"]["input_tokens"])
        unresolved = audit_events("opencode", jsonl({"type": "message.part.updated",
            "properties": {"part": {"type": "step-finish", "id": "p", "messageID": "m"}}}),
            "p", "m")
        self.assertEqual(unresolved["usage_observations"][0]["model_identity"], "unresolved")

    def test_invalid_events_and_conflicting_identity_stop(self) -> None:
        with self.assertRaisesRegex(TraceError, "invalid JSON"):
            audit_events("codex", ["{"], "p", "m")
        with self.assertRaisesRegex(TraceError, "invalid token count"):
            audit_events("codex", jsonl({"type": "turn.completed",
                "usage": {"input_tokens": -1}}), "p", "m")
        with self.assertRaisesRegex(TraceError, "conflicting assistant"):
            audit_events("opencode", jsonl(
                {"type": "message.updated", "properties": {"info": {
                    "role": "assistant", "id": "m1", "providerID": "p", "modelID": "m"}}},
                {"type": "message.updated", "properties": {"info": {
                    "role": "assistant", "id": "m1", "providerID": "p", "modelID": "x"}}}), "p", "m")
        with self.assertRaisesRegex(TraceError, "part id changed"):
            audit_events("opencode", jsonl(
                {"type": "message.part.updated", "properties": {"part": {
                    "type": "step-finish", "id": "p1", "messageID": "m1"}}},
                {"type": "message.part.updated", "properties": {"part": {
                    "type": "step-finish", "id": "p1", "messageID": "m2"}}}), "p", "m")
        with self.assertRaisesRegex(TraceError, "mixed OpenCode"):
            audit_events("opencode", jsonl(
                {"type": "step_finish", "part": {"type": "step-finish", "id": "p", "messageID": "m"}},
                {"type": "message.updated", "properties": {"info": {
                    "role": "assistant", "id": "m", "providerID": "p", "modelID": "m"}}}), "p", "m")
        with self.assertRaisesRegex(TraceError, "multiple OpenCode"):
            audit_events("opencode", jsonl(
                {"type": "step_start", "sessionID": "one"},
                {"type": "step_start", "sessionID": "two"}), "p", "m")


if __name__ == "__main__":
    unittest.main()
