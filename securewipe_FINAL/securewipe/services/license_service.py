"""Exports the Software License page (About > View license) as a PDF.

The PDF is saved in the reports folder chosen in Settings > Reports & Storage (the default
folder if none was chosen). Drawn with Pillow, like the wipe certificate, so no extra library
is needed. Colours are the app's light tokens, so the document is always light."""
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import APP_NAME, APP_VERSION, LIGHT_COLORS, LOGO_PATH
from services import settings_service
from ui.content import about_text as T

W, H = 1240, 1754                 # A4 portrait at 150 dpi
M = 80                            # page margin
PAD = 30                          # inside each section card
DARK = LIGHT_COLORS["green_dark"]
LIGHT = LIGHT_COLORS["green_light"]
SOFT = LIGHT_COLORS["green_soft"]
INK = LIGHT_COLORS["text"]
MUTED = LIGHT_COLORS["muted"]
WARN_BG = LIGHT_COLORS["warn_bg"]
WARN_TEXT = LIGHT_COLORS["warn_text"]
WARN = LIGHT_COLORS["warning"]
WHITE = "#FFFFFF"
CONTENT_W = W - 2 * M


@lru_cache(maxsize=None)
def _font(bold: bool, size: int):
    names = (("arialbd.ttf", "LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf") if bold
             else ("arial.ttf", "LiberationSans-Regular.ttf", "DejaVuSans.ttf"))
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)      # Pillow 10.1+
    except TypeError:
        return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _logo(height: int) -> Image.Image:
    img = Image.open(LOGO_PATH).convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    if bbox:
        img = img.crop(bbox)
    width = round(img.width * height / img.height)
    return img.resize((width, height), Image.LANCZOS)


def _section_height(draw, items, width: int, heading_h: int) -> int:
    """Height of one section card (used to draw its background before its text)."""
    body = _font(False, 28)
    if isinstance(items, str):
        lines = _wrap(draw, items, body, width)
        return PAD * 2 + heading_h + len(lines) * 38
    total = PAD * 2 + heading_h
    for item in items:
        total += len(_wrap(draw, item, body, width - 40)) * 38 + 8
    return total


def render() -> Image.Image:
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    y = M

    # header band: logo, app name, licence title
    band_h = 220
    d.rounded_rectangle((M, y, W - M, y + band_h), radius=28, fill=LIGHT, outline=SOFT, width=2)
    logo = _logo(150)
    img.paste(logo, (M + 40, y + (band_h - logo.height) // 2), logo)
    tx = M + 40 + logo.width + 40
    d.text((tx, y + 60), APP_NAME, font=_font(True, 64), fill=DARK)
    d.text((tx, y + 142), T.LICENSE_TITLE, font=_font(False, 40), fill=INK)
    y += band_h + 36

    # badge
    badge_font = _font(True, 28)
    badge_w = int(d.textlength(T.LICENSE_BADGE, font=badge_font)) + 60
    d.rounded_rectangle((M, y, M + badge_w, y + 62), radius=31, fill=SOFT)
    d.text((M + 30, y + 31), T.LICENSE_BADGE, font=badge_font, fill=DARK, anchor="lm")
    y += 62 + 30

    # version and introduction
    d.text((M, y), f"Version {APP_VERSION}   ·   © 2026 {T.TEAM_NAME}", font=_font(False, 28),
           fill=MUTED)
    y += 50
    for line in T.LICENSE_INTRO.split("\n"):
        d.text((M, y), line, font=_font(False, 28), fill=INK)
        y += 38
    y += 34

    # sections
    for heading, tone, _icon, items in T.LICENSE_SECTIONS:
        if not isinstance(items, str) and all(len(i) <= 24 for i in items):
            items = "   ·   ".join(items)          # short names (e.g. technologies) on one line
        fill = LIGHT if tone == "ok" else WARN_BG
        outline = SOFT if tone == "ok" else WARN
        head_color = DARK if tone == "ok" else WARN_TEXT
        heading_h = 48
        card_h = _section_height(d, items, CONTENT_W - 2 * PAD, heading_h)
        d.rounded_rectangle((M, y, W - M, y + card_h), radius=24, fill=fill, outline=outline, width=2)
        ty = y + PAD
        d.text((M + PAD, ty), heading, font=_font(True, 36), fill=head_color)
        ty += heading_h
        if isinstance(items, str):
            for line in _wrap(d, items, _font(False, 28), CONTENT_W - 2 * PAD):
                d.text((M + PAD, ty), line, font=_font(False, 28), fill=INK)
                ty += 38
        else:
            bullet = DARK if tone == "ok" else WARN
            for item in items:
                d.text((M + PAD, ty), "•", font=_font(True, 30), fill=bullet)
                for line in _wrap(d, item, _font(False, 28), CONTENT_W - 2 * PAD - 40):
                    d.text((M + PAD + 40, ty), line, font=_font(False, 28), fill=INK)
                    ty += 38
                ty += 10
        y += card_h + 20

    # footer, at the bottom of the page
    footer_top = H - M - 150
    if y > footer_top:
        raise ValueError("The licence text does not fit on one page")
    d.line([(M, footer_top), (W - M, footer_top)], fill=SOFT, width=2)
    fy = footer_top + 26
    guide_line = f"Project guide: {T.GUIDE}   ·   {T.DEPARTMENT.split(',')[0]}"
    d.text((M, fy), guide_line, font=_font(True, 28), fill=INK)
    fy += 52
    for line in _wrap(d, T.LICENSE_TECH_NOTE, _font(False, 24), CONTENT_W):
        d.text((M, fy), line, font=_font(False, 24), fill=MUTED)
        fy += 32
    stamp = f"Exported {settings_service.format_date(datetime.now())}"
    d.text((W - M, H - M), stamp, font=_font(False, 24), fill=MUTED, anchor="rs")
    return img


def export(folder: Path | None = None) -> Path:
    """Writes the licence PDF to the reports folder (or `folder`) and returns its path."""
    target_dir = folder or settings_service.reports_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / T.LICENSE_EXPORT_NAME
    render().save(path, "PDF", resolution=150.0)
    return path
