# Recipe Nutrients

How recipes are tracked, consumed, and reported on in Grocy Nutrients — both as a user-facing flow and a technical reference.

## What this module does

Grocy itself tracks recipes and stock, but doesn't compute per-serving nutrient breakdowns or keep a history of *how much* of each product was actually consumed each time you cooked something. This module fills that gap:

- For any recipe, calculate aggregate and per-serving nutrients from its ingredients (recursively, including nested sub-recipes).
- Trigger a real Grocy "consume recipe" action — Grocy deducts stock; we read the resulting stock log to capture what was actually used.
- Persist a per-preparation history locally with servings, weight, price, nutrients, and the exact products + quantities + costs that went into that preparation.
- Surface that history in the UI: rolling stats (avg calories/serving, avg price/serving, total preparations, last prepared) plus a drill-down per preparation.

The catch: Grocy's API only gives recipe ingredients in their stock units (kg, pcs, l, etc.). To turn that into nutrients we need everything in **grams or millilitres**, since `ProductData` stores nutrients per gram. The bulk of the calculation logic is unit conversion plumbing on top of Grocy's `recipes_pos_resolved` and `quantity_unit_conversions` endpoints.

## User flow

The main entry point is the **Recipes** page (`/recipes`):

1. **Browse / search** — paginated list of recipes synced from Grocy, sortable by creation date or last-consumed date. Each row shows the latest preparation's stats (servings, calories, weight, price) so you can see at a glance which recipes you cook regularly.
2. **Open a recipe** (`/recipes/:id`) — header with rolling stats; the **Calculate & Consume** button runs the nutrient calculation against current stock. If everything is in stock, the user confirms servings/portions and the recipe is consumed in Grocy. If something is missing, the UI offers to create a Grocy shopping list with the missing items.
3. **Inspect history** — every past preparation is listed with full nutrient breakdown and a per-ingredient cost/nutrient row, lazy-loaded when expanded.

There's also a standalone **Recipe Nutrients** tool (`/recipe-nutrients`) — a step-by-step diagnostic UI that lets you punch in any recipe ID and see the calculation result without committing to a consume action. Useful when debugging recipe data in Grocy (missing nutrients, wrong stock units, broken conversions).

## Architecture overview

```
┌──────────────────┐    HTTP     ┌─────────────────────┐
│ RecipesView      │ ──────────▶ │ /api/recipes/*      │
│ RecipeDetailView │             │ (FastAPI routes)    │
│ RecipeNutrients  │             └──────────┬──────────┘
└──────────────────┘                        │
                                            ▼
                              ┌─────────────────────────┐
                              │ services/recipe.py      │
                              │  • calculate_nutrients  │
                              │  • consume_recipe       │
                              │  • sync / save / detail │
                              └────┬───────────────┬────┘
                                   │               │
                          Grocy HTTP API     Local Postgres
                       (recipes,           (Recipe,
                        stock_log,          RecipeData,
                        conversions)        RecipeConsumedProduct,
                                            ProductData)
```

Three layers, separated cleanly:

- **`api/endpoints/recipes.py`** — thin HTTP layer. Wraps service calls, raises `HTTPException` on `RecipeCalculationError`, enforces `household_id` scoping via `get_grocy_api`.
- **`services/recipe.py`** — all business logic: nutrient aggregation, unit conversion, Grocy consume + stock-log reconciliation, local DB persistence.
- **`models/recipe.py`** — SQLModel tables `Recipe`, `RecipeData`, `RecipeConsumedProduct`.

## Data model

### `Recipe`
Lightweight local mirror of a Grocy recipe — only `grocy_id` + `name`, scoped per household via `(grocy_id, household_id)` unique constraint. Created on first sync; updated by re-sync.

### `RecipeData`
One row per preparation. Stores **per-serving** nutrients (kcal, proteins, carbs, sugars, fats, sat. fat, salt, fibers), `servings`, `price_per_serving`, `weight_per_serving`, `user_id`, `consumed_at`, and an optional `consumed_date` for back-dated entries from meal plans. `consumed_at` defaults to `now()`; nutrient fields are nullable so partial data can still be saved.

