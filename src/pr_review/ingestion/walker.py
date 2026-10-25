"""Which files get indexed, and why the others don't (matrix 02: I3, I4, I11)."""

from __future__ import annotations

import fnmatch
import re
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".tox", ".mypy_cache",
             ".pytest_cache", ".ruff_cache", ".pr_review", ".idea", ".vscode"}
SKIP_NAMES = ("package-lock.json", "yarn.lock", "poetry.lock", "Pipfile.lock", "uv.lock", "pnpm-lock.yaml", "*.min.js",
              "*.min.css", "*.map")
SECRET_NAMES = (".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*", "*.keystore")
SECRET_TEXT = re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}|"
                         rb"xox[baprs]-[A-Za-z0-9-]{10,}")
MAX_BYTES = 200_000


def _match(name: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def walk(root: Path, skipped: Counter) -> Iterator[tuple[str, bytes]]:
    """Yield (posix relative path, raw bytes) for each file worth indexing; count every skip by reason.
    The secret check reports only the reason, never the matched text (same rule as ingress F15)."""
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]) or not p.is_file():
            continue
        name = p.name
        if _match(name, SECRET_NAMES):
            skipped["possible secret (name)"] += 1
            continue
        if _match(name, SKIP_NAMES):
            skipped["lock or generated file"] += 1
            continue
        size = p.stat().st_size
        if size > MAX_BYTES:
            skipped["over 200 KB"] += 1
            continue
        data = p.read_bytes()
        if b"\0" in data[:8192]:
            skipped["binary"] += 1
            continue
        if SECRET_TEXT.search(data):
            skipped["possible secret (content)"] += 1
            continue
        yield rel.as_posix(), data
