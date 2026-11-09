"""Fonts, colours and ttk styling shared by every screen."""
from functools import lru_cache
from tkinter import ttk

import customtkinter as ctk

from config import COLORS, DARK_COLORS, FONT_FAMILY, LIGHT_COLORS, SIDEBAR, SIDEBAR_DARK, SIDEBAR_LIGHT

C = COLORS


def apply_palette(mode: str, root=None) -> None:
    """Switch every screen to 'light' or 'dark'. Screens read COLORS / SIDEBAR when they are
    built, so the caller must rebuild the visible screens afterwards (app.rebuild_dashboard).
    `root` is needed to restyle the ttk tables."""
    dark = mode == "dark"
    COLORS.update(DARK_COLORS if dark else LIGHT_COLORS)
    SIDEBAR.update(SIDEBAR_DARK if dark else SIDEBAR_LIGHT)
    ctk.set_appearance_mode("dark" if dark else "light")   # CTk defaults follow the same mode
    if root is not None:
        apply_ttk_styles(root)


@lru_cache(maxsize=None)
def font(size: int = 13, bold: bool = False, italic: bool = False) -> ctk.CTkFont:
    """Shared font objects: one per (size, bold, italic) instead of one per widget.
    (Creating 100+ separate fonts was a large part of the slow screen switches.)"""
    return ctk.CTkFont(family=FONT_FAMILY, size=size,
                       weight="bold" if bold else "normal",
                       slant="italic" if italic else "roman")


def lighten(hex_color: str, amount: float = 0.25) -> str:
    """Mix a colour with white (used for icon tiles on coloured cards)."""
    hex_color = hex_color.lstrip("#")
    rgb = [int(hex_color[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{int(v + (255 - v) * amount):02x}" for v in rgb)


def apply_ttk_styles(root) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("SW.Treeview", font=(FONT_FAMILY, 10), rowheight=32,
                    background=C["surface"], fieldbackground=C["surface"],
                    foreground=C["text"], bordercolor=C["border"], borderwidth=0)
    style.configure("SW.Treeview.Heading", font=(FONT_FAMILY, 10, "bold"),
                    background=C["bg"], foreground=C["muted"], relief="flat", padding=(8, 8))
    style.map("SW.Treeview", background=[("selected", C["hero"])],
              foreground=[("selected", C["text"])])
    style.map("SW.Treeview.Heading", background=[("active", C["hero"])])
