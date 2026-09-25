"""Small, deliberately strict Markdown task contract for the first slice."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


class TaskError(ValueError):
    """The task cannot be used safely for preflight."""


_REQUIRED = ("Scope", "Must do", "Must not", "Acceptance", "Checks", "Stop rule")
_OPTIONAL = ("Sources",)
_ID = re.compile(r"[A-Z][A-Z0-9-]{2,63}\Z")
_HEADER = re.compile(r"^## (.+?)\s*$")
_FIELD = re.compile(r"^(Task ID|Branch):\s*(.*?)\s*$")


@dataclass(frozen=True)
class Task:
    identifier: str
    branch: str
    scope: tuple[str, ...]
    must_do: tuple[str, ...]
    must_not: tuple[str, ...]
    acceptance: tuple[str, ...]
    checks: tuple[str, ...]
    stop_rule: str
    sources: tuple[str, ...]


def _bullets(title: str, body: list[str]) -> tuple[str, ...]:
    items: list[str] = []
    for line in body:
        if not line.strip():
            continue
        if not line.startswith("- ") or not line[2:].strip():
            raise TaskError(f"{title}: use nonempty '- ' list items")
        items.append(line[2:].strip())
    if title in _REQUIRED and not items:
        raise TaskError(f"{title}: at least one item is required")
    return tuple(items)


def parse_task(path: Path) -> Task:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise TaskError(f"Cannot read task file: {exc}") from exc
    fields: dict[str, str] = {}
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        match = _HEADER.fullmatch(line)
        if match:
            current = match.group(1)
            if current not in (*_REQUIRED, *_OPTIONAL):
                raise TaskError(f"Unexpected section: {current}")
            if current in sections:
                raise TaskError(f"Duplicate section: {current}")
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
        else:
            match = _FIELD.fullmatch(line)
            if match:
                key, value = match.groups()
                if key in fields:
                    raise TaskError(f"Duplicate field: {key}")
                fields[key] = value
            elif line.strip() and not line.startswith("# "):
                raise TaskError("Before sections, only title, Task ID and Branch are allowed")

    missing = [name for name in _REQUIRED if name not in sections]
    if missing:
        raise TaskError(f"Missing sections: {', '.join(missing)}")
    identifier = fields.get("Task ID", "")
    if not _ID.fullmatch(identifier):
        raise TaskError("Task ID must be 3-64 uppercase letters, digits or hyphens")
    branch = fields.get("Branch", "")
    if not branch or branch.strip() != branch or branch.startswith("-"):
        raise TaskError("Branch must name an existing authorized branch")

    stop = _bullets("Stop rule", sections["Stop rule"])
    return Task(
        identifier=identifier,
        branch=branch,
        scope=_bullets("Scope", sections["Scope"]),
        must_do=_bullets("Must do", sections["Must do"]),
        must_not=_bullets("Must not", sections["Must not"]),
        acceptance=_bullets("Acceptance", sections["Acceptance"]),
        checks=_bullets("Checks", sections["Checks"]),
        stop_rule="; ".join(stop),
        sources=_bullets("Sources", sections.get("Sources", [])),
    )
