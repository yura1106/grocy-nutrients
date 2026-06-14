import ipaddress

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.redis import get_redis


def _peer_is_trusted_proxy(peer: str) -> bool:
    try:
        ip = ipaddress.ip_address(peer)
    except ValueError:
        return False
    for cidr in settings.TRUSTED_PROXY_IPS:
        try:
            if ip in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def get_client_ip(request: Request) -> str:
    """Resolve the real client IP.

    Only honour X-Forwarded-For when the immediate socket peer is a trusted
    proxy; otherwise a client could spoof the header to evade or poison rate
    limiting. Returns the rightmost untrusted address from the forwarded chain.
    """
    peer = request.client.host if request.client else "unknown"
    if not _peer_is_trusted_proxy(peer):
        return peer

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return peer

    # XFF is "client, proxy1, proxy2, ...". Walk right-to-left and return the
    # first address that is NOT itself a trusted proxy — that's the real client.
    for candidate in reversed([h.strip() for h in forwarded.split(",") if h.strip()]):
        if not _peer_is_trusted_proxy(candidate):
            return candidate
    return peer


def _enforce(key: str, max_attempts: int, window_seconds: int) -> None:
    r = get_redis()
    attempts = r.get(key)
    if attempts and int(attempts) >= max_attempts:  # type: ignore[arg-type]
        ttl = r.ttl(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Try again in {ttl} seconds.",
        )
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    pipe.execute()


def check_login_rate_limit(request: Request, username: str | None = None) -> None:
    """Throttle login by client IP and (independently) by target account.

    Two keys are enforced: a per-IP key (blocks spray attacks from one source)
    and a per-account key (blocks distributed attacks against one account).
    """
    client_ip = get_client_ip(request)
    _enforce(
        f"login_attempts:ip:{client_ip}",
        settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
        settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )
    if username:
        _enforce(
            f"login_attempts:user:{username.lower()}",
            settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS_PER_ACCOUNT,
            settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        )


def reset_login_attempts(request: Request, username: str | None = None) -> None:
    """Clear the counters for a successful login.

    Only the keys tied to THIS login (this IP and this username) are cleared.
    The previous implementation deleted the whole-IP counter, which let an
    attacker who owned one valid account reset the brute-force window between
    batches against other accounts.
    """
    r = get_redis()
    client_ip = get_client_ip(request)
    keys = [f"login_attempts:ip:{client_ip}"]
    if username:
        keys.append(f"login_attempts:user:{username.lower()}")
    r.delete(*keys)


def check_sensitive_rate_limit(request: Request, scope: str) -> None:
    """Throttle a sensitive endpoint (forgot-password, reset, deletion, refresh)
    by client IP under a named scope."""
    client_ip = get_client_ip(request)
    _enforce(
        f"sensitive:{scope}:{client_ip}",
        settings.SENSITIVE_RATE_LIMIT_MAX_ATTEMPTS,
        settings.SENSITIVE_RATE_LIMIT_WINDOW_SECONDS,
    )
