"""Plain-text log in data/app.log: startup problems, sound and notification errors, crashes.
Writing the log never raises, so logging cannot break the app."""
import traceback
from datetime import datetime

from config import DATA_DIR

LOG_FILE = DATA_DIR / "app.log"


def log(message: str) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {message}\n")
    except OSError:
        pass


def log_exception(where: str) -> None:
    log(f"{where}\n{traceback.format_exc()}")
