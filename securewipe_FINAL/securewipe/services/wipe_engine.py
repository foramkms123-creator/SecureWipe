"""Handles the disk wiping process."""
import threading
import time
from dataclasses import dataclass, replace

from config import DEMO_MAX_SECONDS, NOMINAL_WIPE_SPEED_MB_S, SIMULATE_WIPE
from services.algorithms import dod, gutmann, one_fill, random_data, zero_fill
from services.algorithms.writer import Cancelled, Hooks
from services.target_info import TargetInfo
from services.wipe_methods import WipeMethod

RUNNING, SUCCESS, CANCELLED, FAILED = "RUNNING", "SUCCESS", "CANCELLED", "FAILED"

# Algorithms that really overwrite (key from wipe_methods.py -> module with run()).
ALGORITHMS = {"zero": zero_fill, "one": one_fill, "random": random_data, "dod": dod,
              "gutmann": gutmann}


@dataclass
class Progress:
    state: str = RUNNING
    bytes_done: int = 0        # across all passes
    bytes_total: int = 0       # target size x passes
    pass_no: int = 1
    passes: int = 1
    pattern: str = ""
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0

    @property
    def fraction(self) -> float:
        return 1.0 if self.bytes_total == 0 else min(1.0, self.bytes_done / self.bytes_total)


def estimate_seconds(size_bytes: int, passes: int) -> float:
    """Rough duration before a wipe starts (the live figure replaces it once running)."""
    return size_bytes * passes / (NOMINAL_WIPE_SPEED_MB_S * 1024 * 1024)


class WipeJob:
    def __init__(self, target: TargetInfo, method: WipeMethod, passes: int):
        self.target, self.method, self.passes = target, method, passes
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._p = Progress(bytes_total=max(target.total_size, 1) * passes, passes=passes,
                           pattern=method.pattern_for_pass(1, passes))
        self._thread = threading.Thread(target=self._run, daemon=True)

    # ---- API used by the UI -----------------------------------------------------
    def start(self) -> None:
        self._p.started_at = time.time()
        self._thread.start()

    def cancel(self) -> None:
        self._cancel.set()

    def snapshot(self) -> Progress:
        with self._lock:
            return replace(self._p)

    @property
    def is_running(self) -> bool:
        return self._thread.is_alive()

    # ---- worker -----------------------------------------------------------------
    def _update(self, **fields) -> None:
        with self._lock:
            for k, v in fields.items():
                setattr(self._p, k, v)

    def _run(self) -> None:
        try:
            (self._run_simulated if SIMULATE_WIPE else self._run_real)()
            state = CANCELLED if self._cancel.is_set() else SUCCESS
            self._update(state=state, finished_at=time.time())
        except Exception as exc:                       # surface any error to the UI
            self._update(state=FAILED, error=str(exc), finished_at=time.time())

    def _run_simulated(self) -> None:
        total = self._p.bytes_total
        per_pass = total // self.passes or 1
        duration = min(max(estimate_seconds(self.target.total_size, self.passes), 3.0),
                       DEMO_MAX_SECONDS)
        speed = total / duration                       # bytes per second
        done, last = 0, time.time()
        while done < total and not self._cancel.is_set():
            time.sleep(0.1)
            now = time.time()
            done = min(total, done + int(speed * (now - last)))
            last = now
            pass_no = min(self.passes, done // per_pass + 1)
            self._update(bytes_done=done, pass_no=pass_no,
                         pattern=self.method.pattern_for_pass(pass_no, self.passes))

    def _add_bytes(self, n: int) -> None:
        with self._lock:
            self._p.bytes_done += n

    def _run_real(self) -> None:
        algorithm = ALGORITHMS.get(self.method.key)
        if algorithm is None:                   # no overwrite code for this method
            raise NotImplementedError(f"{self.method.name} is not implemented yet")
        hooks = Hooks(
            should_stop=self._cancel.is_set,
            add_bytes=self._add_bytes,
            set_total=lambda total: self._update(bytes_total=total),
            set_pass=lambda n: self._update(pass_no=n,
                                            pattern=self.method.pattern_for_pass(n, self.passes)),
        )
        try:
            algorithm.run(self.target, self.passes, hooks)
        except Cancelled:
            pass                                 # _run() marks the job CANCELLED
