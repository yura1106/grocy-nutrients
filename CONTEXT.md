# CONTEXT

Domain glossary and key concepts for grocy-reports. Terms here are meaningful to
domain experts — not implementation details.

## Glossary

### Fresh product
A whole, unprocessed food whose sugars are "natural" rather than added/processed
(e.g. a whole banana, a whole apple). The user wants the sugars contributed by
fresh products **excluded from the tracked daily sugar total**, on the principle
that natural sugars in whole foods should not count against the sugar limit the
same way processed sugars do.

- **Naming:** code field `is_fresh` (matches the codebase's `is_active` convention);
  UI label **"Свіжий продукт"** with a hint/tooltip: "цукри з цього продукту не
  враховуються в денну норму цукрів".
- Modeled as a boolean flag `is_fresh` on **`Product`** (product identity), not on
  `ProductData` (the nutrition snapshot). Freshness is a stable property of the
  food itself, set once and applied to all past and future consumption of that product.
- **Local-only, permanently — never synced to Grocy.** `is_fresh` is this app's domain
  concept with no Grocy equivalent. It lives only in the local `products` table, and
  round-tripping it to Grocy is a permanent non-goal (not a deferred one). Confirmed safe
  across syncs: `upsert_product` only updates `name`/`active`/`product_group_id`/`qu_id_stock`
  on existing rows, so it never resets `is_fresh`.
- `is_fresh` is the **first locally-editable product field** — every other product field
  is a one-way mirror of Grocy.

**Toggle endpoint:** dedicated `PATCH /products/{id}/fresh`, body `{is_fresh: bool}`,
`household_id` query param. Because it is a **write**, it verifies active household
membership (inline `select(HouseholdUser).where(household_id, user_id,
is_active==True)` → 403 if not a member — same check `build_grocy_api` uses) and
scopes the UPDATE `WHERE id = ? AND household_id = ?` (404 on mismatch). The existing
read endpoints (`get_products`, `get_product`) skip this membership check; that loose
pattern is NOT retrofitted here — out of scope.

### Tracked sugar total (daily)
The sum of `carbohydrates_of_sugars * quantity` across all consumed products for a
day, plus note-derived sugars. **Computed on the fly at read time** — it is NOT a
stored value. Lives in two read paths:
- `_build_daily_stats` — per-day list (`GET /consumption/stats`)
- `get_consumed_day_detail` — single-day breakdown (`GET /consumption/stats/{date}`)

Because the total is computed at read time, excluding fresh-product sugars is a
matter of changing how these endpoints sum — there is no stored total to decrement
and no historical migration/recompute needed.

**Scope of exclusion:** Fresh products are excluded from the **sugar total only**.
Their carbohydrates, calories, and all other nutrients still count fully and
normally. The rationale (per the user) is specifically that natural sugars
shouldn't count as sugar — but a whole banana still has real carbs and energy that
matter for the rest of the tracking. Only the sugar accumulation branches on
`is_fresh`; every other nutrient sums unchanged.

**Recipes vs standalone:** A fresh product's sugars are excluded **only when the
product was consumed standalone** — i.e. `is_fresh AND
ConsumedProduct.recipe_grocy_id IS NULL`. The same fresh product consumed as a
recipe ingredient (non-null `recipe_grocy_id`) counts its sugars **normally**
toward the daily sugar total.

Rationale (per the user): a whole banana eaten on its own is "natural sugar" and
shouldn't count; but a banana baked into a recipe is part of a prepared dish and
should count like any other recipe sugar. The freshness flag is still
identity-level on `Product` (set once per food), but the *exclusion* is now
source-aware — it branches on the per-consumption `recipe_grocy_id`, not just the
product flag. This reverses the earlier "excluded everywhere" rule.

### Bundle recipe (`is_bundle`)
A **bundle recipe** is a recipe that is not a real cooked dish but just a grouping
of products eaten together as one meal-plan element (e.g. "Вечеря №5"). The user
marks such a recipe as a bundle so that its products are treated **as if eaten
standalone** for the fresh-sugar rule.

- **Naming:** code field `is_bundle` on **`Recipe`** (matches the `is_fresh` /
  `is_active` convention); UI label **"Збірка продуктів"** with tooltip: "це не
  страва, а просто набір продуктів — свіжі продукти всередині не враховують цукри".
- **Local-only, permanently — never synced to Grocy.** Like `is_fresh`, this is
  the app's own domain concept with no Grocy equivalent. Lives only in the local
  `recipes` table; sync must never reset it.
- **Effect — the exclusion rule extends by one clause.** Fresh-sugar exclusion
  becomes: `product.is_fresh AND (recipe_grocy_id IS NULL OR
  COALESCE(originating_recipe_grocy_id, recipe_grocy_id).is_bundle)`.
  A bundle makes its products behave exactly like standalone eating: fresh ones
  excluded, non-fresh ones (sugar, honey) still count. Only fresh products are
  ever excluded.
- **Sub-recipes ARE handled — nested bundles work (user: "real and common").**
  The bundle test runs against each consumed product's **originating** sub-recipe,
  not just the top-level meal-plan recipe. So a bundle grouping nested inside a
  real consumed dish still excludes its fresh products.
  - New column `ConsumedProduct.originating_recipe_grocy_id` (REAL grocy id of the
    immediate sub-recipe a product came from; NULL for standalone / old rows).
    Daily join uses `COALESCE(originating_recipe_grocy_id, recipe_grocy_id)` so old
    rows fall back to top-level (no backfill job). Chosen over a frozen
    `sugar_excluded` flag to **preserve retroactivity** — toggling `is_bundle`
    re-classifies past days live.
  - **Attribution source:** Grocy's `recipes_pos_resolved` (queried for the consumed
    shadow recipe) carries `is_nested_recipe_pos` (0/1) and `child_recipe_id` — the
    **REAL** (positive) sub-recipe id, NOT a shadow id. So
    `originating_recipe_grocy_id = child_recipe_id if is_nested_recipe_pos else
    meal["recipe_id"]`. No shadow→real mapping or `recipes_nestings` walk needed.
  - **Consume save-loop rewrite:** today one `ConsumedProduct` per `stock_log` leaf.
    Now: iterate `recipes_pos_resolved` (attribution + per-position planned amount),
    one row per position with its `originating_recipe_grocy_id`; **scale amounts to
    match `stock_log` totals** per effective product (stock_log is authoritative for
    what Grocy actually deducted — substitutions/rounding; resolved amounts are
    planned). A leaf split across a bundle and a non-bundle origin yields **two rows**
    with proportionally split quantity/cost.
