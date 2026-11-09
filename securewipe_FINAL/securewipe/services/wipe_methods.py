"""Wipe algorithms offered on the Algorithms page, and the rules for their pass counts.

Pass rules
    Zero Fill / One Fill / Random Data : 1 .. MAX_CUSTOM_PASSES, step 1
    DoD 5220.22-M                      : only 3 (standard) or 7 (ECE)
    Gutmann                            : fixed at 35, cannot be changed
"""
from dataclasses import dataclass

from config import MAX_CUSTOM_PASSES


@dataclass(frozen=True)
class WipeMethod:
    key: str
    name: str
    summary: str               # one line under the name on the option tile
    detail: str                # shown under the passes control when selected
    default_passes: int
    allowed_passes: tuple      # every pass count the user may pick
    passes_locked: bool = False

    def next_passes(self, current: int, step: int) -> int:
        """Move one position up (+1) or down (-1) inside allowed_passes."""
        if self.passes_locked:
            return self.default_passes
        options = self.allowed_passes
        i = options.index(current) if current in options else options.index(self.default_passes)
        return options[max(0, min(len(options) - 1, i + step))]

    def can_step(self, current: int, step: int) -> bool:
        return not self.passes_locked and self.next_passes(current, step) != current

    def pattern_for_pass(self, pass_no: int, total: int) -> str:
        """Human-readable pattern written in a given pass (for the progress line)."""
        if self.key == "zero":
            return "0x00"
        if self.key == "one":
            return "0xFF"
        if self.key == "random":
            return "random data"
        if self.key == "dod":
            byte = DOD_SEQUENCE[total][pass_no - 1]
            return "random data" if byte is None else f"0x{byte:02X}"
        if self.key == "gutmann":
            entry = GUTMANN_SEQUENCE[pass_no - 1]
            if entry is None:
                return "random data"
            if isinstance(entry, tuple):
                return " ".join(f"0x{b:02X}" for b in entry)
            return f"0x{entry:02X}"
        return ""


_CUSTOM = tuple(range(1, MAX_CUSTOM_PASSES + 1))

# DoD 5220.22-M byte written in each pass. None = random data.
#   3 passes : 0x00, 0xFF, random
#   7 passes (ECE): 0x00, 0xFF, random, 0x96, 0x00, 0xFF, random
DOD_SEQUENCE = {
    3: (0x00, 0xFF, None),
    7: (0x00, 0xFF, None, 0x96, 0x00, 0xFF, None),
}

# Gutmann's 35 passes (1996 paper). None = random data, an int = one byte,
# a tuple = a 3-byte pattern that repeats across the file.
GUTMANN_SEQUENCE = (
    None, None, None, None,                                       # 1-4   random
    0x55, 0xAA, (0x92, 0x49, 0x24), (0x49, 0x24, 0x92),           # 5-8
    (0x24, 0x92, 0x49), 0x00, 0x11, 0x22,                         # 9-12
    0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0xAA,               # 13-20
    0xBB, 0xCC, 0xDD, 0xEE, 0xFF,                                 # 21-25
    (0x92, 0x49, 0x24), (0x49, 0x24, 0x92), (0x24, 0x92, 0x49),   # 26-28
    (0x6D, 0xB6, 0xDB), (0xB6, 0xDB, 0x6D), (0xDB, 0x6D, 0xB6),   # 29-31
    None, None, None, None,                                       # 32-35 random
)

METHODS: list[WipeMethod] = [
    WipeMethod("zero", "Zero Fill", "Writes 0x00 bytes",
               "Every byte is overwritten with zeros. Matches NIST SP 800-88 Clear "
               "with 1 pass.", 1, _CUSTOM),
    WipeMethod("one", "One Fill", "Writes 0xFF bytes",
               "Every byte is overwritten with ones (0xFF).", 1, _CUSTOM),
    WipeMethod("random", "Random Data", "Writes random bytes",
               "Every byte is overwritten with cryptographically random data. "
               "Matches NIST SP 800-88 Clear with 1 pass.", 1, _CUSTOM),
    WipeMethod("dod", "DoD 5220.22-M", "3 or 7 passes",
               "3 passes: 0x00, 0xFF, random.  7 passes (ECE): 0x00, 0xFF, random, "
               "0x96, 0x00, 0xFF, random.", 3, (3, 7)),
    WipeMethod("gutmann", "Gutmann", "35 fixed passes",
               "Peter Gutmann's 35-pass sequence: 4 random passes, 27 fixed patterns, "
               "4 random passes. The pass count cannot be changed.", 35, (35,),
               passes_locked=True),
]

BY_KEY = {m.key: m for m in METHODS}
DEFAULT_METHOD = "dod"
