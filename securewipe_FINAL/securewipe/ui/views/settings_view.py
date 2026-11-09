"""Settings page: general preferences, security, data wiping defaults, reports and storage,
notifications. One Restore Defaults and one Save Changes apply to the whole page.

Settings are stored by services/settings_service.py. Changes are applied when Save Changes is
pressed (the theme and date format take effect at once)."""
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from services import notify_service, sound_service
from services import settings_service as sp
from services.auth_service import User
from services.system_service import is_windows
from services.wipe_methods import METHODS
from ui.components.password_dialogs import ChangePasswordDialog
from ui.components.scroll_frame import ScrollFrame
from ui.icons import icon
from ui.light import Box, Label
from ui.theme import C, font

THEME_LABELS = {"light": "Light", "dark": "Dark", "system": "System"}
DATE_LABELS = {key: label for key, (label, _) in sp.DATE_FORMATS.items()}
POLICY_LABELS = dict(sp.PASSWORD_POLICIES)
LOCK_LABELS = {m: sp.AUTO_LOCK_LABELS[m] for m in sp.AUTO_LOCK_MINUTES}
METHOD_LABELS = {m.key: m.name for m in METHODS}
SOUND_LABELS = {"chime": "Chime", "success": "Success", "alert": "Alert", "off": "No sound"}
# (event key from services/notify_service.py, row text)
NOTIFY_ROWS = (
    ("wipe_done", "When a wipe is completed"),
    ("wipe_failed", "When a wipe is stopped or fails"),
    ("certificate", "When a certificate is issued"),
)


def _invert(mapping: dict) -> dict:
    return {label: key for key, label in mapping.items()}


