"""Token authentication."""

import hmac
import sqlite3


def check_token(conn: sqlite3.Connection, user_id: int, token: str) -> bool:
    """True if `token` is the user's token. Constant-time comparison."""
    row = conn.execute("SELECT token FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return False
    return hmac.compare_digest(row["token"], token)
