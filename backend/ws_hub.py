"""Fan-out of real backend events to connected dashboard clients.

Camera worker threads call publish() from outside the event loop. publish() is thread-safe:
it hands the message to the loop with call_soon_threadsafe. Each client has a bounded queue.
A slow or stalled browser loses its own oldest messages; it never blocks a camera worker
or other clients.
"""

from __future__ import annotations

import asyncio
import itertools
import threading
from typing import Any

DEFAULT_QUEUE_SIZE = 200


class Hub:
    def __init__(self, queue_size: int = DEFAULT_QUEUE_SIZE) -> None:
        self._queue_size = queue_size
        self._clients: dict[int, asyncio.Queue] = {}
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self.dropped = 0

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def subscribe(self) -> tuple[int, asyncio.Queue]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._queue_size)
        with self._lock:
            client_id = next(self._ids)
            self._clients[client_id] = queue
        return client_id, queue

    def unsubscribe(self, client_id: int) -> None:
        with self._lock:
            self._clients.pop(client_id, None)

    def publish(self, message: dict[str, Any]) -> None:
        """Safe to call from any thread. Drops silently if no event loop is bound yet."""
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(self._fan_out, message)
        except RuntimeError:
            return

    def _fan_out(self, message: dict[str, Any]) -> None:
        with self._lock:
            queues = list(self._clients.values())
        for queue in queues:
            if queue.full():
                try:
                    queue.get_nowait()
                    self.dropped += 1
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                self.dropped += 1
