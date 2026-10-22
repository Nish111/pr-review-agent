"""Internal admin report: row counts per table."""

import sqlite3

_TABLES = ("users", "notes", "tags")


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    counts = {}
    for table in _TABLES:
        sql = "SELECT COUNT(*) AS n FROM " + table
        counts[table] = conn.execute(sql).fetchone()["n"]
    return counts
