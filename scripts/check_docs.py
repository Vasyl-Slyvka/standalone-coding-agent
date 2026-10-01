"""Check local inline Markdown link targets; never fetch external URLs."""

from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]\n]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")


def main() -> int:
    checked = 0
    errors = []
    for path in sorted(ROOT.rglob("*.md")):
        if ".git" in path.relative_to(ROOT).parts:
            continue
        # Links in fenced examples are literal input, not navigation.
        content = re.sub(r"^```[^\n]*\n.*?^```\s*$", "", path.read_text(encoding="utf-8"),
                         flags=re.MULTILINE | re.DOTALL)
        for match in LINK.finditer(content):
            target = match.group(1).strip("<>")
            parts = urlsplit(target)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            resolved = (path.parent / unquote(parts.path)).resolve()
            checked += 1
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)}: {target}")
    for error in errors:
        print(f"BROKEN: {error}")
    print(f"Local Markdown path targets: {checked}; broken: {len(errors)}")
    print("External URLs, anchors and reference-style links are not validated.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
