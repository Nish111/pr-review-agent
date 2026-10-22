"""Notes: create, list, search, tag."""

import sqlite3

from notes_svc.db import utc_now


def create_note(conn: sqlite3.Connection, user_id: int, title: str, body: str) -> int:
    """Save a note and return its id."""
    with conn:
        cur = conn.execute(
            "INSERT INTO notes (user_id, title, body, created_at) VALUES (?, ?, ?, ?)",
            (user_id, title, body, utc_now()),
        )
    return cur.lastrowid


def list_notes(conn: sqlite3.Connection, user_id: int, page: int = 1, per_page: int = 20) -> list[dict]:
    """One page of the user's notes, newest first."""
    offset = (page - 1) * per_page
    rows = conn.execute(
        "SELECT id, title, body, created_at FROM notes WHERE user_id = ? "
        "ORDER BY id DESC LIMIT ? OFFSET ?",
        (user_id, per_page, offset),
    ).fetchall()
    return [dict(r) for r in rows]


def search(conn: sqlite3.Connection, user_id: int, keyword: str) -> list[dict]:
    """Notes whose title or body contains `keyword`."""
    pattern = f"%{keyword}%"
    rows = conn.execute(
        "SELECT id, title, body FROM notes WHERE user_id = ? AND (title LIKE ? OR body LIKE ?)",
        (user_id, pattern, pattern),
    ).fetchall()
    return [dict(r) for r in rows]


def get_tags(conn: sqlite3.Connection, note_ids: list[int]) -> dict[int, list[str]]:
    """Tags for many notes in one query."""
    if not note_ids:
        return {}
    marks = ",".join("?" for _ in note_ids)
    rows = conn.execute(f"SELECT note_id, tag FROM tags WHERE note_id IN ({marks})", note_ids).fetchall()
    out: dict[int, list[str]] = {i: [] for i in note_ids}
    for r in rows:
        out[r["note_id"]].append(r["tag"])
    return out
