# Meal Plan: Local UI + Async Grocy Sync

## Context

Today, meal plans are created directly in Grocy. Grocy's UI is slow and inconvenient — every line item requires a round-trip, and there's no batch interface.

We're building a local meal-plan creation experience that:
- Lets users compose multiple meal-plan lines (products + recipes) in a single modal, scoped to one date.
- Persists rows in our DB immediately (optimistic), then syncs them to Grocy in the background via a Celery batch job.
- Shows a progress bar while the batch runs.
- Treats Grocy as the canonical store for the *line data* (we mirror it back), but owns the lifecycle metadata (`status`, `done`, retries).
- Guards against double-consumption by flipping a local `done` flag when consumption execution runs.

Deletes remain on the Grocy side for v1; a periodic reconcile-sync hard-deletes locally-orphaned rows.

The intended outcome: opening the modal, composing 10–15 lines for a day, hitting Save, and watching them appear in Grocy in 30–60 seconds with a progress bar — without any blocked UI thread and without the user babysitting.

---

## Architecture

### Source of truth & sync direction

**Grocy-mirrored.** Local writes go through us, then POST to Grocy, then reconcile-fetch to capture Grocy's IDs. A periodic sync (`/objects/meal_plan` GET) reconciles out-of-band changes (deletes done in Grocy UI). Our `done` flag is preserved across reconciles because we match by `grocy_meal_plan_id`.

### Row lifecycle

```
created (modal submit)
  -> status='pending'           [row in our DB, no Grocy ID]
  -> status='syncing'            [Celery task picks it up]
  -> POST /objects/meal_plan
  -> status='synced' + grocy_meal_plan_id + grocy_shadow_recipe_id
                                [after batch fetch-after diff]
  -> done=true                   [when execute_consumption runs and creates MealPlanConsumption]

Failure path:
  -> status='failed' + error_message after 3 auto-retries on transient errors
  -> User can retry (single-line task) or delete locally
```

### Components

- **DB model** `MealPlan` — new table `meal_plans`. Schema below.
- **Celery batch task** `create_meal_plan_batch_task` — single task per modal submit; sequential POSTs; per-line auto-retry; final reconcile-fetch to assign Grocy IDs.
- **Reconcile task** `reconcile_meal_plans_task` — daily Celery beat + on-demand. GETs `/objects/meal_plan`, hard-deletes locally-orphaned rows, refreshes IDs.
- **Sections + units cache** — Redis, 24h TTL, lazy population.
- **API endpoints** — create (returns task_id), list (with date range filter), retry-line, delete-local, sections, units, job-status.
- **Frontend** — `MealPlanView`, `MealPlanModal`, `meal_plan` Pinia store; reactive client-side nutrition totals using `NutrientGauge` x 4.

### Critical: ID matching after POST

`POST /objects/meal_plan` doesn't return the created object's ID. After all POSTs in the batch:

