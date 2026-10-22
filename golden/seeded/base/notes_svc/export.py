"""Export a user's notes to a file under exports/."""

import re
import sqlite3
from pathlib import Path

EXPORT_DIR = Path("exports")
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def export_notes(conn: sqlite3.Connection, user_id: int, name: str) -> Path:
    """Write the user's notes to exports/<name>.txt and return the path."""
    if not _SAFE_NAME.match(name):
        raise ValueError("export name may only contain letters, digits, '_' and '-'")
    rows = conn.execute(
        "SELECT title, body, created_at FROM notes WHERE user_id = ? ORDER BY id", (user_id,)
    ).fetchall()
    EXPORT_DIR.mkdir(exist_ok=True)
    path = EXPORT_DIR / f"{name}.txt"
    text = "\n\n".join(f"{r['title']} ({r['created_at']})\n{r['body']}" for r in rows)
    path.write_text(text, encoding="utf-8")
    return path
