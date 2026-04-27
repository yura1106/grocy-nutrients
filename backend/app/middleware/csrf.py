"""CSRF protection via Origin header check.

SameSite=Strict on auth cookies is the primary defense. This middleware adds a
belt-and-suspenders Origin check on mutating requests: if the Origin header is
missing or not in the allowlist, the request is rejected. Login/register are
bypassed because no cookie is set yet and browsers may omit Origin on form
posts to those endpoints.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.core.config import settings

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_BYPASS_PATHS = {"/api/auth/login", "/api/auth/register"}


async def csrf_origin_check(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.method in _MUTATING_METHODS and request.url.path not in _BYPASS_PATHS:
        origin = request.headers.get("origin")
        if not origin or origin not in settings.CORS_ORIGINS:
            return JSONResponse(
                {"detail": "Cross-origin request blocked"},
                status_code=403,
            )
    return await call_next(request)