1. `GET /objects/meal_plan` (filtered by household + a date window covering the batch's days)
2. Diff against the snapshot taken before the batch started — call the new rows the *candidate set*
3. Match each pending local row to a candidate by **tuple equality**: `(day, section_id, type, product_id|recipe_id, product_amount|recipe_servings)`. This is unambiguous for unique tuples and handles concurrent unrelated writes correctly.
4. If multiple candidates match the same tuple (the user added two identical lines), assign in **batch insertion order, scoped to the matching subset** — not globally by ascending id.
5. Capture both `id` (-> `grocy_meal_plan_id`) and the auto-created shadow recipe's negative ID (-> `grocy_shadow_recipe_id`)
6. If a local row has no tuple match in the candidate set, it stays `syncing`; the recovery sweep (see "Recovery sweep" below) will mark it `failed` after 10 minutes.

This is why the batch must be **sequential** (no fan-out): parallel POSTs would interleave with other clients' writes and break ordering, even with tuple matching.

---

## Data model

### `meal_plans` (new table)

```python
class MealPlan(SQLModel, table=True):
    __tablename__ = "meal_plans"

    id: int | None = Field(default=None, primary_key=True)

    household_id: int = Field(foreign_key="households.id", index=True)
    user_id: int = Field(foreign_key="users.id")  # creator; not indexed

    # Grocy linkage (nullable until batch reconcile fills them in)
    grocy_meal_plan_id: int | None = None
    grocy_shadow_recipe_id: int | None = None  # negative; only for type='product'

    # Mirrors Grocy payload
    type: str  # 'product' | 'recipe'
    day: date
    section_id: int

    product_id: int | None = None       # null when type='recipe'
    product_amount: Decimal | None = None
    product_qu_id: int | None = None

    recipe_id: int | None = None        # null when type='product'
    recipe_servings: Decimal | None = None

    # Lifecycle
    status: str = Field(default="pending")
    # one of: pending | syncing | synced | failed
    error_message: str | None = None
    retry_count: int = Field(default=0)

    done: bool = Field(default=False)
    done_at: datetime | None = None

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True),
                         server_default=func.now(), onupdate=func.now())
    )

    __table_args__ = (
        UniqueConstraint("household_id", "grocy_meal_plan_id",
                         name="uq_meal_plans_grocy_id"),
        Index("ix_meal_plans_household_day", "household_id", "day"),
        Index("ix_meal_plans_status_pending", "status",
              postgresql_where=text("status IN ('pending','syncing','failed')")),
    )
```

Notes:
- `UniqueConstraint(household_id, grocy_meal_plan_id)` — Postgres allows multiple NULLs, so pending rows don't conflict.
- Partial index keeps the recovery sweep cheap as `synced` rows accumulate.
- No FK to `meal_plan_sections` table because we don't have one (sections live in Redis cache).

### Alembic migration

New migration `026_add_meal_plans_table.py` following the style of `025_add_household_grocy_mapping.py`:
- `sa.Column` definitions matching the model
- FKs with `ondelete="CASCADE"` for `household_id`, `ondelete="SET NULL"` for `user_id`
- Server-default `func.now()` timestamps

### Done-flag wiring

Existing flow at `backend/app/services/consumption.py:924` already inserts a `MealPlanConsumption` row keyed on Grocy's `meal["id"]`. Add one operation in the same transaction:

```python
db.exec(
    update(MealPlan)
    .where(MealPlan.grocy_meal_plan_id == meal["id"])
    .values(done=True, done_at=datetime.now(UTC))
)
```

The existing dedup logic at line 924 already protects against double-consumption; the new `done` column is a denormalized read-cache for UI ("is this line consumed?") without a join.

**Non-rule (do not add):** Do **not** add a foreign key from `MealPlanConsumption.meal_plan_id` to `meal_plans.grocy_meal_plan_id`. The two are linked by Grocy's id only; reconcile may hard-delete a `meal_plans` row while keeping `MealPlanConsumption` history. A FK would block reconcile.

---

## Backend

### New service: `app/services/meal_plan.py`

- `create_lines(db, household_id, user_id, lines: list[MealPlanLineCreate]) -> list[MealPlan]` — Inserts rows with `status='pending'`. Returns inserted rows.

- `submit_batch(db, household_id, user_id, line_ids: list[int]) -> str` (task_id) — Enqueues `create_meal_plan_batch_task.delay(...)` first, then writes initial job state to Redis (matches `range-check` pattern at `backend/app/api/endpoints/consumption.py:200-211`), returns task_id. Rows stay `status='pending'` until the task itself flips them to `syncing` — this avoids a window where rows are marked `syncing` but no task exists (broker rejection or Redis outage).

- `reconcile(db, grocy_api, household_id) -> ReconcileResult` — GETs Grocy meal plans, diffs against local. **Skips rows where `status IN ('pending','syncing')`** to avoid racing in-flight batches. For each Grocy row: upsert-by-id. For each local row with non-null `grocy_meal_plan_id` not in Grocy: hard-delete. Used by both the periodic beat task and a manual "Refresh" button.

- `retry_line(db, household_id, line_id, grocy_api) -> MealPlan` — Single-line synchronous retry (or kicks a tiny task; sync is fine since it's one POST + one GET). **Resets `retry_count=0`** before kicking off — manual retry starts a fresh 3-retry cycle. **Authorization:** `SELECT meal_plans WHERE id = ? AND household_id IN (current_user's households)`; if not found, return 404 (do not return 403 — don't leak existence).

- `mark_done(db, grocy_meal_plan_id)` — called from `consumption.py` flow (above).

### New Celery task: `app/tasks/create_meal_plan_batch.py`

Bound task with `soft_time_limit=300, time_limit=360`. Uses its own `db = SessionLocal()` session (not the request session), wrapped in `try/finally: db.close()` matching `app/tasks/execute_consumption.py`. **Commits per-line** so partial progress survives a worker crash. Steps:

1. Build `grocy_api` via existing helper.
2. Mark all `line_ids` rows `status='syncing'` (single UPDATE, commit).
3. Snapshot existing Grocy meal_plan IDs for the day window.
4. For each line in `line_ids`:
   - `update_state(state='PROGRESS', meta={current, total, errors})`
   - Try POST with up to 3 retries (1s, 3s, 9s) on transport/5xx
   - On success: row stays `syncing` (ID not yet known); commit
   - On final failure: `status='failed'`, `error_message=truncate(str(exc), 500)`, `retry_count=3`; commit
5. After all POSTs: GET meal plans for the day window, diff against snapshot.
6. Match candidates to `syncing` rows by tuple (see "ID matching" above).
7. Set `status='synced'`, `grocy_meal_plan_id=...`, `grocy_shadow_recipe_id=...`. Rows that didn't match remain `syncing` for the recovery sweep to handle.
8. Return summary `{synced: N, failed: M, errors: [...]}`.

`error_message` is always truncated to 500 chars (Grocy's response body can include the full request payload — keeps DB rows bounded and avoids leaking large stack traces into the UI).

Pattern matches `app/tasks/execute_consumption.py`. State stored in Redis with TTL (matches range-check pattern).

### New Celery beat task: `recovery_sweep_meal_plans_task`

Runs every 5 minutes. Finds rows `WHERE status='syncing' AND updated_at < now() - interval '10 minutes'` and marks them `status='failed', error_message='Task timed out or worker crashed before reconcile'`. This handles two cases:
- Worker crashed mid-batch (Redis-backed task state may also be stale).
- A line's tuple didn't match in the post-batch diff (rare, but covered).

The user sees the failed row in the UI and can retry manually.

### New Celery beat task: `reconcile_meal_plans_task`

Daily at e.g. 04:30 (after the 04:00 product/recipe sync). For each household, call `reconcile(...)`.

### New API endpoints: `app/api/endpoints/meal_plan.py`

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/meal-plan/lines` | Create N lines + enqueue batch task. Returns `{task_id, line_ids}` |
| `GET`  | `/api/meal-plan/lines?household_id=&start_date=&end_date=` | List rows in date range |
| `POST` | `/api/meal-plan/lines/{id}/retry` | Single-line retry |
| `DELETE` | `/api/meal-plan/lines/{id}/local` | Hard-delete a `failed` row from our DB only. Same authorization rule as retry: ownership check by `household_id`, 404 on miss. Refuses to delete rows where `status != 'failed'` (returns 409). |
| `POST` | `/api/meal-plan/reconcile` | Manual refresh (kicks reconcile task) |
| `GET`  | `/api/meal-plan/job/{task_id}` | Poll job status (matches `consumption.py:218-234`) |
| `GET`  | `/api/meal-plan/sections?household_id=` | Cached sections (lazy-fill from Grocy) |
| `GET`  | `/api/meal-plan/units?household_id=&product_id=` | Cached available units for a product |

All authenticated, all use `get_grocy_api(household_id)` dependency for membership validation + decrypted key.

### Schemas: `app/schemas/meal_plan.py`

`MealPlanLineCreate`, `MealPlanLineRead`, `MealPlanBatchCreateRequest`, `MealPlanBatchCreateResponse`, `MealPlanJobStatusResponse`, `MealPlanSectionsResponse`, `MealPlanUnitsResponse`. Mirrors the `consumption.py` schema style.

### Caching layer

Redis keys + 24h TTL:

- `meal_plan:sections:household:{household_id}` -> `[{section_id, name, sort_number}, ...]`
  Filled on first `GET /sections` call by fetching `/objects/meal_plan_sections` from Grocy.

- `meal_plan:units:household:{household_id}:product:{product_id}` -> `[{qu_id, name, name_plural, is_stock_default, factor_to_stock}, ...]`
  Filled on first `GET /units?product_id=X` call. Source: existing unit-conversion logic + product's `qu_id_stock`/`qu_id_purchase` (see `backend/app/services/grocy_api.py:220-232`).
  **Validation:** before fetching/caching, the endpoint verifies `product_id` exists in our local `products_data` for that household. Prevents cache pollution from arbitrary `product_id` values.

Cache invalidation: TTL only for v1. Add manual purge if it becomes a problem.

---

## Frontend

### New view: `frontend/src/views/MealPlanView.vue`

- Header: date range picker, "+ Add to plan" button (opens modal), "Refresh from Grocy" button.
- Body: rows grouped by day, each day grouped by section (Breakfast / Lunch / Dinner). Each row shows:
  - Product/recipe name + amount + unit
  - Status badge: `pending`/`syncing` (spinner) / `synced` (check) / `done` (green check) / `failed` (red)
  - Failed rows: hover tooltip with `error_message` + inline Retry / Delete-locally buttons
- Use existing layout patterns from `ConsumeView.vue`.

### New component: `frontend/src/components/MealPlanModal.vue`

HeadlessUI Dialog. Layout:

```
+----------------------------------------------------------+
| Add to meal plan                                    [x]  |
+----------------------------------------------------------+
| Date: [2026-05-10 v]                                     |
|                                                          |
| Already on this day:                                     |
|   Breakfast: oats 50g [synced], egg 1pc [done]           |
|   Lunch:    (none)                                       |
|   Dinner:   chicken 200g [pending]                       |
|                                                          |
| --- New lines ---                                        |
| +------------------------------------------------------+ |
| | [Product v] [yogurt v search]  [120] [g v] [Brk v] [x]||
| |   ~85 kcal . 8g P . 12g C . 0g F                     ||
| +------------------------------------------------------+ |
| | [Recipe v]  [borscht v search] [1.5]      [Lun v] [x] ||
| |   ~520 kcal . 32g P . 45g C . 18g F                  ||
| +------------------------------------------------------+ |
| [+ Add line]                                             |
|                                                          |
| +-Total for day-------------------------------------+    |
| |  Cal       Protein     Carbs       Fat            |    |
| |  1850/2200  110/120     220/250     60/70         |    |
| +---------------------------------------------------+    |
+----------------------------------------------------------+
|                                  [Cancel]  [Save (3)]    |
+----------------------------------------------------------+
```

Per-line UI:
- **Type toggle**: switches the picker between products and recipes; clears the previously-selected id, resets unit & amount.
- **Picker**: HeadlessUI `Combobox` with type-ahead, recently-used pinned to top.
- **Amount field**: numeric, validates positive decimal.
- **Unit dropdown**: only for `type='product'`; populated from `/api/meal-plan/units` cache. Defaults to product's stock unit.
- **Section dropdown**: from `/api/meal-plan/sections` cache.
- **Per-row reactive nutrition**: computed from `productsStore` / `recipesStore`. Formulas (verify against `backend/app/core/nutrient_calculator.py` for the exact storage convention):
  - **Product line:** `kcal = amount × factor_to_stock × calories_per_100g / 100` (and same shape for protein/carbs/fat). `factor_to_stock` is 1 when the user picked the stock unit; otherwise the cached conversion factor.
  - **Recipe line:** `kcal = recipe_servings × calories_per_serving` (recipes already store per-serving aggregates in `recipesStore`).

Footer:
- 4 small `NutrientGauge` components (Cal / P / C / F). Targets pulled from `nutritionLimits.getLimitByDate(modal_date)`. Reactive — updates as user types.

Behavior:
- **Cancel** discards in-progress lines (modal-local state, no draft save).
- **Save** calls `POST /api/meal-plan/lines`, receives `task_id`, closes modal, switches the page to a progress-strip mode at the top showing "Syncing 3/12..." driven by polling `GET /api/meal-plan/job/{task_id}` every 1.5s. The pending rows already appear in the grouped view immediately (optimistic).
- **Keyboard**: Enter on last cell of last row -> add new row. Cmd/Ctrl+Enter -> submit.

### New store: `frontend/src/store/mealPlan.ts`

Pinia store mirroring the `recipes.ts` pattern:
- State: `lines[]`, `loading`, `error`, `currentJob: {task_id, current, total, errors[]} | null`
- Actions: `loadRange(start, end)`, `submit(lines)`, `pollJob()`, `retry(line_id)`, `deleteLocal(line_id)`, `reconcile()`
- `pollJob` self-schedules with `setTimeout(1500)` while job is `PENDING`/`PROGRESS`; clears on completion. On poll error (network, 5xx), backs off exponentially: 3s, 6s, 12s, then gives up and surfaces an error toast. Resumes normal cadence on first successful response.

### Router

Add a new route `/meal-plan` guarded by `requiresAuth`. Add a nav link.

---

## Critical files

**New files:**
- `backend/app/models/meal_plan.py`
- `backend/app/schemas/meal_plan.py`
- `backend/app/services/meal_plan.py`
- `backend/app/tasks/create_meal_plan_batch.py`
- `backend/app/tasks/reconcile_meal_plans.py`
- `backend/app/tasks/recovery_sweep_meal_plans.py`
- `backend/app/api/endpoints/meal_plan.py`
- `backend/migrations/versions/026_add_meal_plans_table.py`
- `frontend/src/views/MealPlanView.vue`
- `frontend/src/components/MealPlanModal.vue`
- `frontend/src/components/MealPlanLineRow.vue`
- `frontend/src/store/mealPlan.ts`
- `frontend/src/types/mealPlan.ts`
- `backend/tests/services_new/test_meal_plan.py`
- `backend/tests/api/test_meal_plan_endpoints.py`
- `frontend/src/tests/store/mealPlan.test.ts`
- `frontend/src/tests/components/MealPlanModal.test.ts`

**Modified files:**
- `backend/app/services/consumption.py` — at line ~924 (where `MealPlanConsumption` is inserted), also `UPDATE meal_plans SET done=true, done_at=now() WHERE grocy_meal_plan_id = meal["id"]`.
- `backend/app/db/base.py` — import the new `MealPlan` model so SQLModel metadata sees it.
- `backend/app/main.py` — mount new `meal_plan` router.
- `backend/app/tasks/__init__.py` — register new tasks; add reconcile (daily 04:30) and recovery sweep (every 5 min) to `celery_beat` schedule.
- `backend/app/services/grocy_api.py` — small additions:
  - `create_meal_plan_entry(payload) -> None` thin wrapper around `self.post('/objects/meal_plan', payload)`.
  - `get_meal_plan_sections() -> list[dict]` thin wrapper around `self.get('/objects/meal_plan_sections')`.
  - `get_quantity_unit_conversions_for_product(product_id) -> list[dict]` (extracted from existing logic at lines 220-232).
- `frontend/src/router/index.ts` — register `/meal-plan` route.
- `frontend/src/components/Layout.vue` (or wherever the nav lives) — add the nav link.

**Reused existing pieces:**
- `backend/app/core/auth.py:get_grocy_api` — household validation + decrypted key dependency.
- `backend/app/core/redis.py:get_redis` — Redis client.
- `backend/app/services/grocy_api.py:GrocyAPI.post` / `.get` — HTTP layer.
- `backend/app/api/endpoints/consumption.py:200-243` — Redis-backed job state pattern (copy this for the meal-plan job endpoint, not Celery `AsyncResult` directly).
- `frontend/src/components/NutrientGauge.vue` — modal footer gauges.
- `frontend/src/store/products.ts`, `recipes.ts` — already-cached product/recipe data for reactive nutrition math.
- `frontend/src/store/nutritionLimits.ts:getLimitByDate` — daily targets for the gauges.
- `frontend/src/utils/parseApiError.ts` — error parsing in store actions.

---

## Verification

### Backend

1. `make backend-shell`, then `pytest tests/services_new/test_meal_plan.py -v` — service unit tests cover:
   - `create_lines` inserts rows in `pending`
   - `submit_batch` enqueues a task and flips status to `syncing`
   - Mocked Grocy POST -> reconcile-fetch -> status `synced` with correct `grocy_meal_plan_id` ordering
   - Auto-retry on transient 5xx
   - Failed rows after 3 retries have correct error_message
   - `reconcile` hard-deletes rows missing from Grocy
   - `mark_done` flips both `done` and `done_at`
2. `pytest tests/api/test_meal_plan_endpoints.py -v` — endpoint tests cover the full happy path + auth/household-membership errors.
3. `make migrate` — run on a dev database; verify the new table, indices, FKs, and unique constraint exist.

### Frontend

1. `make frontend-shell`, then `npm run test -- mealPlan` — store and component unit tests.
2. `make up`. In a browser:
   - Navigate to `/meal-plan`.
   - Open modal, verify date defaults to today.
   - Pick a product -> unit dropdown populates from `/api/meal-plan/units` (check Network tab).
   - Type -> reactive nutrition under the row matches expected.
   - Add 5 lines, watch the 4 footer gauges update reactively.
   - Submit; modal closes; rows appear in `pending` immediately; progress bar at top counts up; rows transition to `synced` as the batch progresses.
   - Verify in Grocy UI that all 5 lines exist with correct `grocy_meal_plan_id`.
3. Provoke a failure: pick a deleted product (or temporarily kill the Grocy connection mid-batch). Verify failed row shows red, retry button works, delete-local removes the row.
4. Manually delete a row in Grocy UI. Click "Refresh from Grocy" in our UI. Verify the row disappears locally; rows that were `done` remain `done` in `MealPlanConsumption` history.
5. Run consumption-execute on a day with planned rows. Verify `done` flips to true on the consumed rows; verify a second consumption-execute on the same day does not create duplicate `MealPlanConsumption` rows (existing dedup at consumption.py:924 still works).

### Edge cases worth testing

- Two lines with identical `(day, section, product_id, amount, qu_id)` in one batch — both must end up with distinct `grocy_meal_plan_id`s (tuple match returns 2 candidates → assigned in batch insertion order, scoped to the matching subset).
- Concurrent unrelated write to Grocy mid-batch (e.g. another user adds a meal plan in another household) — must not leak into our match set; tuple matching scoped to our batch's tuples handles this.
- Batch interrupted by `SoftTimeLimitExceeded` — rows that were POSTed have `synced` (after final reconcile-fetch) or `failed`; rows not yet attempted stay `syncing` and are caught by the recovery sweep within ~10 minutes.
- IDOR: user A calls `POST /lines/{id}/retry` with user B's row id → 404, no state change.
- Polling endpoint returns 500 once → frontend backs off to 3s, then resumes 1.5s on next success.
- User picks "1 пачка" (factor_to_stock=300) → row nutrition = `1 × 300 × kcal_per_100g / 100`. Verify against the existing `nutrient_calculator.py` math.
- Token-refresh during a 60-second batch — task uses one Grocy session built at task start; should not be affected by frontend token rotation.
