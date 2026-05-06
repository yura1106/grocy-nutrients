from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.api import api_router
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.middleware.csrf import csrf_origin_check

app = FastAPI(
    title="Grocy Nutrients API",
    description=(
        "Nutrition tracking and consumption analytics for self-hosted Grocy.\n\n"
        "Daily nutrition limits, recipe nutrient calculation, consumption logging, "
        "and per-user encrypted Grocy API keys.\n\n"
        "Most data endpoints require an `household_id` query parameter. Authentication "
        "is via HttpOnly session cookies set by `POST /api/auth/login`."
    ),
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# CORS — must allow credentials so cookies traverse the proxy correctly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# CSRF: belt-and-suspenders Origin check on top of SameSite=Strict cookies.
app.middleware("http")(csrf_origin_check)

app.include_router(api_router, prefix="/api")


@app.get("/api/openapi.json", include_in_schema=False)
async def openapi_schema(_user: AuthenticatedUser = Depends(get_current_user)) -> JSONResponse:
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    return JSONResponse(schema)


@app.get("/api/docs", include_in_schema=False)
async def swagger_ui(_user: AuthenticatedUser = Depends(get_current_user)) -> HTMLResponse:
    # Read-only schema browser: try-it-out is disabled by passing an empty list
    # of supported submit methods to swagger-ui.
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title=f"{app.title} — Swagger UI",
        swagger_ui_parameters={"supportedSubmitMethods": []},
    )


@app.get("/")
async def root():
    return {
        "message": "Welcome to Grocy Nutrients API. Go to /api/docs for the API documentation."
    }
