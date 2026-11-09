"""Gutmann: 35 overwrite passes, the pattern of each pass from wipe_methods.GUTMANN_SEQUENCE.

Passes 1-4 and 32-35: random data.  Passes 5-31: fixed patterns (Gutmann, 1996, "Secure
Deletion of Data from Magnetic and Solid-State Memory").

The work is done by services/algorithms/fill.py. This file only gives the pattern of each pass.
"""
from services.algorithms import fill
from services.algorithms.writer import Hooks
from services.target_info import TargetInfo
from services.wipe_methods import GUTMANN_SEQUENCE


def run(target: TargetInfo, passes: int, hooks: Hooks) -> None:
    if passes != len(GUTMANN_SEQUENCE):
        raise ValueError(f"Gutmann uses {len(GUTMANN_SEQUENCE)} passes, not {passes}")
    fill.run(target, passes, hooks, None, pass_bytes=list(GUTMANN_SEQUENCE))
