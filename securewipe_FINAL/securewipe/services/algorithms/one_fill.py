"""One Fill: every byte is overwritten with 0xFF, once per pass.

The work is done by services/algorithms/fill.py. This file only says which byte to write.
"""
from services.algorithms import fill
from services.algorithms.writer import Hooks
from services.target_info import TargetInfo

FILL_BYTE = 0xFF


def run(target: TargetInfo, passes: int, hooks: Hooks) -> None:
    fill.run(target, passes, hooks, FILL_BYTE)