class SettingsView(ctk.CTkFrame):
    title = "Settings"

    def __init__(self, master, user: User, on_saved):
        super().__init__(master, fg_color="transparent")
        self._user = user
        self._on_saved = on_saved               # callback(theme_changed) after a successful save
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        head = Box(self)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        Label(head, text="Manage your application preferences and security options", size=14,
              color=C["muted"]).pack(anchor="w")

        scroll = ScrollFrame(self, bg=C["bg"])
        scroll.grid(row=1, column=0, sticky="nsew")
        page = scroll.inner
        page.grid_columnconfigure(0, weight=1)

        self._build_vars()
        self._build_general(page)
        self._build_security(page)
        self._build_wiping(page)
        self._build_storage(page)
        self._build_notifications(page)
        self._build_footer()
        self._load(sp.load())

    # =============================================================================
    # variables and loading
    # =============================================================================
    def _build_vars(self) -> None:
        self._theme = ctk.StringVar()
        self._date = ctk.StringVar()
        self._startup = ctk.BooleanVar()
        self._policy = ctk.StringVar()
        self._lock = ctk.StringVar()
        self._require = ctk.BooleanVar()
        self._method = ctk.StringVar()
        self._folder = ctk.StringVar()
        self._auto_cert = ctk.BooleanVar()
        self._notif = ctk.BooleanVar()
        self._banner = ctk.BooleanVar()
        # event -> (on/off variable, sound variable)
        self._event_vars = {ev: (ctk.BooleanVar(), ctk.StringVar()) for ev, _ in NOTIFY_ROWS}

    def _load(self, prefs: dict) -> None:
        self._theme.set(THEME_LABELS[prefs["theme"]])
        self._date.set(DATE_LABELS[prefs["date_format"]])
        self._startup.set(prefs["launch_at_startup"])
        self._policy.set(POLICY_LABELS[prefs["password_policy"]])
        self._lock.set(LOCK_LABELS[prefs["auto_lock_minutes"]])
        self._require.set(prefs["require_password"])
        self._method.set(METHOD_LABELS.get(prefs["default_method"], METHOD_LABELS["dod"]))
        self._folder.set(prefs["reports_folder"] or str(sp.DEFAULT_REPORTS_DIR))
        self._auto_cert.set(prefs["auto_certificate"])
        self._notif.set(prefs["notifications_enabled"])
        self._banner.set(prefs["notify_banner"])
        for ev, (flag_var, sound_var) in self._event_vars.items():
            flag_var.set(prefs[notify_service.EVENTS[ev][0]])
            sound_var.set(SOUND_LABELS[prefs[notify_service.EVENTS[ev][1]]])
        self._sync_notifications()

    def _collect(self) -> dict:
        folder = self._folder.get().strip()
        default_folder = str(sp.DEFAULT_REPORTS_DIR)
        sound_keys = _invert(SOUND_LABELS)
        notify = {}
        for ev, (flag_var, sound_var) in self._event_vars.items():
            flag_key, sound_key, _, _ = notify_service.EVENTS[ev]
            notify[flag_key] = bool(flag_var.get())
            notify[sound_key] = sound_keys[sound_var.get()]
        return {
            **notify,
            "notify_banner": bool(self._banner.get()),
            "theme": _invert(THEME_LABELS)[self._theme.get()],
            "date_format": _invert(DATE_LABELS)[self._date.get()],
            "launch_at_startup": bool(self._startup.get()),
            "password_policy": _invert(POLICY_LABELS)[self._policy.get()],
            "auto_lock_minutes": _invert(LOCK_LABELS)[self._lock.get()],
            "require_password": bool(self._require.get()),
            "default_method": _invert(METHOD_LABELS)[self._method.get()],
            "reports_folder": "" if folder in ("", default_folder) else folder,
            "auto_certificate": bool(self._auto_cert.get()),
            "notifications_enabled": bool(self._notif.get()),
        }

    # =============================================================================
    # cards
    # =============================================================================
    def _card(self, parent, row: int, icon_name: str, title: str) -> Box:
        card = ctk.CTkFrame(parent, fg_color=C["surface"], corner_radius=16,
                            border_width=1, border_color=C["border"])
        card.grid(row=row, column=0, sticky="ew", pady=(0, 14), padx=(0, 6))
        card.grid_columnconfigure(0, weight=1)
        head = Box(card, bg=C["surface"])
        head.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 0))
        ctk.CTkLabel(head, text="", image=icon(icon_name, C["green_dark"], 26)).pack(side="left")
        Label(head, text=title, size=18, bold=True, color=C["green_dark"], bg=C["surface"]
              ).pack(side="left", padx=10)
        body = Box(card, bg=C["surface"])
        body.grid(row=1, column=0, sticky="ew", padx=22, pady=(14, 20))
        return body

    @staticmethod
    def _field(parent, col: int, label: str, widget_factory, span: int = 1) -> object:
        box = Box(parent, bg=C["surface"])
        box.grid(row=0, column=col, columnspan=span, sticky="ew",
                 padx=(0 if col == 0 else 18, 0))
        Label(box, text=label, size=12, bold=True, color=C["muted"], bg=C["surface"]
              ).pack(anchor="w", pady=(0, 6))
        widget = widget_factory(box)
        widget.pack(fill="x")
        return widget

    @staticmethod
    def _dropdown(values_var, values):
        def make(parent):
            return ctk.CTkOptionMenu(
                parent, variable=values_var, values=list(values), height=40, corner_radius=10,
                font=font(13), dropdown_font=font(13), text_color=C["text"],
                fg_color=C["bg"], button_color=C["green_light"],
                button_hover_color=C["green_soft"], dropdown_fg_color=C["surface"],
                dropdown_text_color=C["text"], dropdown_hover_color=C["green_light"])
        return make

    @staticmethod
    def _checkbox(var, text: str, enabled: bool = True):
        def make(parent):
            return ctk.CTkCheckBox(
                parent, text=text, variable=var, font=font(13), text_color=C["text"],
                checkbox_width=22, checkbox_height=22, corner_radius=6, border_width=2,
                fg_color=C["green_dark"], hover_color=C["green_dark_hover"],
                border_color=C["muted"], state="normal" if enabled else "disabled")
        return make

    @staticmethod
    def _switch(var, text: str, command=None):
        def make(parent):
            return ctk.CTkSwitch(
                parent, text=text, variable=var, font=font(13), text_color=C["text"],
                progress_color=C["green_dark"], button_color="#FFFFFF",
                button_hover_color=C["green_light"], fg_color=C["border"], command=command)
        return make

    # ---- 1. general preferences ----------------------------------------------------
    def _build_general(self, parent) -> None:
        body = self._card(parent, 0, "gear", "General Preferences")
        for i in range(4):
            body.grid_columnconfigure(i, weight=1, uniform="gen")
        self._field(body, 0, "Theme", self._dropdown(self._theme, THEME_LABELS.values()))
        self._field(body, 1, "Date format", self._dropdown(self._date, DATE_LABELS.values()))
        startup_text = "Launch SecureWipe when Windows starts"
        if not is_windows():
            startup_text += " (Windows only)"
        self._field(body, 2, "Startup", self._checkbox(self._startup, startup_text,
                                                       enabled=is_windows()))

    # ---- 2. security & authentication -----------------------------------------------
    def _build_security(self, parent) -> None:
        body = self._card(parent, 1, "shield", "Security & Authentication")
        for i in range(4):
            body.grid_columnconfigure(i, weight=1, uniform="sec")
        self._field(body, 0, "Password policy",
                    self._dropdown(self._policy, POLICY_LABELS.values()))
        self._field(body, 1, "Auto-lock after inactivity",
                    self._dropdown(self._lock, LOCK_LABELS.values()))
        self._field(body, 2, "Sensitive actions",
                    self._checkbox(self._require, "Require password before starting a wipe"))

        def change_button(box_parent):
            return ctk.CTkButton(box_parent, text="  Change Password", height=40, corner_radius=10,
                                 image=icon("lock", C["green_dark"], 18), compound="left",
                                 font=font(13, bold=True), fg_color=C["surface"],
                                 text_color=C["green_dark"], border_width=1,
                                 border_color=C["green_dark"], hover_color=C["green_light"],
                                 command=self._change_password)
        self._field(body, 3, "Account", change_button)

    def _change_password(self) -> None:
        ChangePasswordDialog(self, self._user,
                             on_done=lambda: messagebox.showinfo(
                                 "Password changed", "Your password was updated."))

    # ---- 3. data wiping defaults ------------------------------------------------------
    def _build_wiping(self, parent) -> None:
        body = self._card(parent, 2, "database", "Data Wiping Defaults")
        for i in range(2):
            body.grid_columnconfigure(i, weight=1, uniform="wipe")
        self._field(body, 0, "Default wiping method",
                    self._dropdown(self._method, METHOD_LABELS.values()))
        Label(body, text="The Algorithms page opens with this method selected. You can still "
                         "change it for each wipe.", size=12, color=C["muted"], bg=C["surface"],
              wrap=700).grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 0))

    # ---- 4. reports & storage -------------------------------------------------------
    def _build_storage(self, parent) -> None:
        body = self._card(parent, 3, "document", "Reports & Storage")
        body.grid_columnconfigure(0, weight=1)

        folder_box = Box(body, bg=C["surface"])
        folder_box.grid(row=0, column=0, sticky="ew")
        folder_box.grid_columnconfigure(0, weight=1)
        Label(folder_box, text="Save reports to folder", size=12, bold=True, color=C["muted"],
              bg=C["surface"]).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ctk.CTkEntry(folder_box, textvariable=self._folder, height=40, corner_radius=10,
                     font=font(13), border_color=C["border"], fg_color=C["bg"],
                     text_color=C["text"]).grid(row=1, column=0, sticky="ew")
        ctk.CTkButton(folder_box, text="  Browse", image=icon("folder", C["green_dark"], 18),
                      compound="left", height=40, width=130, corner_radius=10, font=font(13, bold=True),
                      fg_color=C["surface"], text_color=C["green_dark"], border_width=1,
                      border_color=C["green_dark"], hover_color=C["green_light"],
                      command=self._browse).grid(row=1, column=1, padx=(12, 0))

        ctk.CTkSwitch(body, text="Generate PDF certificate automatically when a wipe succeeds",
                      variable=self._auto_cert, font=font(13), text_color=C["text"],
                      progress_color=C["green_dark"], button_color="#FFFFFF",
                      button_hover_color=C["green_light"], fg_color=C["border"]
                      ).grid(row=2, column=0, sticky="w", pady=(18, 0))
        Label(body, text="The certificate is created and saved to the folder above without "
                         "pressing Generate certificate.", size=12, color=C["muted"],
              bg=C["surface"], wrap=760).grid(row=3, column=0, sticky="w", pady=(4, 0))

    def _browse(self) -> None:
        start = self._folder.get().strip() or str(sp.DEFAULT_REPORTS_DIR)
        chosen = filedialog.askdirectory(title="Choose the reports folder",
                                         initialdir=start if Path(start).exists() else None)
        if chosen:
            self._folder.set(chosen)

    # ---- 5. notifications -------------------------------------------------------------
    def _build_notifications(self, parent) -> None:
        body = self._card(parent, 4, "bell", "Notifications")
        body.grid_columnconfigure(0, weight=1)
        self._notif_widgets = []          # switched off together with the master switch
        ctk.CTkSwitch(body, text="Show notifications", variable=self._notif,
                      font=font(13), text_color=C["text"], progress_color=C["green_dark"],
                      button_color="#FFFFFF", button_hover_color=C["green_light"],
                      fg_color=C["border"], command=self._sync_notifications
                      ).grid(row=0, column=0, columnspan=3, sticky="w")
        banner = ctk.CTkSwitch(body, text="Show a pop-up banner at the top of the screen",
                               variable=self._banner, font=font(13), text_color=C["text"],
                               progress_color=C["green_dark"], button_color="#FFFFFF",
                               button_hover_color=C["green_light"], fg_color=C["border"])
        banner.grid(row=1, column=0, columnspan=3, sticky="w", padx=(28, 0), pady=(12, 0))
        self._notif_widgets.append(banner)

        Label(body, text="Sound", size=12, bold=True, color=C["muted"], bg=C["surface"]
              ).grid(row=2, column=1, sticky="w", padx=(18, 0), pady=(20, 0))
        for i, (ev, text) in enumerate(NOTIFY_ROWS, start=3):
            flag_var, sound_var = self._event_vars[ev]
            switch = ctk.CTkSwitch(body, text=text, variable=flag_var, font=font(13),
                                   text_color=C["text"], progress_color=C["green_dark"],
                                   button_color="#FFFFFF", button_hover_color=C["green_light"],
                                   fg_color=C["border"])
            switch.grid(row=i, column=0, sticky="w", padx=(28, 0), pady=(12, 0))
            menu = ctk.CTkOptionMenu(body, variable=sound_var, values=list(SOUND_LABELS.values()),
                                     width=180, height=36, corner_radius=10, font=font(13),
                                     dropdown_font=font(13), text_color=C["text"],
                                     fg_color=C["bg"], button_color=C["green_light"],
                                     button_hover_color=C["green_soft"],
                                     dropdown_fg_color=C["surface"], dropdown_text_color=C["text"],
                                     dropdown_hover_color=C["green_light"])
            menu.grid(row=i, column=1, sticky="w", padx=(18, 0), pady=(12, 0))
            play = ctk.CTkButton(body, text="Test sound", width=110, height=36, corner_radius=10,
                                 font=font(12, bold=True), fg_color=C["surface"],
                                 text_color=C["green_dark"], border_width=1,
                                 border_color=C["green_dark"], hover_color=C["green_light"],
                                 command=lambda v=sound_var: self._test_sound(v))
            play.grid(row=i, column=2, sticky="w", padx=(12, 0), pady=(12, 0))
            self._notif_widgets += [switch, menu, play]
        Label(body, text="A banner stays for a few seconds, and the sound plays when the event "
                         "happens. 'Test sound' plays the sound selected in the list.",
              size=12, color=C["muted"], bg=C["surface"], wrap=760
              ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(16, 0))

    def _test_sound(self, sound_var) -> None:
        sound_service.play(_invert(SOUND_LABELS)[sound_var.get()])

    def _sync_notifications(self) -> None:
        """Everything below the master switch is used only while notifications are on."""
        state = "normal" if self._notif.get() else "disabled"
        for w in getattr(self, "_notif_widgets", []):
            w.configure(state=state)

    # ---- footer -----------------------------------------------------------------------
    def _build_footer(self) -> None:
        bar = Box(self)
        bar.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        bar.grid_columnconfigure(0, weight=1)
        self._status = Label(bar, size=12, color=C["muted"])
        self._status.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(bar, text="  Restore Defaults", image=icon("refresh", C["green_dark"], 18),
                      compound="left", height=44, corner_radius=12, font=font(13, bold=True),
                      fg_color=C["surface"], text_color=C["green_dark"], border_width=1,
                      border_color=C["green_dark"], hover_color=C["green_light"],
                      command=self._restore).grid(row=0, column=1, padx=(0, 12))
        ctk.CTkButton(bar, text="Save Changes", height=44, corner_radius=12,
                      font=font(13, bold=True), fg_color=C["green_dark"],
                      hover_color=C["green_dark_hover"], command=self._save
                      ).grid(row=0, column=2)

    def _restore(self) -> None:
        if messagebox.askyesno("Restore defaults",
                               "Put every setting on this page back to its default value?\n"
                               "Nothing is saved until you press Save Changes."):
            self._load(sp.defaults())
            self._status.configure(text="Defaults restored. Press Save Changes to keep them.",
                                   fg=C["muted"])

    def _save(self) -> None:
        prefs = self._collect()
        theme_before = sp.resolve_theme(sp.get("theme"))
        try:
            target = Path(prefs["reports_folder"]) if prefs["reports_folder"] else sp.DEFAULT_REPORTS_DIR
            target.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Reports folder", f"This folder cannot be used:\n{exc}")
            return
        try:
            sp.set_launch_at_startup(prefs["launch_at_startup"])
        except OSError as exc:
            messagebox.showerror("Startup", f"Windows did not accept the startup setting:\n{exc}")
            return
        sp.save(prefs)
        theme_changed = sp.resolve_theme(prefs["theme"]) != theme_before
        self._status.configure(text="Settings saved.", fg=C["green_dark"])
        self._on_saved(theme_changed)           # last call: the screen may be rebuilt
