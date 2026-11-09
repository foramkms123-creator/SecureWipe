"""Coloured overview card (icon tile, big number, label).

Text uses plain tk labels (ui/light.py): cheaper to draw than CTkLabel."""
import customtkinter as ctk

from ui.light import Box, Label
from ui.theme import font, lighten


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title: str, color: str, icon: str):
        super().__init__(master, fg_color=color, corner_radius=14, height=100)
        self.pack_propagate(False)
        # icon may be a text symbol or a CTkImage (drawn icon)
        is_image = isinstance(icon, ctk.CTkImage)
        ctk.CTkLabel(self, text="" if is_image else icon, image=icon if is_image else None,
                     width=44, height=44, corner_radius=10,
                     fg_color=lighten(color, 0.22), text_color="white",
                     font=font(19, bold=True)).pack(side="left", padx=(16, 12))
        text = Box(self, bg=color)
        text.pack(side="left", fill="x", expand=True)
        self._value = Label(text, text="0", size=26, bold=True, color="white", bg=color, ipady=0)
        self._value.pack(fill="x")
        self._title = Label(text, text=title, size=12, color="white", bg=color, ipady=0)
        self._title.pack(fill="x")
        self._sub = Label(text, text="", size=11, italic=True, color="white", bg=color, ipady=0)
        self._shown = (None, None)

    def update_value(self, value, subtitle: str = "") -> None:
        if self._shown == (value, subtitle):       # nothing changed: no redraw
            return
        self._shown = (value, subtitle)
        self._value.configure(text=str(value))
        self._sub.configure(text=subtitle)
        if subtitle:
            self._sub.pack(fill="x")
        else:
            self._sub.pack_forget()