- **Toggle endpoint:** dedicated `PATCH /recipes/{id}/bundle`, body
  `{is_bundle: bool}`, `household_id` query param — mirrors `PATCH /products/{id}/fresh`
  (verifies active household membership; scopes UPDATE `WHERE id AND household_id`).
- **Retroactive by design**, same as `is_fresh`: totals are computed live at read
  time, so marking a recipe a bundle re-classifies past days' fresh sugars too
  (for nested attribution, only for rows that already have
  `originating_recipe_grocy_id`; old rows fall back to top-level).
- **Fresh-sugars figure:** bundle-excluded sugars roll into the **same**
  `total_fresh_sugars` figure / green chart band as standalone-fresh. The excluded
  set and the "shown as fresh" set stay identical — no separate bundle band.
- **Day-detail item:** `ConsumedProductDetailItem` gains **both** `is_bundle` (the
  reason) and `sugar_excluded` (the backend-computed verdict), so the frontend can
  show the verdict and a precise hint (standalone-fresh vs bundle-fresh vs
  fresh-but-real-recipe).
- **RecipeData inconsistency accepted**, same deferral as `is_fresh`: a bundle's own
  stored `RecipeData` sugar figure is NOT recomputed; only the daily
  consumed-products aggregation honors `is_bundle`.
- **Sync preserves it:** `sync_all_recipes_from_grocy` only updates `name` on
  existing recipes (like `upsert_product`), so `is_bundle` survives sync untouched.

**Known/accepted inconsistency:** A recipe's own stored sugar figure
(`RecipeData.carbohydrates_of_sugars`, computed at consumption time) does NOT
retroactively change when an ingredient is later marked fresh. So a recipe's own
view may show e.g. 30g sugar while it contributes less to the daily sugar total.
This is accepted: only the daily consumed-products aggregation honors `is_fresh`.

**Retroactive by design:** Marking a product fresh applies to ALL days it was ever
consumed, including past days — because daily sugar totals are computed live at read
time, not stored. Ticking "banana" today lowers yesterday's tracked sugar total and
raises its fresh-sugars figure on next view. This is the intended, no-extra-work
behavior (flag is identity-level on `Product`). Migration: `is_fresh BOOLEAN NOT NULL
DEFAULT FALSE`, so on deploy every product is non-fresh and no totals change until the
user manually ticks products.

