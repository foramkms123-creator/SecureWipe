"""Opens a whole drive (pendrive or disk) for raw writing.

Linux    /dev/sdX: the disk that holds the picked partition. Mounted partitions are
         unmounted first. Needs root:  sudo python3 main.py
Windows  \\.\\PhysicalDriveN: the disk that holds the picked volume. The volume is
         locked and dismounted first so Windows lets go of the disk.
         Needs Administrator.

Safety: the disk that holds the operating system is always refused.
Sizes are rounded down to whole 512-byte sectors (writes must be sector multiples).
"""
import contextlib
import ctypes
import os
import re
import subprocess
from dataclasses import dataclass

from config import BASE_DIR
from services.algorithms.writer import O_BINARY
from services.system_service import is_windows
from services.target_info import TargetInfo

SECTOR = 512


def guard_windows_disk(target_disk: int, disk_of_letter, app_dir=None) -> None:
    """Refuse to wipe a Windows disk that holds Windows or the SecureWipe folder.

    disk_of_letter("C:") must return the number of the disk that holds that volume. If a
    check cannot be made, the wipe is refused (fail closed). Runs before the volume is locked.
    """
    app_dir = str(BASE_DIR) if app_dir is None else app_dir
    checks = (
        ("the Windows system drive", os.environ.get("SystemDrive", "C:")),
        ("the folder where SecureWipe runs", os.path.splitdrive(os.path.abspath(app_dir))[0]),
    )
    for what, letter in checks:
        try:
            holder = disk_of_letter(letter)
        except (OSError, RuntimeError) as exc:
            raise RuntimeError(f"Wipe refused: could not check {what} ({letter}). "
                               f"Nothing was wiped. {exc}") from exc
        if holder == target_disk:
            raise RuntimeError(f"Refusing to wipe disk {target_disk}: it holds {what} ({letter}). "
                               "Choose a pendrive or a disk that does not hold Windows or SecureWipe.")


@dataclass
class RawDevice:
    fd: int
    path: str
    size: int                     # bytes, multiple of SECTOR


@contextlib.contextmanager
def open_for_wipe(target: TargetInfo):
    if target.is_system_drive:
        raise RuntimeError("Refusing to wipe the system drive.")
    opener = _open_windows if is_windows() else _open_linux
    with opener(target.paths[0]) as dev:
        yield dev


# ---- Linux --------------------------------------------------------------------
@contextlib.contextmanager
def _open_linux(mount: str):
    st = os.stat(mount)
    if st.st_dev == os.stat("/").st_dev:
        raise RuntimeError("Refusing to wipe the disk that holds the operating system.")
    node = _parent_disk(os.major(st.st_dev), os.minor(st.st_dev))
    _unmount_disk(os.path.basename(node))
    fd = os.open(node, os.O_RDWR)
    try:
        size = os.lseek(fd, 0, os.SEEK_END)
        os.lseek(fd, 0, os.SEEK_SET)
        yield RawDevice(fd, node, size - size % SECTOR)
    finally:
        os.close(fd)


def _parent_disk(major: int, minor: int) -> str:
    """/dev/sdb1 (a partition) -> /dev/sdb (the whole disk)."""
    node = os.path.realpath(f"/sys/dev/block/{major}:{minor}")
    if os.path.exists(os.path.join(node, "partition")):
        node = os.path.dirname(node)
    return "/dev/" + os.path.basename(node)


