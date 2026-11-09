"""Notifications for finished wipes and certificates.

Each notification does three things, all controlled in Settings > Notifications:
  1. adds an entry to the bell menu in the top bar (database),
  2. shows a banner at the top right of the screen (if banners are on),
  3. plays the sound chosen for that event (if not 'off').

The screen registers a listener with set_listener(); without one only the bell entry is added."""
from typing import Callable

from database import notifications_repo
from services import app_log, settings_service

# event -> (switch that turns it on, sound setting, banner title, banner colour)
EVENTS = {
    "wipe_done": ("notify_wipe_done", "sound_wipe_done", "Wipe completed", "ok"),
    "wipe_failed": ("notify_wipe_failed", "sound_wipe_failed", "Wipe stopped or failed", "bad"),
    "certificate": ("notify_certificate", "sound_certificate", "Certificate issued", "ok"),
}

# listener(title, message, kind, show_banner, sound) -- set by the app window
_listener: Callable | None = None


def set_listener(fn: Callable | None) -> None:
    global _listener
    _listener = fn


def notify(user_id: int, event: str, message: str) -> None:
    flag, sound_key, title, kind = EVENTS[event]
    prefs = settings_service.load()
    if not (prefs["notifications_enabled"] and prefs[flag]):
        return
    notifications_repo.add(user_id, message)
    if _listener is not None:
        try:
            _listener(title, message, kind, prefs["notify_banner"], prefs[sound_key])
        except Exception:
            app_log.log_exception(f"Showing the '{event}' notification failed")
