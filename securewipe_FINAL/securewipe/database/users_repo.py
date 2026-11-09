"""All SQL touching the users table."""
from datetime import datetime

from database.connection import get_connection, transaction


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def count_users() -> int:
    return get_connection().execute("SELECT COUNT(*) FROM users").fetchone()[0]


def get_by_username(username: str):
    return get_connection().execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()


def create_user(username: str, full_name: str, password_hash: str, role: str) -> int:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, full_name, password_hash, role, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, full_name, password_hash, role, _now()),
        )
        return cur.lastrowid


def record_failed_login(user_id: int, attempts: int, locked_until: str | None) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
            (attempts, locked_until, user_id),
        )


def record_successful_login(user_id: int) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login = ? "
            "WHERE id = ?",
            (_now(), user_id),
        )


def update_password(user_id: int, password_hash: str) -> None:
    with transaction() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
