from collections import OrderedDict
from copy import deepcopy
from threading import RLock
from time import monotonic
from typing import Hashable


CacheKey = tuple[Hashable, ...]


class TTLCache:
    def __init__(self, max_entries: int = 256):
        self._entries: OrderedDict[CacheKey, tuple[float, object]] = OrderedDict()
        self._generations: dict[str, int] = {}
        self._max_entries = max_entries
        self._lock = RLock()

    def generation(self, namespace: str) -> int:
        with self._lock:
            return self._generations.get(namespace, 0)

    def get(self, key: CacheKey) -> object | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None

            expires_at, value = entry
            if expires_at <= monotonic():
                del self._entries[key]
                return None

            self._entries.move_to_end(key)
            return deepcopy(value)

    def set(
        self,
        key: CacheKey,
        value: object,
        ttl_seconds: float,
        expected_generation: int | None = None,
    ) -> None:
        with self._lock:
            namespace = str(key[0]) if key else ""
            if (
                expected_generation is not None
                and self._generations.get(namespace, 0) != expected_generation
            ):
                return

            now = monotonic()
            expired_keys = [
                cached_key
                for cached_key, (expires_at, _) in self._entries.items()
                if expires_at <= now
            ]
            for cached_key in expired_keys:
                del self._entries[cached_key]

            self._entries[key] = (now + ttl_seconds, deepcopy(value))
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def invalidate(self, namespace: str) -> None:
        with self._lock:
            self._generations[namespace] = self._generations.get(namespace, 0) + 1
            stale_keys = [
                key for key in self._entries if key and key[0] == namespace
            ]
            for key in stale_keys:
                del self._entries[key]


response_cache = TTLCache()


def user_cache_scope(user: object) -> str | None:
    user_id = getattr(user, "doc_id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    return str(user_id) if user_id is not None else None