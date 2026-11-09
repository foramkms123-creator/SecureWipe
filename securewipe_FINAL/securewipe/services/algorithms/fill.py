"""Generic overwrite engine. Zero Fill (0x00), One Fill (0xFF) and Random Data (fill_byte=None)
all call run() with their byte, or None for random bytes.

What it does for each target type
    file    the bytes of the file are overwritten in place (size does not change)
    folder  every file below the folder is overwritten, then the files and folders are
            deleted when config.REMOVE_AFTER_WIPE is True
    drive   the whole pendrive / disk is overwritten, from the first to the last sector

No verification read is done (by design, to save time).
"""
import os
import stat

import config
from services import raw_device
from services.algorithms.writer import O_BINARY, Hooks, fill_fd, pattern_buffer, sequence_buffer
from services.target_info import TargetInfo


def run(target: TargetInfo, passes: int, hooks: Hooks, fill_byte: int | None,
        pass_bytes: list | None = None) -> None:
    """fill_byte: 0x00, 0xFF, ... or None for random data (new random bytes on every write).
    pass_bytes: optional entry for each pass (DoD, Gutmann). When given, it replaces fill_byte.
    An entry is None (random data), one byte, or a tuple of bytes that repeats (Gutmann)."""
    if pass_bytes is None:
        pass_bytes = [fill_byte] * passes
    buffers: dict = {}
    patterns = []                            # one pattern per pass
    for b in pass_bytes:
        if b not in buffers:
            buffers[b] = sequence_buffer(b) if isinstance(b, tuple) else pattern_buffer(b)
        patterns.append(buffers[b])
    if target.kind == "drive":
        _wipe_drive(target, passes, hooks, patterns)
    else:
        _wipe_files(target, passes, hooks, patterns)


# ---- files and folders --------------------------------------------------------
def _list_files(target: TargetInfo) -> list[str]:
    if target.kind == "folder":
        found = []
        for dirpath, _dirs, names in os.walk(target.paths[0]):   # does not follow symlinks
            found.extend(os.path.join(dirpath, n) for n in names)
    else:
        found = list(target.paths)
    return [p for p in found if not os.path.islink(p)]


def _wipe_files(target: TargetInfo, passes: int, hooks: Hooks, patterns: list) -> None:
    files = _list_files(target)
    sizes: dict[str, int] = {}
    failed: dict[str, str] = {}             # path -> error message

    for path in files:
        try:
            sizes[path] = os.path.getsize(path)
        except OSError as exc:
            failed[path] = f"{path}: {exc.strerror or exc}"
    hooks.set_total(sum(sizes.values()) * passes)

    for pass_no in range(1, passes + 1):
        hooks.set_pass(pass_no)
        for path in files:
            if path in sizes and path not in failed:
                try:
                    _overwrite_file(path, patterns[pass_no - 1], hooks)
                except OSError as exc:
                    failed[path] = f"{path}: {exc.strerror or exc}"

    if config.REMOVE_AFTER_WIPE:
        _delete_names(target, files, failed)
    if failed:
        first = next(iter(failed.values()))
        raise RuntimeError(f"{len(failed)} item(s) could not be wiped. First: {first}")


def _overwrite_file(path: str, pattern: memoryview | None, hooks: Hooks) -> None:
    _make_writable(path)
    fd = os.open(path, os.O_WRONLY | O_BINARY)     # no O_TRUNC: size is kept
    try:
        size = os.fstat(fd).st_size                # current size, in case it changed
        fill_fd(fd, size, pattern, hooks)
        os.fsync(fd)                               # make sure the bytes reached the disk
    finally:
        os.close(fd)


def _delete_names(target: TargetInfo, files: list[str], failed: dict[str, str]) -> None:
    for path in files:
        if path in failed:
            continue
        try:
            _make_writable(path)
            os.remove(path)
        except OSError as exc:
            failed[path] = f"{path}: {exc.strerror or exc}"
    if target.kind == "folder":
        for dirpath, _dirs, _names in os.walk(target.paths[0], topdown=False):
            try:
                os.rmdir(dirpath)                  # only succeeds when empty
            except OSError:
                pass


def _make_writable(path: str) -> None:
    """Windows: clear the read-only attribute so the file can be opened for writing."""
    try:
        mode = os.stat(path).st_mode
        if not mode & stat.S_IWRITE:
            os.chmod(path, mode | stat.S_IWRITE)
    except OSError:
        pass


# ---- whole drive (pendrive / disk) --------------------------------------------
def _wipe_drive(target: TargetInfo, passes: int, hooks: Hooks, patterns: list) -> None:
    with raw_device.open_for_wipe(target) as dev:
        hooks.set_total(dev.size * passes)
        for pass_no in range(1, passes + 1):
            hooks.set_pass(pass_no)
            os.lseek(dev.fd, 0, os.SEEK_SET)
            fill_fd(dev.fd, dev.size, patterns[pass_no - 1], hooks)
            os.fsync(dev.fd)
