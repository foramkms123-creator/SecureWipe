"""Logo splash shown for SPLASH_DURATION_MS."""
import customtkinter as ctk

from config import APP_NAME, APP_VERSION, SPLASH_DURATION_MS
from ui import assets
from ui.theme import C, font

STEP_MS = 40


class SplashScreen(ctk.CTkFrame):
    def __init__(self, master, on_done):
        super().__init__(master, fg_color=C["surface"], corner_radius=0)
        self._on_done = on_done
        self._elapsed = 0
        self._job = None

        box = ctk.CTkFrame(self, fg_color="transparent")
        box.place(relx=0.5, rely=0.46, anchor="center")
        ctk.CTkLabel(box, text="", image=assets.logo(230)).pack()
        ctk.CTkLabel(box, text=APP_NAME, font=font(30, bold=True),
                     text_color=C["text"]).pack(pady=(18, 2))
        ctk.CTkLabel(box, text="Secure data sanitization", font=font(14, italic=True),
                     text_color=C["muted"]).pack()

        self._bar = ctk.CTkProgressBar(box, width=260, height=4, corner_radius=2,
                                       progress_color=C["primary"], fg_color=C["border"])
        self._bar.set(0)
        self._bar.pack(pady=(28, 0))

        ctk.CTkLabel(self, text=f"Version {APP_VERSION}", font=font(11),
                     text_color=C["muted"]).place(relx=0.5, rely=0.95, anchor="center")
        self._job = self.after(STEP_MS, self._tick)

    def _tick(self):
        self._elapsed += STEP_MS
        self._bar.set(min(self._elapsed / SPLASH_DURATION_MS, 1))
        if self._elapsed >= SPLASH_DURATION_MS:
            self._job = None
            self._on_done()
        else:
            self._job = self.after(STEP_MS, self._tick)

    def destroy(self):
        if self._job:
            self.after_cancel(self._job)
        super().destroy()
