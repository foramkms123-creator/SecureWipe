"""OS-level checks: admin rights, elevation, onboarding state."""
import ctypes
import json
import os
import sys

from config import ALWAYS_SHOW_ONBOARDING
from database import settings_repo


def is_windows() -> bool:
    return os.name == "nt"


def is_admin() -> bool:
    try:
        if is_windows():
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    """Windows only: restart this program with a UAC prompt. Returns True if launched."""
    if not is_windows():
        return False
    params = " ".join(f'"{a}"' for a in sys.argv)
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    return rc > 32


def onboarding_required() -> bool:
    return ALWAYS_SHOW_ONBOARDING or settings_repo.get("onboarding_done") != "1"


def save_permissions(optional: dict[str, bool], done: bool = True) -> None:
    """Stores the optional choices. done=False keeps the permissions page open at the next start."""
    settings_repo.set("optional_permissions", json.dumps(optional))
    settings_repo.set("onboarding_done", "1" if done else "0")


def load_permissions() -> dict[str, bool]:
    return json.loads(settings_repo.get("optional_permissions", "{}"))