### `RecipeConsumedProduct`
The "what actually went in" detail: links each `RecipeData` to one or more `ProductData` snapshots with the consumed `quantity` (in grams/ml) and `cost`. Populated by reading Grocy's `stock_log` immediately after a consume call.

## Nutrient calculation algorithm

`calculate_recipe_nutrients(recipe_id)` returns a `RecipeCalculateResponse` containing total nutrients, per-serving nutrients (if the recipe has a linked product with `desired_servings`), the ingredient list, fulfillment status, and a list of products with missing nutrient data.

The flow:

1. **Fetch the recipe** from Grocy (`/objects/recipes`).
2. **Recurse into nested recipes** — `/objects/recipes_nestings` lists sub-recipes; each is processed before the main recipe so all ingredient lists feed into the same accumulator.
3. **For each ingredient** (`/objects/recipes_pos_resolved`):
   - Resolve the *effective* product (Grocy's pluggable product substitution).
   - Get `qu_id_stock` for both base and effective products from local DB (fallback: Grocy API).
   - **Step A:** if base and effective stock units differ, get the conversion factor between them.
   - **Step B:** convert the resulting amount to grams or millilitres using `get_conversion_factor_safe()` against `(GRAM_UNIT_ID=82, ML_UNIT_ID=85)`.
   - Multiply each nutrient (stored per-gram in `ProductData`) by the gram quantity and add to the total.
4. **Per-serving nutrients** — if the recipe has `product_id` and `desired_servings`, divide totals by `desired_servings`.
5. **Weight per serving** — if the linked product's stock unit isn't already grams/ml, look up its conversion factor to grams/ml; that factor *is* the weight of one stock unit (one serving).
6. **Missing-data tracking** — for any nutrient field that's `0` or missing on a non-portion product, append the product to `MissingNutrients[field]`. Portion-unit products (`PORTION_UNIT_ID=103`) are skipped — they typically don't carry their own nutrient data because they inherit from a recipe.

### Why local DB first, Grocy API second

`_process_recipe` reads `qu_id_stock` and product names from the local `Product` table before falling back to Grocy. This keeps recipe calculations fast even with dozens of ingredients — the daily Celery sync (04:00) ensures the local copy is fresh.

### Unit IDs are hard-coded

`GRAM_UNIT_ID=82`, `ML_UNIT_ID=85`, `PORTION_UNIT_ID=103` are the canonical IDs from a stock Grocy installation. If you've recreated quantity units from scratch, these IDs may differ — adjust the constants at the top of `services/recipe.py`.

## Consumption flow

`consume_recipe()` does six things in order:

1. **Pre-flight check** — if `fulfillment.missing_products_count > 0`, return early without consuming.
2. **Snapshot `max(stock_log.id)`** — used to filter out pre-existing log entries when reading back.
3. **POST `/recipes/{id}/consume`** — Grocy deducts stock and writes new `stock_log` entries.
4. **Reconcile from `stock_log`** — query `stock_log` for entries with `recipe_id={id}` and `transaction_type=consume`, filter by `id > max_log_id`, compute gram-equivalent quantities and per-line cost. Build `consumed_products_data` from this.
5. **Update the linked Grocy product's nutrients** — if the recipe has a linked product and the user provided `per_serving_nutrients`, push fresh per-100-units-of-stock values back into Grocy via `update_grocy_product_nutrients`. This keeps the Grocy product card in sync with the recipe's actual nutrient profile.
6. **Save locally** — `save_recipe_consumption_data()` writes a `RecipeData` row plus one `RecipeConsumedProduct` per stock-log entry. If `weight_per_serving` wasn't supplied, it's derived from the sum of consumed quantities divided by servings.

Steps 4–6 are all best-effort — failures are logged but don't fail the overall consume, since the stock deduction in Grocy has already happened.

## Endpoints

All endpoints live under `/api/recipes` and require auth + an `household_id` query param. Auth + Grocy client decryption are handled by the `get_grocy_api` dependency.

| Method | Path                          | Purpose                                                                          |
|--------|-------------------------------|----------------------------------------------------------------------------------|
| POST   | `/calculate`                  | Calculate nutrients for a recipe without consuming.                              |
| POST   | `/consume`                    | Consume the recipe in Grocy, reconcile stock log, persist local history.         |
| POST   | `/update-conversion`          | Add/update a Grocy unit conversion (used when calculation hits a missing factor). |
| GET    | `/grocy-list`                 | Lightweight `[{id, name}]` list of all recipes from Grocy.                       |
| GET    | `/list`                       | Paginated local list with latest-consumption stats. Supports `search`, `sort_by`. |
| GET    | `/{recipe_id}`                | Recipe detail with full consumption history (per-user).                          |
| POST   | `/sync/{recipe_id}`           | Sync one recipe from Grocy → local DB (idempotent).                              |
| POST   | `/sync-all`                   | Sync every recipe from Grocy → local DB.                                         |
| POST   | `/save-data`                  | Save consumption data without going through Grocy consume (e.g. backfill).       |
| GET    | `/data/{recipe_data_id}/products` | Lazy-load the ingredient breakdown for a single past preparation.            |
| POST   | `/create-shopping-list`       | Create a Grocy shopping list with missing products for a recipe.                 |

## Service functions

| Function                          | What it does                                                                  |
|-----------------------------------|-------------------------------------------------------------------------------|
| `calculate_recipe_nutrients`      | Main entry: aggregates nutrients + fulfillment + missing-data report.         |
| `_process_recipe`                 | Internal: walks one recipe's ingredients, handles unit conversion.            |
| `_increase_nutrients_from_product`| Internal: adds one product's contribution to the running totals.              |
| `consume_recipe`                  | Consumes in Grocy, reads stock log, persists locally.                         |
| `get_recipe_by_grocy_id`          | Lookup local `Recipe` by `grocy_id` (household-scoped).                       |
| `get_latest_recipe_data`          | Most recent `RecipeData` row for a recipe.                                    |
| `get_recipes_with_pagination`     | Paginated list with search + sort, joined with latest preparation stats.      |
| `sync_recipe_from_grocy`          | Upsert one recipe locally.                                                    |
| `sync_all_recipes_from_grocy`     | Upsert all recipes locally; returns `{processed, synced, errors}`.            |
| `save_recipe_consumption_data`    | Persist a preparation + its consumed products.                                |
| `get_recipe_detail`               | Recipe + per-user consumption history.                                        |
| `get_recipe_consumed_products`    | Per-product breakdown for one past preparation (lazy-loaded by UI).           |

## Frontend

| View                  | Route                  | Role                                                                        |
|-----------------------|------------------------|-----------------------------------------------------------------------------|
| `RecipesView`         | `/recipes`             | Paginated/searchable list, sortable by creation or last-consumed date.      |
| `RecipeDetailView`    | `/recipes/:id`         | Stats header, calculate-and-consume action, expandable history rows.        |
| `RecipeNutrientsView` | `/recipe-nutrients`    | Standalone diagnostic — enter a Grocy recipe ID and inspect the calculation.|

State is managed by Pinia stores `store/recipes.ts` and `store/recipeDetail.ts`. All requests use household-scoped axios calls (`/api/recipes/...?household_id=...`).

## Edge cases worth knowing about

- **Recipe without a linked product** — calculation works, but per-serving nutrients can't be derived (no `desired_servings`). Consumption is still possible if all ingredients are in stock; we just can't push back nutrients to a linked product.
- **Portion-unit ingredients** — we don't flag missing nutrients for them; they typically inherit from a sub-recipe.
- **Mixed base/effective stock units** — handled by Step A in the calculation (separate conversion before grams/ml).
- **Stock log race** — if someone else triggers a consume between `max_log_id` snapshot and the recipe's own consume, those entries leak into our reconciliation. Mitigation: the `recipe_id={id}` filter on `stock_log` makes a cross-recipe collision unlikely.
- **`update-conversion` UX** — when the calculator hits a missing factor (e.g. a product priced in pieces with no conversion to grams), the UI surfaces a form letting the user fix the conversion in Grocy without leaving the page.
