"""DoD 5220.22-M: overwrite passes with the byte sequence from wipe_methods.DOD_SEQUENCE.

3 passes : 0x00, 0xFF, random data
7 passes : 0x00, 0xFF, random data, 0x96, 0x00, 0xFF, random data  (ECE)

The work is done by services/algorithms/fill.py. This file only gives the byte of each pass.
"""
from services.algorithms import fill
from services.algorithms.writer import Hooks
from services.target_info import TargetInfo
from services.wipe_methods import DOD_SEQUENCE


def run(target: TargetInfo, passes: int, hooks: Hooks) -> None:
    if passes not in DOD_SEQUENCE:
        raise ValueError(f"DoD 5220.22-M allows 3 or 7 passes, not {passes}")
    fill.run(target, passes, hooks, None, pass_bytes=list(DOD_SEQUENCE[passes]))
