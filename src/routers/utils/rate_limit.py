"""In-memory sliding window rate limiter"""

import time
from collections import deque


class RateLimiter:
    """Allow at most `limit` requests per `window_sec` seconds for each key.

    The state is kept in the memory of the process, so it is not shared between multiple server processes.
    """

    # When the number of keys exceeds this value, keys without recent requests are removed.
    PRUNE_THRESHOLD = 1024

    def __init__(self, limit: int, window_sec: float):
        self.limit = limit
        self.window_sec = window_sec
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        """Record a request for the key.

        Returns:
          bool: True if the request is within the limit, False if it should be rejected.
        """
        now = time.monotonic()
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= self.window_sec:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        if len(self._hits) > self.PRUNE_THRESHOLD:
            self._prune(now)
        return True

    def _prune(self, now: float):
        for k in list(self._hits):
            hits = self._hits[k]
            if not hits or now - hits[-1] >= self.window_sec:
                del self._hits[k]
