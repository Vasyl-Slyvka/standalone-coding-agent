"""Verify that published task scopes resolve to real paths, not prose lists."""

from pathlib import Path
import unittest

from sca.preflight import _scope_path
from sca.task import parse_task


class RepositoryContractTests(unittest.TestCase):
    def test_published_task_scopes_are_individual_existing_paths(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for path in sorted((root / "tasks").glob("task-*.md")):
            task = parse_task(path)
            self.assertEqual(len(task.scope), len(set(task.scope)), path.name)
            for item in task.scope:
                with self.subTest(task=path.name, scope=item):
                    relative = _scope_path(root, item)
                    self.assertTrue((root / relative).exists(), item)


if __name__ == "__main__":
    unittest.main()
