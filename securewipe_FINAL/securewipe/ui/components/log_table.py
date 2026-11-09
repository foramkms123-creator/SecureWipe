"""Scrollable detailed log (ttk.Treeview styled to match the app)."""
from tkinter import ttk

import customtkinter as ctk

from ui.theme import C, font

# key, heading, width, anchor, stretch
COLUMNS = [
    ("date", "Date", 100, "w", False),
    ("day", "Day", 90, "w", False),
    ("time", "Time", 80, "w", False),
    ("user", "User", 100, "w", False),
    ("file_name", "File name", 180, "w", True),
    ("location", "File location", 220, "w", True),
    ("algorithm", "Algorithm", 130, "w", False),
    ("passes", "Passes", 60, "center", False),
    ("status", "Status", 170, "w", False),
    ("report", "Report", 70, "center", False),
]


class LogTable(ctk.CTkFrame):
    def __init__(self, master, show_user: bool):
        super().__init__(master, fg_color=C["surface"], corner_radius=14,
                         border_width=1, border_color=C["border"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        keys = [c[0] for c in COLUMNS]
        self._tree = ttk.Treeview(self, columns=keys, show="headings", style="SW.Treeview")
        for key, heading, width, anchor, stretch in COLUMNS:
            self._tree.heading(key, text=heading, anchor=anchor)
            self._tree.column(key, width=width, minwidth=50, anchor=anchor, stretch=stretch)
        self._tree["displaycolumns"] = keys if show_user else [k for k in keys if k != "user"]

        self._tree.tag_configure("odd", background=C["row_alt"])
        self._tree.tag_configure("failed", foreground=C["danger"])
        self._tree.tag_configure("limited", foreground=C["warning"])

        ys = ctk.CTkScrollbar(self, orientation="vertical", command=self._tree.yview)
        xs = ctk.CTkScrollbar(self, orientation="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self._tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
        ys.grid(row=0, column=1, sticky="ns", pady=8)
        xs.grid(row=1, column=0, sticky="ew", padx=8)

        self._empty = ctk.CTkLabel(self, text="No wipes yet. Use New Erasure Task (+) to start one.",
                                   font=font(13, italic=True), text_color=C["muted"],
                                   fg_color=C["surface"])

    def set_rows(self, rows) -> None:
        self._tree.delete(*self._tree.get_children())
        for i, r in enumerate(rows):
            tags = ["odd"] if i % 2 else []
            if r.status in ("Failed", "Cancelled"):
                tags.append("failed")
            elif r.status == "Success With Limitations":
                tags.append("limited")
            self._tree.insert("", "end", tags=tags, values=(
                r.date, r.day, r.time, r.user, r.file_name, r.location,
                r.algorithm, r.passes, r.status, r.report))
        if rows:
            self._empty.place_forget()
        else:
            self._empty.place(relx=0.5, rely=0.55, anchor="center")
