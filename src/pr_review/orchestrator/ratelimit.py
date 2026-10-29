"""W2: one tokens-per-minute budget shared by all specialists (Groq free tier: 8,000 TPM, S1)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class TokenBucket:
    """Sliding 60-second window. reserve(n) waits until n more tokens fit in the window, then records them.
    Calls still run in parallel whenever they fit; they just never add up to more than `per_minute`."""

    def __init__(self, per_minute: int = 8000, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep, window_s: float = 60.0):
        self.per_minute, self.clock, self.sleep, self.window = per_minute, clock, sleep, window_s
        self._log: list[tuple[float, int]] = []
        self._lock = threading.Lock()

    def reserve(self, n: int) -> float:
        """Returns seconds waited. A single call bigger than the whole budget is refused (it could never fit)."""
        if n > self.per_minute:
            raise ValueError(f"{n} tokens can never fit a {self.per_minute}/min budget")
        waited = 0.0
        while True:
            with self._lock:
                now = self.clock()
                self._log = [(t, k) for t, k in self._log if t > now - self.window]
                used = sum(k for _, k in self._log)
                if used + n <= self.per_minute:
                    self._log.append((now, n))
                    return waited
                pause = max(0.05, self._log[0][0] + self.window - now)
            self.sleep(pause)
            waited += pause

    def used(self) -> int:
        with self._lock:
            now = self.clock()
            return sum(k for t, k in self._log if t > now - self.window)
