"""Modal dialog listing connected drives. The system drive is shown but cannot be picked."""
import customtkinter as ctk

from services.target_info import DriveInfo, human_size, list_drives
from ui.components.scroll_frame import ScrollFrame
from ui.icons import icon
from ui.light import Box, Label
from ui.theme import C, font


class DrivePicker(ctk.CTkToplevel):
    def __init__(self, master, on_pick):
        super().__init__(master)
        self._on_pick = on_pick
        self._choice = ctk.StringVar(value="")
        self._drives: dict[str, DriveInfo] = {}
        self.title("Select a drive to wipe")
        self.configure(fg_color=C["bg"])
        self.resizable(False, False)
        self.geometry(self._centered(560, 460, master))
        self.transient(master.winfo_toplevel())
        self.after(50, self._bring_to_front)   # CTkToplevel can open behind the main window

        head = Box(self, bg=C["bg"])
        head.pack(fill="x", padx=24, pady=(20, 6))
        Label(head, text="Select a drive", size=18, bold=True).pack(side="left")
        ctk.CTkButton(head, text="Refresh", width=84, height=30, corner_radius=8, font=font(12),
                      fg_color=C["surface"], text_color=C["text"], border_width=1,
                      border_color=C["border"], hover_color=C["green_light"],
                      command=self._load).pack(side="right")
        Label(self, text="Every file on the chosen drive will be destroyed.", size=12,
              color=C["muted"], bg=C["bg"]).pack(fill="x", padx=24)

        foot = Box(self, bg=C["bg"])                  # packed before the list so it never clips
        foot.pack(fill="x", side="bottom", padx=24, pady=(0, 18))
        self._ok = ctk.CTkButton(foot, text="Continue", width=120, height=38, corner_radius=10,
                                 font=font(13, bold=True), fg_color=C["green_dark"],
                                 hover_color=C["green_dark_hover"], state="disabled",
                                 command=self._confirm)
        self._ok.pack(side="right")
        ctk.CTkButton(foot, text="Cancel", width=100, height=38, corner_radius=10, font=font(13),
                      fg_color=C["surface"], text_color=C["text"], border_width=1,
                      border_color=C["border"], hover_color=C["green_light"],
                      command=self.destroy).pack(side="right", padx=10)
        scroll = ScrollFrame(self, bg=C["bg"])
        scroll.pack(fill="both", expand=True, padx=16, pady=10)
        self._list = scroll.inner
        self._load()

    def _bring_to_front(self) -> None:
        self.lift()
        self.focus_force()
        self.grab_set()

    @staticmethod
    def _centered(w, h, master) -> str:
        top = master.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - w) // 2
        y = top.winfo_rooty() + (top.winfo_height() - h) // 3
        return f"{w}x{h}+{max(x, 0)}+{max(y, 0)}"

    def _load(self) -> None:
        for w in self._list.winfo_children():
            w.destroy()
        self._choice.set("")
        self._ok.configure(state="disabled")
        self._drives = {d.root: d for d in list_drives()}
        if not self._drives:
            Label(self._list, text="No drives found. Connect a drive and press Refresh.",
                  color=C["muted"], anchor="center").pack(fill="x", pady=40)
        for d in self._drives.values():
            self._row(d)

    def _row(self, d: DriveInfo) -> None:
        row = ctk.CTkFrame(self._list, fg_color=C["surface"], corner_radius=12,
                           border_width=1, border_color=C["border"])
        row.pack(fill="x", pady=4, padx=4)
        rb = ctk.CTkRadioButton(row, text="", variable=self._choice, value=d.root, width=24,
                                fg_color=C["green_dark"], hover_color=C["green_dark_hover"],
                                command=lambda: self._ok.configure(state="normal"))
        rb.pack(side="left", padx=(14, 4), pady=14)
        ctk.CTkLabel(row, text="", image=icon("drive", C["green_dark"], 26)).pack(side="left",
                                                                                  padx=6)
        text = Box(row, bg=C["surface"])
        text.pack(side="left", fill="x", expand=True, padx=6, pady=8)
        Label(text, text=d.display_name, size=14, bold=True).pack(fill="x")
        meta = f"{d.kind}   {d.filesystem or 'Unknown FS'}   {human_size(d.total)} total, " \
               f"{human_size(d.free)} free"
        Label(text, text=meta, size=11, color=C["muted"]).pack(fill="x")
        if d.is_system:
            rb.configure(state="disabled")
            Label(row, text="System drive, protected", size=11, bold=True, color=C["danger"],
                  bg=C["surface"]).pack(side="right", padx=14)

    def _confirm(self) -> None:
        root = self._choice.get()
        if root:
            self.grab_release()
            self.destroy()
            self._on_pick(root)
