"""Random Data: every byte is overwritten with cryptographically random data, once per pass.

Matches NIST SP 800-88 Clear with 1 pass. Every write gets new random bytes from the
operating system, so no two blocks on the target carry the same pattern.

The work is done by services/algorithms/fill.py. This file only says that the byte is random (None).
"""
from services.algorithms import fill
from services.algorithms.writer import Hooks
from services.target_info import TargetInfo

FILL_BYTE = None          # None = random data (see writer.fill_fd)


def run(target: TargetInfo, passes: int, hooks: Hooks) -> None:
    fill.run(target, passes, hooks, FILL_BYTE)
