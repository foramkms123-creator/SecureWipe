"""Software License window, opened from About > View license.

Layout follows the reference page: header with logo and title; the academic licence badge;
the app summary; four cards (Permissions, Restrictions, Warranty & Liability, Technology
acknowledgements); and a footer with the project guide and Export License.

The window uses the Windows title bar, which already has Minimise, Maximise and Close at the
top right, so there is only one set of window buttons. The window is placed so that its
buttons are always on screen. Export License saves the same text as a PDF in the reports
folder (Settings > Reports & Storage)."""
from tkinter import messagebox

import customtkinter as ctk

from config import APP_NAME, APP_VERSION, SIDEBAR
from services import app_log, license_service
from ui import assets
from ui.components.scroll_frame import ScrollFrame
from ui.content import about_text as T
from ui.icons import icon
from ui.light import Box, Label
from ui.theme import C, font

WIDTH, HEIGHT = 760, 820           # logical size; CustomTkinter scales it to the screen DPI
MIN_WIDTH, MIN_HEIGHT = 560, 420
TEXT_W = 600                       # wrap width of paragraphs inside the cards


class LicenseDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master, fg_color=C["surface"])
        self.title(f"{APP_NAME} - {T.LICENSE_TITLE}")
        self.resizable(True, True)                       # enables Minimise and Maximise
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.transient(master.winfo_toplevel())
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)              # only the middle part stretches
        self.bind("<Escape>", lambda _e: self.destroy())

        self._header()
        self._body()
        self._footer()
        self._place_over(master)
        self.after(120, self._grab)                      # grab only once the window is drawn

    # ---- layout -----------------------------------------------------------------
    def _place_over(self, master) -> None:
        """Centres the window over the main window, but keeps all of it on screen."""
        scale = self._get_widget_scaling() or 1.0
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width_px = min(round(WIDTH * scale), screen_w - 40)
        height_px = min(round(HEIGHT * scale), screen_h - 120)     # room for the taskbar
        top = master.winfo_toplevel()
        x_px = top.winfo_rootx() + (top.winfo_width() - width_px) // 2
        y_px = top.winfo_rooty() + (top.winfo_height() - height_px) // 2
        x_px = max(0, min(x_px, screen_w - width_px - 20))
        y_px = max(0, min(y_px, screen_h - height_px - 60))
        # CustomTkinter multiplies the numbers by the scale itself, so give logical values
        self.geometry(f"{round(width_px / scale)}x{round(height_px / scale)}"
                      f"+{round(x_px / scale)}+{round(y_px / scale)}")

    def _header(self) -> None:
        bar = Box(self, bg=SIDEBAR["bg"])
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(bar, text="", image=assets.logo(44)).grid(row=0, column=0, padx=(22, 14), pady=16)
        Label(bar, text=T.LICENSE_TITLE, size=20, bold=True, color=C["text"], bg=SIDEBAR["bg"]
              ).grid(row=0, column=1, sticky="w")

    def _body(self) -> None:
        scroll = ScrollFrame(self, bg=C["surface"])
        scroll.grid(row=1, column=0, sticky="nsew")
        page = scroll.inner
        page.grid_columnconfigure(0, weight=1)

        # badge
        badge = ctk.CTkFrame(page, fg_color=C["green_light"], corner_radius=16)
        badge.grid(row=0, column=0, sticky="w", padx=28, pady=(24, 0))
        ctk.CTkLabel(badge, text="", image=icon("cap", C["green_dark"], 20)).pack(side="left", padx=(10, 8), pady=8)
        ctk.CTkLabel(badge, text=T.LICENSE_BADGE, font=font(13, bold=True),
                     text_color=C["green_dark"]).pack(side="left", padx=(0, 16), pady=8)

        # app summary
        top = Box(page, bg=C["surface"])
        top.grid(row=1, column=0, sticky="ew", padx=28, pady=(20, 0))
        top.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(top, text="", image=assets.logo(96)).grid(row=0, column=0, rowspan=3,
                                                              sticky="n", padx=(0, 22))
        Label(top, text=APP_NAME, size=26, bold=True, color=C["green_dark"], bg=C["surface"]
              ).grid(row=0, column=1, sticky="w")
        Label(top, text=f"Version {APP_VERSION}   ·   © 2026 {T.TEAM_NAME}", size=13,
              color=C["muted"], bg=C["surface"]).grid(row=1, column=1, sticky="w", pady=(2, 8))
        Label(top, text=T.LICENSE_INTRO, size=13, color=C["text"], bg=C["surface"], wrap=470
              ).grid(row=2, column=1, sticky="w")

        # cards
        for i, (heading, tone, icon_name, items) in enumerate(T.LICENSE_SECTIONS, start=2):
            self._card(page, i, heading, tone, icon_name, items)
        Box(page, bg=C["surface"], height=12).grid(row=len(T.LICENSE_SECTIONS) + 2, column=0)

    def _card(self, parent, row: int, heading: str, tone: str, icon_name: str, items) -> None:
        ok = tone == "ok"
        fill = C["green_light"] if ok else C["warn_bg"]
        border = C["green_soft"] if ok else C["warning"]
        head_color = C["green_dark"] if ok else C["warn_text"]
        mark = "check" if ok else "alert"
        mark_color = C["green_dark"] if ok else C["warning"]

        card = ctk.CTkFrame(parent, fg_color=fill, corner_radius=14, border_width=1,
                            border_color=border)
        card.grid(row=row, column=0, sticky="ew", padx=28, pady=(16, 0))
        card.grid_columnconfigure(0, weight=1)

        head = Box(card, bg=fill)
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 6))
        ctk.CTkLabel(head, text="", image=icon(icon_name, head_color, 24)).pack(side="left")
        Label(head, text=heading, size=16, bold=True, color=head_color, bg=fill
              ).pack(side="left", padx=(12, 0))

        body = Box(card, bg=fill)
        body.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))
        if isinstance(items, str):                       # a paragraph
            Label(body, text=items, size=13, color=C["text"], bg=fill, wrap=TEXT_W - 20
                  ).pack(anchor="w", padx=(0, 0))
        elif heading == "Technology acknowledgements":   # tags, then the note
            tags = Box(body, bg=fill)
            tags.pack(anchor="w")
            for name in items:
                ctk.CTkLabel(tags, text=f"  {name}  ", font=font(12, bold=True),
                             text_color=C["green_dark"], fg_color=C["surface"], corner_radius=10,
                             height=28).pack(side="left", padx=(0, 8))
            Label(body, text=T.LICENSE_TECH_NOTE, size=12, color=C["muted"], bg=fill,
                  wrap=TEXT_W - 20).pack(anchor="w", pady=(12, 0))
        else:                                             # bullet list with small marks
            for text in items:
                line = Box(body, bg=fill)
                line.pack(anchor="w", pady=2)
                ctk.CTkLabel(line, text="", image=icon(mark, mark_color, 16)).pack(side="left", padx=(0, 10))
                Label(line, text=text, size=13, color=C["text"], bg=fill, wrap=TEXT_W - 40
                      ).pack(side="left")

    def _footer(self) -> None:
        foot = Box(self, bg=C["surface"])
        foot.grid(row=2, column=0, sticky="ew")
        Box(foot, bg=C["border"], height=1).pack(fill="x")

        guide = Box(foot, bg=C["surface"])
        guide.pack(fill="x", padx=28, pady=(14, 0))
        Label(guide, text="Project Guide:", size=12, color=C["muted"], bg=C["surface"]
              ).pack(side="left")
        Label(guide, text=T.GUIDE, size=12, bold=True, color=C["text"], bg=C["surface"]
              ).pack(side="left", padx=(6, 0))
        Label(guide, text="•", size=12, color=C["muted"], bg=C["surface"]).pack(side="left", padx=8)
        Label(guide, text=T.DEPARTMENT.split(",")[0], size=12, color=C["muted"], bg=C["surface"]
              ).pack(side="left")

        buttons = Box(foot, bg=C["surface"])
        buttons.pack(fill="x", padx=28, pady=(12, 22))
        ctk.CTkButton(buttons, text="  Export License", image=icon("download", "#FFFFFF", 18),
                      compound="left", command=self._export, height=44, width=190,
                      corner_radius=12, font=font(13, bold=True), fg_color=C["green_dark"],
                      hover_color=C["green_dark_hover"], text_color="#FFFFFF"
                      ).pack(side="right")

    # ---- actions ----------------------------------------------------------------
    def _export(self) -> None:
        try:
            path = license_service.export()
        except Exception as exc:
            app_log.log_exception("Exporting the licence failed")
            messagebox.showerror("Export License", f"The license could not be saved:\n{exc}",
                                 parent=self)
            return
        messagebox.showinfo("Export License", f"The license was saved as:\n{path}", parent=self)

    def _grab(self) -> None:
        try:
            self.grab_set()
        except Exception:
            pass
