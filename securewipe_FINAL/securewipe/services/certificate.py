"""Certificate of Destruction: records a finished wipe, draws the certificate, saves it as PDF.

Layout follows the "Certificate of Destruction" sample (title band, labelled fields, items
table, statement, signatures), in the app's own dark green / light green palette.

The certificate is drawn with Pillow at A4 landscape, 200 dpi. The same image is shown in the
app (preview) and written to the PDF, so both always match. Pillow writes single-image PDFs,
so no extra PDF library is needed.
"""
import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from config import APP_NAME, LIGHT_COLORS, LOGO_PATH
from database import operations_repo
from services import settings_service
from services.auth_service import User
from services.target_info import TargetInfo, human_size

# ---- page -----------------------------------------------------------------------
W, H = 2339, 1654                     # A4 landscape at 200 dpi
MAX_ITEM_ROWS = 10                    # longer lists show "+ N more" on the last row

# ---- colours: the app's dark green and light green only ------------------------
DARK = LIGHT_COLORS["green_dark"]           # #0F9F6E
LIGHT = LIGHT_COLORS["green_light"]         # #EEF9F3
SOFT = LIGHT_COLORS["green_soft"]           # #DDF1E6
INK = LIGHT_COLORS["text"]
MUTED = LIGHT_COLORS["muted"]
ROW_ALT = "#F7FBF9"
WHITE = "#FFFFFF"

_FONT_FILES = {
    "regular": ("arial.ttf", "LiberationSans-Regular.ttf", "DejaVuSans.ttf"),
    "bold": ("arialbd.ttf", "LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf"),
    "serif": ("timesbd.ttf", "LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf"),
}
KIND_LABEL = {"file": "File", "folder": "Folder", "drive": "Drive"}


@dataclass
class CertificateData:
    op_id: int
    report_id: str
    certificate_id: str
    issued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    target_name: str
    items: list[tuple[str, str, int | None]]   # (name, type, bytes before the wipe)
    total_size: int | None
    method: str
    passes: int
    operator: str
    skipped: int = 0                           # items that could not be read
    simulated: bool = False                    # simulation mode: nothing was written

    @property
    def method_label(self) -> str:
        return f"{self.method} ({self.passes} pass{'es' if self.passes != 1 else ''})"


# ---- ids, parsing ---------------------------------------------------------------
def report_id(op_id: int, issued: datetime) -> str:
    return f"SW-{issued:%Y%m%d}-{op_id:03d}"


def certificate_id(op_id: int, issued: datetime) -> str:
    return f"SW-CERT-{issued:%Y%m%d}-{op_id:03d}"


def from_row(row) -> CertificateData:
    """Build the certificate data from an operations row (see operations_repo)."""
    issued = datetime.fromisoformat(
        row["certificate_issued_at"] or row["finished_at"] or row["started_at"])
    started = datetime.fromisoformat(row["started_at"]) if row["started_at"] else None
    finished = datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None

    items, skipped, simulated = [], 0, False
    if row["items_json"]:
        data = json.loads(row["items_json"])
        items = [(i["name"], i["type"], i.get("size")) for i in data.get("items", [])]
        skipped = int(data.get("skipped", 0))
        simulated = bool(data.get("simulated", False))
    if not items:                              # wipes recorded before items were stored
        items = [(row["target_name"], KIND_LABEL.get(row["target_type"], ""), row["total_size"])]

    return CertificateData(
        op_id=row["id"],
        report_id=report_id(row["id"], issued),
        certificate_id=certificate_id(row["id"], issued),
        issued_at=issued,
        started_at=started,
        finished_at=finished,
        target_name=row["target_name"],
        items=items,
        total_size=row["total_size"],
        method=row["algorithm"],
        passes=row["passes"],
        operator=row["full_name"] or row["username"],
        skipped=skipped,
        simulated=simulated,
    )


