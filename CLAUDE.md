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

## Code Knowledge Graph

Each app can be mirrored as a dependency graph under `backend/graphify-out/` and `frontend/graphify-out/`. These are **local-only** (gitignored) — regenerated manually during development, not checked in. When present, two files per app matter:

- `index.json` — compact lookup: `{node_name → {kind, src, loc, community, block_id, out, in}}`. **Read this first** — a single Read gives full node lookup and edge traversal, and it's ~4× smaller than the raw graph.
- `graph.json` — the full raw node/edge graph. Fall back to it only for fields `index.json` omits.

When a question involves "where is X used", "what depends on Y", call/import chains, or any cross-file reasoning, **consult `index.json` before grepping the source tree** — it's faster and gives a complete dependency picture.

Regenerating needs the host `graphify` CLI on PATH (e.g. `conda activate grocy`); it is **not** dockerized:

```bash
make graphify     # fast AST-only refresh (no LLM): structural imports/calls only
```

`make graphify` runs `graphify update backend` + `graphify update frontend` (re-extracts code, no LLM, no tokens), then `scripts/graphify_index.py` derives `index.json` from each `graph.json`. This captures code structure but **not** semantic/doc relationships (code↔docs rationale edges from CONTEXT.md, ADRs, README). **For most navigation `make graphify` is enough** — the corpus is mostly code, which AST covers fully.

For the richer **semantic graph**, the extraction runs through LLM subagents — that's the token-heavy part. To keep it cheap:

- **`/model sonnet`, then `/graphify backend` and `/graphify frontend`.** The skill's semantic subagents inherit the session model, so switching to Sonnet first runs the whole extraction on Sonnet instead of Opus — far fewer tokens. Run the index step afterward (below).
- **Or Kimi (zero Claude-session tokens):** set `MOONSHOT_API_KEY` and use `graphify extract <path> --backend kimi` — graphify calls Kimi directly (~3× cheaper, richer graphs), bypassing the Claude session entirely.

After any semantic rebuild, refresh the lookup:

```bash
python3 scripts/graphify_index.py backend/graphify-out frontend/graphify-out
```

Treat a stale graph as a hint to regenerate before relying on it.

## Second-Brain Vault (durable project knowledge)

Separate from the code-graph vault above, the user's Obsidian **second-brain** vault at `~/obsidian/assistant/` is the canonical home for this project's durable, non-code knowledge — decisions, plans, and session history that aren't derivable from the source or git. Relevant notes:

- `Projects/grocy-nutrients.md` — canonical project state, key decisions, open questions, working rules
- `Projects/grocy-nutrients — MCP Server.md` — MCP server status and design
- `Dev Logs/` — per-session implementation reports

**Consult the relevant `Projects/` note before planning or non-trivial work**, and record significant decisions or session outcomes back to the vault (use the `obsidian-second-brain` skill). The project auto-memory (`MEMORY.md`) keeps terse pointers; the vault holds the depth. This is always available — no need for the user to mention it each session.

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
