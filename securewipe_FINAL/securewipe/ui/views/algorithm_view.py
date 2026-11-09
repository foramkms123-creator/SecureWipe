"""Algorithms page: shown after "New Erasure Task".

Sections, top to bottom
    1. Target        name, type, total size, used space, free space of the selection
    2. Wipe method   Zero Fill / One Fill / Random Data / DoD 5220.22-M / Gutmann + passes
    3. Progress      percentage, bar, elapsed, remaining, estimated total, current pass
    4. Actions       Start, Stop, Generate Certificate (enabled only at 100 %)

Performance: text uses lightweight Label/Box (ui/light.py) and the page scrolls in
ScrollFrame (ui/components/scroll_frame.py). CTk widgets are kept only where they are
needed (rounded cards, buttons, radio buttons, progress bars).
"""
import os
import threading
import time
from tkinter import messagebox, ttk

import customtkinter as ctk

from config import SIMULATE_WIPE
from services import app_log, certificate, notify_service, report_service
from services import settings_service as sp
from services import target_info as ti
from services.auth_service import User
from services.wipe_engine import CANCELLED, FAILED, SUCCESS, WipeJob, estimate_seconds
from services.wipe_methods import BY_KEY, DEFAULT_METHOD, METHODS
from ui.components.password_dialogs import ask_password
from ui.components.scroll_frame import ScrollFrame
from ui.icons import icon
from ui.light import Box, Label
from ui.theme import C, font

POLL_MS = 200
DASH = "--:--:--"
MAX_TREE_ROWS = 16                 # visible rows of the file tree (it scrolls for more)


def fmt_time(seconds: float | None) -> str:
    if seconds is None or seconds != seconds or seconds == float("inf"):
        return DASH
    s = int(round(max(seconds, 0)))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


