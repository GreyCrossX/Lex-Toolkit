import logging
import os
from time import monotonic
from typing import Dict, List

import redis

logger = logging.getLogger("rate_limit")

REDIS_URL = os.environ.get("RATE_LIMIT_REDIS_URL") or os.environ.get("CELERY_BROKER_URL") or "redis://redis:6379/0"
_client: redis.Redis | None = None
_fallback_buckets: Dict[str, List[float]] = {}


class RateLimitExceeded(Exception):
    pass


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
    return _client


def enforce(bucket: str, identifier: str, limit: int, window_seconds: int) -> None:
    """
    Sliding fixed-window rate limit using Redis INCR/EXPIRE.
    Falls back to in-process buckets if Redis is unavailable.
    """
    key = f"rl:{bucket}:{identifier}"
    try:
        client = _get_client()
        count = client.incr(key)
        if count == 1:
            client.expire(key, window_seconds)
        if count > limit:
            raise RateLimitExceeded
        return
    except RateLimitExceeded:
        raise
    except Exception as exc:
        logger.warning("Rate limit Redis fallback engaged: %s", exc.__class__.__name__)

    # Fallback: naive in-memory bucket by monotonic time.
    now = monotonic()
    timestamps = _fallback_buckets.setdefault(key, [])
    cutoff = now - window_seconds
    while timestamps and timestamps[0] < cutoff:
        timestamps.pop(0)
    if len(timestamps) >= limit:
        raise RateLimitExceeded
    timestamps.append(now)
