"""Negative and positive checks for explicit, offline model choice."""

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from sca.selection import SelectionError, load_selection


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "selection.json"
        self.data = {"schema_version": 1, "provider": "example-provider",
                     "model": "example/model:v1", "endpoint_alias": "local-test"}

    def write(self, data: dict) -> None:
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def test_selection_snapshot_is_immutable_and_deterministic(self) -> None:
        self.write(self.data)
        selected = load_selection(self.path)
        first = selected.snapshot()
        original_digest = first["sha256"]
        self.data["model"] = "another-model"
        self.write(self.data)
        first["selection"]["model"] = "tampered"
        self.assertEqual(selected.snapshot()["selection"]["model"], "example/model:v1")
        self.assertEqual(selected.snapshot()["sha256"], original_digest)
        self.assertNotEqual(selected.snapshot()["sha256"], load_selection(self.path).snapshot()["sha256"])
        self.assertEqual(selected.snapshot()["status"], "UNVERIFIED_SELECTION")

    def test_invalid_or_ambiguous_config_is_rejected(self) -> None:
        cases = [
            {**self.data, "provider": ""},
            {**self.data, "model": "auto default"},
            {**self.data, "model": "auto"},
            {**self.data, "endpoint_alias": "https://api.example"},
            {**self.data, "api_key": "SECRET"},
            {**self.data, "schema_version": True},
            {**self.data, "schema_version": 2},
        ]
        for case in cases:
            with self.subTest(case=case):
                self.write(case)
                with self.assertRaises(SelectionError):
                    load_selection(self.path)

    def test_duplicate_field_and_non_object_are_rejected(self) -> None:
        for value in ('{"schema_version":1,"provider":"a","provider":"b",'
                      '"model":"m","endpoint_alias":"e"}', '[]'):
            self.path.write_text(value, encoding="utf-8")
            with self.assertRaises(SelectionError):
                load_selection(self.path)

    def test_missing_and_oversize_config_are_rejected(self) -> None:
        with self.assertRaises(SelectionError):
            load_selection(self.path)
        self.path.write_text(" " * 16_385, encoding="utf-8")
        with self.assertRaises(SelectionError):
            load_selection(self.path)

    def test_cli_reports_unverified_choice_and_fails_closed(self) -> None:
        self.write(self.data)
        command = [sys.executable, "-m", "sca.selection", str(self.path)]
        good = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(good.returncode, 0)
        self.assertEqual(json.loads(good.stdout)["selection"]["model"], "example/model:v1")
        self.assertEqual(json.loads(good.stdout)["status"], "UNVERIFIED_SELECTION")
        self.write({**self.data, "provider": "auto"})
        bad = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(bad.returncode, 2)
        self.assertFalse(bad.stdout)
        self.assertIn("INVALID SELECTION", bad.stderr)
