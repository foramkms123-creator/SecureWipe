"""Key/value application settings (per installation)."""
from database.connection import get_connection, transaction


def get(key: str, default: str | None = None) -> str | None:
    row = get_connection().execute(
        "SELECT value FROM app_settings WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row else default


def set(key: str, value: str) -> None:  # noqa: A001 - mirrors dict-style API
    with transaction() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
