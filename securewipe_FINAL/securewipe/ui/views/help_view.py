"""Help page: team contact email and basic FAQs (text lives in ui/content/help_text.py)."""
import webbrowser

import customtkinter as ctk

from ui.components.scroll_frame import ScrollFrame
from ui.content import help_text as T
from ui.light import Box, Label
from ui.theme import C

PANEL_PAD = 20                     # inner left/right padding of the light green boxes
REWRAP_DELAY_MS = 120              # re-wrap text once, after resizing stops


class HelpView(ctk.CTkFrame):
    title = "Help"

    def __init__(self, master, on_close=None):
        super().__init__(master, fg_color=C["surface"], corner_radius=20)
        self._on_close = on_close
        self._wrapped: list[tuple[Label, int]] = []   # (label, space taken on the left/right)
        self._wrap_job = None
        self._wrap_width = 0
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        scroll = ScrollFrame(self, bg=C["surface"], bar_color=C["green_soft"], bar_hover=C["green_dark"])
        scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        scroll.inner.grid_columnconfigure(0, weight=1)

        self._body = Box(scroll.inner, bg=C["surface"])
        self._body.grid(row=0, column=0, sticky="ew", padx=30, pady=(22, 28))
        self._body.bind("<Configure>", self._on_resize)

        self._build()

    # ---- layout -----------------------------------------------------------
    def _build(self):
        b = self._body

        # title and intro, in a light green box
        top = self._panel(b, pady=(0, 18))
        Label(top, text="Help", size=28, bold=True, color=C["green_dark"], bg=C["green_light"]
              ).pack(fill="x", padx=PANEL_PAD, pady=(20, 0))
        self._para(top, T.INTRO, padx=PANEL_PAD, pady=(6, 20), bg=C["green_light"], offset=2 * PANEL_PAD)

        # team contact, in a light green box
        contact = self._panel(b, pady=(0, 6))
        Label(contact, text="Contact our team", size=17, bold=True, color=C["green_dark"],
              bg=C["green_light"]).pack(fill="x", padx=PANEL_PAD, pady=(18, 6))
        row = Box(contact, bg=C["green_light"])
        row.pack(fill="x", padx=PANEL_PAD, pady=(0, 18))
        Label(row, text="Email:", bg=C["green_light"]).pack(side="left")
        link = Label(row, text=T.SUPPORT_EMAIL, bold=True, color=C["green_dark"],
                     bg=C["green_light"], cursor="hand2")
        link.pack(side="left", padx=(6, 0))
        link.bind("<Button-1>", lambda _e: webbrowser.open(f"mailto:{T.SUPPORT_EMAIL}"))

        # FAQs
        Label(b, text="Frequently asked questions", size=17, bold=True, color=C["green_dark"],
              bg=C["surface"]).pack(fill="x", pady=(26, 8))
        for question, answer in T.FAQS:
            card = self._panel(b, pady=(0, 10))
            Label(card, text=question, size=14, bold=True, color=C["green_dark"],
                  bg=C["green_light"]).pack(fill="x", padx=PANEL_PAD, pady=(14, 4))
            self._para(card, answer, padx=PANEL_PAD, pady=(0, 14), bg=C["green_light"],
                       offset=2 * PANEL_PAD)

    # ---- building blocks --------------------------------------------------
    def _panel(self, parent, pady):
        box = Box(parent, bg=C["green_light"])
        box.pack(fill="x", pady=pady)
        return box

    def _para(self, parent, text, padx=0, pady=(0, 0), bg=None, offset=0):
        lbl = Label(parent, text=text, color=C["text"], bg=bg or C["surface"], wrap=700)
        lbl.pack(fill="x", padx=padx, pady=pady)
        self._wrapped.append((lbl, offset))

    def _on_resize(self, event):
        # Tk labels don't wrap by themselves: re-wrap every paragraph to the current width.
        # Done once after resizing settles, and only if the width really changed.
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
