"""Read-only preview of one full-file replacement against an expected Git state.

This checks a candidate, but does not authorize or apply it. Repository policy,
including nested AGENTS.md and NODREN gates, is not evaluated here.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import stat
import sys
from typing import Any

from .preflight import GitError, _git, _scope_path, inspect
from .task import TaskError


class PreviewError(ValueError):
    """The candidate cannot be previewed against this repository state."""


_FIELDS = {"path", "expected_head", "expected_sha256", "replacement"}
_HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_HEX_HEAD = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
_FILE_LIMIT = 131_072


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PreviewError(f"Duplicate field: {key}")
        result[key] = value
    return result


def preview(repo: Path, task_file: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    """Produce a diff for an unchanged, tracked UTF-8 file; never write it."""
    if not isinstance(candidate, dict) or set(candidate) != _FIELDS:
        raise PreviewError("Candidate requires exactly path, expected_head, expected_sha256, replacement")
    path, head, expected, replacement = (candidate[key] for key in
                                         ("path", "expected_head", "expected_sha256", "replacement"))
    if not isinstance(path, str) or any(ord(char) < 32 for char in path) \
            or len(path) > 512 or not isinstance(head, str) or not _HEX_HEAD.fullmatch(head) \
            or not isinstance(expected, str) or not _HEX_SHA256.fullmatch(expected) \
            or not isinstance(replacement, str):
        raise PreviewError("Candidate fields have invalid types or digests")
    try:
        after_bytes = replacement.encode("utf-8")
    except UnicodeError as exc:
        raise PreviewError("Replacement is not valid UTF-8 text") from exc
    if "\0" in replacement or len(after_bytes) > _FILE_LIMIT:
        raise PreviewError("Replacement must be UTF-8 text up to 128 KiB without NUL")

    checked = inspect(repo, task_file)
    if checked.status != "INSPECTED" or not checked.repository or not checked.head:
        raise PreviewError("Task/Git inspection blocked: " + "; ".join(checked.issues))
    if checked.head != head:
        raise PreviewError("HEAD changed since candidate preparation")
    root = Path(checked.repository)
    try:
        path = _scope_path(root, path)
    except TaskError as exc:
        raise PreviewError(str(exc)) from exc
    if not any(path == scope or path.startswith(scope + "/") for scope in checked.scope):
        raise PreviewError("Candidate path is outside task Scope")

    target = root / path
    try:
        if not stat.S_ISREG(target.lstat().st_mode):
            raise PreviewError("Candidate must target an existing regular file")
        _git(root, "ls-files", "--error-unmatch", "--", ":(literal)" + path)
        if target.stat().st_size > _FILE_LIMIT:
            raise PreviewError("Existing file exceeds 128 KiB")
        before_bytes = target.read_bytes()
    except (OSError, GitError) as exc:
        raise PreviewError(f"Cannot inspect tracked file: {exc}") from exc
    if len(before_bytes) > _FILE_LIMIT or b"\0" in before_bytes:
        raise PreviewError("Existing file must be UTF-8 text up to 128 KiB without NUL")
    actual = hashlib.sha256(before_bytes).hexdigest()
    if actual != expected:
        raise PreviewError("File digest differs from expected_sha256")
    try:
        before = before_bytes.decode("utf-8")
    except UnicodeError as exc:
        raise PreviewError("Existing file is not UTF-8") from exc
    # Split only on LF: splitlines() silently erases CRLF/CR and Unicode separators.
    # JSON output escapes retained CR characters, keeping byte-only changes visible.
    delta = difflib.unified_diff(before.split("\n"), replacement.split("\n"),
                                 fromfile="a/" + path, tofile="b/" + path, lineterm="")
    return {
        "status": "PREVIEW_ONLY",
        "policy_status": "not_evaluated",
        "path": path,
        "base_head": head,
        "base_sha256": actual,
        "replacement_sha256": hashlib.sha256(after_bytes).hexdigest(),
        "changed": before_bytes != after_bytes,
        "diff": "\n".join(delta),
        "diff_applicable": False,
        "diff_format": "review display only; CR characters retained and escaped in JSON",
        "before_final_newline": before.endswith("\n"),
        "after_final_newline": replacement.endswith("\n"),
        "note": "Read-only preview; no policy authorization, workspace isolation or edit was performed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview one candidate file replacement without edits")
    parser.add_argument("repo", type=Path)
    parser.add_argument("task", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    try:
        if args.candidate.stat().st_size > 262_144:
            raise PreviewError("Candidate JSON exceeds 256 KiB")
        data = json.loads(args.candidate.read_text(encoding="utf-8"),
                          object_pairs_hook=_unique_pairs)
        result = preview(args.repo, args.task, data)
    except (OSError, UnicodeError, json.JSONDecodeError, PreviewError) as exc:
        print(f"BLOCKED PREVIEW: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
