"""All SQL touching the notifications table."""
from datetime import datetime

from database.connection import get_connection, transaction


def add(user_id: int, message: str) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO notifications (user_id, message, created_at) VALUES (?, ?, ?)",
            (user_id, message, datetime.now().isoformat(timespec="seconds")),
        )


def unread_count(user_id: int) -> int:
    return get_connection().execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,)
    ).fetchone()[0]


def recent(user_id: int, limit: int = 10) -> list:
    return get_connection().execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


def mark_all_read(user_id: int) -> None:
    with transaction() as conn:
        conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
