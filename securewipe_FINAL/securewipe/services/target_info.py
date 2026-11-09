"""Information about what the user picked to wipe: file(s), a folder or a drive.

TargetInfo holds everything the Algorithms page shows in its first section.
Sizes of files/folders are the content size; used/free space always refer to the
drive (volume) the target lives on.
"""
import os
import shutil
import string
from dataclasses import dataclass, field
from pathlib import Path

from services.system_service import is_windows

_DRIVE_TYPES = {2: "Removable", 3: "Local disk", 4: "Network", 5: "CD/DVD", 6: "RAM disk"}


@dataclass
class DriveInfo:
    root: str                  # "E:\\" on Windows, "/media/usb" elsewhere
    label: str
    kind: str                  # Removable, Local disk, ...
    filesystem: str
    total: int
    used: int
    free: int
    is_system: bool

    @property
    def display_name(self) -> str:
        letter = self.root.rstrip("\\/") or self.root
        return f"{self.label} ({letter})" if self.label else letter


@dataclass
class TargetInfo:
    kind: str                  # "file" | "folder" | "drive"
    paths: list[str]
    name: str = ""
    location: str = ""
    total_size: int = 0        # bytes that will be overwritten
    item_count: int = 0        # files included
    drive_root: str = ""
    drive_total: int = 0
    drive_used: int = 0
    drive_free: int = 0
    filesystem: str = ""
    drive_kind: str = ""
    is_system_drive: bool = False
    skipped: list[str] = field(default_factory=list)   # unreadable entries
    # What the certificate lists: (name, type, size in bytes before the wipe).
    # Files keep their extension; a folder or drive is one item with its full size.
    items: list[tuple[str, str, int]] = field(default_factory=list)
    # Every file in the selection for the Algorithms page list: (name, size in bytes).
    # A folder's names are relative to the folder (e.g. "photos/cat.png").
    files: list[tuple[str, int]] = field(default_factory=list)

    @property
    def type_label(self) -> str:
        if self.kind == "drive":
            return f"Drive ({self.drive_kind})" if self.drive_kind else "Drive"
        if self.kind == "folder":
            return "Folder"
        return "File" if len(self.paths) == 1 else "Files"


def folder_tree(files: list[tuple[str, int]]) -> dict:
    """Nests (relative name, size) pairs into folders.
    Each node: {"dirs": {name: node}, "files": [(name, size)], "size": total bytes below it}."""
    root = {"dirs": {}, "files": [], "size": 0}
    for rel, size in files:
        parts = [p for p in rel.split(os.sep) if p]
        node = root
        node["size"] += size
        for part in parts[:-1]:
            node = node["dirs"].setdefault(part, {"dirs": {}, "files": [], "size": 0})
            node["size"] += size
        node["files"].append((parts[-1] if parts else rel, size))
    return root


def count_folders(node: dict) -> int:
    return sum(1 + count_folders(sub) for sub in node["dirs"].values())


# ---- formatting ---------------------------------------------------------------
def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


# ---- drives -------------------------------------------------------------------
def _system_root() -> str:
    if is_windows():
        return os.environ.get("SystemDrive", "C:") + "\\"
    return "/"


def _volume_info(root: str) -> tuple[str, str]:
    """(label, filesystem) for a Windows drive root; empty strings elsewhere."""
    if not is_windows():
        return "", ""
    import ctypes
    label = ctypes.create_unicode_buffer(261)
    fs = ctypes.create_unicode_buffer(261)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(root), label, 261, None, None, None, fs, 261)
    return (label.value, fs.value) if ok else ("", "")


def _drive_kind(root: str) -> str:
    if not is_windows():
        return "Removable" if root.startswith(("/media", "/run/media", "/mnt", "/Volumes")) \
            else "Local disk"
    import ctypes
    return _DRIVE_TYPES.get(ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root)), "Unknown")


def drive_info(root: str) -> DriveInfo | None:
    try:
        usage = shutil.disk_usage(root)
    except OSError:                       # empty card reader, no disc in drive, ...
        return None
    label, fs = _volume_info(root)
    sys_root = _system_root()
    return DriveInfo(root=root, label=label, kind=_drive_kind(root), filesystem=fs,
                     total=usage.total, used=usage.used, free=usage.free,
                     is_system=os.path.normcase(root) == os.path.normcase(sys_root))


def list_drives() -> list[DriveInfo]:
    if is_windows():
        import ctypes
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        roots = [f"{c}:\\" for i, c in enumerate(string.ascii_uppercase) if mask >> i & 1]
    else:
        roots = ["/"]
        for base in ("/media", "/run/media", "/mnt", "/Volumes"):
            if os.path.isdir(base):
                for dirpath, dirs, _ in os.walk(base):
                    for d in dirs:
                        p = os.path.join(dirpath, d)
                        if os.path.ismount(p):
                            roots.append(p)
                    if dirpath.count(os.sep) - base.count(os.sep) >= 1:
                        dirs.clear()      # look at most two levels deep
    drives = [d for d in (drive_info(r) for r in roots) if d is not None]
    return [d for d in drives if d.kind not in ("CD/DVD", "Network")]


def _drive_root_of(path: str) -> str:
    if is_windows():
        return os.path.splitdrive(os.path.abspath(path))[0] + "\\"
    p = Path(path).resolve()
    while not os.path.ismount(p):
        p = p.parent
    return str(p)


# ---- targets ------------------------------------------------------------------
def _fill_drive_fields(info: TargetInfo, root: str) -> None:
    d = drive_info(root)
    if d is None:
        return
    info.drive_root, info.drive_total, info.drive_used, info.drive_free = d.root, d.total, d.used, d.free
    info.filesystem, info.drive_kind, info.is_system_drive = d.filesystem, d.kind, d.is_system


def collect(kind: str, paths: list[str]) -> TargetInfo:
    """Build TargetInfo. Walking a big folder can take a while: call from a thread."""
    info = TargetInfo(kind=kind, paths=list(paths))
    first = paths[0]

    if kind == "drive":
        _fill_drive_fields(info, first)
        d = drive_info(first)
        info.name = d.display_name if d else first
        info.location = first
        info.total_size = info.drive_total
        info.items = [(info.name, "Drive", info.total_size)]
        return info

    if kind == "folder":
        info.name = os.path.basename(os.path.normpath(first)) or first
        info.location = os.path.dirname(os.path.normpath(first))
        for dirpath, _, files in os.walk(first, onerror=lambda e: info.skipped.append(e.filename)):
            for f in files:
                fp = os.path.join(dirpath, f)
                try:
                    if not os.path.islink(fp):
                        size = os.path.getsize(fp)
                        info.total_size += size
                        info.item_count += 1
                        info.files.append((os.path.relpath(fp, first), size))
                except OSError:
                    info.skipped.append(fp)
        info.files.sort(key=lambda f: f[0].lower())
        info.items = [(info.name, "Folder", info.total_size)]
    else:                                                    # one or more files
        info.name = os.path.basename(first) if len(paths) == 1 else f"{len(paths)} files"
        info.location = os.path.dirname(first)
        for fp in paths:
            try:
                size = os.path.getsize(fp)
                info.total_size += size
                info.item_count += 1
                info.items.append((os.path.basename(fp), "File", size))
                info.files.append((os.path.basename(fp), size))
            except OSError:
                info.skipped.append(fp)

    _fill_drive_fields(info, _drive_root_of(first))
    return info
