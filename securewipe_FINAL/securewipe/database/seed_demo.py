"""Fill the log with sample rows so the dashboard can be demoed.

Usage (after creating at least one account):  python -m database.seed_demo
"""
import json
import random
from datetime import datetime, timedelta

from database import operations_repo, users_repo
from database.connection import get_connection
from database.schema import init_db

SAMPLES = [
    ("file", "salary_2025.xlsx", r"D:\HR\Payroll"),
    ("file", "client_contracts.pdf", r"C:\Users\Public\Documents"),
    ("folder", "Old_Projects", r"E:\Archive"),
    ("drive", "SanDisk Ultra 32GB", "F:\\"),
    ("file", "backup_2024.zip", r"D:\Backups"),
    ("folder", "Scans", r"C:\Users\Public\Pictures"),
]

ALGORITHMS = [
    ("Zero Fill", 1),
    ("One Fill", 1),
    ("Random Data", 1),
    ("DoD 5220.22-M", 3),
    ("Random Data", 3),
    ("Gutmann", 35)
]



def main() -> None:
    init_db()
    if users_repo.count_users() == 0:
        print("Create an account in the app first.")
        return
    user_ids = [r[0] for r in get_connection().execute("SELECT id FROM users")]
    now = datetime.now()
    for i in range(18):
        kind, name, path = random.choice(SAMPLES)
        algo, passes = random.choice(ALGORITHMS)
        start = now - timedelta(hours=i * 7 + random.randint(0, 5))
        status = random.choices(
            ["SUCCESS", "SUCCESS_WITH_LIMITATIONS", "FAILED", "CANCELLED"], [6, 3, 1, 1])[0]
        size = random.randint(1, 900) * 1024 * 1024 if kind != "file" else random.randint(
            10, 900) * 1024
        finished = start + timedelta(minutes=random.randint(1, 90))
        ok = status.startswith("SUCCESS")
        payload = {"items": [{"name": name, "type": kind.title(), "size": size}],
                   "skipped": 0, "simulated": False}
        operations_repo.add_operation(
            random.choice(user_ids), start.isoformat(timespec="seconds"),
            finished.isoformat(timespec="seconds"),
            kind, name, path, algo, passes, status,
            report_generated=ok,
            total_size=size,
            items_json=json.dumps(payload),
            certificate_issued_at=finished.isoformat(timespec="seconds") if ok else None,
        )
    print("Inserted 18 demo operations.")


if __name__ == "__main__":
    main()