class AlgorithmView(ctk.CTkFrame):
    title = "Algorithms"

    def __init__(self, master, user: User, on_new_wipe, on_finished=None, on_certificate=None):
        super().__init__(master, fg_color="transparent")
        self._user = user
        self._on_new_wipe = on_new_wipe          # callback(kind) -> opens the file/folder/drive picker
        self._on_finished = on_finished          # callback() -> refresh dashboard etc.
        self._on_certificate = on_certificate    # callback(op_id) -> shows the certificate
        self._op_id = None                       # row in the detailed log for the current wipe
        self._cert_op_id = None                  # set once the certificate is generated
        self._info: ti.TargetInfo | None = None
        self._job: WipeJob | None = None
        self._poll_job = None
        self._loading = False
        self._method_key = ctk.StringVar(value=DEFAULT_METHOD)
        self._passes = BY_KEY[DEFAULT_METHOD].default_passes
        self._tiles: dict[str, ctk.CTkFrame] = {}
        self._last_cells: dict[str, str] = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._body = None
        self._show_empty()

    # =============================================================================
    # public
    # =============================================================================
    @property
    def busy(self) -> bool:
        return self._job is not None and self._job.is_running

    def set_target(self, kind: str, paths: list[str]) -> bool:
        """Called by the dashboard shell after the user picks something. False if busy."""
        if self.busy:
            return False
        self._job = None
        self._op_id = None
        self._cert_op_id = None
        default = sp.get("default_method")         # Settings > Data Wiping Defaults
        self._method_key.set(default)
        self._passes = BY_KEY[default].default_passes
        self._loading = True               # stays True until the size scan finishes
        self._info = ti.TargetInfo(kind=kind, paths=paths)
        self._build_page()
        self._load_target_async(kind, paths)
        return True

    # =============================================================================
    # empty state (Algorithms clicked with nothing selected)
    # =============================================================================
    def _replace_body(self, widget) -> None:
        if self._body is not None:
            self._body.destroy()
        self._body = widget
        widget.grid(row=0, column=0, sticky="nsew")

    def _show_empty(self) -> None:
        box = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=20)
        inner = Box(box, bg=C["surface"])
        inner.place(relx=0.5, rely=0.45, anchor="center")
        ctk.CTkLabel(inner, text="", image=icon("algorithm", C["green_dark"], 54)).pack()
        Label(inner, text="Choose what to wipe", size=22, bold=True,
              anchor="center").pack(pady=(14, 4))
        Label(inner, text="Pick a file, a folder or a drive. Its details and the wipe methods "
                          "will appear here.", color=C["muted"], anchor="center").pack()
        row = Box(inner)
        row.pack(pady=(20, 0))
        for kind, label in (("file", "Select files"), ("folder", "Select a folder"),
                            ("drive", "Select a drive")):
            ctk.CTkButton(row, text=f"  {label}", image=icon(kind, "#FFFFFF", 18),
                          compound="left", height=40, corner_radius=10, font=font(13, bold=True),
                          fg_color=C["green_dark"], hover_color=C["green_dark_hover"],
                          command=lambda k=kind: self._on_new_wipe(k)).pack(side="left", padx=6)
        self._replace_body(box)

    # =============================================================================
    # page layout
    # =============================================================================
    @property
    def _done(self) -> bool:
        """True once the current target has been wiped to 100 %."""
        if self._job is None or self.busy:
            return False
        p = self._job.snapshot()
        return p.state == SUCCESS and p.fraction >= 1.0

    def _build_page(self) -> None:
        for attr in ("_start_btn", "_cells", "_change_btn"):   # forget widgets of the old page
            self.__dict__.pop(attr, None)
        self._last_cells = {}
        scroll = ScrollFrame(self, bg=C["bg"])
        page = scroll.inner
        page.grid_columnconfigure(0, weight=1)
        self._replace_body(scroll)
        self._build_target(self._section(page, 0, "1", "Selected target"))
        self._build_method(self._section(page, 1, "2", "Wipe method"))
        self._build_progress(self._section(page, 2, "3", "Progress"))
        self._build_actions(self._section(page, 3, "4", "Actions"))
        self._select_method(self._method_key.get(), keep_passes=True)

    def _section(self, parent, row: int, number: str, title: str) -> Box:
        card = ctk.CTkFrame(parent, fg_color=C["surface"], corner_radius=16,
                            border_width=1, border_color=C["border"])
        card.grid(row=row, column=0, sticky="ew", pady=(0, 14), padx=(0, 6))
        card.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(card, fg_color=C["green_light"], corner_radius=12, height=44)
        head.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
        head.pack_propagate(False)
        ctk.CTkLabel(head, text=number, width=26, height=26, corner_radius=13,
                     fg_color=C["green_dark"], text_color="#FFFFFF", font=font(12, bold=True)
                     ).pack(side="left", padx=(14, 10))
        Label(head, text=title, size=15, bold=True, color=C["green_dark"],
              bg=C["green_light"]).pack(side="left")
        body = Box(card, bg=C["surface"])
        body.grid(row=1, column=0, sticky="ew", padx=20, pady=(14, 18))
        body.header = head
        return body

    # ---- 1. target -------------------------------------------------------------
    def _build_target(self, body) -> None:
        body.grid_columnconfigure(1, weight=1)
        kind = self._info.kind
        ctk.CTkLabel(body, text="", width=58, height=58, corner_radius=14,
                     fg_color=C["green_light"],
                     image=icon("drive" if kind == "drive" else kind, C["green_dark"], 30)
                     ).grid(row=0, column=0, rowspan=2, padx=(0, 14))
        self._t_name = Label(body, size=18, bold=True)
        self._t_name.grid(row=0, column=1, sticky="sw")
        self._t_path = Label(body, size=12, color=C["muted"], wrap=620)
        self._t_path.grid(row=1, column=1, sticky="nw")
        self._change_btn = ctk.CTkButton(body.header, text="Change target", width=120, height=30,
                                         corner_radius=8, font=font(12), fg_color=C["surface"],
                                         text_color=C["green_dark"], border_width=1,
                                         border_color=C["green_soft"],
                                         hover_color=C["green_soft"], command=self._change_target)
        self._change_btn.pack(side="right", padx=10)

        tiles = Box(body)
        tiles.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        self._t_tiles = {}
        for i, (key, label) in enumerate((("type", "Type"), ("total", "Total size"),
                                          ("used", "Used space"), ("free", "Free space"))):
            tiles.grid_columnconfigure(i, weight=1, uniform="tile")
            tile = ctk.CTkFrame(tiles, fg_color=C["bg"], corner_radius=12)
            tile.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0 if i == 3 else 6))
            Label(tile, text=label, size=12, color=C["muted"], bg=C["bg"]
                  ).pack(fill="x", padx=14, pady=(10, 0))
            value = Label(tile, text="Calculating…", size=17, bold=True, bg=C["bg"])
            value.pack(fill="x", padx=14)
            sub = Label(tile, text=" ", size=11, color=C["muted"], bg=C["bg"])
            sub.pack(fill="x", padx=14, pady=(0, 8))
            self._t_tiles[key] = (value, sub)

        usage = Box(body)
        usage.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        self._t_usage_lbl = Label(usage, size=11, color=C["muted"])
        self._t_usage_lbl.pack(fill="x")
        self._t_usage = ctk.CTkProgressBar(usage, height=8, corner_radius=4,
                                           fg_color=C["green_light"],
                                           progress_color=C["green"])
        self._t_usage.set(0)
        self._t_usage.pack(fill="x", pady=(4, 0))
        self._t_note = Label(body, size=12, bold=True, color=C["warning"], wrap=760)
        self._t_note.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self._t_files = Box(body)                       # list of the files inside the target
        self._t_files.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        self._render_target()

    def _render_target(self) -> None:
        info = self._info
        self._t_name.configure(text=info.name or (info.paths[0] if info.paths else ""))
        where = info.location if info.kind != "drive" else info.drive_root
        extra = f"   (+{len(info.paths) - 1} more)" if len(info.paths) > 1 else ""
        self._t_path.configure(text=f"{where}{extra}" if where else "")
        self._render_files()
        if self._loading:
            return
        size = ti.human_size
        drive = info.drive_root or "drive"
        self._set_tile("type", info.type_label,
                       info.filesystem or ("" if info.kind == "drive" else f"on {drive}"))
        count = "" if info.kind == "drive" else \
            f"{info.item_count} file{'s' if info.item_count != 1 else ''} to overwrite"
        self._set_tile("total", size(info.total_size), count or f"capacity of {drive}")
        self._set_tile("used", size(info.drive_used), f"on {drive}")
        self._set_tile("free", size(info.drive_free), f"on {drive}")
        frac = info.drive_used / info.drive_total if info.drive_total else 0
        self._t_usage.set(frac)
        self._t_usage_lbl.configure(
            text=f"{frac * 100:.0f}% of {drive} in use ({size(info.drive_total)} capacity)")

        notes = []
        if info.kind == "drive" and info.is_system_drive:
            notes.append("This is the system drive. Wiping it is blocked.")
        if info.kind != "drive" and info.total_size == 0:
            notes.append("Nothing to overwrite: the selection is empty.")
        if info.skipped:
            notes.append(f"{len(info.skipped)} item(s) could not be read and will be skipped "
                         "(check permissions or run as Administrator).")
        self._t_note.configure(text="\n".join(notes))
        self._refresh_estimate()
        self._update_buttons()

    def _set_tile(self, key, value, sub="") -> None:
        v, s = self._t_tiles[key]
        v.configure(text=value)
        s.configure(text=sub or " ")

    def _render_files(self) -> None:
        """Shows every file inside the selection as a folder tree: folders with their total size,
        subfolders and files nested under them, with extension and size. Nothing is cut off."""
        box = self._t_files
        for child in box.winfo_children():
            child.destroy()
        info = self._info
        if info is None or info.kind == "drive" or not info.files:
            box.grid_remove()
            return
        box.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(14, 0))

        root = ti.folder_tree(info.files)
        folders = ti.count_folders(root)
        total = len(info.files)
        size = ti.human_size(info.total_size)
        summary = (f"{total} files in {folders} folder{'s' if folders != 1 else ''}, {size}"
                   if folders else f"{total} file{'s' if total != 1 else ''}, {size}")
        Label(box, text=f"Files in this selection ({summary})", size=14, bold=True,
              color=C["green_dark"], bg=C["surface"]).pack(fill="x", pady=(0, 6))

        tree = ttk.Treeview(box, columns=("ext", "size"), show="tree headings",
                            selectmode="none", style="SW.Treeview",
                            height=max(3, min(total + folders, MAX_TREE_ROWS)))
        tree.heading("#0", text="Name", anchor="w")
        tree.heading("ext", text="Extension", anchor="w")
        tree.heading("size", text="Size", anchor="e")
        tree.column("#0", width=460, minwidth=200, stretch=True, anchor="w")
        tree.column("ext", width=110, minwidth=80, stretch=False, anchor="w")
        tree.column("size", width=120, minwidth=90, stretch=False, anchor="e")
        scroll = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        def add(parent: str, node: dict) -> None:
            for name in sorted(node["dirs"], key=str.lower):
                sub = node["dirs"][name]
                iid = tree.insert(parent, "end", text=name, open=True,
                                  values=("", ti.human_size(sub["size"])))
                add(iid, sub)
            for name, fsize in sorted(node["files"], key=lambda f: f[0].lower()):
                ext = os.path.splitext(name)[1].lstrip(".").upper() or "-"
                tree.insert(parent, "end", text=name, values=(ext, ti.human_size(fsize)))

        add("", root)

    def _load_target_async(self, kind, paths) -> None:
        """Folder sizes can take seconds, so collect them off the UI thread."""
        self._loading = True
        result = {}

        def work():
            try:
                result["info"] = ti.collect(kind, paths)
            except Exception as exc:
                result["error"] = str(exc)

        worker = threading.Thread(target=work, daemon=True)
        worker.start()

        def wait():
            if not self.winfo_exists():
                return
            if worker.is_alive():
                self.after(150, wait)
                return
            self._loading = False
            if "error" in result:
                messagebox.showerror("Could not read target", result["error"])
                return
            self._info = result["info"]
            self._render_target()

        self.after(150, wait)

    def _change_target(self) -> None:
        if not self.busy:
            self._on_new_wipe(self._info.kind if self._info else "file")

    # ---- 2. method -------------------------------------------------------------
    def _build_method(self, body) -> None:
        grid = Box(body)
        grid.pack(fill="x")
        self._tiles.clear()
        for i, m in enumerate(METHODS):
            grid.grid_columnconfigure(i, weight=1, uniform="method")
            tile = ctk.CTkFrame(grid, fg_color=C["surface"], corner_radius=12, border_width=1,
                                border_color=C["border"], height=96)
            tile.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 5,
                                                              0 if i == len(METHODS) - 1 else 5))
            rb = ctk.CTkRadioButton(tile, text=m.name, variable=self._method_key, value=m.key,
                                    font=font(13, bold=True), text_color=C["text"],
                                    fg_color=C["green_dark"], hover_color=C["green_dark_hover"],
                                    border_color=C["muted"], radiobutton_width=18,
                                    radiobutton_height=18,
                                    command=lambda k=m.key: self._select_method(k))
            rb.pack(anchor="w", padx=14, pady=(14, 2))
            desc = Label(tile, text=m.summary, size=11, color=C["muted"], bg=C["surface"])
            desc.pack(fill="x", padx=(42, 10), pady=(0, 12))
            for w in (tile, desc):
                w.bind("<Button-1>", lambda _e, k=m.key: self._select_method(k))
            tile.radio, tile.desc = rb, desc
            self._tiles[m.key] = tile

        row = Box(body)
        row.pack(fill="x", pady=(18, 0))
        Label(row, text="Passes", bold=True).pack(side="left", padx=(2, 14))
        stepper = ctk.CTkFrame(row, fg_color=C["bg"], corner_radius=10, border_width=1,
                               border_color=C["border"])
        stepper.pack(side="left")
        btn = dict(width=36, height=34, corner_radius=8, font=font(16, bold=True),
                   fg_color=C["green_dark"], hover_color=C["green_dark_hover"],
                   text_color="#FFFFFF", text_color_disabled="#FFFFFF")
        self._minus = ctk.CTkButton(stepper, text="−", command=lambda: self._step(-1), **btn)
        self._minus.pack(side="left", padx=4, pady=4)
        self._pass_lbl = Label(stepper, size=16, bold=True, bg=C["bg"], anchor="center",
                               width=4)
        self._pass_lbl.pack(side="left")
        self._plus = ctk.CTkButton(stepper, text="+", command=lambda: self._step(+1), **btn)
        self._plus.pack(side="left", padx=4, pady=4)
        self._pass_hint = Label(row, size=12, color=C["muted"])
        self._pass_hint.pack(side="left", padx=14)

        self._method_detail = Label(body, size=12, color=C["muted"], wrap=780)
        self._method_detail.pack(fill="x", pady=(12, 0))

    def _select_method(self, key: str, keep_passes: bool = False) -> None:
        if self.busy or self._done:
            return
        m = BY_KEY[key]
        self._method_key.set(key)
        if not keep_passes or self._passes not in m.allowed_passes:
            self._passes = m.default_passes
        for k, tile in self._tiles.items():
            on = k == key
            color = C["green_light"] if on else C["surface"]
            if tile.cget("fg_color") != color:           # redraw only the tiles that change
                tile.configure(fg_color=color, border_color=C["green_dark"] if on else C["border"],
                               border_width=2 if on else 1)
                tile.desc.configure(bg=color)
        self._method_detail.configure(text=m.detail)
        self._render_passes()

    def _step(self, direction: int) -> None:
        m = BY_KEY[self._method_key.get()]
        if not (self.busy or self._done):
            self._passes = m.next_passes(self._passes, direction)
            self._render_passes()

    def _render_passes(self) -> None:
        m = BY_KEY[self._method_key.get()]
        self._pass_lbl.configure(text=str(self._passes))
        locked = self.busy or self._done
        for b, d in ((self._minus, -1), (self._plus, +1)):
            ok = not locked and m.can_step(self._passes, d)
            self._set_btn(b, ok, C["green_dark"])
        if m.passes_locked:
            hint = "Fixed at 35 passes for Gutmann"
        elif m.key == "dod":
            hint = "DoD allows 3 passes (standard) or 7 passes (ECE)"
        else:
            hint = f"Choose {m.allowed_passes[0]} to {m.allowed_passes[-1]} passes"
        self._pass_hint.configure(text=hint)
        self._refresh_estimate()

    @staticmethod
    def _set_btn(btn, enabled: bool, color: str) -> None:
        """Reconfigure a CTkButton only when its state really changes (each change = redraw)."""
        state = "normal" if enabled else "disabled"
        if btn.cget("state") != state:
            btn.configure(state=state, fg_color=color if enabled else C["green_soft"])

    # ---- 3. progress -----------------------------------------------------------
    def _build_progress(self, body) -> None:
        if SIMULATE_WIPE:
            ctk.CTkLabel(body.header, text="  Simulation mode: nothing is written to disk  ",
                         font=font(11, bold=True), fg_color=C["orange"], text_color="#FFFFFF",
                         corner_radius=10, height=24).pack(side="right", padx=12)
        top = Box(body)
        top.pack(fill="x")
        self._status = Label(top, text="Ready to start")
        self._status.pack(side="left", anchor="s")
        self._percent = Label(top, text="0%", size=30, bold=True, color=C["green_dark"])
        self._percent.pack(side="right")
        self._bar = ctk.CTkProgressBar(body, height=16, corner_radius=8,
                                       fg_color=C["green_light"], progress_color=C["green_dark"])
        self._bar.set(0)
        self._bar.pack(fill="x", pady=(6, 14))

        cells = Box(body)
        cells.pack(fill="x")
        self._cells = {}
        for i, (key, label) in enumerate((("elapsed", "Elapsed time"),
                                          ("remaining", "Remaining time"),
                                          ("estimated", "Estimated total time"),
                                          ("pass", "Current pass"))):
            cells.grid_columnconfigure(i, weight=1, uniform="cell")
            cell = ctk.CTkFrame(cells, fg_color=C["bg"], corner_radius=12)
            cell.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0 if i == 3 else 6))
            Label(cell, text=label, size=12, color=C["muted"], bg=C["bg"], anchor="center"
                  ).pack(fill="x", pady=(8, 0))
            v = Label(cell, text=DASH, size=17, bold=True, bg=C["bg"], anchor="center")
            v.pack(fill="x", pady=(0, 8))
            self._cells[key] = v

    def _set_cell(self, key: str, text: str) -> None:
        if self._last_cells.get(key) != text:      # skip identical updates
            self._last_cells[key] = text
            self._cells[key].configure(text=text)

    def _refresh_estimate(self) -> None:
        """Before a wipe starts: estimated time from size x passes x nominal speed."""
        if self._job is not None or not hasattr(self, "_cells"):
            return
        if self._loading or not self._info:
            est = None
        else:
            est = estimate_seconds(self._info.total_size, self._passes)
        self._set_cell("elapsed", "00:00:00")
        self._set_cell("remaining", fmt_time(est))
        self._set_cell("estimated", fmt_time(est))
        self._set_cell("pass", f"— / {self._passes}")

    # ---- 4. actions ------------------------------------------------------------
    def _build_actions(self, body) -> None:
        row = Box(body)
        row.pack(fill="x")
        for i in range(3):
            row.grid_columnconfigure(i, weight=1, uniform="act")
        common = dict(height=46, corner_radius=12, font=font(14, bold=True), compound="left",
                      text_color_disabled="#FFFFFF")
        self._start_btn = ctk.CTkButton(row, text="▶  Start wipe", fg_color=C["green_dark"],
                                        hover_color=C["green_dark_hover"],
                                        command=self._start, **common)
        self._start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._stop_btn = ctk.CTkButton(row, text="■  Stop", fg_color=C["danger"],
                                       hover_color="#B94440", command=self._stop, **common)
        self._stop_btn.grid(row=0, column=1, sticky="ew", padx=6)
        self._cert_btn = ctk.CTkButton(row, text="  Generate certificate",
                                       image=icon("document", "#FFFFFF", 18),
                                       fg_color=C["green_dark"], hover_color=C["green_dark_hover"],
                                       command=self._generate_certificate, **common)
        self._cert_btn.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        warn = ctk.CTkFrame(body, fg_color=C["warn_bg"], corner_radius=12)
        warn.pack(fill="x", pady=(14, 0))
        Label(warn, text="⚠", size=20, bold=True, color=C["warning"], bg=C["warn_bg"]
              ).pack(side="left", padx=(16, 10), pady=10)
        Label(warn, text="Wiping cannot be undone. Check the target above before you start; "
                         "the certificate unlocks when progress reaches 100%.",
              size=12, color=C["warn_text"], bg=C["warn_bg"], wrap=760
              ).pack(side="left", fill="x", expand=True, pady=10)
        self._update_buttons()

    def _update_buttons(self) -> None:
        if not hasattr(self, "_start_btn"):
            return
        running = self.busy
        finished_ok = self._done
        info = self._info
        can_start = (not running and not finished_ok and not self._loading and info is not None
                     and info.total_size > 0
                     and not (info.kind == "drive" and info.is_system_drive))
        self._set_btn(self._start_btn, can_start, C["green_dark"])
        self._set_btn(self._stop_btn, running, C["danger"])
        self._set_btn(self._cert_btn, finished_ok, C["green_dark"])     # only at 100 %
        state = "disabled" if running else "normal"
        if self._change_btn.cget("state") != state:
            self._change_btn.configure(state=state)
        radio_state = "disabled" if running or finished_ok else "normal"
        for tile in self._tiles.values():
            if tile.radio.cget("state") != radio_state:
                tile.radio.configure(state=radio_state)

    # =============================================================================
    # wipe run
    # =============================================================================
    def _start(self) -> None:
        info = self._info
        m = BY_KEY[self._method_key.get()]
        msg = (f"Target:  {info.name}\nType:  {info.type_label}\n"
               f"Size:  {ti.human_size(info.total_size)}\n"
               f"Method:  {m.name}, {self._passes} pass(es)\n\n"
               "All data in this target will be permanently destroyed. Continue?")
        if not messagebox.askyesno("Confirm wipe", msg, icon="warning"):
            return
        if sp.get("require_password") and not ask_password(
                self, self._user, "Enter your password to start this wipe."):
            return
        self._job = WipeJob(info, m, self._passes)
        self._job.start()
        self._op_id = None             # a new run gets its own row in the detailed log
        self._cert_op_id = None
        self._last_bar = -1
        self._render_passes()          # locks the stepper
        self._update_buttons()
        self._poll()

    def _stop(self) -> None:
        if self.busy and messagebox.askyesno(
                "Stop wipe", "Stop now? The target will be left partly overwritten."):
            self._job.cancel()

    def _poll(self) -> None:
        p = self._job.snapshot()
        elapsed = time.time() - p.started_at
        frac = p.fraction
        pct = int(frac * 100)
        if round(frac, 3) != self._last_bar:       # progress bar redraw only when it moves
            self._last_bar = round(frac, 3)
            self._bar.set(frac)
        if self._percent.cget("text") != f"{pct}%":
            self._percent.configure(text=f"{pct}%")
        rate = p.bytes_done / elapsed if elapsed > 0.5 and p.bytes_done else 0
        remaining = (p.bytes_total - p.bytes_done) / rate if rate else None
        self._set_cell("elapsed", fmt_time(elapsed))
        self._set_cell("remaining", fmt_time(remaining))
        self._set_cell("estimated", fmt_time(elapsed + remaining) if remaining is not None else DASH)
        self._set_cell("pass", f"{p.pass_no} / {p.passes}")

        if self._job.is_running:
            text = f"Wiping: pass {p.pass_no} of {p.passes}, writing {p.pattern}"
            if self._status.cget("text") != text:
                self._status.configure(text=text, fg=C["text"])
            self._poll_job = self.after(POLL_MS, self._poll)
            return

        # finished
        self._poll_job = None
        total = (p.finished_at or time.time()) - p.started_at
        self._set_cell("elapsed", fmt_time(total))
        self._record_wipe(p)                # in the detailed log now, with Report = No
        if p.state == SUCCESS:
            self._bar.set(1)
            self._percent.configure(text="100%")
            self._set_cell("remaining", "00:00:00")
            self._set_cell("estimated", fmt_time(total))
            self._status.configure(text="Completed. You can now generate the certificate.",
                                   fg=C["success"])
        elif p.state == CANCELLED:
            self._status.configure(text="Stopped by user. The target was only partly wiped.",
                                   fg=C["warning"])
        elif p.state == FAILED:
            self._status.configure(text=f"Failed: {p.error}", fg=C["danger"])
        self._render_passes()
        self._update_buttons()
        if p.state != SUCCESS:
            self._job = None           # allow a fresh start with the same target
            self._update_buttons()
        if p.state == SUCCESS:
            notify_service.notify(self._user.id, "wipe_done",
                                  f"Wipe completed: {self._info.name}.")
            if sp.get("auto_certificate"):
                self._auto_certificate()
        elif p.state in (FAILED, CANCELLED):
            verb = "stopped" if p.state == CANCELLED else "failed"
            notify_service.notify(self._user.id, "wipe_failed",
                                  f"Wipe {verb}: {self._info.name}.")
        if self._on_finished:
            self._on_finished()

    def _record_wipe(self, p) -> None:
        """Adds the finished wipe to the detailed log (once per wipe, whatever its result)."""
        if self._op_id is not None or self._info is None or self._job is None:
            return
        try:
            self._op_id = certificate.record_wipe(
                self._user, self._info, self._job.method.name, self._job.passes,
                started_ts=p.started_at, finished_ts=p.finished_at,
                state=p.state, simulated=SIMULATE_WIPE)
        except Exception:
            app_log.log_exception("Saving the wipe to the detailed log failed")
            messagebox.showerror("Wipe log", "The wipe finished, but it could not be saved to "
                                             "the detailed log. See data/app.log.")

    def _issue_certificate(self) -> int | None:
        """Generates the certificate for a successful wipe (once). Returns its operation id."""
        if self._cert_op_id is not None:
            return self._cert_op_id
        if self._op_id is None:
            return None
        try:
            certificate.issue(self._op_id)
        except Exception as exc:
            messagebox.showerror("Certificate", f"The certificate could not be saved:\n{exc}")
            return None
        op_id = self._op_id
        self._cert_op_id = op_id
        self._cert_btn.configure(text="  View certificate")
        cert = report_service.get_certificate(self._user, op_id)
        if cert is not None:
            notify_service.notify(self._user.id, "certificate",
                                  f"Certificate {cert.certificate_id} is ready in Reports.")
        if self._on_finished:
            self._on_finished()                 # dashboard and Reports list update
        return op_id

    def _auto_certificate(self) -> None:
        """Settings > Generate PDF certificate automatically: record and save the PDF."""
        op_id = self._issue_certificate()
        cert = report_service.get_certificate(self._user, op_id) if op_id else None
        if cert is None:
            return
        try:
            path = sp.reports_dir() / f"{cert.certificate_id}.pdf"
            path.parent.mkdir(parents=True, exist_ok=True)
            certificate.save_pdf(cert, str(path))
        except OSError as exc:
            messagebox.showerror("Certificate",
                                 f"The certificate was recorded but the PDF could not be saved:\n{exc}")
            return
        self._status.configure(text=f"Completed. Certificate saved as {path.name}.",
                               fg=C["success"])

    def _generate_certificate(self) -> None:
        if not self._done or self._job is None:
            return
        op_id = self._issue_certificate()
        if op_id is not None and self._on_certificate:
            self._on_certificate(op_id)

    def destroy(self):
        if self._poll_job:
            self.after_cancel(self._poll_job)
        if self.busy:
            self._job.cancel()
        super().destroy()
