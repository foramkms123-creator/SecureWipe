"""Image loading. The logo is auto-cropped to its visible area so it stays crisp when small."""
from functools import lru_cache

import customtkinter as ctk
from PIL import Image

from config import DATA_DIR, LOGO_PATH


@lru_cache(maxsize=1)
def _logo_source() -> Image.Image:
    img = Image.open(LOGO_PATH).convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    return img.crop(bbox) if bbox else img


@lru_cache(maxsize=None)
def logo(height: int) -> ctk.CTkImage:
    """Cached, pre-shrunk logo. The source PNG is 1600 px wide; handing it to CTkImage
    unshrunk made every screen resize the full image again (slow login / screen changes).
    It is shrunk once to 2x the display size, which stays sharp up to 200 % Windows scaling."""
    src = _logo_source()
    width = round(src.width * height / src.height)
    img = src.resize((width * 2, height * 2), Image.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))


def logo_pil(size: int) -> Image.Image:
    img = _logo_source().copy()
    img.thumbnail((size, size))
    return img


def window_icon_ico() -> str:
    """Windows title-bar icon (.ico) generated from the logo on first run."""
    path = DATA_DIR / "app_icon.ico"
    if not path.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        square = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        img = logo_pil(256)
        square.paste(img, ((256 - img.width) // 2, (256 - img.height) // 2), img)
        square.save(path, sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
    return str(path)