# ---- issuing --------------------------------------------------------------------
def record_wipe(user: User, info: TargetInfo, method: str, passes: int,
                started_ts: float, finished_ts: float, state: str, simulated: bool) -> int:
    """Write a finished wipe to the detailed log, whether or not a certificate is made.
    `state` is the wipe state: SUCCESS, FAILED or CANCELLED. Returns the operation id.
    Sizes come from `info`, which was measured before the wipe started."""
    now = datetime.now()
    started = datetime.fromtimestamp(started_ts)
    finished = datetime.fromtimestamp(finished_ts or now.timestamp())
    skipped = len(info.skipped)
    if state == "SUCCESS" and skipped:
        status = "SUCCESS_WITH_LIMITATIONS"
    else:
        status = state
    payload = {
        "items": [{"name": n, "type": t, "size": s} for n, t, s in info.items],
        "skipped": skipped,
        "simulated": simulated,
    }
    return operations_repo.add_operation(
        user_id=user.id,
        started_at=started.isoformat(timespec="seconds"),
        finished_at=finished.isoformat(timespec="seconds"),
        target_type=info.kind,
        target_name=info.name,
        target_path=info.location or info.drive_root or (info.paths[0] if info.paths else ""),
        algorithm=method,
        passes=passes,
        status=status,
        report_generated=False,          # becomes True when the certificate is generated
        total_size=info.total_size,
        items_json=json.dumps(payload),
    )


def issue(op_id: int) -> None:
    """The user generated the certificate for a logged wipe: it now appears in Reports."""
    operations_repo.mark_certificate(op_id, datetime.now().isoformat(timespec="seconds"))


# ---- drawing helpers ------------------------------------------------------------
@lru_cache(maxsize=None)
def _font(kind: str, size: int):
    for name in _FONT_FILES[kind]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)     # Pillow 10.1+
    except TypeError:
        return ImageFont.load_default()


@lru_cache(maxsize=4)
def _logo(height: int) -> Image.Image:
    img = Image.open(LOGO_PATH).convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    if bbox:
        img = img.crop(bbox)
    width = round(img.width * height / img.height)
    return img.resize((width, height), Image.LANCZOS)


