import redis
from fastapi import HTTPException, Request, status

from app.core.config import settings

_redis_client = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def check_login_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    key = f"login_attempts:{client_ip}"
    r = _get_redis()

    attempts = r.get(key)
    if attempts and int(attempts) >= settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
        ttl = r.ttl(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {ttl} seconds.",
        )

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS)
    pipe.execute()


def reset_login_attempts(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    key = f"login_attempts:{client_ip}"
    _get_redis().delete(key)
