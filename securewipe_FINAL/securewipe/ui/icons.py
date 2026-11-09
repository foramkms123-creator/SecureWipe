"""Line icons drawn with Pillow (no icon files needed).

Drawn large on a 96x96 canvas, then shrunk with LANCZOS so edges stay smooth.
Add a new icon by writing a _draw function and registering it in _DRAWERS."""
import math
from functools import lru_cache

import customtkinter as ctk
from PIL import Image, ImageDraw

_CANVAS = 96
_STROKE = 7
_CLEAR = (0, 0, 0, 0)


def _rgba(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def _home(d, c, w):
    d.line([(12, 46), (48, 14), (84, 46)], fill=c, width=w, joint="curve")
    d.line([(24, 38), (24, 82), (72, 82), (72, 38)], fill=c, width=w, joint="curve")
    d.line([(40, 82), (40, 60), (56, 60), (56, 82)], fill=c, width=w, joint="curve")


def _sliders(d, c, w):
    for y, x in ((24, 62), (48, 32), (72, 56)):
        d.line([(12, y), (84, y)], fill=c, width=w)
        d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=_CLEAR, outline=c, width=w)


def _document(d, c, w):
    d.rounded_rectangle((20, 10, 76, 86), radius=10, outline=c, width=w)
    for y, x_end in ((32, 62), (48, 62), (64, 50)):
        d.line([(34, y), (x_end, y)], fill=c, width=w)


def _gear(d, c, w):
    cx = cy = 48
    teeth, r_out, r_in = 8, 40, 31
    pts = []
    for i in range(teeth):
        base = i * 360 / teeth
        for r, off in ((r_in, -14), (r_out, -8), (r_out, 8), (r_in, 14)):
            a = math.radians(base + off)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.line(pts + pts[:1], fill=c, width=w, joint="curve")
    d.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), outline=c, width=w)


def _help(d, c, w):
    d.ellipse((8, 8, 88, 88), outline=c, width=w)
    d.arc((34, 22, 62, 50), start=180, end=360, fill=c, width=w)
    d.arc((34, 22, 62, 50), start=0, end=60, fill=c, width=w)
    d.line([(55, 48), (48, 55), (48, 61)], fill=c, width=w, joint="curve")
    d.ellipse((43, 67, 53, 77), fill=c)


def _info(d, c, w):
    d.ellipse((8, 8, 88, 88), outline=c, width=w)
    d.ellipse((43, 24, 53, 34), fill=c)
    d.line([(48, 44), (48, 72)], fill=c, width=w)


def _algorithm(d, c, w):
    d.rounded_rectangle((8, 8, 88, 88), radius=18, outline=c, width=w)        # window
    d.line([(24, 26), (34, 26)], fill=c, width=w + 3)                           # title pill
    d.line([(36, 42), (26, 55), (36, 68)], fill=c, width=w + 1, joint="curve")  # <
    d.line([(53, 38), (43, 72)], fill=c, width=w + 1)                           # /
    d.line([(60, 42), (70, 55), (60, 68)], fill=c, width=w + 1, joint="curve")  # >


def _plus(d, c, w):
    w = w + 4
    d.line([(48, 18), (48, 78)], fill=c, width=w)
    d.line([(18, 48), (78, 48)], fill=c, width=w)


def _shield_broom(d, c, w):
    shield = [(48, 6), (84, 18), (82, 50), (70, 74), (48, 90), (26, 74), (14, 50), (12, 18)]
    d.line(shield + shield[:2], fill=c, width=w, joint="curve")
    d.line([(64, 26), (52, 46)], fill=c, width=w)                               # handle
    d.polygon([(44, 42), (60, 52), (54, 72), (30, 64)], fill=c)                 # broom head
    for x in (36, 43, 50):                                                      # bristle gaps
        d.line([(x, 56), (x + 4, 69)], fill=_CLEAR, width=3)
    d.polygon([(32, 24), (35, 31), (42, 34), (35, 37), (32, 44),                # sparkle
               (29, 37), (22, 34), (29, 31)], fill=c)


def _file(d, c, w):
    d.line([(22, 10), (58, 10), (76, 28), (76, 86), (22, 86), (22, 10)], fill=c, width=w,
           joint="curve")
    d.line([(58, 10), (58, 28), (76, 28)], fill=c, width=w, joint="curve")
    for y in (48, 62):
        d.line([(34, y), (64, y)], fill=c, width=w)


def _folder(d, c, w):
    d.line([(10, 22), (38, 22), (46, 32), (86, 32), (86, 80), (10, 80), (10, 22)], fill=c,
           width=w, joint="curve")
    d.line([(10, 44), (86, 44)], fill=c, width=w)


