"""Shared low-level writer used by every wipe algorithm (Zero, One, Random, DoD, Gutmann).

Two things make it fast:
  * one pattern buffer is built once and re-used for every write (no allocation per write);
  * writes are large and sequential (WRITE_CHUNK_MB). USB flash and disks only reach
    their top speed with big sequential writes; many small writes waste time.

Random Data has no fixed pattern: when the pattern is None, every write gets a fresh
block of cryptographically random bytes from the operating system (os.urandom).

Algorithms never touch the UI. They receive a Hooks object from the engine.
"""
import math
import os
from dataclasses import dataclass
from typing import Callable

from config import WRITE_CHUNK_MB

CHUNK_BYTES = WRITE_CHUNK_MB * 1024 * 1024
O_BINARY = getattr(os, "O_BINARY", 0)          # exists on Windows only
SECTOR = 512                                   # raw disk writes must be whole sectors


class Cancelled(Exception):
    """Raised inside a wipe when the user presses Stop."""


@dataclass
class Hooks:
    """How an algorithm reports to the engine (WipeJob)."""
    should_stop: Callable[[], bool]     # True once the user pressed Stop
    add_bytes: Callable[[int], None]    # bytes written so far (adds up over all passes)
    set_total: Callable[[int], None]    # total bytes the whole job will write
    set_pass: Callable[[int], None]     # pass number that is starting (1-based)


def pattern_buffer(fill: int | None) -> memoryview | None:
    """One CHUNK_BYTES block filled with a single byte value, e.g. 0x00 or 0xFF.

    fill=None means random data: returns None and fill_fd() makes fresh random bytes.
    """
    if fill is None:
        return None
    return memoryview(bytes([fill]) * CHUNK_BYTES)


def sequence_buffer(seq: tuple) -> memoryview:
    """A block made of a repeating byte sequence, e.g. (0x92, 0x49, 0x24) for Gutmann pass 7.

    The block length is a multiple of the sequence length, so each write starts at the right
    place in the sequence (every write starts at a multiple of the block length).
    """
    unit = math.lcm(len(seq), SECTOR)          # whole repeats AND whole 512-byte sectors
    block = (CHUNK_BYTES // unit) * unit
    return memoryview(bytes(seq) * (block // len(seq)))


def fill_fd(fd: int, size: int, pattern: memoryview | None, hooks: Hooks) -> None:
    """Write exactly `size` bytes at the descriptor's current position.

    With a pattern: the pattern is repeated.  With pattern=None: every write is new random data.
    """
    remaining = size
    while remaining > 0:
        if hooks.should_stop():
            raise Cancelled()
        n = min(remaining, CHUNK_BYTES if pattern is None else len(pattern))
        view = memoryview(os.urandom(n)) if pattern is None else pattern[:n]
        while len(view):                      # os.write may write less than asked
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("write returned 0 bytes")
            view = view[written:]
        remaining -= n
        hooks.add_bytes(n)
