"""Stand-in for sections that are built next (Settings, Reports, Algorithms, Help)."""
import customtkinter as ctk

from ui.theme import C, font


class PlaceholderView(ctk.CTkFrame):
    def __init__(self, master, title: str):
        super().__init__(master, fg_color=C["surface"], corner_radius=20)
        self.title = title
        ctk.CTkLabel(self, text=title, font=font(24, bold=True), text_color=C["text"]
                     ).place(relx=0.5, rely=0.45, anchor="center")
        ctk.CTkLabel(self, text="This section connects here in the next build step.",
                     font=font(14), text_color=C["muted"]
                     ).place(relx=0.5, rely=0.53, anchor="center")
