"""Read-only task/Git inspection. An INSPECTED result never authorizes editing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
import os
import subprocess

from .task import TaskError, parse_task


class GitError(ValueError):
    """Git state could not be inspected."""


def _git(directory: Path, *arguments: str) -> bytes:
    env = {**{key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
           "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
    command = ["git", "-c", "core.fsmonitor=false", "-C", str(directory)]
    try:
        # Even `git status` can execute a configured clean/process filter while
        # hashing a same-size changed file. Disable every discovered filter for
        # this process; repository/global configuration is never rewritten.
        config = subprocess.run(command + ["config", "--null", "--name-only", "--get-regexp",
                                           r"^filter\..*\.(clean|smudge|process|required)$"],
                                capture_output=True, timeout=10, env=env)
        if config.returncode not in (0, 1):
            raise GitError("Cannot inspect Git content filters")
        for raw_key in sorted(set(config.stdout.split(b"\0")) - {b""}):
            key = raw_key.decode("utf-8")
            command.extend(["-c", key + ("=false" if key.endswith(".required") else "=")])
        result = subprocess.run(
            [*command, *arguments],
            capture_output=True,
            check=False,
            timeout=10,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitError(f"Git inspection unavailable: {exc}") from exc
    if result.returncode:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise GitError(message or f"git {arguments[0]} failed ({result.returncode})")
    return result.stdout


def _status_paths(root: Path) -> tuple[str, ...]:
    """Parse Git porcelain v1 with NUL delimiters, including both rename paths."""
    fields = _git(root, "status", "--porcelain=v1", "--untracked-files=all", "-z").split(b"\0")
    paths: list[str] = []
    index = 0
    while index < len(fields) and fields[index]:
        entry = fields[index]
        if len(entry) < 4 or entry[2:3] != b" ":
            raise GitError("Unrecognized git status entry")
        paths.append(entry[3:].decode("utf-8", "surrogateescape"))
        if b"R" in entry[:2] or b"C" in entry[:2]:
            index += 1
            if index >= len(fields) or not fields[index]:
                raise GitError("Unrecognized renamed git status entry")
            paths.append(fields[index].decode("utf-8", "surrogateescape"))
        index += 1
    return tuple(sorted(set(paths)))


def _scope_path(root: Path, raw: str) -> str:
    if not raw or raw.strip() != raw or "\\" in raw or any(c in raw for c in "*?[]") \
            or any(ord(c) < 32 or ord(c) == 127 for c in raw):
        raise TaskError(f"Unsafe or unsupported Scope path: {raw!r}")
    value = raw.rstrip("/")
    parts = value.split("/")
    if not value or value.startswith("/") or any(p in ("", ".", "..") for p in parts):
        raise TaskError(f"Unsafe Scope path: {raw!r}")
    if any(p.lower() == ".git" for p in parts):
        raise TaskError(f"Git metadata is out of scope: {raw!r}")
    rel = PurePosixPath(value)
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise TaskError(f"Symlink in Scope path: {raw!r}")
    if not cursor.resolve().is_relative_to(root):
        raise TaskError(f"Scope escapes repository: {raw!r}")
    return value


def _overlaps(path: str, scope: str) -> bool:
    return path == scope or path.startswith(scope + "/") or scope.startswith(path + "/")


@dataclass(frozen=True)
class PreflightReport:
    status: str
    task_id: str | None
    repository: str | None
    branch: str | None
    head: str | None
    scope: tuple[str, ...]
    dirty_paths: tuple[str, ...]
    checks_declared: tuple[str, ...]
    issues: tuple[str, ...]
    policy_status: str = "not_evaluated"
    note: str = "Read-only inspection; no repo policy, command, model or edit was executed."

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def inspect(repo: Path, task_file: Path) -> PreflightReport:
    identifier: str | None = None
    root: Path | None = None
    branch: str | None = None
    head: str | None = None
    scope: tuple[str, ...] = ()
    dirty: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    issues: list[str] = []
    try:
        task = parse_task(task_file)
        identifier = task.identifier
        checks = task.checks
        root = Path(_git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
        branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD").decode().strip()
        head = _git(root, "rev-parse", "HEAD").decode().strip()
        scope = tuple(_scope_path(root, item) for item in task.scope)
        dirty = _status_paths(root)
        if branch != task.branch:
            issues.append(f"Branch mismatch: expected {task.branch!r}, found {branch!r}")
        overlaps = [path for path in dirty if any(_overlaps(path, item) for item in scope)]
        if overlaps:
            issues.append("Dirty Scope paths: " + ", ".join(overlaps))
    except (TaskError, GitError, UnicodeError, ValueError) as exc:
        issues.append(str(exc))
    return PreflightReport(
        status="BLOCKED" if issues else "INSPECTED",
        task_id=identifier,
        repository=str(root) if root else None,
        branch=branch,
        head=head,
        scope=scope,
        dirty_paths=dirty,
        checks_declared=checks,
        issues=tuple(issues),
    )
