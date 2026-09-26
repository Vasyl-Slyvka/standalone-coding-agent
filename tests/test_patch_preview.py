"""Synthetic Git fixtures for a read-only, scoped patch preview."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from sca.patch_preview import PreviewError, preview


TASK = """# Synthetic preview
Task ID: EXP-004
Branch: main

## Scope
- src/app.py

## Must do
- Change a greeting.

## Must not
- Touch notes or perform external actions.

## Acceptance
- Review the diff before any edit.

## Checks
- python -m unittest

## Stop rule
- Stop if Git state or source digest differs.
"""


class PreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        (self.repo / "src").mkdir(parents=True)
        self.git("init", "-b", "main")
        self.original = b"print('hello')\n"
        (self.repo / "src/app.py").write_bytes(self.original)
        self.git("add", "src/app.py")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.com",
                 "commit", "-m", "initial")
        self.task = self.root / "task.md"
        self.task.write_text(TASK, encoding="utf-8")
        self.candidate = {
            "path": "src/app.py", "expected_head": self.git("rev-parse", "HEAD").strip(),
            "expected_sha256": hashlib.sha256(self.original).hexdigest(),
            "replacement": "print('goodbye')\n",
        }

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                              capture_output=True, text=True).stdout

    def test_preview_has_diff_but_never_changes_worktree_or_git(self) -> None:
        result = preview(self.repo, self.task, self.candidate)
        self.assertEqual(result["status"], "PREVIEW_ONLY")
        self.assertEqual(result["policy_status"], "not_evaluated")
        self.assertIn("-print('hello')", result["diff"])
        self.assertIn("+print('goodbye')", result["diff"])
        self.assertEqual((self.repo / "src/app.py").read_bytes(), self.original)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_base_head_and_digest_mismatches_block(self) -> None:
        for field, value in (("expected_head", "0" * 40),
                             ("expected_sha256", "0" * 64)):
            with self.subTest(field=field):
                with self.assertRaises(PreviewError):
                    preview(self.repo, self.task, {**self.candidate, field: value})

    def test_dirty_scope_blocks_and_preserves_user_work(self) -> None:
        target = self.repo / "src/app.py"
        target.write_text("MY WORK\n")
        with self.assertRaisesRegex(PreviewError, "Dirty Scope"):
            preview(self.repo, self.task, self.candidate)
        self.assertEqual(target.read_text(), "MY WORK\n")

    def test_unrelated_dirty_file_remains_untouched(self) -> None:
        (self.repo / "notes.txt").write_text("Keep me")
        self.assertEqual(preview(self.repo, self.task, self.candidate)["status"], "PREVIEW_ONLY")
        self.assertEqual((self.repo / "notes.txt").read_text(), "Keep me")

    def test_path_traversal_symlink_and_out_of_scope_block(self) -> None:
        (self.repo / "src/alias.py").symlink_to("app.py")
        (self.repo / "src/other.py").write_text("nothing")
        for path in ("../outside", "/tmp/outside", ".git/config", "src/alias.py",
                     "src/other.py", "src/app.py/../other.py"):
            with self.subTest(path=path), self.assertRaises(PreviewError):
                preview(self.repo, self.task, {**self.candidate, "path": path})

    def test_untracked_target_and_wrong_branch_block(self) -> None:
        self.task.write_text(TASK.replace("src/app.py", "src/new.py"))
        (self.repo / ".gitignore").write_text("src/new.py\n")
        (self.repo / "src/new.py").write_bytes(self.original)
        with self.assertRaisesRegex(PreviewError, "tracked file"):
            preview(self.repo, self.task, {**self.candidate, "path": "src/new.py"})
        self.task.write_text(TASK.replace("Branch: main", "Branch: wrong"))
        with self.assertRaises(PreviewError):
            preview(self.repo, self.task, self.candidate)

    def test_newline_only_change_is_visible_as_metadata(self) -> None:
        result = preview(self.repo, self.task,
                         {**self.candidate, "replacement": "print('hello')"})
        self.assertTrue(result["changed"])
        self.assertFalse(result["after_final_newline"])
        self.assertTrue(result["before_final_newline"])

    def test_crlf_only_change_has_a_visible_diff(self) -> None:
        result = preview(self.repo, self.task,
                         {**self.candidate, "replacement": "print('hello')\r\n"})
        self.assertTrue(result["changed"])
        self.assertTrue(result["diff"])
        self.assertIn("\\r", json.dumps(result["diff"]))
        self.assertFalse(result["diff_applicable"])
        self.assertEqual((self.repo / "src/app.py").read_bytes(), self.original)

    def test_malformed_content_and_cli_duplicate_field_block(self) -> None:
        for value in (b"x", "\x00", "a" * 131_073, "\ud800"):
            candidate = {**self.candidate, "replacement": value}
            with self.subTest(size=len(value)), self.assertRaises(PreviewError):
                preview(self.repo, self.task, candidate)
        path = self.root / "candidate.json"
        path.write_text(json.dumps(self.candidate), encoding="utf-8")
        command = [sys.executable, "-m", "sca.patch_preview", str(self.repo),
                   str(self.task), str(path)]
        good = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(good.returncode, 0)
        self.assertEqual(json.loads(good.stdout)["status"], "PREVIEW_ONLY")
        path.write_text('{"path":"x","path":"y"}', encoding="utf-8")
        bad = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(bad.returncode, 2)
        self.assertIn("Duplicate field", bad.stderr)


if __name__ == "__main__":
    unittest.main()
