"""Shapes database rows into what the dashboard displays.
Admins see every user's operations; staff see their own."""
from dataclasses import dataclass
from datetime import datetime

from config import LOG_ROW_LIMIT
from database import notifications_repo, operations_repo
from services import settings_service
from services.auth_service import User


@dataclass
class Overview:
    reports: int
    total: int
    successful: int
    failed: int
    algorithms: list[tuple[str, int]]


@dataclass
class LogRow:
    date: str
    day: str
    time: str
    user: str
    file_name: str
    location: str
    algorithm: str
    passes: int
    status: str
    report: str


def _scope(user: User):
    return None if user.is_admin else user.id


def get_overview(user: User) -> Overview:
    s = operations_repo.get_summary(_scope(user))
    return Overview(s["reports"], s["total"], s["successful"], s["failed"],
                    operations_repo.get_algorithm_usage(_scope(user)))


def get_log_rows(user: User, search: str = "") -> list[LogRow]:
    rows = []
    for r in operations_repo.get_logs(_scope(user), search.strip(), LOG_ROW_LIMIT):
        ts = datetime.fromisoformat(r["started_at"])
        rows.append(LogRow(
            date=settings_service.format_date(ts), day=ts.strftime("%A"), time=ts.strftime("%H:%M:%S"),
            user=r["username"], file_name=r["target_name"], location=r["target_path"],
            algorithm=r["algorithm"], passes=r["passes"],
            status=r["status"].replace("_", " ").title(),
            report="Yes" if r["report_generated"] else "No",
        ))
    return rows


def get_notifications(user: User):
    return notifications_repo.unread_count(user.id), notifications_repo.recent(user.id)


def mark_notifications_read(user: User) -> None:
    notifications_repo.mark_all_read(user.id)
