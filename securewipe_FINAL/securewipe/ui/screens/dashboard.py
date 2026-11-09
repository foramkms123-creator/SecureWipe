"""Signed-in shell: sidebar + top bar + swappable content views."""
from tkinter import filedialog, messagebox

import customtkinter as ctk

from config import NAV_BOTTOM, NAV_TOP
from services.auth_service import User
from ui.components.drive_picker import DrivePicker
from ui.components.sidebar import Sidebar
from ui.components.topbar import TopBar
from ui.theme import C
from ui.views.about_view import AboutView
from ui.views.algorithm_view import AlgorithmView
from ui.views.dashboard_view import DashboardView
from ui.views.certificate_view import CertificateView
from ui.views.help_view import HelpView
from ui.views.placeholder_view import PlaceholderView
from ui.views.reports_view import ReportsView
from ui.views.settings_view import SettingsView

TITLES = {key: label for key, label, _ in NAV_TOP + NAV_BOTTOM}


class DashboardScreen(ctk.CTkFrame):
    def __init__(self, master, user: User, on_logout, start: str = "dashboard",
                 on_settings_saved=None):
        super().__init__(master, fg_color=C["bg"], corner_radius=0)
        self._user = user
        self._views: dict[str, ctk.CTkFrame] = {}
        self._current = None
        self._transient = None             # a certificate page opened on top of a section
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._sidebar = Sidebar(self, on_navigate=self.navigate, on_new_wipe=self._new_wipe)
        self._sidebar.grid(row=0, column=0, sticky="ns")

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=34, pady=(18, 22))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)
        self._topbar = TopBar(main, user, on_logout=on_logout)
        self._topbar.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        self._content = ctk.CTkFrame(main, fg_color="transparent")
        self._content.grid(row=1, column=0, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._on_settings_saved = on_settings_saved     # app: rebuild screens for a new theme
        self.navigate(start)

    # ---- navigation -------------------------------------------------------
    def _make_view(self, key: str):
        if key == "dashboard":
            return DashboardView(self._content, self._user)
        if key == "algorithms":
            return AlgorithmView(self._content, self._user, on_new_wipe=self._new_wipe,
                                 on_finished=self.refresh_all,
                                 on_certificate=self.open_certificate)
        if key == "reports":
            return ReportsView(self._content, self._user, on_open=self.open_certificate)
        if key == "settings":
            return SettingsView(self._content, self._user, on_saved=self._settings_saved)
        if key == "about":
            return AboutView(self._content, on_close=lambda: self.navigate("dashboard"))
        if key == "help":
            return HelpView(self._content)
        return PlaceholderView(self._content, TITLES.get(key, key.title()))

    def navigate(self, key: str) -> None:
        view = self._views.get(key)
        if view is None:
            view = self._views[key] = self._make_view(key)
        self._show(view, key)

    def open_certificate(self, op_id: int) -> None:
        """Shows one certificate on top of the current section; Back returns to Reports."""
        view = CertificateView(self._content, self._user, op_id,
                               on_back=lambda: self.navigate("reports"))
        self._show(view, "reports", transient=True)

    def _show(self, view, key: str, transient: bool = False) -> None:
        if self._current is not None:
            self._current.grid_remove()
        if self._transient is not None:           # a certificate page is not kept
            self._transient.destroy()
            self._transient = None
        view.grid(row=0, column=0, sticky="nsew")
        self._current = view
        if transient:
            self._transient = view
        self._topbar.set_title(view.title)
        self._sidebar.set_active(key)
        if hasattr(view, "refresh"):
            view.refresh()

    def _settings_saved(self, theme_changed: bool) -> None:
        if theme_changed and self._on_settings_saved and self._on_settings_saved():
            return                          # the app rebuilt this screen
        if theme_changed:
            messagebox.showinfo("Theme", "The new theme applies when the current wipe finishes "
                                         "(or the next time you open SecureWipe).")
        self.refresh_all()

    @property
    def busy(self) -> bool:
        """True while a wipe is running (auto-lock must not interrupt it)."""
        algo = self._views.get("algorithms")
        return algo is not None and algo.busy

    # ---- new wipe ("+") ---------------------------------------------------
    def _new_wipe(self, kind: str) -> None:
        algo = self._views.get("algorithms")
        if algo is not None and algo.busy:
            messagebox.showwarning("Wipe in progress",
                                   "Finish or stop the current wipe before starting a new task.")
            self.navigate("algorithms")
            return
        if kind == "file":
            paths = list(filedialog.askopenfilenames(title="Choose files to wipe"))
        elif kind == "folder":
            folder = filedialog.askdirectory(title="Choose a folder to wipe")
            paths = [folder] if folder else []
        else:
            DrivePicker(self, on_pick=lambda root: self.on_targets_selected("drive", [root]))
            return
        if paths:
            self.on_targets_selected(kind, paths)

    def on_targets_selected(self, kind: str, paths: list[str]) -> None:
        """Dashboard -> Algorithms page, with the chosen target loaded."""
        self.navigate("algorithms")
        self._views["algorithms"].set_target(kind, paths)

    def refresh_all(self) -> None:
        if "dashboard" in self._views:
            self._views["dashboard"].refresh()
        if "reports" in self._views:
            self._views["reports"].refresh()
        self._topbar.refresh_notifications()
