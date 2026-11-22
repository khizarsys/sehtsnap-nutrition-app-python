"""In-memory usage limits for one server instance."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

HOUR_SECONDS = 3600
DAY_SECONDS = 86400


class RateLimiter:
    """Sliding-window limits per user and across all users."""

    def __init__(
        self, user_limit: int, global_limit: int, clock: Callable[[], float] = time.time
    ) -> None:
        self._user_limit = user_limit
        self._global_limit = global_limit
        self._clock = clock
        self._lock = threading.Lock()
        self._users: defaultdict[str, deque[float]] = defaultdict(deque)
        self._global: deque[float] = deque()

    @staticmethod
    def _trim(window: deque[float], cutoff: float) -> None:
        while window and window[0] <= cutoff:
            window.popleft()

    def allow(self, uid: str) -> bool:
        """Record and allow a request if both limits have capacity."""
        now = self._clock()
        with self._lock:
            self._trim(self._global, now - DAY_SECONDS)
            user_window = self._users[uid]
            self._trim(user_window, now - HOUR_SECONDS)
            if len(user_window) >= self._user_limit or len(self._global) >= self._global_limit:
                if not user_window:
                    del self._users[uid]
                return False
            user_window.append(now)
            self._global.append(now)
            return True