### RecipeData servings convention (per-serving invariant)
A `RecipeData` row records one recipe consumption. Its **nutrient fields
(`calories`, `proteins`, …), `weight_per_serving`, and `price_per_serving` are
stored PER ONE SERVING**; `servings` records how many servings were consumed.
Every reader multiplies by servings to get the meal total:
- `compute_daily_totals` (meal-plan day total) — `per_serving * recipe_servings`.
- Frontend `MealPlanLineRow` — `latest_calories * amount(servings)` (same rule;
  guarded by the test "computes recipe nutrition by simple servings multiplication").
- `get_recipe_detail` history — shows `servings` + per-serving figures as-is.

**Mixed convention (intentional):** the child `RecipeConsumedProduct.quantity`
and `cost` are stored as **batch totals** (full consumed amount across all
servings), NOT per-serving — `get_recipe_consumed_products` shows the whole batch
(`pd.calories * quantity`). So within one consumption: parent `RecipeData` =
per-serving, child ingredient rows = total. Both write paths must honour this.

**Two write paths, must agree:**
- `save_recipe_consumption_data` (manual consume — `RecipeNutrientsView` /
  `consume_recipe` service): already correct — stores `per_serving_nutrients`,
  `servings=N`, `weight_per_serving = total/servings`.
- `_save_recipe_data` (meal-plan `execute_consumption`): **was the bug.** It
  hardcoded `servings=1` and stored the accumulated total (the shadow recipe's
  stock_log is already scaled to the meal's `recipe_servings`, so the total is for
  ALL servings). For 1-serving meals this coincides with per-serving; for a
  multi-serving meal it stored an N× per-serving figure mislabelled `servings=1`,
  so daily totals under-counted (read side had nothing to multiply) and the recipe
  detail misreported. Fix: divide accumulated nutrients (and the
  summed-weight fallback) by the meal's `recipe_servings`, and store
  `servings = recipe_servings`. The linked-product `weight_per_serving` (portion→g
  factor) is ALREADY per-serving and must NOT be divided.
- **Divisor:** `float(meal["recipe_servings"])` (Grocy returns it as a string).
  Missing/≤0 falls back to `servings = 1` (never divide by zero).
- **`price_per_serving` also needs ÷servings.** Verified against Grocy: a recipe's
  `fulfillment.calories` is PER-SERVING (constant across `desired_servings`), but
  `fulfillment.costs` scales linearly with `desired_servings` — i.e. it is the TOTAL
  cost for all servings. The shadow recipe is consumed at `desired_servings =
  recipe_servings`, so `fulfillment["costs"]` is an N-serving total. Storing it
  raw as `price_per_serving` (the old code) was wrong for N>1; divide by `servings`.
- **Why hidden so long:** multi-serving meal-plan consumption of a recipe was rare;
  the user historically consumed these at exactly 1 serving.
- **Shared persist core:** both paths now build the row via
  `_build_recipe_data_row(db, recipe, *, servings, price_per_serving,
  weight_per_serving, nutrients: RecipeNutrients, ...)` in `services/recipe.py`. It
  takes FINISHED per-serving figures, builds the `RecipeData` row + the batch-total
  `RecipeConsumedProduct` children, flushes, and returns WITHOUT committing — the
  caller owns the transaction (meal-plan orchestrator must stay atomic per ADR-0001;
  manual path commits itself). The per-serving division and the weight-fallback
  rounding stay caller-side (meal-plan ÷recipe_servings, round 4; manual round 2),
  so neither path's numeric behaviour changed in the dedup.

### Fresh sugars (UI-only figure)
A separate, display-only number: the sum of sugars contributed by **standalone**
fresh products (`is_fresh AND recipe_grocy_id IS NULL`), shown so the user can still
see how much natural sugar they ate without it counting against the limit. Sugars
from fresh products consumed inside a recipe are **not** counted here — they sit in
the normal tracked total instead. Not persisted; derived at read time alongside the
tracked total. The stacked "sugars" chart's fresh band equals this figure per day.

**Shape of the figure:**
- A **day-level total** `total_fresh_sugars` is added to both read paths'
  day-level response (`_build_daily_stats` and `get_consumed_day_detail`).
