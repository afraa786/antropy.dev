from datetime import UTC, datetime

from redis.asyncio import Redis

_BLACKLIST_PREFIX = "jwt:blacklist:"


class TokenBlacklist:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def revoke(self, jti: str, expires_at: datetime) -> None:
        ttl = max(int((expires_at - datetime.now(UTC)).total_seconds()), 0)
        if ttl > 0:
            await self._redis.set(f"{_BLACKLIST_PREFIX}{jti}", "1", ex=ttl)

    async def is_revoked(self, jti: str) -> bool:
        return await self._redis.exists(f"{_BLACKLIST_PREFIX}{jti}") == 1
