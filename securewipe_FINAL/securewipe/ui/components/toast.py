"""Pop-up banners at the top right of the window (like Windows notifications).

At most three are shown at once. Each closes after a few seconds, or when its close button is
pressed. The stack is placed above the current screen by the app window (see ui/app.py)."""
import customtkinter as ctk

from ui.light import Box, Label
from ui.theme import C, font

MAX_TOASTS = 3
SECONDS_VISIBLE = 7


class ToastStack(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._cards: list[tuple[ctk.CTkFrame, str]] = []   # (card, pending close job)

    def show(self, title: str, message: str, kind: str = "ok") -> None:
        """kind: 'ok' (green) or 'bad' (red)."""
        accent = C["danger"] if kind == "bad" else C["green_dark"]
        while len(self._cards) >= MAX_TOASTS:
            self._dismiss(self._cards[0][0])

        card = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=12, border_width=1,
                            border_color=C["border"])
        card.pack(side="top", anchor="e", pady=(0, 10))

        Box(card, bg=accent, width=6).pack(side="left", fill="y")
        body = Box(card, bg=C["surface"])
        body.pack(side="left", fill="both", expand=True, padx=(14, 8), pady=12)

        head = Box(body, bg=C["surface"])
        head.pack(fill="x")
        Label(head, text=title, size=13, bold=True, color=accent, bg=C["surface"]
              ).pack(side="left")
        ctk.CTkButton(head, text="×", width=26, height=26, corner_radius=8,
                      font=font(15, bold=True), fg_color="transparent", text_color=C["muted"],
                      hover_color=C["green_light"],
                      command=lambda c=card: self._dismiss(c)).pack(side="right")

        Label(body, text=message, size=12, color=C["text"], bg=C["surface"], wrap=320
              ).pack(fill="x", pady=(4, 0))

        job = self.after(SECONDS_VISIBLE * 1000, lambda c=card: self._dismiss(c))
        self._cards.append((card, job))
        self.place(relx=1.0, x=-24, y=24, anchor="ne")
        self.lift()

    def _dismiss(self, card) -> None:
        for i, (c, job) in enumerate(self._cards):
            if c is card:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
                del self._cards[i]
                break
        try:
            card.destroy()
        except Exception:
            pass
        if not self._cards:
            self.place_forget()          # an empty stack must not sit over the screen
