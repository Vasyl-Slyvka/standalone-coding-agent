from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from sca.preflight import inspect


TASK = """# Synthetic task
Task ID: EXP-001
Branch: main

## Scope
- src/app.py

## Must do
- Add a greeting.

## Must not
- Modify the license.

## Acceptance
- The greeting is covered by a test.

## Checks
- python -m unittest

## Stop rule
- Stop when a requested edit conflicts with repository rules.
"""


class PreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-b", "main")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "app.py").write_text("print('hello')\n")
        self.git("add", "src/app.py")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "init")
        self.task = self.root / "task.md"
        self.task.write_text(TASK)

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)

    def test_clean_repository_is_inspected_but_never_authorized(self) -> None:
        result = inspect(self.repo, self.task)
        self.assertEqual(result.status, "INSPECTED")
        self.assertEqual(result.policy_status, "not_evaluated")
        self.assertEqual(result.scope, ("src/app.py",))
        self.assertIn("python -m unittest", result.checks_declared)
        self.assertIn("no repo policy", result.note)

    def test_changed_scoped_file_blocks_and_preserves_user_content(self) -> None:
        changed = self.repo / "src" / "app.py"
        changed.write_text("MY UNCOMMITTED WORK\n")
        result = inspect(self.repo, self.task)
        self.assertEqual(result.status, "BLOCKED")
        self.assertIn("Dirty Scope paths", result.issues[0])
        self.assertEqual(changed.read_text(), "MY UNCOMMITTED WORK\n")

    def test_unrelated_dirty_file_is_reported_without_blocking(self) -> None:
        (self.repo / "notes.txt").write_text("Keep me")
        result = inspect(self.repo, self.task)
        self.assertEqual(result.status, "INSPECTED")
        self.assertEqual(result.dirty_paths, ("notes.txt",))

    def test_branch_mismatch_blocks(self) -> None:
        self.task.write_text(TASK.replace("Branch: main", "Branch: not-main"))
        result = inspect(self.repo, self.task)
        self.assertEqual(result.status, "BLOCKED")
        self.assertIn("Branch mismatch", result.issues[0])

    def test_invalid_or_malicious_scope_blocks(self) -> None:
        for path in ("../outside", "/tmp/outside", "src/../../x", ".git/config", "src/*.py"):
            with self.subTest(path=path):
                self.task.write_text(TASK.replace("src/app.py", path))
                self.assertEqual(inspect(self.repo, self.task).status, "BLOCKED")

    def test_symlink_scope_blocks_even_if_target_is_within_repo(self) -> None:
        (self.repo / "src" / "alias.py").symlink_to("app.py")
        self.task.write_text(TASK.replace("src/app.py", "src/alias.py"))
        result = inspect(self.repo, self.task)
        self.assertEqual(result.status, "BLOCKED")
        self.assertIn("Symlink", result.issues[0])

    def test_missing_or_duplicate_contract_sections_block(self) -> None:
        for invalid in (TASK.replace("## Acceptance", "## Unsupported"), TASK + "\n## Scope\n- x\n"):
            with self.subTest(invalid=invalid[-35:]):
                self.task.write_text(invalid)
                self.assertEqual(inspect(self.repo, self.task).status, "BLOCKED")

    def test_declared_check_is_never_executed(self) -> None:
        marker = self.root / "must-not-exist"
        self.task.write_text(TASK.replace("python -m unittest", f"touch {marker}"))
        result = inspect(self.repo, self.task)
        self.assertEqual(result.status, "INSPECTED")
        self.assertFalse(marker.exists())

    def test_non_git_directory_blocks(self) -> None:
        result = inspect(self.root, self.task)
        self.assertEqual(result.status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
