"""Sign in / sign up page.

Performance: both forms share one set of widgets that is built once. Switching between
"Sign in" and "Sign up" only shows/hides the two extra fields and changes two texts,
instead of destroying and re-creating every entry, checkbox and button (that was the lag).
Password hashing (scrypt, deliberately slow) runs in a background thread so the window
never freezes while signing in.
"""
import threading

import customtkinter as ctk

from config import APP_NAME, TAGLINE
from services import auth_service
from services.auth_service import AuthError
from ui import assets
from ui.light import Box, Label
from ui.theme import C, font

FIELD_W = 340


class AuthScreen(ctk.CTkFrame):
    def __init__(self, master, on_success):
        super().__init__(master, fg_color=C["bg"], corner_radius=0)
        self._on_success = on_success
        self._busy = False
        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=6)
        self.grid_rowconfigure(0, weight=1)

        # left: brand panel
        brand = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=0)
        brand.grid(row=0, column=0, sticky="nsew")
        inner = Box(brand, bg=C["surface"])
        inner.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(inner, text="", image=assets.logo(170)).pack()
        Label(inner, text=APP_NAME, size=28, bold=True, anchor="center").pack(pady=(16, 4))
        Label(inner, text=TAGLINE, size=13, italic=True, color=C["muted"], wrap=320,
              anchor="center", justify="center").pack()

        # right: form card
        card = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=18,
                            border_width=1, border_color=C["border"])
        card.grid(row=0, column=1, padx=60, pady=60)
        self._mode = ctk.CTkSegmentedButton(
            card, values=["Sign in", "Sign up"], command=self._render, font=font(13, bold=True),
            selected_color=C["primary"], selected_hover_color=C["primary_hover"],
            unselected_color=C["bg"], unselected_hover_color=C["hero"], text_color=C["text"],
            width=FIELD_W, height=38)
        self._mode.pack(padx=40, pady=(36, 8))
        self._mode.set("Sign in")

        form = Box(card, bg=C["surface"])
        form.pack(padx=40, pady=(8, 36))
        form.grid_columnconfigure(0, weight=1)
        self._form = form

        # every widget of both forms, built once (row numbers fixed so hiding keeps order)
        self._title = Label(form, text="Welcome back", size=22, bold=True)
        self._title.grid(row=0, column=0, sticky="ew", pady=(4, 6))
        self._full_name_row = self._field(1, "Full name")
        self._username_row = self._field(2, "Username")
        self._password_row = self._field(3, "Password", show="•")
        self._confirm_row = self._field(4, "Confirm password", show="•")
        self._full_name = self._full_name_row.entry
        self._username = self._username_row.entry
        self._password = self._password_row.entry
        self._confirm = self._confirm_row.entry

        self._show = ctk.CTkCheckBox(form, text="Show password", font=font(12),
                                     text_color=C["muted"], fg_color=C["primary"],
                                     hover_color=C["primary_hover"], checkbox_width=18,
                                     checkbox_height=18, command=self._toggle_show)
        self._show.grid(row=5, column=0, sticky="w", pady=(10, 0))
        self._error = Label(form, text="", size=12, color=C["danger"], wrap=FIELD_W)
        self._error.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        self._submit_btn = ctk.CTkButton(form, text="Sign in", font=font(14, bold=True),
                                         width=FIELD_W, height=44, corner_radius=10,
                                         fg_color=C["primary"], hover_color=C["primary_hover"],
                                         command=self._submit)
        self._submit_btn.grid(row=7, column=0, pady=(8, 0))
        self._render("Sign in")

    # ---- form -------------------------------------------------------------
    def _field(self, row: int, label: str, show: str | None = None) -> Box:
        box = Box(self._form, bg=C["surface"])
        box.grid(row=row, column=0, sticky="ew")
        Label(box, text=label, size=12, bold=True).pack(fill="x", pady=(8, 4))
        e = ctk.CTkEntry(box, width=FIELD_W, height=40, font=font(13), corner_radius=10,
                         border_color=C["border"], fg_color=C["bg"], text_color=C["text"],
                         placeholder_text_color=C["muted"],
                         **({"show": show} if show else {}))
        e.pack()
        e.bind("<Return>", lambda _e: self._submit())
        box.entry = e
        return box

    def _render(self, mode):
        """Switch Sign in <-> Sign up by showing/hiding rows (no rebuilding)."""
        signing_up = mode == "Sign up"
        self._title.configure(text="Create your account" if signing_up else "Welcome back")
        self._submit_btn.configure(text="Create account" if signing_up else "Sign in")
        for row in (self._full_name_row, self._confirm_row):
            if signing_up:
                row.grid()
            else:
                row.grid_remove()
        self._error.configure(text="")
        self._password.delete(0, "end")
        self._confirm.delete(0, "end")
        (self._full_name if signing_up else self._username).focus_set()

    def _toggle_show(self):
        show = "" if self._password.cget("show") else "•"
        for e in (self._password, self._confirm):
            e.configure(show=show)

    # ---- submit (hashing runs off the UI thread) ---------------------------
    def _submit(self):
        if self._busy:
            return
        signing_up = self._mode.get() == "Sign up"
        values = (self._full_name.get(), self._username.get(), self._password.get(),
                  self._confirm.get())
        self._busy = True
        self._error.configure(text="")
        self._submit_btn.configure(state="disabled",
                                   text="Creating account…" if signing_up else "Signing in…")
        result = {}

        def work():
            try:
                if signing_up:
                    result["user"] = auth_service.sign_up(*values)
                else:
                    result["user"] = auth_service.sign_in(values[1], values[2])
            except AuthError as exc:
                result["error"] = str(exc)
            except Exception as exc:                     # database problems etc.
                result["error"] = f"Unexpected error: {exc}"

        worker = threading.Thread(target=work, daemon=True)
        worker.start()

        def wait():
            if worker.is_alive():
                self.after(40, wait)
                return
            self._busy = False
            if "user" in result:
                self._on_success(result["user"])        # this screen is replaced now
                return
            self._submit_btn.configure(state="normal",
                                       text="Create account" if signing_up else "Sign in")
            self._error.configure(text=result["error"])
            self._password.delete(0, "end")

        self.after(40, wait)
