"""Offline, explicit provider/model selection for a future single run.

This module does not resolve endpoints or call a model. A selection snapshot
records the owner's choice, not evidence that an engine honored it.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


class SelectionError(ValueError):
    """The configuration cannot be used as an explicit model selection."""


_KEYS = frozenset({"schema_version", "provider", "model", "endpoint_alias"})
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SelectionError(f"Duplicate field: {key}")
        result[key] = value
    return result


@dataclass(frozen=True)
class Selection:
    schema_version: int
    provider: str
    model: str
    endpoint_alias: str

    def snapshot(self) -> dict[str, Any]:
        """Return a detached value and digest suitable for a run record."""
        data = asdict(self)
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return {"selection": data, "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
                "status": "UNVERIFIED_SELECTION"}


def load_selection(path: Path) -> Selection:
    try:
        if path.stat().st_size > 16_384:
            raise SelectionError("Configuration exceeds 16 KiB")
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SelectionError(f"Cannot read selection: {exc}") from exc
    try:
        data = json.loads(raw, object_pairs_hook=_unique_pairs)
    except json.JSONDecodeError as exc:
        raise SelectionError(f"Invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict) or set(data) != _KEYS:
        raise SelectionError("Expected exactly schema_version, provider, model, endpoint_alias")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise SelectionError("Only schema_version 1 is supported")
    for field in ("provider", "model", "endpoint_alias"):
        value = data[field]
        if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
            raise SelectionError(f"Invalid {field}: use a nonempty identifier without spaces or secrets")
        if field in ("provider", "model") and value.lower() in ("auto", "default"):
            raise SelectionError(f"{field} must be an explicit identifier, not auto/default")
    if "://" in data["endpoint_alias"] or "/" in data["endpoint_alias"]:
        raise SelectionError("endpoint_alias must be a name, not a URL or path")
    return Selection(**data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect an explicit model selection offline")
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    try:
        result = load_selection(args.config).snapshot()
    except SelectionError as exc:
        print(f"INVALID SELECTION: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