def _unmount_disk(disk: str) -> None:
    """Unmount every partition of the disk (sdb, sdb1, sdb2 ...)."""
    name = re.compile(re.escape(disk) + r"p?\d*")
    mounts = []
    with open("/proc/mounts", encoding="utf-8") as f:
        for line in f:
            source, mountpoint = line.split()[:2]
            if source.startswith("/dev/") and name.fullmatch(os.path.basename(source)):
                mounts.append(mountpoint.replace("\\040", " "))
    for mp in sorted(mounts, key=len, reverse=True):          # deepest first
        result = subprocess.run(["umount", mp], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Could not unmount {mp}: {result.stderr.strip()}")


# ---- Windows ------------------------------------------------------------------
@contextlib.contextmanager
def _open_windows(mount: str):
    import msvcrt
    from ctypes import wintypes as wt

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wt.HANDLE
    k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p,
                                wt.DWORD, wt.DWORD, ctypes.c_void_p]
    k32.DeviceIoControl.restype = wt.BOOL
    k32.DeviceIoControl.argtypes = [wt.HANDLE, wt.DWORD, ctypes.c_void_p, wt.DWORD,
                                    ctypes.c_void_p, wt.DWORD,
                                    ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
    k32.CloseHandle.argtypes = [wt.HANDLE]

    GENERIC_RW, SHARE_RW, OPEN_EXISTING = 0xC0000000, 0x3, 3
    INVALID_HANDLE = ctypes.c_void_p(-1).value
    IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS = 0x00560000
    FSCTL_LOCK_VOLUME, FSCTL_DISMOUNT_VOLUME, FSCTL_UNLOCK_VOLUME = 0x00090018, 0x00090020, 0x0009001C
    IOCTL_DISK_GET_LENGTH_INFO = 0x0007405C

    class DISK_EXTENT(ctypes.Structure):
        _fields_ = [("DiskNumber", wt.DWORD),
                    ("StartingOffset", ctypes.c_longlong),
                    ("ExtentLength", ctypes.c_longlong)]

    class VOLUME_DISK_EXTENTS(ctypes.Structure):
        _fields_ = [("NumberOfDiskExtents", wt.DWORD), ("Extents", DISK_EXTENT * 1)]

    def ioctl(handle, code, out=None):
        returned = wt.DWORD()
        ok = k32.DeviceIoControl(handle, code, None, 0,
                                 ctypes.addressof(out) if out is not None else None,
                                 ctypes.sizeof(out) if out is not None else 0,
                                 ctypes.byref(returned), None)
        if not ok:
            err = ctypes.FormatError(ctypes.get_last_error())
            raise RuntimeError(f"Windows refused control 0x{code:X}: {err}. "
                               "Close Explorer windows and other programs using the drive.")

    def disk_of_letter(volume):
        """Number of the disk that holds a volume. Opened with no read/write access."""
        h = k32.CreateFileW(f"\\\\.\\{volume}", 0, SHARE_RW, None, OPEN_EXISTING, 0, None)
        if h in (None, INVALID_HANDLE):
            raise OSError(f"Could not open volume {volume}. Run the app as Administrator.")
        try:
            found = VOLUME_DISK_EXTENTS()
            ioctl(h, IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS, found)
            if found.NumberOfDiskExtents != 1:
                raise RuntimeError(f"Volume {volume} spans several disks.")
            return found.Extents[0].DiskNumber
        finally:
            k32.CloseHandle(h)

    def volume_names():
        """Every volume on this PC, letter or not, as Volume{GUID} path names."""
        k32.FindFirstVolumeW.restype = wt.HANDLE
        k32.FindFirstVolumeW.argtypes = [wt.LPWSTR, wt.DWORD]
        k32.FindNextVolumeW.argtypes = [wt.HANDLE, wt.LPWSTR, wt.DWORD]
        k32.FindVolumeClose.argtypes = [wt.HANDLE]
        buf = ctypes.create_unicode_buffer(260)
        found = k32.FindFirstVolumeW(buf, 260)
        if found in (None, INVALID_HANDLE):
            raise RuntimeError("Could not list the volumes on this PC. Run the app as Administrator.")
        try:
            names = [buf.value]
            while k32.FindNextVolumeW(found, buf, 260):
                names.append(buf.value)
            return names
        finally:
            k32.FindVolumeClose(found)

    def lock_and_dismount_disk(disk_no, held):
        """Lock and dismount EVERY volume on disk_no: the picked one and any others on the same
        disk (for example a second partition). Windows refuses raw writes to a disk while any of
        its volumes is mounted. The locked handles go into `held` and stay open until the end."""
        count = 0
        for name in volume_names():
            path = name.rstrip("\\")
            h = k32.CreateFileW(path, 0, SHARE_RW, None, OPEN_EXISTING, 0, None)
            if h in (None, INVALID_HANDLE):
                continue
            try:
                found = VOLUME_DISK_EXTENTS()
                try:
                    ioctl(h, IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS, found)
                except RuntimeError:
                    continue                          # not a disk volume
                on_target = found.NumberOfDiskExtents == 1 and found.Extents[0].DiskNumber == disk_no
            finally:
                k32.CloseHandle(h)
            if not on_target:
                continue
            rw = k32.CreateFileW(path, GENERIC_RW, SHARE_RW, None, OPEN_EXISTING, 0, None)
            if rw in (None, INVALID_HANDLE):
                raise RuntimeError(f"Could not open {path} to lock it. Run the app as Administrator.")
            held.append(rw)
            ioctl(rw, FSCTL_LOCK_VOLUME)
            ioctl(rw, FSCTL_DISMOUNT_VOLUME)
            count += 1
        if count == 0:
            raise RuntimeError(f"No volume on disk {disk_no} could be found to lock.")

    letter = os.path.splitdrive(os.path.abspath(mount))[0]              # "E:"
    disk_no = disk_of_letter(letter)                  # nothing is locked yet
    held = []                                         # locked volume handles, open until the end
    phys = None
    disk_fd = None
    try:
        guard_windows_disk(disk_no, disk_of_letter)   # before anything is locked or dismounted
        lock_and_dismount_disk(disk_no, held)
        phys = k32.CreateFileW(f"\\\\.\\PhysicalDrive{disk_no}", GENERIC_RW, SHARE_RW,
                               None, OPEN_EXISTING, 0, None)
        if phys in (None, INVALID_HANDLE):
            code = ctypes.get_last_error()
            raise RuntimeError(
                f"Windows would not open PhysicalDrive{disk_no} for writing (error {code}: "
                f"{ctypes.FormatError(code)}). Close Explorer windows and other programs that use "
                "this drive, unplug and reinsert it, and run SecureWipe as Administrator.")
        disk_fd = msvcrt.open_osfhandle(phys, os.O_RDWR | O_BINARY)
        phys = None                                   # the descriptor owns the handle now
        length = ctypes.c_longlong()
        ioctl(msvcrt.get_osfhandle(disk_fd), IOCTL_DISK_GET_LENGTH_INFO, length)
        yield RawDevice(disk_fd, f"PhysicalDrive{disk_no}", length.value - length.value % SECTOR)
    finally:
        if disk_fd is not None:
            os.close(disk_fd)                         # also closes the disk handle
        elif phys not in (None, INVALID_HANDLE):
            k32.CloseHandle(phys)
        for h in held:
            try:
                ioctl(h, FSCTL_UNLOCK_VOLUME)
            except RuntimeError:
                pass
            k32.CloseHandle(h)
