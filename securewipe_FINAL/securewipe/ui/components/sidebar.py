"""Left navigation: logo, '+' New Erasure Task, top nav group, space, bottom nav group."""
import tkinter as tk

import customtkinter as ctk

from config import APP_NAME, APP_VERSION, FONT_FAMILY, NAV_BOTTOM, NAV_TOP, SIDEBAR
from ui import assets
from ui.components.popup import popup_below
from ui.icons import icon
from ui.theme import C, font

S = SIDEBAR


class Sidebar(ctk.CTkFrame):
    WIDTH = 250

    def __init__(self, master, on_navigate, on_new_wipe):
        super().__init__(master, width=self.WIDTH, fg_color=S["bg"], corner_radius=0)
        self.grid_propagate(False)
        self.pack_propagate(False)
        self._on_navigate = on_navigate
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._icons: dict[str, tuple] = {}   # key -> (normal icon, selected icon)

        # logo + name
        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(22, 24))
        ctk.CTkLabel(brand, text="", image=assets.logo(58)).pack(side="left")
        ctk.CTkLabel(brand, text=APP_NAME, font=font(20, bold=True),
                     text_color=C["text"]).pack(side="left", padx=10)

        # "+" New Erasure Task
        # Grid: column 0 (text) takes all free space, column 1 holds the + button.
        new = ctk.CTkFrame(self, fg_color=S["card"], corner_radius=14, height=84)
        new.pack(fill="x", padx=14, pady=(0, 22))
        new.grid_propagate(False)                     # keep the taller fixed height
        new.grid_columnconfigure(0, weight=1)
        new.grid_rowconfigure(0, weight=1)
        ctk.CTkLabel(new, text="New Erasure Task", font=font(14, bold=True),
                     text_color=C["text"], wraplength=140, justify="center"
                     ).grid(row=0, column=0, padx=(12, 6))        # centred; wraps, never cuts
        self._plus = ctk.CTkButton(new, text="", image=icon("plus", S["active_text"], 16),
                                   width=40, height=40, corner_radius=20,
                                   fg_color=S["active"], hover_color=S["active_hover"],
                                   command=self._open_new_menu)
        self._plus.grid(row=0, column=1, padx=(0, 14))

        self._menu = tk.Menu(self, tearoff=0, font=(FONT_FAMILY, 11))
        self._menu.add_command(label="Select a file…", command=lambda: on_new_wipe("file"))
        self._menu.add_command(label="Select a folder…", command=lambda: on_new_wipe("folder"))
        self._menu.add_command(label="Select a drive…", command=lambda: on_new_wipe("drive"))

        # top group
        for key, label, icon_name in NAV_TOP:
            self._make_button(key, label, icon_name).pack(fill="x", padx=14, pady=3)

        # bottom group: version first, then items bottom-up, so About sits just above it
        ctk.CTkLabel(self, text=f"Version {APP_VERSION}\nNIST SP 800-88 aligned",
                     font=font(10), text_color=S["text"], justify="left"
                     ).pack(side="bottom", anchor="w", padx=24, pady=(10, 18))
        for key, label, icon_name in reversed(NAV_BOTTOM):
            self._make_button(key, label, icon_name).pack(side="bottom", fill="x", padx=14, pady=3)

    def _make_button(self, key: str, label: str, icon_name: str) -> ctk.CTkButton:
        self._icons[key] = (icon(icon_name, S["text"]), icon(icon_name, S["active_text"]))
        btn = ctk.CTkButton(self, text=f"  {label}", image=self._icons[key][0], compound="left",
                            anchor="w", height=46, corner_radius=12, border_spacing=12,
                            font=font(14), fg_color="transparent", hover_color=S["hover"],
                            text_color=S["text"], command=lambda k=key: self._on_navigate(k))
        self._buttons[key] = btn
        return btn

    def _open_new_menu(self):
        popup_below(self._menu, self._plus)

    def set_active(self, key: str) -> None:
        for k, btn in self._buttons.items():
            on = k == key
            btn.configure(
                fg_color=S["active"] if on else "transparent",
                hover_color=S["active_hover"] if on else S["hover"],
                text_color=S["active_text"] if on else S["text"],
                image=self._icons[k][1 if on else 0],
                font=font(14, bold=on),
            )
