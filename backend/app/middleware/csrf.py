"""CSRF protection via Origin header check.

SameSite=Strict on auth cookies is the primary defense. This middleware adds a
belt-and-suspenders Origin check on mutating requests.

For most mutating endpoints a missing or non-allowlisted Origin is rejected.

Login/register are special: no cookie is set yet, and browsers may legitimately
omit Origin on a top-level form post, so a *missing* Origin is allowed there.
But when an Origin header IS present on login/register it must still be in the
allowlist — this blocks classic login-CSRF (an attacker silently logging the
victim into the attacker's account from a foreign origin).
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.core.config import settings

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# Paths where a *missing* Origin is tolerated (but a present one is still checked).
_ALLOW_MISSING_ORIGIN_PATHS = {"/api/auth/login", "/api/auth/register"}
# Exempt from the Origin check — /mcp uses Bearer auth, not ambient cookies.
_EXEMPT_PREFIXES = ("/mcp",)


def _blocked() -> JSONResponse:
    return JSONResponse({"detail": "Cross-origin request blocked"}, status_code=403)


async def csrf_origin_check(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.method in _MUTATING_METHODS and not request.url.path.startswith(_EXEMPT_PREFIXES):
        origin = request.headers.get("origin")
        if origin is None:
            if request.url.path not in _ALLOW_MISSING_ORIGIN_PATHS:
                return _blocked()
        elif origin not in settings.CORS_ORIGINS:
            return _blocked()
    return await call_next(request)