- After this change, `total_carbohydrates_of_sugars` represents **non-fresh
  sugars** (the amount that counts against the sugar limit), and
  `total_fresh_sugars` is the excluded amount. Their sum equals the pre-change
  total.
- In the single-day detail endpoint, each product item carries its `is_fresh`
  flag **and `recipe_grocy_id`** (already present), so the frontend can tell
  which rows are actually excluded (fresh + standalone) vs fresh-but-from-recipe
  (shown with a "counts toward total" hint, since toggling fresh won't exclude
  that row). Each item also carries **`product_id`** (the `Product.id`) — distinct
  from `id` (the `ConsumedProduct` row id, used as the list key). The fresh-toggle
  PATCH must target `product_id`; sending the consumed-row `id` was the bug that
  made the "Свіжий" checkbox silently fail to persist.
- Applied to **both** read paths (list and detail) for consistency: a day must
  show the same non-fresh sugar total in the multi-day table and when expanded.
  `_build_daily_stats` gains a `Product` join (one line) to reach `is_fresh`;
  `get_consumed_day_detail` already joins `Product`.

### Meal-plan units cache (Grocy-sourced, sync-invalidated)
The unit dropdown shown when adding a meal-plan **product** line — and the
`stock_to_grams_ml` factor used to convert a planned amount into nutrients —
comes from `get_or_load_units_for_product`, which reads Grocy's
`quantity_unit_conversions_resolved` and **caches the result in Redis for 24h**
(key `meal_plan:units:v2:household:{hh}:product:{pid}`).

- **The cache is Grocy-sourced, not DB-sourced.** Its contents reflect the unit
  conversions configured *in Grocy*, not anything in our local tables. A rebuild
  is therefore always correct regardless of local transaction state.
- **It must be invalidated whenever a product is synced.** Adding a unit
  conversion in Grocy (e.g. "банка ↔ мілілітри") does not change our DB, so a
  product sync would otherwise leave a stale cache: the new unit never appears in
  the dropdown, and — worse — a product that had *no* gram/ml conversion at first
  cache time stays cached with `stock_to_grams_ml: None`, so
  `compute_daily_totals` silently drops it as a "missing item" until the 24h TTL
  expires. This was the observed bug: "after re-sync, мілілітри still not
  selectable; the system doesn't see the conversion."
- **Invalidation point:** `upsert_product`, on the **existing-product branch
  only** (a brand-new product has no cache entry yet). This is the single
  chokepoint all sync paths funnel through (nightly bulk `sync_grocy_products`,
  per-product `sync_single_grocy_product[_detailed]`, meal-plan lazy sync), so one
  eviction there covers every path.
- **Shared helper:** the key builder and `invalidate_units_cache(household_id,
  product_grocy_id)` live in a neutral module (`core/meal_plan_cache.py`) imported
  by both `services/meal_plan.py` and `services/product.py`, to avoid a circular
  import (`meal_plan` already lazy-imports `sync_single_grocy_product` from
  `product`).
