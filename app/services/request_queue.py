from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass
class MediaRequest:
    url: str
    requested_by: str = ""
    request_type: str = "youtube"


class RequestQueue:
    def __init__(self) -> None:
        self._queue: deque[MediaRequest] = deque()

    def add(self, item: MediaRequest) -> None:
        self._queue.append(item)

    def pop_next(self) -> Optional[MediaRequest]:
        if not self._queue:
            return None
        return self._queue.popleft()

    def peek(self) -> Optional[MediaRequest]:
        if not self._queue:
            return None
        return self._queue[0]

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def clear(self) -> None:
        self._queue.clear()

    def items(self) -> list[MediaRequest]:
        return list(self._queue)

    def __len__(self) -> int:
        return len(self._queue)