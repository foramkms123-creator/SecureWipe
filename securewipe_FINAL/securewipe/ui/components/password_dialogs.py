"""Password dialogs: change password (Settings page) and confirm password (before a wipe starts)."""
import customtkinter as ctk

from services import auth_service
from services.auth_service import AuthError, User
from ui.light import Label
from ui.theme import C, font


class _Dialog(ctk.CTkToplevel):
    """Small modal window: stays above the app and blocks clicks on it until closed."""

    def __init__(self, master, title: str, width: int, height: int):
        super().__init__(master)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.configure(fg_color=C["surface"])
        self.transient(master.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(120, self._grab)

    def _grab(self) -> None:
        try:
            self.grab_set()
            self.focus_force()
        except Exception:                       # window not viewable yet: harmless
            pass


def _entry(parent, label: str) -> ctk.CTkEntry:
    Label(parent, text=label, size=12, bold=True, color=C["muted"], bg=C["surface"]
          ).pack(anchor="w", pady=(12, 4))
    entry = ctk.CTkEntry(parent, height=40, corner_radius=10, font=font(13), show="•",
                         border_color=C["border"], fg_color=C["bg"], text_color=C["text"])
    entry.pack(fill="x")
    return entry


def _buttons(parent, cancel_cmd, ok_text: str, ok_cmd) -> None:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=(18, 0))
    ctk.CTkButton(row, text="Cancel", height=40, corner_radius=10, font=font(13),
                  fg_color=C["surface"], text_color=C["text"], border_width=1,
                  border_color=C["border"], hover_color=C["hero"], command=cancel_cmd
                  ).pack(side="right", padx=(8, 0))
    ctk.CTkButton(row, text=ok_text, height=40, corner_radius=10, font=font(13, bold=True),
                  fg_color=C["green_dark"], hover_color=C["green_dark_hover"], command=ok_cmd
                  ).pack(side="right")


class ChangePasswordDialog(_Dialog):
    def __init__(self, master, user: User, on_done):
        super().__init__(master, "Change password", 440, 470)
        self._user = user
        self._on_done = on_done
        body = ctk.CTkFrame(self, fg_color=C["surface"])
        body.pack(fill="both", expand=True, padx=26, pady=22)
        Label(body, text="Change password", size=18, bold=True, bg=C["surface"]).pack(anchor="w")
        Label(body, text="Use the policy chosen in Settings.", size=12, color=C["muted"],
              bg=C["surface"]).pack(anchor="w", pady=(2, 0))
        self._current = _entry(body, "Current password")
        self._new = _entry(body, "New password")
        self._confirm = _entry(body, "Confirm new password")
        self._error = Label(body, size=12, bold=True, color=C["danger"], bg=C["surface"])
        self._error.pack(anchor="w", pady=(10, 0))
        _buttons(body, self.destroy, "Update password", self._save)
        self._current.focus_set()

    def _save(self) -> None:
        try:
            auth_service.change_password(self._user, self._current.get(), self._new.get(),
                                         self._confirm.get())
        except AuthError as exc:
            self._error.configure(text=str(exc))
            return
        self._on_done()
        self.destroy()


def ask_password(master, user: User, reason: str) -> bool:
    """Asks for the signed-in user's password. True only when it is correct."""
    result = {"ok": False}
    dlg = _Dialog(master, "Confirm password", 420, 300)
    body = ctk.CTkFrame(dlg, fg_color=C["surface"])
    body.pack(fill="both", expand=True, padx=26, pady=22)
    Label(body, text="Confirm it is you", size=18, bold=True, bg=C["surface"]).pack(anchor="w")
    Label(body, text=reason, size=12, color=C["muted"], bg=C["surface"], wrap=340
          ).pack(anchor="w", pady=(4, 0))
    entry = _entry(body, "Password")
    error = Label(body, size=12, bold=True, color=C["danger"], bg=C["surface"])
    error.pack(anchor="w", pady=(10, 0))

    def ok(_event=None) -> None:
        if auth_service.confirm_password(user, entry.get()):
            result["ok"] = True
            dlg.destroy()
        else:
            error.configure(text="Incorrect password.")
            entry.delete(0, "end")

    _buttons(body, dlg.destroy, "Confirm", ok)
    entry.bind("<Return>", ok)
    entry.focus_set()
    dlg.wait_window()
    return result["ok"]
