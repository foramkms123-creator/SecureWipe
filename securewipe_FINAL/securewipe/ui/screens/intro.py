"""White introduction page: what the app does, what it needs, its limitations."""
import customtkinter as ctk

from ui import assets
from ui.components.scroll_frame import ScrollFrame
from ui.content import onboarding_text as T
from ui.light import Box, Label
from ui.theme import C, font

TEXT_WIDTH = 720


class IntroScreen(ctk.CTkFrame):
    def __init__(self, master, on_continue):
        super().__init__(master, fg_color=C["surface"], corner_radius=0)

        footer = ctk.CTkFrame(self, fg_color=C["surface"], height=76, corner_radius=0,
                              border_width=1, border_color=C["border"])
        footer.pack(fill="x", side="bottom")  # packed first so it never gets clipped
        ctk.CTkButton(footer, text="Continue reading", font=font(14, bold=True), height=42,
                      width=200, corner_radius=10, fg_color=C["primary"],
                      hover_color=C["primary_hover"], command=on_continue
                      ).place(relx=0.5, rely=0.5, anchor="center")

        body = ScrollFrame(self, bg=C["surface"], bar_color=C["border"], bar_hover=C["primary"])
        body.pack(fill="both", expand=True)
        col = Box(body.inner, bg=C["surface"])
        col.pack(pady=(40, 20))

        head = Box(col)
        head.pack(fill="x")
        ctk.CTkLabel(head, text="", image=assets.logo(48)).pack(side="left")
        Label(head, text=T.INTRO_TITLE, size=28, bold=True).pack(side="left", padx=16)

        Label(col, text=T.INTRO_LEAD, size=15, wrap=TEXT_WIDTH).pack(fill="x", pady=(22, 6))

        for title, points in T.INTRO_SECTIONS:
            Label(col, text=title, size=17, bold=True, color=C["primary"]
                  ).pack(fill="x", pady=(24, 8))
            for p in points:
                row = Box(col)
                row.pack(fill="x", pady=3)
                Label(row, text="•", size=14, bold=True, color=C["orange"], anchor="n", width=2
                      ).pack(side="left", anchor="n")
                Label(row, text=p, size=14, wrap=TEXT_WIDTH - 30).pack(side="left", fill="x")
