"""Fast scrolling container (replacement for ctk.CTkScrollableFrame).

What makes it smoother:
  * Mouse-wheel ticks are collected and applied at most once per frame (~16 ms)
    instead of one full repaint per tick.
  * Dragging the scrollbar is throttled the same way.
  * Width / scroll-region updates after a resize are merged into one idle update,
    so maximising the window does not re-layout the page dozens of times.
  * One global wheel handler per window (not one per scroll area).

Usage:
    sf = ScrollFrame(parent, bg=C["bg"])
    sf.grid(...)
    Label(sf.inner, text="...").pack()
"""
import sys
import tkinter as tk

import customtkinter as ctk

from ui.light import scaling
from ui.theme import C

FRAME_MS = 16
WHEEL_PX = 70          # pixels (CTk units) per wheel notch


class ScrollFrame(tk.Frame):
    def __init__(self, master, bg=None, bar_color=None, bar_hover=None):
        bg = bg or C["bg"]
        super().__init__(master, bg=bg, bd=0, highlightthickness=0)
        self._s = scaling(master)
        self._pending_px = 0.0
        self._pending_moveto = None
        self._flush_job = None
        self._layout_job = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg=bg, bd=0, highlightthickness=0, yscrollincrement=1)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.bar = ctk.CTkScrollbar(self, orientation="vertical", command=self._on_bar,
                                    fg_color=bg, button_color=bar_color or C["green_soft"],
                                    button_hover_color=bar_hover or C["green_dark"])
        self.bar.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        self.canvas.configure(yscrollcommand=self.bar.set)

        self.inner = tk.Frame(self.canvas, bg=bg, bd=0, highlightthickness=0)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._request_layout, add="+")
        self.canvas.bind("<Configure>", self._request_layout, add="+")
        self.inner._scroll_owner = self          # lets the wheel handler find us quickly
        self.canvas._scroll_owner = self
        _install_wheel(self._root())

    # ---- layout (merged into one idle update) ---------------------------------
    def _request_layout(self, _event=None):
        if self._layout_job is None:
            self._layout_job = self.after_idle(self._do_layout)

    def _do_layout(self):
        self._layout_job = None
        width = self.canvas.winfo_width()
        if width > 1 and int(float(self.canvas.itemcget(self._win, "width") or 0)) != width:
            self.canvas.itemconfigure(self._win, width=width)
        height = max(self.inner.winfo_reqheight(), self.canvas.winfo_height())
        self.canvas.configure(scrollregion=(0, 0, width, height))

    # ---- scrolling (at most one repaint per frame) ----------------------------
    def wheel(self, notches: float):
        self._pending_px += -notches * WHEEL_PX * self._s
        self._schedule_flush()

    def _on_bar(self, *args):
        if args and args[0] == "moveto":         # dragging the scrollbar
            self._pending_moveto = float(args[1])
            self._schedule_flush()
        elif args and args[0] == "scroll":       # wheel over the scrollbar (CTk sends delta/40)
            self.wheel(-float(args[1]) / 3)

    def _schedule_flush(self):
        if self._flush_job is None:
            self._flush_job = self.after(FRAME_MS, self._flush)

    def _flush(self):
        self._flush_job = None
        if self._pending_moveto is not None:
            self.canvas.yview_moveto(self._pending_moveto)
            self._pending_moveto = None
        if abs(self._pending_px) >= 1:
            self.canvas.yview_scroll(int(self._pending_px), "units")
            self._pending_px = 0.0

    def scroll_to_top(self):
        self.canvas.yview_moveto(0)

    def destroy(self):
        for job in (self._flush_job, self._layout_job):
            if job:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
        super().destroy()


# ---- one wheel handler for the whole app (bind_all is app-wide) -------------------------------------
def _find_owner(widget):
    w = widget
    while w is not None:
        if isinstance(w, ctk.CTkScrollbar):
            return None                          # the scrollbar handles its own wheel
        owner = getattr(w, "_scroll_owner", None)
        if owner is not None:
            return owner
        w = getattr(w, "master", None)
    return None


def _install_wheel(top):
    if getattr(top, "_sw_wheel_installed", False):
        return
    top._sw_wheel_installed = True

    def target(event):
        try:
            return _find_owner(top.winfo_containing(event.x_root, event.y_root))
        except (KeyError, tk.TclError):
            return None

    def on_wheel(event):
        owner = target(event)
        if owner is not None and owner.winfo_exists():
            step = event.delta / 120 if sys.platform != "darwin" else event.delta / 3
            owner.wheel(step)

    def on_linux(event, direction):
        owner = target(event)
        if owner is not None and owner.winfo_exists():
            owner.wheel(direction)

    top.bind_all("<MouseWheel>", on_wheel, add="+")
    top.bind_all("<Button-4>", lambda e: on_linux(e, 1), add="+")
    top.bind_all("<Button-5>", lambda e: on_linux(e, -1), add="+")
