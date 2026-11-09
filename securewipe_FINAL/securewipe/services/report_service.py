"""Reports section: the list of issued certificates and the lookup of one certificate.

Admins see every user's reports; staff see their own (same rule as the dashboard)."""
from dataclasses import dataclass

from database import operations_repo
from services import certificate
from services.auth_service import User


@dataclass(frozen=True)
class ReportRow:
    op_id: int
    report_id: str
    target: str
    method: str            # "Zero Fill (1 pass)"
    issued: str            # "11 Oct 2026, 05:42 PM" (certificate issue date and time)


def _scope(user: User):
    return None if user.is_admin else user.id


def list_reports(user: User, search: str = "") -> list[ReportRow]:
    needle = search.strip().lower()
    rows = []
    for r in operations_repo.get_report_rows(_scope(user)):
        cert = certificate.from_row(r)
        row = ReportRow(
            op_id=cert.op_id,
            report_id=cert.report_id,
            target=cert.target_name,
            method=cert.method_label,
            issued=certificate.format_datetime(cert.issued_at),
        )
        searchable = " ".join((row.report_id, row.target, row.method, row.issued,
                               *(name for name, _, _ in cert.items))).lower()
        if needle and needle not in searchable:
            continue
        rows.append(row)
    return rows


def get_certificate(user: User, op_id: int) -> certificate.CertificateData | None:
    """The certificate for one report, or None if it does not exist or belongs to someone else."""
    r = operations_repo.get_operation(op_id)
    if r is None or not r["report_generated"]:
        return None
    if not user.is_admin and r["user_id"] != user.id:
        return None
    return certificate.from_row(r)
