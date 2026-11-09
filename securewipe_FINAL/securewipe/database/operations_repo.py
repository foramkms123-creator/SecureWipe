"""All SQL touching the operations (wipe log) table.

user_id=None means "all users" (admin scope)."""
from database.connection import get_connection, transaction

SUCCESS_STATES = ("SUCCESS", "SUCCESS_WITH_LIMITATIONS")
FAILED_STATES = ("FAILED", "CANCELLED")


def _scope(user_id):
    return ("WHERE o.user_id = ?", (user_id,)) if user_id is not None else ("", ())


def add_operation(user_id, started_at, finished_at, target_type, target_name,
                  target_path, algorithm, passes, status, report_generated=False,
                  certificate_path=None, total_size=None, items_json=None,
                  certificate_issued_at=None) -> int:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO operations (user_id, started_at, finished_at, target_type, "
            "target_name, target_path, algorithm, passes, status, report_generated, "
            "certificate_path, total_size, items_json, certificate_issued_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (user_id, started_at, finished_at, target_type, target_name, target_path,
             algorithm, passes, status, int(report_generated), certificate_path,
             total_size, items_json, certificate_issued_at),
        )
        return cur.lastrowid


def mark_certificate(op_id: int, issued_at: str) -> None:
    """A logged wipe got its certificate: the Report column shows Yes from now on."""
    with transaction() as conn:
        conn.execute(
            "UPDATE operations SET report_generated = 1, certificate_issued_at = ? WHERE id = ?",
            (issued_at, op_id),
        )


def get_operation(op_id: int):
    """One operation with the name of the user who ran it (None if it does not exist)."""
    return get_connection().execute(
        "SELECT o.*, u.username, u.full_name FROM operations o "
        "JOIN users u ON u.id = o.user_id WHERE o.id = ?",
        (op_id,),
    ).fetchone()


def get_report_rows(user_id=None, limit: int = 300) -> list:
    """Operations that have a certificate (report_generated = 1), newest first.
    user_id=None returns every user's reports (admin)."""
    clauses, params = ["o.report_generated = 1"], []
    if user_id is not None:
        clauses.append("o.user_id = ?")
        params.append(user_id)
    params.append(limit)
    return get_connection().execute(
        "SELECT o.*, u.username, u.full_name FROM operations o "
        "JOIN users u ON u.id = o.user_id "
        f"WHERE {' AND '.join(clauses)} "
        "ORDER BY COALESCE(o.certificate_issued_at, o.finished_at, o.started_at) DESC, o.id DESC "
        "LIMIT ?",
        params,
    ).fetchall()


def get_summary(user_id=None) -> dict:
    where, params = _scope(user_id)
    row = get_connection().execute(
        f"""SELECT COUNT(*) AS total,
                   COALESCE(SUM(o.report_generated), 0) AS reports,
                   COALESCE(SUM(o.status IN {SUCCESS_STATES}), 0) AS successful,
                   COALESCE(SUM(o.status IN {FAILED_STATES}), 0) AS failed
            FROM operations o {where}""",
        params,
    ).fetchone()
    return dict(row)


def get_algorithm_usage(user_id=None) -> list[tuple[str, int]]:
    where, params = _scope(user_id)
    rows = get_connection().execute(
        f"SELECT o.algorithm, COUNT(*) AS n FROM operations o {where} "
        "GROUP BY o.algorithm ORDER BY n DESC",
        params,
    ).fetchall()
    return [(r["algorithm"], r["n"]) for r in rows]


def get_logs(user_id=None, search: str = "", limit: int = 500) -> list:
    where, params = _scope(user_id)
    params = list(params)
    if search:
        clause = ("(o.target_name LIKE ? OR o.target_path LIKE ? "
                  "OR o.algorithm LIKE ? OR o.status LIKE ? OR u.username LIKE ?)")
        where = f"{where} AND {clause}" if where else f"WHERE {clause}"
        params += [f"%{search}%"] * 5
    params.append(limit)
    return get_connection().execute(
        f"""SELECT o.*, u.username FROM operations o
            JOIN users u ON u.id = o.user_id
            {where} ORDER BY o.started_at DESC LIMIT ?""",
        params,
    ).fetchall()
