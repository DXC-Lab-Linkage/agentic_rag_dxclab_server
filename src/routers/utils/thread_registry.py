"""Track the last use of each chat thread to limit the conversation history kept in memory"""

import time
from collections import OrderedDict


class ThreadRegistry:
    """Keep at most `max_threads` threads, and drop threads not used for `ttl_sec` seconds.

    This class only decides which chat_ids should be removed.
    The caller deletes the conversation history of the returned chat_ids.
    """

    def __init__(self, max_threads: int, ttl_sec: float):
        self.max_threads = max_threads
        self.ttl_sec = ttl_sec
        # chat_id -> last used time. The oldest entry is at the front.
        self._last_used: OrderedDict[str, float] = OrderedDict()

    def touch(self, chat_id: str) -> list[str]:
        """Mark the chat_id as used now.

        Returns:
          list[str]: chat_ids whose conversation history should be deleted.
        """
        now = time.monotonic()
        self._last_used[chat_id] = now
        self._last_used.move_to_end(chat_id)
        evicted = []
        while self._last_used:
            oldest_id, oldest_time = next(iter(self._last_used.items()))
            if oldest_id == chat_id:
                # Never evict the thread that is being used
                break
            if (
                len(self._last_used) > self.max_threads
                or now - oldest_time >= self.ttl_sec
            ):
                del self._last_used[oldest_id]
                evicted.append(oldest_id)
            else:
                break
        return evicted
