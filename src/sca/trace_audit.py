"""Offline audit of machine-readable candidate-engine events.

Usage observations here are turns or steps, never asserted API calls. Raw
messages and tool outputs are deliberately excluded from the summary.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


class TraceError(ValueError):
    """A JSONL trace is invalid or has conflicting event identities."""


def _tokens(data: Any, keys: tuple[str, ...]) -> dict[str, int | None]:
    if not isinstance(data, dict):
        return {key: None for key in keys}
    result: dict[str, int | None] = {}
    for key in keys:
        value = data.get(key)
        if value is not None and (type(value) is not int or value < 0):
            raise TraceError(f"invalid token count: {key}")
        result[key] = value
    return result


def audit_events(engine: str, lines: Iterable[str], provider: str, model: str) -> dict[str, Any]:
    """Summarize a single event stream without counting aggregate messages twice."""
    if engine not in ("codex", "opencode"):
        raise TraceError("supported engines: codex, opencode")
    if not provider.strip() or not model.strip():
        raise TraceError("manual provider and model must be specified")
    counts: dict[str, int] = {}
    observations: list[dict[str, Any]] = []
    messages: dict[str, tuple[str, str]] = {}
    parts: dict[str, dict[str, Any]] = {}
    bad_models: set[str] = set()
    errors = 0
    events = 0
    for line_no, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TraceError(f"line {line_no}: invalid JSON") from exc
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise TraceError(f"line {line_no}: expected event object with type")
        kind = event["type"]
        events += 1
        counts[kind] = counts.get(kind, 0) + 1
        if engine == "codex":
            if kind in ("turn.failed", "error"):
                errors += 1
            if kind == "turn.completed":
                usage = _tokens(event.get("usage"),
                                ("input_tokens", "cached_input_tokens", "output_tokens",
                                 "reasoning_output_tokens"))
                observations.append({"granularity": "turn", "usage_source": "engine_reported",
                                     "tokens": usage, "model_identity": "not_in_event"})
        else:
            props = event.get("properties")
            if kind == "message.updated" and isinstance(props, dict):
                info = props.get("info")
                if isinstance(info, dict) and info.get("role") == "assistant":
                    msg_id = info.get("id")
                    selected = (info.get("providerID"), info.get("modelID"))
                    if not isinstance(msg_id, str) or not msg_id:
                        raise TraceError(f"line {line_no}: assistant message lacks id")
                    if msg_id in messages and messages[msg_id] != selected:
                        raise TraceError(f"line {line_no}: conflicting assistant model identity")
                    messages[msg_id] = selected
                    if all(isinstance(value, str) and value for value in selected) and selected != (provider, model):
                        bad_models.add(f"{selected[0]}/{selected[1]}")
            if kind == "message.part.updated" and isinstance(props, dict):
                part = props.get("part")
                if isinstance(part, dict) and part.get("type") == "step-finish":
                    part_id, msg_id = part.get("id"), part.get("messageID")
                    if not isinstance(part_id, str) or not part_id or not isinstance(msg_id, str):
                        raise TraceError(f"line {line_no}: step-finish lacks id/messageID")
                    # SSE can update the same part multiple times; use its final state once.
                    if part_id in parts and parts[part_id]["messageID"] != msg_id:
                        raise TraceError(f"line {line_no}: part id changed message")
                    parts[part_id] = {"messageID": msg_id, "tokens": part.get("tokens")}
            if kind in ("session.error", "error"):
                errors += 1
    if engine == "opencode":
        for part in parts.values():
            tokens = part.get("tokens")
            flattened = None
            if isinstance(tokens, dict):
                cache = tokens.get("cache")
                flattened = {"input": tokens.get("input"), "output": tokens.get("output"),
                             "reasoning": tokens.get("reasoning"),
                             "cache_read": cache.get("read") if isinstance(cache, dict) else None,
                             "cache_write": cache.get("write") if isinstance(cache, dict) else None}
            usage = _tokens(flattened, ("input", "output", "reasoning", "cache_read", "cache_write"))
            identity = messages.get(part["messageID"])
            if identity is None:
                model_identity = "unresolved"
            elif not all(isinstance(value, str) and value for value in identity):
                model_identity = "unresolved"
            elif identity != (provider, model):
                model_identity = "mismatch"
            else:
                model_identity = "matches_selection"
            observations.append({"granularity": "step", "usage_source": "engine_reported",
                                 "tokens": usage, "model_identity": model_identity})
    return {"engine": engine, "selected_provider": provider, "selected_model": model,
            "event_count": events, "event_types": counts,
            "usage_observations": observations,
            "model_mismatches": sorted(bad_models), "error_events": errors,
            "api_call_count": "UNKNOWN", "trace_completeness": "unverified",
            "note": "Turn/step usage is not independently verified per-request usage. "
                    "No raw prompts, tool outputs or credentials are retained."}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Codex/OpenCode JSONL events offline")
    parser.add_argument("engine", choices=("codex", "opencode"))
    parser.add_argument("trace", type=Path)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    try:
        with args.trace.open(encoding="utf-8") as stream:
            result = audit_events(args.engine, stream, args.provider, args.model)
    except (OSError, UnicodeError, TraceError) as exc:
        parser.exit(2, f"INVALID TRACE: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