def _drive(d, c, w):
    d.rounded_rectangle((8, 26, 88, 70), radius=12, outline=c, width=w)
    d.line([(22, 48), (54, 48)], fill=c, width=w)
    d.ellipse((66, 42, 78, 54), fill=c)


def _shield(d, c, w):
    d.line([(48, 8), (84, 20), (84, 46), (76, 66), (48, 88), (20, 66), (12, 46), (12, 20), (48, 8)],
           fill=c, width=w, joint="curve")
    d.line([(32, 48), (44, 60), (66, 36)], fill=c, width=w, joint="curve")


def _lock(d, c, w):
    d.rounded_rectangle((18, 42, 78, 86), radius=8, outline=c, width=w)
    d.arc((28, 14, 68, 56), start=180, end=360, fill=c, width=w)
    d.line([(28, 42), (28, 30)], fill=c, width=w)
    d.line([(68, 42), (68, 30)], fill=c, width=w)
    d.ellipse((44, 56, 52, 64), fill=c)


def _bell(d, c, w):
    d.line([(24, 70), (24, 44), (32, 24), (48, 16), (64, 24), (72, 44), (72, 70), (24, 70)],
           fill=c, width=w, joint="curve")
    d.line([(14, 70), (82, 70)], fill=c, width=w)
    d.arc((40, 72, 56, 88), start=0, end=180, fill=c, width=w)


def _database(d, c, w):
    d.ellipse((16, 12, 80, 32), outline=c, width=w)
    d.line([(16, 22), (16, 74)], fill=c, width=w)
    d.line([(80, 22), (80, 74)], fill=c, width=w)
    d.arc((16, 62, 80, 86), start=0, end=180, fill=c, width=w)
    d.line([(16, 48), (16, 48)], fill=c, width=w)


def _refresh(d, c, w):
    d.arc((14, 14, 82, 82), start=200, end=520, fill=c, width=w)
    d.polygon([(74, 10), (84, 30), (64, 30)], fill=c)


def _check(d, c, w):
    d.ellipse((8, 8, 88, 88), outline=c, width=w)
    d.line([(30, 50), (43, 63), (68, 36)], fill=c, width=w, joint="curve")


def _alert(d, c, w):
    d.ellipse((8, 8, 88, 88), outline=c, width=w)
    d.line([(48, 26), (48, 56)], fill=c, width=w + 2)
    d.ellipse((43, 64, 53, 74), fill=c)


def _code(d, c, w):
    d.line([(34, 28), (12, 48), (34, 68)], fill=c, width=w, joint="curve")   # <
    d.line([(62, 28), (84, 48), (62, 68)], fill=c, width=w, joint="curve")   # >
    d.line([(56, 20), (40, 76)], fill=c, width=w)                            # /


def _cap(d, c, w):
    d.line([(48, 16), (90, 36), (48, 56), (6, 36), (48, 16)], fill=c, width=w, joint="curve")  # board
    d.line([(24, 46), (24, 70)], fill=c, width=w)                            # cap body
    d.arc((14, 56, 34, 82), start=0, end=180, fill=c, width=w)
    d.line([(78, 40), (78, 66)], fill=c, width=w)                            # tassel


def _download(d, c, w):
    d.line([(48, 12), (48, 60)], fill=c, width=w)                            # arrow shaft
    d.line([(30, 42), (48, 60), (66, 42)], fill=c, width=w, joint="curve")   # arrow head
    d.line([(14, 62), (14, 84), (82, 84), (82, 62)], fill=c, width=w, joint="curve")  # tray


_DRAWERS = {
    "home": _home, "sliders": _sliders, "document": _document,
    "gear": _gear, "help": _help, "info": _info,
    "algorithm": _algorithm, "plus": _plus, "shield_broom": _shield_broom,
    "file": _file, "folder": _folder, "drive": _drive,
    "shield": _shield, "lock": _lock, "bell": _bell, "database": _database,
    "refresh": _refresh,
    "check": _check, "alert": _alert, "code": _code, "cap": _cap, "download": _download,
}


@lru_cache(maxsize=None)
def icon_pil(name: str, color: str, px: int) -> Image.Image:
    img = Image.new("RGBA", (_CANVAS, _CANVAS), _CLEAR)
    _DRAWERS[name](ImageDraw.Draw(img), _rgba(color), _STROKE)
    return img.resize((px, px), Image.LANCZOS)


@lru_cache(maxsize=None)
def icon(name: str, color: str, size: int = 20) -> ctk.CTkImage:
    img = icon_pil(name, color, size * 2)   # 2x for high-DPI screens
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
