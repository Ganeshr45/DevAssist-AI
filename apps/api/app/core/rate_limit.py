import time

from fastapi import HTTPException, Request

from app.core.config import settings
from app.db.redis import redis


async def enforce_limit(key: str, limit: int, window_seconds: int) -> None:
    bucket = int(time.time()) // window_seconds
    redis_key = f"limit:{key}:{bucket}"
    try:
        count = int(
            await redis.eval(
                "local n=redis.call('INCR',KEYS[1]); "
                "if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; "
                "return n",
                1,
                redis_key,
                window_seconds,
            )
        )
    except Exception:
        if settings.app_env == "production":
            raise HTTPException(503, "Request service temporarily unavailable") from None
        return
    if count > limit:
        raise HTTPException(
            429, "Rate limit exceeded", headers={"Retry-After": str(window_seconds)}
        )


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"
