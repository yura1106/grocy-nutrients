# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important: All Commands Run Inside Docker

All development commands must be run inside Docker containers — never locally. Use `make` targets or `docker compose exec` directly.

```bash
# Start the stack (dev mode with hot reload)
make up

# Open a shell inside backend/frontend
make backend-shell
make frontend-shell
```

## Common Commands

```bash
# Tests — user runs manually, never run automatically
make test-backend        # pytest inside backend container
make test-frontend       # npm run test inside frontend container

# Single backend test
docker compose exec backend pytest tests/api/test_auth.py::TestRegister::test_register_success -v

# Linting
make lint-python         # ruff check + mypy
make lint-js             # vue-tsc + eslint
make lint-fix-python     # ruff --fix + ruff format
make lint-fix-js         # eslint --fix

# Database migrations
make migrate             # alembic upgrade head

# Full CI (lint + tests + build + audit)
make ci
```

## Architecture Overview

### Services

| Service | Port | Description |
|---------|------|-------------|
| `backend` | 8000 | FastAPI app |
| `frontend` | 5173 | Vue 3 dev server |
| `db` | 5432 | PostgreSQL 15 |
| `redis` | 6379 | Celery broker + JWT blacklist |
| `celery_worker` | — | Background task executor |
| `celery_beat` | — | Task scheduler (sync at 04:00) |

### Backend (`backend/app/`)

The backend is a **FastAPI + SQLModel** (SQLAlchemy + Pydantic combined) app with this layered structure:

- `main.py` — FastAPI app, CORS config, router mount at `/api`
- `core/config.py` — Pydantic settings from env vars (`JWT_SECRET_KEY`, `DATABASE_URL`, etc.)
- `core/auth.py` — `get_current_user` and `get_grocy_api` FastAPI dependencies
- `core/security.py` — JWT creation/verification, token blacklisting in Redis, bcrypt
- `core/encryption.py` — Themis SCellSeal encrypt/decrypt for Grocy API keys
- `core/rate_limit.py` — Redis-backed login rate limiting
- `core/nutrient_calculator.py` — recipe/portion nutrient aggregation (core feature math)
- `core/redis.py` — singleton Redis client factory
- `api/endpoints/` — Route handlers (auth, users, households, products, recipes, consumption, daily_nutrition, nutrition_limits, sync)
- `services/` — Business logic: `grocy_api.py` (HTTP client), `product.py`, `recipe.py`, `user.py`, `household.py`, `consumption.py`, `daily_nutrition.py`, `nutrition_limits.py`, `health_profile.py`, `email.py`
- `models/` — SQLModel table definitions (User, Household, HouseholdUser, Role, Recipe, Product, DailyNutrition, NutritionLimit, UserHealthProfile, Currency, etc.)
- `schemas/` — Pydantic schemas for API request/response (separate from models)
- `tasks/` — Celery tasks: `sync_products`, `sync_recipes`, `execute_consumption`, `range_check`, `email`
- `db/base.py` — `get_db` dependency; imports all models so SQLModel.metadata is complete

### Key Dependency Pattern: `get_grocy_api`

Most data endpoints require `household_id` as a query param. `get_grocy_api` in `core/auth.py`:
1. Validates the user is an active member of that household
2. Decrypts the per-user Grocy API key (stored encrypted in `HouseholdUser.grocy_api_key`)
3. Returns a configured `GrocyAPI` instance

### API Key Encryption

Grocy API keys are encrypted at rest using **Themis SCellSeal** keyed by the user's bcrypt `hashed_password`. Functions in `core/encryption.py`: `encrypt_api_key`, `decrypt_api_key`, `reencrypt_user_api_keys`. On password change, all keys are re-encrypted with the new hash.

### Frontend (`frontend/src/`)

Vue 3 + TypeScript SPA:
- `store/auth.ts` — Pinia auth store: JWT tokens in localStorage, axios interceptors for token refresh
- `store/health.ts`, `store/household.ts`, `store/nutritionLimits.ts`, `store/recipes.ts`, `store/recipeDetail.ts` — domain Pinia stores
- `router/index.ts` — Vue Router with `requiresAuth` meta guard
- `views/` — Page-level components (Dashboard, Products, Recipes, Consumption, Profile, etc.)
- `components/` — Reusable UI components
- `composables/` — Composition API hooks
- All API calls use axios with relative paths (`/api/...`)

## Test Infrastructure

### Backend

Uses **SQLite in-memory** (StaticPool) — PostgreSQL-specific types work because SQLModel abstracts them.

Three client fixtures in `tests/conftest.py`:
- `client` — authenticated (overrides `get_db` + `get_current_user`)
- `unauthenticated_client` — overrides only `get_db` (for auth endpoint tests)
- `grocy_client` — overrides `get_db` + `get_current_user` + `get_grocy_api` (mock)

**Critical**: `server_default=func.now()` does NOT fire in SQLite. Always set `created_at=datetime.now(UTC)` explicitly in test fixtures.

Frontend tests use **Vitest + jsdom + @vue/test-utils**. Two mocking strategies coexist: `vi.mock('axios')` for unit/store tests, and **MSW** (`tests/handlers.ts`) for component tests that exercise real network calls.

### Test file locations
- Backend: `backend/tests/{api,core,services,services_new,utils}/` (`services` and `services_new` coexist during a transitional refactor — new tests go in `services_new`)
- Frontend: `frontend/src/tests/{components,composables,router,store,views}/` plus `setup.ts`, `handlers.ts`