def _fit(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> str:
    """Shorten text with an ellipsis so it fits max_w pixels."""
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def format_datetime(value: datetime | None) -> str:
    return settings_service.format_datetime(value) if value else "—"


def _elapsed(start: datetime | None, end: datetime | None) -> str:
    if not start or not end:
        return "—"
    s = int(max((end - start).total_seconds(), 0))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def _size(n: int | None) -> str:
    return "—" if n is None else human_size(n)


def _field_column(d, rows, x_label: int, x_value: int, y: int, step: int = 66) -> None:
    for label, value in rows:
        d.text((x_label, y), label, font=_font("bold", 34), fill=INK)
        d.text((x_value, y), _fit(d, value, _font("regular", 34), W - 170 - x_value),
               font=_font("regular", 34), fill=INK)
        y += step


# ---- rendering ------------------------------------------------------------------
def render(cert: CertificateData) -> Image.Image:
    """Draw the certificate at full resolution (W x H, RGB)."""
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    # frame: thick dark green, thin light green inside
    d.rectangle((40, 40, W - 40, H - 40), outline=DARK, width=12)
    d.rectangle((66, 66, W - 66, H - 66), outline=SOFT, width=4)

    # header: logo, app name, report id
    logo = _logo(170)
    img.paste(logo, (120, 110), logo)
    d.text((330, 122), APP_NAME, font=_font("bold", 76), fill=DARK)
    d.text((334, 214), "Secure data erasure", font=_font("regular", 34), fill=MUTED)
    d.text((W - 120, 130), f"Report ID  {cert.report_id}", font=_font("regular", 32),
           fill=INK, anchor="ra")

    # title band
    d.rectangle((120, 300, W - 120, 400), fill=DARK)
    d.text((W // 2, 350), "CERTIFICATE OF DESTRUCTION", font=_font("serif", 84),
           fill=WHITE, anchor="mm")

    # labelled fields, two columns
    _field_column(d, [
        ("Issued By:", APP_NAME),
        ("Certificate ID:", cert.certificate_id),
        ("Method Used:", cert.method),
        ("Number of Passes:", str(cert.passes)),
    ], x_label=170, x_value=640, y=445)
    _field_column(d, [
        ("Destruction Start:", format_datetime(cert.started_at)),
        ("Destruction End:", format_datetime(cert.finished_at)),
        ("Elapsed Time:", _elapsed(cert.started_at, cert.finished_at)),
        ("Certificate Issued:", format_datetime(cert.issued_at)),
    ], x_label=1190, x_value=1720, y=445)
    d.line((120, 705, W - 120, 705), fill=SOFT, width=3)

    # items destroyed
    d.text((170, 725), "Items Destroyed", font=_font("bold", 38), fill=DARK)
    top = 790
    d.rectangle((120, top, W - 120, top + 46), fill=LIGHT)
    head = _font("bold", 26)
    d.text((150, top + 23), "NO.", font=head, fill=DARK, anchor="lm")
    d.text((240, top + 23), "ITEM (WITH EXTENSION)", font=head, fill=DARK, anchor="lm")
    d.text((1560, top + 23), "TYPE", font=head, fill=DARK, anchor="lm")
    d.text((W - 150, top + 23), "SIZE BEFORE DESTRUCTION", font=head, fill=DARK,
           anchor="rm")

    row_h = 36
    items = cert.items
    shown = items if len(items) <= MAX_ITEM_ROWS else items[:MAX_ITEM_ROWS - 1]
    y = top + 46
    body = _font("regular", 28)
    for n, (name, kind, size) in enumerate(shown, start=1):
        if n % 2 == 0:
            d.rectangle((120, y, W - 120, y + row_h), fill=ROW_ALT)
        mid = y + row_h // 2
        d.text((150, mid), str(n), font=body, fill=INK, anchor="lm")
        d.text((240, mid), _fit(d, name, body, 1230), font=body, fill=INK, anchor="lm")
        d.text((1560, mid), kind, font=body, fill=INK, anchor="lm")
        d.text((W - 150, mid), _size(size), font=body, fill=INK, anchor="rm")
        y += row_h
    if len(items) > MAX_ITEM_ROWS:
        more = len(items) - len(shown)
        mid = y + row_h // 2
        d.text((240, mid), f"+ {more} more item{'s' if more != 1 else ''} in this wipe",
               font=body, fill=MUTED, anchor="lm")
        y += row_h
    d.line((120, y, W - 120, y), fill=SOFT, width=3)

    # notes (only when they apply)
    note_font = _font("regular", 26)
    note_y = y + 26
    if cert.simulated:
        d.text((170, note_y), "SIMULATION MODE: no data was written. "
               "This certificate is a preview and is not a destruction record.",
               font=_font("bold", 26), fill=INK)
        note_y += 38
    if cert.skipped:
        d.text((170, note_y), f"{cert.skipped} item(s) could not be read and were not wiped.",
               font=note_font, fill=INK)
        note_y += 38

    # statement
    stmt_font = _font("regular", 30)
    text = ("This record states that the items listed above were overwritten using the method "
            "and number of passes shown. It is not a verified destruction certificate.")
    for line in _wrap(d, text, stmt_font, W - 500):
        d.text((W // 2, note_y + 40), line, font=stmt_font, fill=INK, anchor="mm")
        note_y += 46

    # signatures
    sig_y = 1440
    for x0, label, name in ((170, "Authorized By", cert.operator),):
        d.line((x0, sig_y, x0 + 700, sig_y), fill=INK, width=3)
        d.text((x0, sig_y + 16), label, font=_font("regular", 26), fill=MUTED)
        if name:
            d.text((x0, sig_y + 52), _fit(d, name, _font("bold", 32), 700),
                   font=_font("bold", 32), fill=INK)
    return img


def preview(cert: CertificateData, width: int) -> Image.Image:
    """The same certificate scaled down for the app window."""
    img = render(cert)
    return img.resize((width, round(width * H / W)), Image.LANCZOS)


def save_pdf(cert: CertificateData, path: str) -> None:
    render(cert).save(
        path, "PDF", resolution=200.0,
        title=f"Certificate of Destruction {cert.certificate_id}",
        author=APP_NAME, creator=APP_NAME,
    )
