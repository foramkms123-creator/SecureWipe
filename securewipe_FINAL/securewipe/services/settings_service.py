"""Preferences from the Settings page.

Stored as one JSON value in app_settings (one set of preferences per installation).
Every reader goes through load(), which fills in defaults for anything missing or invalid."""
import json
import sys
from datetime import datetime
from pathlib import Path

from config import APP_NAME, BASE_DIR
from database import settings_repo
from services import app_log
from services.system_service import is_windows

_KEY = "preferences"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
# Windows keeps a separate on/off flag for every startup entry (Task Manager > Startup apps).
# If the user once turned SecureWipe off there, the Run value alone does nothing.
APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
_APPROVED_BYTES = bytes([2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])   # 02 = enabled
DEFAULT_REPORTS_DIR = Path.home() / "SecureWipe" / "Reports"

# key -> default value (the type of each default is the type that is accepted on load)
DEFAULTS = {
    "theme": "light",                 # light | dark | system
    "date_format": "uk_numeric",      # see DATE_FORMATS
    "launch_at_startup": False,
    "password_policy": "standard",    # standard | strong
    "auto_lock_minutes": 10,          # one of AUTO_LOCK_MINUTES
    "require_password": False,        # ask for the password before a wipe starts
    "default_method": "dod",          # key from services/wipe_methods.py
    "reports_folder": "",             # "" = DEFAULT_REPORTS_DIR
    "auto_certificate": False,        # create and save the PDF as soon as a wipe succeeds
    "notifications_enabled": True,    # master switch for the bell and the banners
    "notify_banner": True,            # pop-up banner at the top of the screen
    "notify_wipe_done": True,
    "notify_wipe_failed": True,
    "notify_certificate": True,
    "sound_wipe_done": "chime",       # chime | success | alert | off
    "sound_wipe_failed": "alert",
    "sound_certificate": "success",
}

THEMES = {"light": "Light", "dark": "Dark", "system": "System"}
SOUND_CHOICES = ("chime", "success", "alert", "off")
SOUND_KEYS = ("sound_wipe_done", "sound_wipe_failed", "sound_certificate")

# key -> (label shown in the dropdown, strftime pattern for dates)
DATE_FORMATS = {
    "us_numeric": ("10/11/2026  (US)", "%m/%d/%Y"),
    "us_written": ("Oct 11, 2026  (US)", "%b %d, %Y"),
    "uk_numeric": ("11/10/2026  (British)", "%d/%m/%Y"),
    "uk_written": ("11 October 2026  (British)", "%d %B %Y"),
    "iso": ("2026-10-11  (Worldwide, ISO)", "%Y-%m-%d"),
    "world_written": ("11 Oct 2026  (Worldwide)", "%d %b %Y"),
}

AUTO_LOCK_MINUTES = (10, 20, 30, 60)
AUTO_LOCK_LABELS = {10: "10 minutes", 20: "20 minutes", 30: "30 minutes", 60: "1 hour"}

PASSWORD_POLICIES = {
    "standard": "Standard  (8+ characters, letters and numbers)",
    "strong": "Strong  (12+ characters, upper and lower case, number, symbol)",
}


def load() -> dict:
    try:
        stored = json.loads(settings_repo.get(_KEY, "{}") or "{}")
    except (ValueError, TypeError):
        stored = {}
    prefs = dict(DEFAULTS)
    for key, default in DEFAULTS.items():
        value = stored.get(key)
        if isinstance(value, type(default)):
            prefs[key] = value
    # keep choices inside the allowed lists
    if prefs["theme"] not in THEMES:
        prefs["theme"] = DEFAULTS["theme"]
    if prefs["date_format"] not in DATE_FORMATS:
        prefs["date_format"] = DEFAULTS["date_format"]
    if prefs["password_policy"] not in PASSWORD_POLICIES:
        prefs["password_policy"] = DEFAULTS["password_policy"]
    if prefs["auto_lock_minutes"] not in AUTO_LOCK_MINUTES:
        prefs["auto_lock_minutes"] = DEFAULTS["auto_lock_minutes"]
    for key in SOUND_KEYS:
        if prefs[key] not in SOUND_CHOICES:
            prefs[key] = DEFAULTS[key]
    return prefs


def save(prefs: dict) -> None:
    data = dict(DEFAULTS)
    data.update({k: v for k, v in prefs.items() if k in DEFAULTS})
    settings_repo.set(_KEY, json.dumps(data))


def get(key: str):
    return load()[key]


def resolve_theme(theme: str) -> str:
    """'light' or 'dark'. 'system' follows the Windows app theme (light if unknown)."""
    if theme in ("light", "dark"):
        return theme
    return "dark" if _windows_prefers_dark() else "light"


def _windows_prefers_dark() -> bool:
    if not is_windows():
        return False
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        try:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        finally:
            winreg.CloseKey(key)
        return value == 0
    except OSError:
        return False


def defaults() -> dict:
    return dict(DEFAULTS)


# ---- dates ----------------------------------------------------------------------
def format_date(value: datetime) -> str:
    return value.strftime(DATE_FORMATS[get("date_format")][1])


def format_datetime(value: datetime) -> str:
    return f"{format_date(value)}, {value:%I:%M %p}"


# ---- reports folder -------------------------------------------------------------
def reports_dir() -> Path:
    custom = get("reports_folder").strip()
    return Path(custom) if custom else DEFAULT_REPORTS_DIR


# ---- launch at Windows start ----------------------------------------------------
def set_launch_at_startup(enabled: bool) -> None:
    """Adds or removes SecureWipe from the current user's Windows startup list, and marks the
    entry as enabled in Task Manager. Does nothing on other systems."""
    if not is_windows():
        return
    import winreg
    run = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
    try:
        if enabled:
            winreg.SetValueEx(run, APP_NAME, 0, winreg.REG_SZ, _startup_command())
        else:
            _delete_value(run)
    finally:
        winreg.CloseKey(run)

    approved = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, APPROVED_KEY, 0, winreg.KEY_SET_VALUE)
    try:
        if enabled:
            winreg.SetValueEx(approved, APP_NAME, 0, winreg.REG_BINARY, _APPROVED_BYTES)
        else:
            _delete_value(approved)
    finally:
        winreg.CloseKey(approved)


def _delete_value(key) -> None:
    import winreg
    try:
        winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass


def startup_entry_present() -> bool:
    if not is_windows():
        return False
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        finally:
            winreg.CloseKey(key)
    except OSError:
        return False


def sync_startup_entry() -> None:
    """Runs at every start (after the database is ready). Re-writes the startup entry while the
    setting is on, so a moved install folder or a Task Manager 'disabled' flag is corrected, and
    removes a leftover entry when the setting is off. Problems go to data/app.log."""
    if not is_windows():
        return
    try:
        enabled = load()["launch_at_startup"]
        if enabled or startup_entry_present():
            set_launch_at_startup(enabled)
    except OSError:
        app_log.log_exception("Windows startup entry could not be updated")


def _startup_command() -> str:
    exe = Path(sys.executable)
    if getattr(sys, "frozen", False):                  # packaged .exe
        return f'"{exe}"'
    pyw = exe.with_name("pythonw.exe")                 # no console window at startup
    runner = pyw if pyw.exists() else exe
    return f'"{runner}" "{BASE_DIR / "main.py"}"'
