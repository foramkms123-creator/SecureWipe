"""Top bar: page title with live day/date/time, notifications bell, user menu."""
import tkinter as tk
from datetime import datetime

import customtkinter as ctk

from config import FONT_FAMILY
from services import dashboard_service, settings_service
from services.auth_service import User
from ui.components.popup import popup_below
from ui.light import Box, Label
from ui.theme import C, font


class TopBar(ctk.CTkFrame):
    def __init__(self, master, user: User, on_logout):
        super().__init__(master, fg_color="transparent", height=84)
        self._user = user
        self._clock_job = None
        self.grid_columnconfigure(1, weight=1)

        # title + date
        # title + clock use light labels: the clock changes every second
        left = Box(self)
        left.grid(row=0, column=0, sticky="w")
        self._title = Label(left, text="Dashboard", size=22, bold=True)
        self._title.pack(anchor="w")
        when = Box(left)
        when.pack(anchor="w", pady=(2, 0))
        self._day = Label(when, text="", bold=True, color=C["primary"])
        self._day.pack(side="left")
        self._date = Label(when, text="", color=C["muted"])
        self._date.pack(side="left", padx=(6, 0))

        # bell with unread badge
        bell_box = ctk.CTkFrame(self, fg_color="transparent", width=48, height=48)
        bell_box.grid(row=0, column=2, padx=(0, 22))
        self._bell = ctk.CTkButton(bell_box, text="🔔", width=44, height=44, corner_radius=12,
                                   font=font(18), fg_color=C["surface"], hover_color=C["hero"],
                                   text_color=C["text"], command=self._open_notifications)
        self._bell.place(relx=0.5, rely=0.5, anchor="center")
        self._badge = ctk.CTkLabel(bell_box, text="", width=18, height=18, corner_radius=9,
                                   fg_color=C["orange"], text_color="white", font=font(10, bold=True))

        # user chip
        chip = ctk.CTkFrame(self, fg_color="transparent")
        chip.grid(row=0, column=3)
        ctk.CTkLabel(chip, text=user.initials, width=42, height=42, corner_radius=10,
                     fg_color=C["hero"], text_color=C["primary"], font=font(15, bold=True)
                     ).pack(side="left")
        self._user_btn = ctk.CTkButton(chip, text=f"{user.full_name}   ▾", font=font(14),
                                       fg_color="transparent", hover_color=C["hero"],
                                       text_color=C["text"], height=42, command=self._open_user_menu)
        self._user_btn.pack(side="left", padx=(6, 0))

        self._user_menu = tk.Menu(self, tearoff=0, font=(FONT_FAMILY, 11))
        self._user_menu.add_command(label=f"@{user.username}  ({user.role.title()})", state="disabled")
        self._user_menu.add_separator()
        self._user_menu.add_command(label="Sign out", command=on_logout)

        self._tick()
        self.refresh_notifications()

    # ---- clock ------------------------------------------------------------
    def _tick(self):
        now = datetime.now()
        day = now.strftime("%A,")
        if self._day.cget("text") != day:
            self._day.configure(text=day)
        # read the Date format setting on every tick, so a change in Settings shows at once
        self._date.configure(text=f"{settings_service.format_date(now)}   {now:%H:%M:%S}")
        self._clock_job = self.after(1000 - now.microsecond // 1000, self._tick)

    def set_title(self, text: str) -> None:
        if self._title.cget("text") != text:
            self._title.configure(text=text)

    # ---- notifications ----------------------------------------------------
    def refresh_notifications(self) -> None:
        unread, _ = dashboard_service.get_notifications(self._user)
        if unread:
            self._badge.configure(text=str(min(unread, 9)) + ("+" if unread > 9 else ""))
            self._badge.place(relx=1.0, rely=0.0, anchor="ne")
        else:
            self._badge.place_forget()

    def _open_notifications(self):
        _, items = dashboard_service.get_notifications(self._user)
        menu = tk.Menu(self, tearoff=0, font=(FONT_FAMILY, 11))
        if not items:
            menu.add_command(label="No notifications", state="disabled")
        for n in items:
            when = settings_service.format_datetime(datetime.fromisoformat(n["created_at"]))
            mark = "●  " if not n["is_read"] else "    "
            menu.add_command(label=f"{mark}{n['message']}   ({when})")
        popup_below(menu, self._bell, dx=-220)
        dashboard_service.mark_notifications_read(self._user)
        self.refresh_notifications()

    def _open_user_menu(self):
        popup_below(self._user_menu, self._user_btn)

    def destroy(self):
        if self._clock_job:
            self.after_cancel(self._clock_job)
        super().destroy()
