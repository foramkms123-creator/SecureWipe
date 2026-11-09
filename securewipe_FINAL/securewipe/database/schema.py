"""Database schema and initialisation."""
from database.connection import transaction

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    full_name       TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'staff' CHECK (role IN ('admin', 'staff')),
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT,
    created_at      TEXT NOT NULL,
    last_login      TEXT
);

CREATE TABLE IF NOT EXISTS operations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users(id),
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    target_type      TEXT NOT NULL CHECK (target_type IN ('file', 'folder', 'drive')),
    target_name      TEXT NOT NULL,
    target_path      TEXT NOT NULL,
    algorithm        TEXT NOT NULL,
    passes           INTEGER NOT NULL,
    status           TEXT NOT NULL CHECK (status IN
                     ('SUCCESS', 'SUCCESS_WITH_LIMITATIONS', 'FAILED', 'CANCELLED')),
    report_generated INTEGER NOT NULL DEFAULT 0,
    certificate_path TEXT,
    certificate_issued_at TEXT,      -- when the certificate was generated (ISO 8601)
    total_size       INTEGER,        -- bytes overwritten, measured before the wipe
    items_json       TEXT            -- {"items": [{name, type, size}], "skipped": n, "simulated": bool}
);
CREATE INDEX IF NOT EXISTS idx_ops_user_time ON operations(user_id, started_at);

CREATE TABLE IF NOT EXISTS notifications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    message    TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_read    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, is_read);

CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


# Columns added after the first release. CREATE TABLE only runs for new databases,
# so an existing database gets the missing columns here (ALTER TABLE).
ADDED_OPERATION_COLUMNS = {
    "certificate_issued_at": "TEXT",
    "total_size": "INTEGER",
    "items_json": "TEXT",
}


def init_db() -> None:
    with transaction() as conn:
        conn.executescript(SCHEMA)
        have = {row[1] for row in conn.execute("PRAGMA table_info(operations)")}
        for name, ddl in ADDED_OPERATION_COLUMNS.items():
            if name not in have:
                conn.execute(f"ALTER TABLE operations ADD COLUMN {name} {ddl}")
