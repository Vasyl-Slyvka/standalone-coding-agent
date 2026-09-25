"""Read-only command line entry point for slice 1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .preflight import inspect


def main() -> int:
    parser = argparse.ArgumentParser(prog="sca", description="Offline coding-agent task preflight")
    parser.add_argument("repo", type=Path, help="Git repository to inspect")
    parser.add_argument("task", type=Path, help="Markdown task specification")
    parser.add_argument("--json", action="store_true", help="Print machine-readable inspection")
    args = parser.parse_args()
    report = inspect(args.repo, args.task)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=True, indent=2))
    else:
        print(f"{report.status}: {report.task_id or 'invalid task'}")
        print(f"Repository: {report.repository or 'unavailable'}")
        print(f"Branch: {report.branch or 'unavailable'}")
        print(f"Git HEAD: {report.head or 'unavailable'}")
        print(f"Dirty paths: {len(report.dirty_paths)}")
        for issue in report.issues:
            print(f"Issue: {issue}")
        print(report.note)
    return 0 if report.status == "INSPECTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