- **Warming (re-population after invalidation).** Invalidation deletes the key; it
  does **not** rebuild it. The cache only repopulates when something calls
  `get_or_load_units_for_product` with a real `grocy_api`. The web app warms it
  naturally (any product/meal-plan view runs with a request-scoped `grocy_api`).
  The **MCP path historically passed `grocy_api=None`**, so a cold cache there
  yielded `needs_units` — the failure mode observed when a user clicked "Sync from
  Grocy" (which invalidates) and then immediately tried to meal-plan the same
  product via MCP (the cache was deleted and nothing on the MCP path repopulated
  it). See [[#MCP self-warms the units cache on a cold miss]].
- **MCP self-warms the units cache on a cold miss.**
  `_add_product_to_meal_plan_core` (`app/mcp/server.py`) first reads with
  `grocy_api=None` (the warm-cache hot path stays free of any key decrypt). Only
  if `units` comes back empty does it build a **read-only** `grocy_api`
  (`build_grocy_api(db, household_id, user.id)` — same decrypt path as the 04:00
  sync) and retry `get_or_load_units_for_product` with it, populating the cache and
  proceeding. A `GrocyConfigError` (no key / decrypt fail) falls back to the
  `needs_units` response. This is a **read-only** Grocy call, explicitly sanctioned
  by ADR-0004 (only *writes* are gated); recorded as the 2026-06-24 amendment to
  that ADR. Recipe meal-plan adds have no units dependency and are unaffected.

### Grocy API key encryption (compartment isolation, NOT at-rest)
Each user's Grocy API key is stored encrypted in `HouseholdUser.grocy_api_key`
(Themis SCellSeal, keyed by the user's bcrypt `hashed_password`). **Do not read
this as protection against a DB dump or a server admin.** The encryption key
(`hashed_password`) lives in the same database, and the decrypt path runs in
unattended background Celery tasks (04:00 sync, `execute_consumption`) with no
user session — which only works *because* the key sits next to the ciphertext in
the DB.

- **What it actually defends:** a partial leak of *only* the `householduser` table
  without the `user` table — i.e. compartment isolation. Nothing more.
- **What it does NOT defend:** a full DB dump (has both ciphertext and key); a
  root/server admin (any process-accessible key — master key or hybrid — is
  decryptable by whoever controls the process). The only design that withholds
  plaintext from a server admin needs a user-derived key never stored server-side,
  which is mutually exclusive with unattended background sync.
- **Real protection** is operational: DB network isolation, restricted DB/backup
  access, server access control.
- **Planned future change:** migrate to an app-level master key
  (`APP_ENCRYPTION_KEY` in env, never in the DB) as defense-in-depth against a
  DB-only dump. Honestly raises the bar from "DB dump = all keys" to "DB dump
  without env is useless", without breaking background sync. Full reasoning and the
  rejected alternatives (hybrid `H(master ‖ hash)`, KMS, user-derived key) are in
  **`docs/adr/0002-grocy-api-key-encryption-is-compartment-isolation.md`**.

### User API key
A long-lived token (`gnk_<prefix>_<secret>`) a user creates to let a non-browser
client — currently the MCP server, driven from Claude Code — authenticate **as that
user**. Distinct from the **Grocy API key** (that one talks to Grocy; this one talks
to *our* API).

- Carried as `Authorization: Bearer <key>` (the browser keeps using cookies).
- Stored as `key_prefix` (plaintext, indexed for lookup) + `key_hash` =
  `sha256(secret)` in `user_api_keys`. The plaintext is shown **once** at creation,
  never again. SHA-256 (not bcrypt) suffices — the secret is high-entropy random.
- **It authenticates the user but cannot decrypt their Grocy key** (Themis is keyed
  by the password hash, which this path never has). This is why MCP v1 is read-only:
  `search_product` reads the local `products` table and never calls Grocy. A write
  tool would first have to solve the ADR-0002 key-custody problem.
- Managed at `/api/users/me/api-keys` (create/list/revoke) and on the Profile page.
  Rationale + the household-vs-key scoping decision: **`docs/adr/0004-user-api-keys-for-mcp.md`**.

### Fuzzy product search
Typo-tolerant search over product names for the MCP `search_product` tool, ranked by
relevance. Uses PostgreSQL **pg_trgm** (`similarity()` + the `%` trigram-match
operator, backed by a GIN trigram index on `products.name`). Falls back to substring
`ILIKE` on non-Postgres dialects — the SQLite test DB cannot run pg_trgm, so the
trigram path has no automated coverage and is verified manually. Distinct from the
existing substring-only search on `GET /api/products?search=`, which is unchanged.

### Add meal-plan entry vs. Log consumption (NOT the same)
Two distinct operations that are easy to confuse (the phrase "пишу що спожив" once
conflated them):

- **Add meal-plan entry** — create a *planned* meal row for a day. Writes a local
  `MealPlan` row (`status="pending"`) and POSTs to Grocy's `/objects/meal_plan` via
  the existing `create_lines` + `submit_batch` pipeline (Grocy POST runs in the
  `create_meal_plan_batch` Celery task). **No stock change, no nutrient aggregation.**
  This is what the MCP write tools (`add_product_to_meal_plan`,
  `add_recipe_to_meal_plan`) and the `/plan-meal` skill do.
- **Log consumption** — actually *eat* the plan: decrement Grocy stock and write
  `ConsumedProduct` rows (the `execute_consumption` path). This is a separate flow the
  user runs by hand; the MCP server does **not** expose it.

Product entries need a unit: the MCP tool resolves `product_qu_id` + `product_amount_stock`
from the [Meal-plan units cache](#meal-plan-units-cache-grocy-sourced-sync-invalidated)
(Redis only on the MCP path — a cold cache yields `needs_units`, prompting the user to
open the product once in the app). Recipe entries need only `recipe_servings`.
