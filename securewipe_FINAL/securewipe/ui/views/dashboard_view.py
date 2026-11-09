"""Dashboard content: greeting, overview cards, methods used, detailed log."""
import customtkinter as ctk

from config import REFRESH_INTERVAL_MS
from services import dashboard_service
from services.auth_service import User
from ui import assets
from ui.icons import icon
from ui.components.log_table import LogTable
from ui.components.stat_card import StatCard
from ui.content.taglines import pick_for_login
from ui.light import Label
from ui.theme import C, font


class DashboardView(ctk.CTkFrame):
    title = "Dashboard"

    def __init__(self, master, user: User):
        super().__init__(master, fg_color="transparent")
        self._user = user
        self._refresh_job = None
        self._search_job = None
        self._last_usage = None
        self._last_rows = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        self._build_hero()

        ctk.CTkLabel(self, text="Overview", font=font(15), text_color=C["muted"], anchor="w"
                     ).grid(row=1, column=0, sticky="w", pady=(20, 8))
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=2, column=0, sticky="ew")
        spec = [
            ("reports", "Reports generated", C["orange"], "▤"),
            ("total", "Data wipes", C["primary"], icon("shield_broom", "#FFFFFF", 26)),
            ("successful", "Successful", C["success"], "✓"),
            ("failed", "Not successful", C["danger"], "✕"),
            ("algorithms", "Algorithms used", C["slate"], icon("algorithm", "#FFFFFF", 26)),
        ]
        self._cards = {}
        for i, (key, title, color, symbol) in enumerate(spec):
            cards.grid_columnconfigure(i, weight=1, uniform="card")
            card = StatCard(cards, title, color, symbol)
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 7, 0 if i == 4 else 7))
            self._cards[key] = card

        self._methods = ctk.CTkFrame(self, fg_color="transparent")
        self._methods.grid(row=3, column=0, sticky="ew", pady=(12, 0))

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=4, column=0, sticky="ew", pady=(22, 10))
        ctk.CTkLabel(head, text="Detailed log", font=font(17, bold=True),
                     text_color=C["text"]).pack(side="left")
        ctk.CTkButton(head, text="Refresh", width=90, height=34, corner_radius=8, font=font(12),
                      fg_color=C["surface"], text_color=C["text"], border_width=1,
                      border_color=C["border"], hover_color=C["hero"],
                      command=self.refresh).pack(side="right")
        self._search = ctk.CTkEntry(head, width=320, height=34, corner_radius=8, font=font(12), text_color=C["text"],
                                    border_color=C["border"], fg_color=C["surface"],
                                    placeholder_text="Search file, location, method or status")
        self._search.pack(side="right", padx=10)
        self._search.bind("<KeyRelease>", self._on_search)

        self._table = LogTable(self, show_user=user.is_admin)
        self._table.grid(row=5, column=0, sticky="nsew", pady=(0, 4))
        # first refresh() is done by DashboardScreen.navigate() (was running twice at login)

    def _build_hero(self):
        hero = ctk.CTkFrame(self, fg_color=C["hero"], corner_radius=20, height=150)
        hero.grid(row=0, column=0, sticky="ew")
        hero.grid_propagate(False)
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_rowconfigure((0, 3), weight=1)
        Label(hero, text=f"Hi, {self._user.first_name}", size=34, bold=True, bg=C["hero"]
              ).grid(row=1, column=0, sticky="w", padx=36)
        # One tagline per sign-in (DashboardView is rebuilt on every login)
        Label(hero, text=pick_for_login(), size=15, color=C["muted"], bg=C["hero"]
              ).grid(row=2, column=0, sticky="w", padx=36, pady=(6, 0))
        ctk.CTkLabel(hero, text="", image=assets.logo(118)
                     ).grid(row=0, column=1, rowspan=4, padx=40)

    # ---- data -------------------------------------------------------------
    def refresh(self) -> None:
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
            self._refresh_job = None
        ov = dashboard_service.get_overview(self._user)
        self._cards["reports"].update_value(ov.reports)
        self._cards["total"].update_value(ov.total)
        self._cards["successful"].update_value(ov.successful)
        self._cards["failed"].update_value(ov.failed)
        self._cards["algorithms"].update_value(
            len(ov.algorithms), f"Most used: {ov.algorithms[0][0]}" if ov.algorithms else "")
        if ov.algorithms != self._last_usage:        # rebuild chips only when they change
            self._last_usage = ov.algorithms
            self._render_methods(ov.algorithms)
        rows = dashboard_service.get_log_rows(self._user, self._search.get())
        if rows != self._last_rows:                  # refill the table only when it changes
            self._last_rows = rows
            self._table.set_rows(rows)
        self._refresh_job = self.after(REFRESH_INTERVAL_MS, self._auto_refresh)

    def _auto_refresh(self) -> None:
        """Timer refresh: skipped while another page is shown (it used to run in the
        background every 15 s and cause a hitch on the Algorithms/About pages)."""
        self._refresh_job = None
        if self.winfo_ismapped():
            self.refresh()
        else:
            self._refresh_job = self.after(REFRESH_INTERVAL_MS, self._auto_refresh)

    def _render_methods(self, usage):
        for w in self._methods.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._methods, text="Methods used:", font=font(12), text_color=C["muted"]
                     ).pack(side="left", padx=(0, 8))
        if not usage:
            ctk.CTkLabel(self._methods, text="none yet", font=font(12, italic=True),
                         text_color=C["muted"]).pack(side="left")
        for name, count in usage:
            ctk.CTkLabel(self._methods, text=f"  {name}  ×{count}  ", font=font(12),
                         fg_color=C["surface"], text_color=C["text"], corner_radius=12,
                         height=26).pack(side="left", padx=4)

    def _on_search(self, _event=None):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(300, self.refresh)

    def destroy(self):
        for job in (self._refresh_job, self._search_job):
            if job:
                self.after_cancel(job)
        super().destroy()
