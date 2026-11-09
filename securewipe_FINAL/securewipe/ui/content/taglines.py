"""Greeting lines shown one at a time under "Hi, <name>" on the dashboard.
Add, remove or edit lines freely."""
import random
import re

from config import TAGLINE_SHOW_EMOJI
from database import settings_repo

TAGLINES = [
    "Ready to make your data disappear—safely? 🫥🔐",
    "Ready to wipe it clean and leave no traces? 🧹💾",
    "Got data to delete? Let’s make it vanish! ✨",
    "Ready to say goodbye to your old data? 👋💻",
    "Clean data, clear mind. Ready to wipe? 🧼🔒",
    "Ready to give your data the ultimate goodbye? 💀💾",
    "Time to wipe, protect, and move on! 🔐✨",
    "Ready to wave goodbye to your old data? 👋💾",
    "Ready to leave your old data in the past? ✨",
    "Ready to give your old data a fresh goodbye? 💻👋",
    "Ready to clear out the old and make space for new? 🧹",
    "Ready to wipe away the past? 🫧",
    "Ready to send your old data packing? 📦💾",
    "Ready to let your old data go? 🌱",
    "Ready for a clean slate? ✨",
    "Ready to wipe the slate clean? 🧼",
    "Ready to say goodbye and wipe it clean? 👋🔐",
    "Ready to erase the old and start fresh? 🔄",
    "Ready to give your data a proper farewell? 🥹💾",
    "Ready to make your old data history? 📜",
    "Ready to clean house and clear your data? 🧹💻",
    "Ready to say goodbye to data you no longer need? 👋",
    "Say goodbye to your data as your ex said to you",
    "Delete your data. Unlike your ex, it won't come back.",
    "Your data deserves a cleaner breakup than your ex gave you.",
    "No hard feelings. Just a permanent goodbye.",
]

_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]+")


def display_lines() -> list[str]:
    if TAGLINE_SHOW_EMOJI:
        return TAGLINES
    return [_EMOJI.sub("", line).strip() for line in TAGLINES]


def pick_for_login() -> str:
    """One random line per sign-in. Never the same as the previous sign-in
    (the last choice is saved in the database, so this holds after restarts too)."""
    lines = display_lines()
    last = settings_repo.get("last_tagline_index")
    choices = [i for i in range(len(lines)) if str(i) != last] or [0]
    index = random.choice(choices)
    settings_repo.set("last_tagline_index", str(index))
    return lines[index]
