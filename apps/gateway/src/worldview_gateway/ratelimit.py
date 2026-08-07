"""Rate limiting for the gateway.

Fixed-window limiter, keyed by client IP and upstream service. Uses an
in-memory store by default; switches to Redis when ``REDIS_URL`` is set so the
limit holds across multiple gateway replicas.
"""

import asyncio
import time
from collections import defaultdict


class RateLimiter:
    """Asynchronous, fixed-window rate limiter contract."""

    async def allow(self, key: str) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        raise NotImplementedError


class MemoryRateLimiter(RateLimiter):
    """In-process limiter for single-instance development/dev environments."""

    def __init__(self, rpm: int, window_sec: float = 60.0) -> None:
        self.rpm = rpm
        self.window = window_sec
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        async with self._lock:
            bucket = [t for t in self._hits[key] if now - t < self.window]
            if len(bucket) >= self.rpm:
                retry = max(1, int(self.window - (now - bucket[0])) + 1)
                self._hits[key] = bucket
                return False, retry
            bucket.append(now)
            self._hits[key] = bucket
            if len(self._hits) > 10_000:  # bound memory when many distinct clients
                for k in list(self._hits):
                    if not self._hits[k]:
                        del self._hits[k]
            return True, 0


class RedisRateLimiter(RateLimiter):
    """Shared-limit limiter backed by Redis for multi-replica deployments."""

    def __init__(self, url: str, rpm: int, window_sec: float = 60.0) -> None:
        import redis.asyncio as aioredis

        self._redis = aioredis.from_url(url)
        self.rpm = rpm
        self.window = int(window_sec)

    async def allow(self, key: str) -> tuple[bool, int]:
        bucket = f"rl:{key}"
        count = await self._redis.incr(bucket)
        if count == 1:
            await self._redis.expire(bucket, self.window)
        if count > self.rpm:
            ttl = await self._redis.ttl(bucket)
            return False, max(1, int(ttl))
        return True, 0


def build_rate_limiter(redis_url: str | None, rpm: int) -> RateLimiter:
    if redis_url:
        return RedisRateLimiter(redis_url, rpm)
    return MemoryRateLimiter(rpm)
