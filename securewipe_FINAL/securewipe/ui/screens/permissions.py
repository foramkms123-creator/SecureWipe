"""Permissions page: compulsory permissions (must be acknowledged) and optional ones."""
import customtkinter as ctk
from tkinter import messagebox

from services import system_service
from ui.components.scroll_frame import ScrollFrame
from ui.content import onboarding_text as T
from ui.light import Box, Label
from ui.theme import C, font

WIDTH = 760


class PermissionsScreen(ctk.CTkFrame):
    def __init__(self, master, on_back, on_next):
        super().__init__(master, fg_color=C["surface"], corner_radius=0)
        self._on_next = on_next
        self._optional_vars: dict[str, ctk.BooleanVar] = {}
        self._ack = ctk.BooleanVar(value=False)

        footer = ctk.CTkFrame(self, fg_color=C["surface"], height=76, corner_radius=0,
                              border_width=1, border_color=C["border"])
        footer.pack(fill="x", side="bottom")
        ctk.CTkButton(footer, text="Back", font=font(14), width=120, height=42,
                      corner_radius=10, fg_color="transparent", border_width=1,
                      border_color=C["border"], text_color=C["text"], hover_color=C["bg"],
                      command=on_back).place(relx=0.5, x=-75, rely=0.5, anchor="center")
        self._next_btn = ctk.CTkButton(
            footer, text="Next", font=font(14, bold=True), width=120, height=42,
            corner_radius=10, fg_color=C["primary"], hover_color=C["primary_hover"],
            state="disabled", command=self._finish)
        self._next_btn.place(relx=0.5, x=75, rely=0.5, anchor="center")

        body = ScrollFrame(self, bg=C["surface"], bar_color=C["border"], bar_hover=C["primary"])
        body.pack(fill="both", expand=True)
        col = Box(body.inner, bg=C["surface"])
        col.pack(pady=(40, 20))

        Label(col, text="Permissions", size=28, bold=True).pack(fill="x")
        Label(col, text="Required permissions keep wiping safe and auditable. "
                        "Optional ones can be changed later in Settings.",
              size=14, color=C["muted"], wrap=WIDTH).pack(fill="x", pady=(6, 20))

        self._section(col, "Required")
        for key, title, desc in T.REQUIRED_PERMISSIONS:
            self._required_row(col, key, title, desc)

        ctk.CTkCheckBox(col, text=T.ACKNOWLEDGEMENT, variable=self._ack, font=font(13, bold=True),
                        text_color=C["text"], fg_color=C["primary"], hover_color=C["primary_hover"],
                        command=self._toggle_next).pack(fill="x", pady=(14, 8))

        self._section(col, "Optional")
        saved = system_service.load_permissions()          # choices made before (e.g. before a restart)
        for key, title, desc, default in T.OPTIONAL_PERMISSIONS:
            var = ctk.BooleanVar(value=bool(saved.get(key, default)))
            self._optional_vars[key] = var
            row = self._row(col, title, desc)
            ctk.CTkSwitch(row, text="", variable=var, progress_color=C["primary"],
                          width=46).pack(side="right", padx=16)

    # ---- building blocks --------------------------------------------------
    def _section(self, parent, title):
        Label(parent, text=title, size=17, bold=True, color=C["primary"]
              ).pack(fill="x", pady=(18, 8))

    def _row(self, parent, title, desc):
        row = ctk.CTkFrame(parent, fg_color=C["bg"], corner_radius=12)
        row.pack(fill="x", pady=4)
        text = Box(row, bg=C["bg"])
        text.pack(side="left", fill="x", expand=True, padx=16, pady=10)
        Label(text, text=title, size=14, bold=True, bg=C["bg"]).pack(fill="x")
        Label(text, text=desc, size=12, color=C["muted"], bg=C["bg"]).pack(fill="x")
        return row

    def _required_row(self, parent, key, title, desc):
        row = self._row(parent, title, desc)
        if key != "admin":
            Label(row, text="Required", size=12, italic=True, color=C["muted"], bg=C["bg"]
                  ).pack(side="right", padx=16)
            return
        if system_service.is_admin():
            Label(row, text="Granted", size=12, bold=True, color=C["success"], bg=C["bg"]
                  ).pack(side="right", padx=16)
        elif system_service.is_windows():
            ctk.CTkButton(row, text="Restart as administrator", font=font(12, bold=True),
                          height=32, corner_radius=8, fg_color=C["orange"],
                          hover_color="#CF7438", command=self._elevate).pack(side="right", padx=16)
        else:
            Label(row, text="Run with sudo", size=12, bold=True, color=C["warning"], bg=C["bg"]
                  ).pack(side="right", padx=16)

    # ---- actions ----------------------------------------------------------
    def _toggle_next(self):
        self._next_btn.configure(state="normal" if self._ack.get() else "disabled")

    def _values(self) -> dict[str, bool]:
        return {k: v.get() for k, v in self._optional_vars.items()}

    def _elevate(self):
        if not self._ack.get():
            messagebox.showinfo("Permissions", "Tick the box above to accept the terms first, "
                                "then restart as administrator.")
            return
        # Save before restarting, so the new window keeps these choices and skips this page.
        values = self._values()
        system_service.save_permissions(values, done=True)
        if system_service.relaunch_as_admin():
            self.winfo_toplevel().destroy()
        else:
            system_service.save_permissions(values, done=False)   # cancelled: show this page again next start
            messagebox.showwarning("Administrator rights",
                                   "Elevation was cancelled. Drive wiping stays disabled "
                                   "until SecureWipe runs as administrator.")

    def _finish(self):
        system_service.save_permissions(self._values())
        self._on_next()
