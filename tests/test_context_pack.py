from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import os
import hashlib

from sca.context_pack import ContextError, build_pack
from sca.task import Task


def task() -> Task:
    return Task("SCA-TEST", "main", ("src",), ("Preserve precise behavior.",),
                ("Never publish a secret.",), ("Return a reviewed diff.",),
                ("python3 -m unittest",), "Stop before any unauthorized write.", ())


class ContextPackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / "greet.py").write_text("def greet(name):\n    return 'Hello, ' + name\n")
        (self.repo / "other.py").write_text("def unrelated():\n    return 42\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "greet.py", "other.py"], check=True)
        self.before = subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain"],
                                     capture_output=True, check=True).stdout

    def test_selects_exact_mandatory_and_ranked_optional_without_writes(self) -> None:
        result = build_pack(task(), self.repo, "greet name", ["other.py", "greet.py"], 1000)
        self.assertEqual(result["mandatory"]["must_not"], ["Never publish a secret."])
        self.assertEqual(result["mandatory"]["acceptance"], ["Return a reviewed diff."])
        self.assertEqual(result["mandatory"]["scope"], ["src"])
        self.assertEqual(result["mandatory"]["checks"], ["python3 -m unittest"])
        self.assertEqual([item["path"] for item in result["optional"]], ["greet.py"])
        self.assertIn("1: def greet(name)", result["optional"][0]["excerpt"])
        self.assertEqual(result["used_bytes"], len(json.dumps(result, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")))
        self.assertLessEqual(result["used_bytes"], 1000)
        self.assertEqual(subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain"],
                          capture_output=True, check=True).stdout, self.before)

    def test_git_hooks_environment_and_index_are_isolated(self) -> None:
        hook = self.repo / "fsmonitor.sh"
        marker = self.repo / "hook-executed"
        hook.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\nprintf "token\\0"\n')
        hook.chmod(0o755)
        subprocess.run(["git", "-C", str(self.repo), "config", "core.fsmonitor", str(hook)], check=True)
        index = self.repo / ".git/index"
        before = hashlib.sha256(index.read_bytes()).hexdigest()
        with patch.dict(os.environ, {"GIT_DIR": str(self.repo / "missing.git")}):
            result = build_pack(task(), self.repo, "greet", ["greet.py"], 2000)
        self.assertEqual(len(result["optional"]), 1)
        self.assertFalse(marker.exists())
        self.assertEqual(hashlib.sha256(index.read_bytes()).hexdigest(), before)

    def test_utf8_budget_and_order_are_deterministic(self) -> None:
        (self.repo / "greet.py").write_text("# привіт\ndef greet(name):\n    return name\n", encoding="utf-8")
        first = build_pack(task(), self.repo, "привіт greet", ["greet.py", "other.py"], 2000)
        second = build_pack(task(), self.repo, "привіт greet", ["other.py", "greet.py"], 2000)
        self.assertEqual(first, second)
        self.assertEqual(first["used_bytes"], len(json.dumps(first, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")))

    def test_budget_drops_optional_but_never_mandatory(self) -> None:
        minimum = build_pack(task(), self.repo, "greet", [], 1000)["used_bytes"]
        small = build_pack(task(), self.repo, "greet", ["greet.py"], minimum + 40)
        self.assertEqual(small["optional"], [])
        self.assertEqual(small["omitted"], ["greet.py"])
        with self.assertRaisesRegex(ContextError, "Mandatory"):
            build_pack(task(), self.repo, "greet", [], 256)

    def test_untrusted_paths_and_contents_fail_closed(self) -> None:
        (self.repo / "untracked.py").write_text("greet\n")
        (self.repo / "binary.py").write_bytes(b"greet\0")
        (self.repo / "large.py").write_bytes(b"greet" * 14000)
        (self.repo / "bad.py").write_bytes(b"\xffgreet")
        (self.repo / "link.py").symlink_to("greet.py")
        subprocess.run(["git", "-C", str(self.repo), "add", "binary.py", "large.py",
                        "bad.py", "link.py"], check=True)
        for name in ("../outside", "/tmp/greet.py", "./greet.py", "untracked.py",
                     "binary.py", "large.py", "bad.py", "link.py"):
            with self.subTest(name=name), self.assertRaises(ContextError):
                build_pack(task(), self.repo, "greet", [name], 2000)

    def test_invalid_limits_and_duplicate_paths(self) -> None:
        for paths, budget in ((["greet.py", "greet.py"], 1000), ([], 200), ([], True)):
            with self.subTest(paths=paths, budget=budget), self.assertRaises(ContextError):
                build_pack(task(), self.repo, "greet", paths, budget)


if __name__ == "__main__":
    unittest.main()
