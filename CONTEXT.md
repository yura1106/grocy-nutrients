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
