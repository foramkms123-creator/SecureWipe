"""Central configuration. Change values here, not inside the UI code."""
from pathlib import Path

APP_NAME = "SecureWipe"
APP_VERSION = "1.0.0"

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "securewipe.db"          # final DB details to be supplied later

# Startup flow
SPLASH_DURATION_MS = 4000
ALWAYS_SHOW_ONBOARDING = False   # True = show intro + permissions on every launch

# Dashboard
TAGLINE = "Erase with confidence. Every wipe logged, every certificate on record."  # placeholder
REFRESH_INTERVAL_MS = 15000      # auto-refresh so changes by other users appear
LOG_ROW_LIMIT = 500
REPORT_ROW_LIMIT = 300           # Reports section: newest certificates shown

# Security
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 5
MIN_PASSWORD_LENGTH = 8

# Typography (Arial MT is exposed to Tk as "Arial")
FONT_FAMILY = "Arial"

# Palettes. LIGHT_COLORS is the original design; DARK_COLORS is the same tokens for dark mode.
# COLORS is the live palette that the screens read; ui/theme.apply_palette() switches it.
LIGHT_COLORS = {
    "bg": "#F5F8F6",
    "surface": "#FFFFFF",
    "border": "#E3EAE6",
    "text": "#1E2B28",
    "muted": "#74857F",
    "primary": "#23A487",        # logo teal
    "primary_hover": "#1B8A71",
    "orange": "#E8894A",         # logo orange
    "green": "#6DBB78",          # logo mid green
    "hero": "#E7F5EF",
    "nav_active": "#E7F5EF",
    "success": "#3E9E5C",
    "warning": "#C9851F",
    "danger": "#D9534F",
    "slate": "#3F7F93",
    # Wipe / Algorithms page: same greens as the sidebar
    "green_dark": "#0F9F6E",       # selected item, primary buttons, progress fill
    "green_dark_hover": "#0B8A5F",
    "green_light": "#EEF9F3",      # section headers, selected tiles, progress track
    "green_soft": "#DDF1E6",       # hover / borders on light green
    "row_alt": "#FAFCFB",          # every second table row
    "warn_bg": "#FDF3E4",          # warning banners
    "warn_text": "#7A4E12",
}

DARK_COLORS = {
    "bg": "#0F1A17",
    "surface": "#17251F",
    "border": "#2B3F38",
    "text": "#E8F3EE",
    "muted": "#9BB3AA",
    "primary": "#2BB896",
    "primary_hover": "#23A487",
    "orange": "#E8894A",
    "green": "#6DBB78",
    "hero": "#1D3A31",
    "nav_active": "#1D3A31",
    "success": "#4DB874",
    "warning": "#E0A53A",
    "danger": "#E5736F",
    "slate": "#5C9DB2",
    "green_dark": "#0F9F6E",
    "green_dark_hover": "#0B8A5F",
    "green_light": "#1B3A31",
    "green_soft": "#26493F",
    "row_alt": "#1A2B25",
    "warn_bg": "#3A2E18",
    "warn_text": "#F2C98A",
}

COLORS = dict(LIGHT_COLORS)

# Sidebar: top group, then empty space, then bottom group (just above the version).
# (key, label, icon name from ui/icons.py)
NAV_TOP = [
    ("dashboard", "Dashboard", "home"),
    ("algorithms", "Algorithms", "algorithm"),
    ("reports", "Reports", "document"),
]
NAV_BOTTOM = [
    ("settings", "Settings", "gear"),
    ("help", "Help", "help"),
    ("about", "About", "info"),
]

# Sidebar colours (mint panel, dark-green selected item)
SIDEBAR_LIGHT = {
    "bg": "#EEF9F3",
    "card": "#FFFFFF",
    "text": "#56645E",
    "hover": "#DDF1E6",
    "active": "#0F9F6E",
    "active_hover": "#0B8A5F",
    "active_text": "#FFFFFF",
}
SIDEBAR_DARK = {
    "bg": "#122520",
    "card": "#1B302A",
    "text": "#C5D9D0",
    "hover": "#22443A",
    "active": "#0F9F6E",
    "active_hover": "#0B8A5F",
    "active_text": "#FFFFFF",
}
SIDEBAR = dict(SIDEBAR_LIGHT)     # live copy, switched with COLORS

# Greeting line under "Hi, <name>": one random line per sign-in (ui/content/taglines.py)
TAGLINE_SHOW_EMOJI = True    # set False if emoji show as empty boxes on your PC

WIPE_STATUSES = ("SUCCESS", "SUCCESS_WITH_LIMITATIONS", "FAILED", "CANCELLED")

# Algorithms page (wipe setup)
MAX_CUSTOM_PASSES = 10           # upper limit for Zero Fill / One Fill / Random Data
NOMINAL_WIPE_SPEED_MB_S = 100    # used for the "Estimated time" shown before a wipe starts
SIMULATE_WIPE = False            # True = progress is simulated, NOTHING is written to disk
DEMO_MAX_SECONDS = 40            # a simulated wipe never takes longer than this
WRITE_CHUNK_MB = 8               # size of each write during a real wipe (tune per device, see notes)
REMOVE_AFTER_WIPE = False        # file/folder: delete the names after the bytes are overwritten
