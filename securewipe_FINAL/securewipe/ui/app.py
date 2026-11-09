"""Main window and screen router: splash -> intro -> permissions -> auth -> dashboard."""
import time

import customtkinter as ctk
from PIL import ImageTk

from config import APP_NAME
from services import notify_service, settings_service, sound_service
from services import system_service
from services.auth_service import User
from ui import assets
from ui.components.toast import ToastStack
from ui.theme import C, apply_palette, apply_ttk_styles

IDLE_CHECK_MS = 15000        # how often the auto-lock timer looks at the time since last input


class SecureWipeApp(ctk.CTk):
    WIDTH, HEIGHT = 1320, 800

    def __init__(self):
        super().__init__()
        apply_palette("light")              # sign-in screens are always light
        self.title(APP_NAME)
        self.minsize(1100, 680)
        self.configure(fg_color=C["bg"])
        self._center(self.WIDTH, self.HEIGHT)
        self._set_icon()
        apply_ttk_styles(self)

        self.current_user: User | None = None
        self._screen = None
        self._toasts = ToastStack(self)     # notification banners, above every screen
        self._last_input = time.time()
        self.bind_all("<Any-KeyPress>", self._note_input, add="+")
        self.bind_all("<Any-ButtonPress>", self._note_input, add="+")
        self.bind_all("<Motion>", self._note_input, add="+")
        self._idle_job = self.after(IDLE_CHECK_MS, self._check_idle)
        self.show_splash()

    # ---- auto-lock (Settings > Auto-lock after inactivity) ---------------------
    def _note_input(self, _event=None) -> None:
        self._last_input = time.time()

    def _check_idle(self) -> None:
        self._idle_job = self.after(IDLE_CHECK_MS, self._check_idle)
        if self.current_user is None:
            return
        limit = settings_service.get("auto_lock_minutes") * 60
        busy = getattr(self._screen, "busy", False)       # never lock during a wipe
        if not busy and time.time() - self._last_input > limit:
            self._last_input = time.time()
            self.logout()

    def _set_icon(self) -> None:
        if system_service.is_windows():
            self.iconbitmap(assets.window_icon_ico())   # also stops CTk replacing it
        else:
            self._icon = ImageTk.PhotoImage(assets.logo_pil(64))
            self.iconphoto(True, self._icon)

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = max((self.winfo_screenheight() - h) // 2 - 20, 0)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _swap(self, screen) -> None:
        """Show the new screen fully drawn, then remove the old one.
        (Destroying first showed an empty window while the next screen was drawn piece by piece.)"""
        old, self._screen = self._screen, screen
        screen.place(x=0, y=0, relwidth=1, relheight=1)
        screen.lift()
        self._toasts.lift()
        self.update_idletasks()
        if old is not None:
            old.destroy()

    # ---- flow -------------------------------------------------------------
    def show_splash(self):
        from ui.screens.splash import SplashScreen
        self._swap(SplashScreen(self, on_done=self._after_splash))

    def _after_splash(self):
        if system_service.onboarding_required():
            self.show_intro()
        else:
            self.show_auth()

    def show_intro(self):
        from ui.screens.intro import IntroScreen
        self._swap(IntroScreen(self, on_continue=self.show_permissions))

    def show_permissions(self):
        from ui.screens.permissions import PermissionsScreen
        self._swap(PermissionsScreen(self, on_back=self.show_intro, on_next=self.show_auth))

    def show_auth(self):
        from ui.screens.auth import AuthScreen
        apply_palette("light", self)        # sign-in and sign-up stay light whatever the theme
        self.configure(fg_color=C["bg"])
        notify_service.set_listener(None)
        self._toasts.place_forget()
        self._swap(AuthScreen(self, on_success=self.show_dashboard))

    def show_dashboard(self, user: User, start: str = "dashboard"):
        from ui.screens.dashboard import DashboardScreen
        self.current_user = user
        theme = settings_service.resolve_theme(settings_service.get("theme"))
        apply_palette(theme, self)          # Settings > Theme
        self.configure(fg_color=C["bg"])
        self._swap(DashboardScreen(self, user, on_logout=self.logout, start=start,
                                   on_settings_saved=self._settings_saved))
        notify_service.set_listener(self._on_notification)

    def _on_notification(self, title: str, message: str, kind: str,
                         show_banner: bool, sound: str) -> None:
        """Called by services/notify_service.py when a wipe finishes, fails or a certificate is made."""
        if show_banner:
            self._toasts.show(title, message, kind)
        sound_service.play(sound)           # 'off' is silent

    def _settings_saved(self) -> bool:
        """Called after Save Changes on the Settings page. Rebuilds the signed-in screens so
        every setting (theme, dates, ...) is applied. False while a wipe runs: the wipe screen
        must not be rebuilt, so the new theme waits for the next rebuild."""
        if getattr(self._screen, "busy", False):
            return False
        self.show_dashboard(self.current_user, start="settings")
        return True

    def logout(self):
        self.current_user = None
        self.show_auth()
