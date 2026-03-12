"""
src/utils/cache.py
Simple TTL-based in-process cache for SQL query results.
Keyed by (user_query, sql) to avoid serving stale results after schema changes.
"""
import hashlib
import time
from typing import Any

from src.core.config import get_settings
from src.core.logger import get_logger

log = get_logger(__name__)


class QueryCache:
    def __init__(self, ttl_seconds: int | None = None):
        settings = get_settings()
        self._ttl = ttl_seconds if ttl_seconds is not None else settings.query_cache_ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def _key(self, user_query: str, sql: str) -> str:
        raw = f"{user_query.strip().lower()}::{sql.strip().lower()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, user_query: str, sql: str) -> Any | None:
        key = self._key(user_query, sql)
        if key in self._store:
            ts, value = self._store[key]
            if time.time() - ts < self._ttl:
                log.info("cache_hit", key_prefix=key[:12])
                return value
            del self._store[key]
        return None

    def set(self, user_query: str, sql: str, value: Any) -> None:
        key = self._key(user_query, sql)
        self._store[key] = (time.time(), value)
        log.info("cache_set", key_prefix=key[:12], ttl=self._ttl)

    def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count

    @property
    def size(self) -> int:
        return len(self._store)


# Singleton instance
_cache: QueryCache | None = None


def get_cache() -> QueryCache:
    global _cache
    if _cache is None:
        _cache = QueryCache()
    return _cache
