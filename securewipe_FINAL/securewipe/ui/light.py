"""Lightweight widgets for static text and layout.

Why: every CTkLabel / CTkFrame is a full Tk canvas that is redrawn on scroll and resize.
Plain tk.Label / tk.Frame are drawn natively by Windows and are many times cheaper.
Use these for text and invisible layout boxes; keep CTk for rounded cards, buttons,
entries, radio buttons and progress bars.

Both classes follow CustomTkinter's DPI scaling, so sizes and paddings match CTk widgets.
"""
import tkinter as tk

from config import FONT_FAMILY
from ui.theme import C

_PAD_KEYS = ("padx", "pady", "ipadx", "ipady", "x", "y")


def scaling(widget) -> float:
    """CustomTkinter widget scaling (1.0, 1.25, 1.5 ...) for the window holding `widget`."""
    w = widget
    while w is not None:
        getter = getattr(w, "_get_widget_scaling", None)
        if getter is not None:
            try:
                return float(getter())
            except Exception:
                break
        w = getattr(w, "master", None)
    return 1.0


def bg_of(widget) -> str:
    """Background colour a child of `widget` should use (walks up past 'transparent')."""
    w = widget
    while w is not None:
        try:
            color = w.cget("fg_color")              # CTk widgets
        except (tk.TclError, ValueError, AttributeError):
            try:
                return w.cget("bg")                 # plain tk widgets
            except (tk.TclError, AttributeError):
                color = None
        if color and color != "transparent":
            return color[0] if isinstance(color, (list, tuple)) else color
        w = getattr(w, "master", None)
    return C["bg"]


def tk_font(size: int, bold=False, italic=False, scale=1.0) -> tuple:
    style = " ".join(s for s in ("bold" if bold else "", "italic" if italic else "") if s)
    return (FONT_FAMILY, -round(size * scale), style) if style else (FONT_FAMILY, -round(size * scale))


def _scaled(kw: dict, s: float) -> dict:
    out = dict(kw)
    for k in _PAD_KEYS:
        if k in out:
            v = out[k]
            out[k] = tuple(round(i * s) for i in v) if isinstance(v, (tuple, list)) else round(v * s)
    return out


class _ScaledGeometry:
    """pack/grid/place with paddings given in CTk units (scaled like CTk widgets)."""
    _s = 1.0

    def pack(self, **kw):
        return tk.Pack.pack_configure(self, **_scaled(kw, self._s))

    def grid(self, **kw):
        return tk.Grid.grid_configure(self, **_scaled(kw, self._s))

    def place(self, **kw):
        return tk.Place.place_configure(self, **_scaled(kw, self._s))


class Label(_ScaledGeometry, tk.Label):
    """Static text. `wrap` is the wrap width in CTk units (0 = no wrapping)."""

    def __init__(self, master, text="", size=13, bold=False, italic=False, color=None,
                 bg=None, wrap=0, anchor="w", justify="left", ipady=3, **kw):
        self._s = scaling(master)
        super().__init__(master, text=text, font=tk_font(size, bold, italic, self._s),
                         fg=color or C["text"], bg=bg or bg_of(master), anchor=anchor,
                         justify=justify, bd=0, highlightthickness=0, padx=0,
                         pady=round(ipady * self._s), wraplength=round(wrap * self._s), **kw)

    def set_wrap(self, width_px_real: int) -> None:
        """Wrap width in real screen pixels (e.g. from a <Configure> event)."""
        if int(float(str(self.cget("wraplength")))) != width_px_real:
            self.configure(wraplength=width_px_real)


class Box(_ScaledGeometry, tk.Frame):
    """Invisible layout container (replacement for CTkFrame(fg_color='transparent'))."""

    def __init__(self, master, bg=None, **kw):
        self._s = scaling(master)
        super().__init__(master, bg=bg or bg_of(master), bd=0, highlightthickness=0, **kw)
