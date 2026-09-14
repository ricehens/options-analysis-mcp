"""Small bounded process-local TTL cache for read-only snapshots."""

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True, slots=True)
class _Entry[V]:
    expires_at: float
    value: V


class TTLCache[K, V]:
    def __init__(
        self,
        *,
        ttl_seconds: float,
        max_entries: int,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if ttl_seconds < 0:
            raise ValueError("cache TTL cannot be negative")
        if max_entries < 1:
            raise ValueError("cache must allow at least one entry")
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[K, _Entry[V]] = OrderedDict()

    def get(self, key: K) -> V | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._clock():
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return entry.value

    def put(self, key: K, value: V) -> None:
        if self._ttl_seconds == 0:
            return
        self._entries[key] = _Entry(
            expires_at=self._clock() + self._ttl_seconds,
            value=value,
        )
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
