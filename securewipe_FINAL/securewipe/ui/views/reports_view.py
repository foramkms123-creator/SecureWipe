"""Reports section: one row per issued certificate, newest first.

Columns: Report ID, Target, Wiping method, Date & time (= certificate issue time), Actions.
Admins see every user's reports; staff see their own.

Rows are built from lightweight Label/Box widgets; only the action button is a CTk widget.
"""
import customtkinter as ctk

from config import REPORT_ROW_LIMIT
from services import report_service
from services.auth_service import User
from ui.components.scroll_frame import ScrollFrame
from ui.light import Box, Label
from ui.theme import C, font

# column weights shared by the header and every row, so the columns line up
WEIGHTS = (2, 3, 3, 3)
ACTION_MIN = 170
HEADERS = ("Report ID", "Target", "Wiping method", "Date & time")


class ReportsView(ctk.CTkFrame):
    title = "Reports"

    def __init__(self, master, user: User, on_open):
        super().__init__(master, fg_color="transparent")
        self._user = user
        self._on_open = on_open            # callback(op_id) -> shows the certificate
        self._search_job = None
        self._last = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        head = Box(self)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        head.grid_columnconfigure(0, weight=1)
        Label(head, text="View and manage your wipe reports", size=14, color=C["muted"]
              ).grid(row=0, column=0, sticky="w")
        self._search = ctk.CTkEntry(head, width=380, height=40, corner_radius=12, font=font(13), text_color=C["text"],
                                    border_color=C["border"], fg_color=C["surface"],
                                    placeholder_text="Search by device, date or report ID...")
        self._search.grid(row=0, column=1, sticky="e")
        self._search.bind("<KeyRelease>", self._on_search)

        card = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=16, border_width=1,
                            border_color=C["border"])
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        self._header = Box(card, bg=C["green_light"])
        self._header.grid(row=0, column=0, sticky="ew", padx=1, pady=(1, 0))
        self._layout_columns(self._header)
        for i, text in enumerate(HEADERS):
            Label(self._header, text=text, size=12, bold=True, color=C["green_dark"],
                  bg=C["green_light"]).grid(row=0, column=i, sticky="w", padx=(18, 8), pady=10)
        Label(self._header, text="Actions", size=12, bold=True, color=C["green_dark"],
              bg=C["green_light"]).grid(row=0, column=len(WEIGHTS), sticky="w", padx=(8, 18))

        self._scroll = ScrollFrame(card, bg=C["surface"])
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=1, pady=(0, 1))
        self._rows = Box(self._scroll.inner, bg=C["surface"])
        self._rows.pack(fill="x")
        self._layout_columns(self._rows)

    @staticmethod
    def _layout_columns(frame) -> None:
        for i, w in enumerate(WEIGHTS):
            frame.grid_columnconfigure(i, weight=w, uniform="report-col")
        frame.grid_columnconfigure(len(WEIGHTS), minsize=ACTION_MIN)

    # ---- data -------------------------------------------------------------------
    def refresh(self) -> None:
        rows = report_service.list_reports(self._user, self._search.get())[:REPORT_ROW_LIMIT]
        if rows == self._last:             # rebuild only when the list changes
            return
        self._last = rows
        self._render(rows)

    def _render(self, rows) -> None:
        for w in self._rows.winfo_children():
            w.destroy()
        if not rows:
            Label(self._rows, text="No reports yet. Finish a wipe and generate its certificate "
                                   "to see it here.", size=13, italic=True, color=C["muted"],
                  bg=C["surface"], anchor="center", ipady=40
                  ).grid(row=0, column=0, columnspan=len(WEIGHTS) + 1, sticky="ew")
            return
        for r in rows:
            row = Box(self._rows, bg=C["surface"])
            row.pack(side="top", fill="x")
            self._layout_columns(row)
            cells = (
                (r.report_id, dict(bold=True, color=C["green_dark"])),
                (r.target, {}),
                (r.method, {}),
                (r.issued, {}),
            )
            for col, (text, style) in enumerate(cells):
                Label(row, text=_ellipsis(text, 46), size=13, bg=C["surface"], **style
                      ).grid(row=0, column=col, sticky="w", padx=(18, 8), pady=12)
            ctk.CTkButton(row, text="View Report", height=34, width=130, corner_radius=10,
                          font=font(12, bold=True), fg_color=C["surface"],
                          text_color=C["green_dark"], border_width=1,
                          border_color=C["green_dark"], hover_color=C["green_light"],
                          command=lambda op=r.op_id: self._on_open(op)
                          ).grid(row=0, column=len(WEIGHTS), sticky="w", padx=(8, 18))
            Box(self._rows, bg=C["border"], height=1).pack(side="top", fill="x")   # divider

    # ---- search -----------------------------------------------------------------
    def _on_search(self, _event=None) -> None:
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(300, self.refresh)

    def destroy(self):
        if self._search_job:
            self.after_cancel(self._search_job)
        super().destroy()


def _ellipsis(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
