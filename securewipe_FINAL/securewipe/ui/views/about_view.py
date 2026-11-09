"""About page: app info, standards, team and support (text lives in ui/content/about_text.py)."""
import webbrowser
from tkinter import messagebox

import customtkinter as ctk

from config import APP_NAME, APP_VERSION, SIDEBAR
from ui import assets
from ui.components.license_dialog import LicenseDialog
from ui.components.scroll_frame import ScrollFrame
from ui.content import about_text as T
from ui.light import Box, Label
from ui.theme import C, font

PANEL_PAD = 24                     # inner left/right padding of the light green boxes
REWRAP_DELAY_MS = 120              # re-wrap text once, after resizing stops


class AboutView(ctk.CTkFrame):
    title = "About SecureWipe"

    def __init__(self, master, on_close=None):
        super().__init__(master, fg_color=C["surface"], corner_radius=20)
        self._on_close = on_close
        self._wrapped: list[tuple[Label, int]] = []   # (label, space taken on the left/right)
        self._wrap_job = None
        self._wrap_width = 0
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Fast scroll area (CTkScrollableFrame repainted every widget on every wheel tick)
        scroll = ScrollFrame(self, bg=C["surface"], bar_color=SIDEBAR["hover"], bar_hover=C["green_dark"])
        scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        scroll.inner.grid_columnconfigure(0, weight=1)

        self._body = Box(scroll.inner, bg=C["surface"])
        self._body.grid(row=0, column=0, sticky="ew", padx=30, pady=(22, 28))
        self._body.bind("<Configure>", self._on_resize)

        self._build()

    # ---- layout -----------------------------------------------------------
    def _build(self):
        b = self._body

        # logo + name + version, in a light green box
        top = self._panel(b, pady=(0, 18))
        top.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(top, text="", image=assets.logo(80)
                     ).grid(row=0, column=0, rowspan=2, padx=(PANEL_PAD, 20), pady=22)
        Label(top, text=APP_NAME, size=28, bold=True, color=C["green_dark"], bg=SIDEBAR["bg"]
              ).grid(row=0, column=1, sticky="sw", pady=(24, 0))
        Label(top, text=f"Version {APP_VERSION}   ·   Build {T.BUILD}", color=C["muted"], bg=SIDEBAR["bg"]
              ).grid(row=1, column=1, sticky="nw", pady=(4, 24))

        self._para(b, T.DESCRIPTION)

        self._heading(b, "Our purpose")
        self._para(b, T.PURPOSE)

        self._heading(b, "Standards")
        for line in T.STANDARDS:
            self._bullet(b, line)

        self._heading(b, "Built with")
        self._para(b, T.BUILT_WITH)

        # developed by, in a light green box
        team = self._panel(b, pady=(26, 0))
        self._heading(team, "Developed by", top=18, padx=PANEL_PAD)
        for name in T.TEAM:                                          # team members: 14 bold
            Label(team, text=name, size=14, bold=True, color=C["primary"], bg=SIDEBAR["bg"]
                  ).pack(fill="x", padx=PANEL_PAD, pady=1)
        self._para(team, T.DEPARTMENT, padx=PANEL_PAD, pady=(10, 2), color=C["primary"],
                   offset=2 * PANEL_PAD)
        guide = Box(team, bg=SIDEBAR["bg"])
        guide.pack(fill="x", padx=PANEL_PAD, pady=(4, 20))
        Label(guide, text="Project guide:", size=14, color=C["primary"], bg=SIDEBAR["bg"]
              ).pack(side="left")
        Label(guide, text=T.GUIDE, size=16, bold=True, color=C["primary"], bg=SIDEBAR["bg"]
              ).pack(side="left", padx=(6, 0))                       # guide: 16 bold, bigger

        self._heading(b, "Support")
        row = Box(b)
        row.pack(fill="x")
        Label(row, text="Email:").pack(side="left")
        link = Label(row, text=T.SUPPORT_EMAIL, bold=True, color=C["green_dark"], cursor="hand2")
        link.pack(side="left", padx=(6, 0))
        link.bind("<Button-1>", lambda _e: webbrowser.open(f"mailto:{T.SUPPORT_EMAIL}"))

        self._heading(b, "License")
        self._para(b, T.LICENSE_SHORT)

        self._heading(b, "Disclaimer")
        self._para(b, T.DISCLAIMER)

        # buttons
        btns = Box(b)
        btns.pack(fill="x", pady=(28, 0))
        self._button(btns, "Check for updates", self._check_updates, filled=False)
        self._button(btns, "View license", self._view_license, filled=False)
        self._button(btns, "Close", self._close, filled=True)

    # ---- building blocks --------------------------------------------------
    def _panel(self, parent, pady):
        box = ctk.CTkFrame(parent, fg_color=SIDEBAR["bg"], corner_radius=16,
                           border_width=1, border_color=SIDEBAR["hover"])
        box.pack(fill="x", pady=pady)
        return box

    def _heading(self, parent, text, top=26, padx=0):
        Label(parent, text=text, size=17, bold=True, color=C["green_dark"]
              ).pack(fill="x", padx=padx, pady=(top, 6))

    def _para(self, parent, text, padx=0, pady=(0, 0), color=None, offset=0):
        lbl = Label(parent, text=text, color=color or C["text"], wrap=700)
        lbl.pack(fill="x", padx=padx, pady=pady)
        self._wrapped.append((lbl, offset))

    def _bullet(self, parent, text):
        row = Box(parent)
        row.pack(fill="x", pady=2)
        Label(row, text="•", size=15, bold=True, color=C["green_dark"], anchor="n", width=2
              ).pack(side="left", anchor="n")
        lbl = Label(row, text=text, wrap=680)
        lbl.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self._wrapped.append((lbl, 26))

    def _button(self, parent, text, command, filled):
        ctk.CTkButton(parent, text=text, command=command, height=38, corner_radius=10,
                      font=font(13, bold=filled), width=150,
                      fg_color=C["green_dark"] if filled else C["surface"],
                      hover_color="#095A40" if filled else SIDEBAR["bg"],
                      text_color="white" if filled else C["green_dark"],
                      border_width=0 if filled else 1, border_color=C["green_dark"]
                      ).pack(side="right", padx=(10, 0))

    def _on_resize(self, event):
        # Tk labels don't wrap by themselves: re-wrap every paragraph to the current width.
        # Done once after resizing settles (not on every resize event), and only if the
        # width really changed - this was the main cause of lag when maximising.
        if event.width == self._wrap_width:
            return
        self._wrap_width = event.width
        if self._wrap_job:
            self.after_cancel(self._wrap_job)
        self._wrap_job = self.after(REWRAP_DELAY_MS, self._rewrap)

    def _rewrap(self):
        self._wrap_job = None
        scale = self._get_widget_scaling()
        for lbl, offset in self._wrapped:
            lbl.set_wrap(max(int(self._wrap_width - (offset + 8) * scale), 200))

    def destroy(self):
        if self._wrap_job:
            self.after_cancel(self._wrap_job)
        super().destroy()

    # ---- actions ----------------------------------------------------------
    def _check_updates(self):
        messagebox.showinfo(
            "Check for updates",
            f"You are using {APP_NAME} {APP_VERSION} (build {T.BUILD}).\n\n"
            f"Online update checks are not available yet. For the latest version, "
            f"contact {T.SUPPORT_EMAIL}.")

    def _view_license(self):
        LicenseDialog(self)

    def _close(self):
        if self._on_close:
            self._on_close()