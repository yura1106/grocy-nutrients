# Daily Nutrition Limits — Design Spec

**Date:** 2026-03-27
**Status:** Approved
**Approach:** Backend-heavy calculation (Approach 1)

---

## Problem Statement

`UserHealthProfile` stores static daily nutrient limits — one global set per user, never tied to a specific day. There is no way to record that on Monday the user burned 2 800 kcal (from Garmin) and weighed 84 kg, and to get auto-calculated per-day nutrient targets from those inputs. Additionally, all comparison charts on existing pages always use the same static profile norms, regardless of actual daily variance in activity and body weight.

---

## Goals

1. Allow users to save per-day nutrient limits derived from TDEE (Garmin), body weight, and activity level.
2. Auto-calculate all 8 nutrients using evidence-based formulas on the backend.
3. Provide a "Fill from profile" shortcut that copies existing profile limits directly.
4. Update all comparison pages (ConsumedProductsStats, Recipes, Products) to resolve norms as: today's daily limit → fallback to profile.

---

## Data Model

### New table: `daily_nutrition_limits`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `user_id` | INTEGER FK→users | NOT NULL, INDEX |
| `date` | DATE | NOT NULL, UNIQUE(user_id, date) |
| `calories_burned` | FLOAT | TDEE from Garmin, nullable |
| `body_weight` | FLOAT | kg, nullable |
| `activity_level` | VARCHAR | same enum as UserHealthProfile, nullable |
| `calories` | FLOAT | calculated/editable limit |
| `proteins` | FLOAT | |
| `carbohydrates` | FLOAT | |
| `carbohydrates_of_sugars` | FLOAT | |
| `fats` | FLOAT | |
| `fats_saturated` | FLOAT | |
| `salt` | FLOAT | |
| `fibers` | FLOAT | |
| `created_at` | TIMESTAMPTZ | server_default=now() |
| `updated_at` | TIMESTAMPTZ | onupdate=now() |

No `household_id` — personal health data, same pattern as `user_health_profiles`.

### Updated table: `user_health_profiles`

New column:
```
calorie_deficit_percent  FLOAT NULL
```

Used as:
- `goal=lose`:     `calories = TDEE × (1 − deficit_percent/100)`
- `goal=gain`:     `calories = TDEE × (1 + deficit_percent/100)`
- `goal=maintain`: `calories = TDEE`

Default when NULL: 15%.

### Alembic migrations (2)
1. `add_daily_nutrition_limits_table`
2. `add_calorie_deficit_percent_to_user_health_profiles`

---

## Nutrient Calculation Logic

Module: `app/core/nutrient_calculator.py` — pure functions, no DB dependencies.

### Input parameters
- `calories_burned: float` — TDEE from Garmin
- `body_weight: float` — kg
- `activity_level: ActivityLevelEnum`
- `goal: GoalEnum` — from user profile
- `calorie_deficit_percent: float` — from user profile (default 15.0)

### Formulas

#### 1. Calories (kcal)
```
calories = calories_burned × adjustment_factor

adjustment_factor:
  lose:     1 − deficit_percent / 100
  gain:     1 + deficit_percent / 100
  maintain: 1.0
```
**Science:** ISSN (2014), Hall et al. (2012) — 10–20% caloric deficit from TDEE is the optimal range for fat loss while preserving lean mass. Default 15% chosen as conservative midpoint.

#### 2. Proteins (g) — body weight × activity factor
```
proteins = body_weight × protein_factor × goal_multiplier

protein_factor by activity_level:
  sedentary:          0.9 g/kg
  lightly_active:     1.4 g/kg
  moderately_active:  1.6 g/kg
  very_active:        2.0 g/kg
  extra_active:       2.2 g/kg

goal_multiplier:
  lose:     1.15  (extra protein preserves muscle in deficit)
  gain:     1.10  (supports muscle protein synthesis)
  maintain: 1.0
```
**Science:** ISSN Position Stand (Stokes et al., 2018): 1.4–2.0 g/kg for active individuals. During caloric restriction, requirements rise to 2.3–3.1 g/kg LBM (Helms et al., 2014). Sedentary base of 0.9 g/kg slightly above WHO RDA (0.8) for a conservative buffer.

#### 3. Fats (g) — % of calories
```
fats = (calories × 0.25) / 9
```
**Science:** AMDR (IOM/DRI, 2005): 20–35% of energy from fat. 25% chosen as conservative midpoint — sufficient for absorption of fat-soluble vitamins (A, D, E, K) and hormonal synthesis.

#### 4. Saturated fat (g) — upper limit, `lessIsBetter`
```
sat_fat = (calories × 0.10) / 9
```
**Science:** WHO (2018) and AHA (2021): saturated fat < 10% of total daily energy to reduce cardiovascular disease risk.

#### 5. Carbohydrates (g) — remainder
```
carbohydrates = (calories − proteins×4 − fats×9) / 4
```
If the result is negative (edge case: very high protein for a low calorie budget), clamp to 0. The service validates this and raises a descriptive error prompting the user to adjust inputs.

**Science:** AMDR for carbohydrates: 45–65% of energy. The remainder formula naturally lands in this range for typical protein/fat factors and automatically adapts to any calorie level without hardcoding a percentage.

#### 6. Sugars (g) — % of calories, `lessIsBetter`
```
sugars = (calories × 0.10) / 4
```
**Science:** WHO Guideline on Sugars (2015): free sugars < 10% of total energy (strong recommendation); < 5% conditional recommendation. 10% used as the daily limit.

#### 7. Salt (g) — activity-scaled, `lessIsBetter`
```
sedentary / lightly_active:    5.0 g
moderately_active:             5.5 g
very_active:                   6.0 g
extra_active:                  7.0 g
```
**Science:** WHO (2012): < 5 g/day for general population. Athletes lose 0.5–2.0 g sodium/hour in sweat (Maughan & Shirreffs, 2010), justifying higher limits at greater activity levels.

#### 8. Fiber (g) — per 1 000 kcal
```
fibers = (calories / 1000) × 14
```
**Science:** USDA Dietary Guidelines 2020–2025 and AHA: 14 g fiber per 1 000 kcal consumed. At 2 000 kcal → 28 g, consistent with EFSA adequate intake (25 g/day for adults).

---

## Backend API

### New files
```
app/core/nutrient_calculator.py
app/models/nutrition_limit.py
app/schemas/nutrition_limit.py
app/services/nutrition_limits.py
app/api/endpoints/nutrition_limits.py
```

### Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/nutrition-limits/preview` | Calculate limits without saving. Reads `goal` and `calorie_deficit_percent` from user's profile. Returns `NutrientLimitsPreview`. |
| `GET` | `/api/nutrition-limits` | Paginated list for current user, sorted by date desc. Query: `skip`, `limit`. |
| `GET` | `/api/nutrition-limits/today` | Today's record or null. Accepts optional `?date=YYYY-MM-DD` query param so the client can pass its local date (avoids server/client timezone mismatch). |
| `POST` | `/api/nutrition-limits` | Create new daily limit record. Body includes input fields + nutrient limits (already calculated by preview). |
| `PUT` | `/api/nutrition-limits/{id}` | Update any field of existing record. Verifies `record.user_id == current_user.id`. |
| `DELETE` | `/api/nutrition-limits/{id}` | Delete record. Verifies ownership. Returns 204. |

All endpoints: `Depends(get_current_user)`, no `household_id` required.

### Updated schemas (users)
`HealthParametersUpdate` and `HealthParametersRead` gain `calorie_deficit_percent: float | None`.

---

## Frontend Architecture

### New Pinia store: `store/nutritionLimits.ts`

**State:**
```typescript
todayLimit:     NutritionLimit | null
preview:        NutrientLimitsPreview | null
list:           NutritionLimit[]
total:          number
loading:        boolean
previewLoading: boolean
error:          string
```

**Actions:**
- `fetchTodayLimit()` — GET /nutrition-limits/today
- `fetchList(skip, limit)` — GET /nutrition-limits
- `previewLimits(params)` — POST /nutrition-limits/preview
- `createLimit(data)` — POST /nutrition-limits
- `updateLimit(id, data)` — PUT /nutrition-limits/{id}
- `deleteLimit(id)` — DELETE /nutrition-limits/{id}

**Getter:**
- `getLimitByDate(date: string): NutritionLimit | undefined`

### New composable: `composables/useNorms.ts`

Single source of truth for norm resolution across all pages:

```typescript
export function useNorms(date?: MaybeRef<string | null>) {
  const limitsStore = useNutritionLimitsStore()
  const healthStore = useHealthStore()

  const norms = computed(() => {
    const d = unref(date)
    const limit = d
      ? limitsStore.getLimitByDate(d)
      : limitsStore.todayLimit
    return limit ?? healthStore.params
  })

  return { norms }
}
```

### New page: `views/DailyNutritionLimitsView.vue`

Layout-only view, delegates to:

```
components/nutrition-limits/
  NewLimitForm.vue     — form for today's new entry
                         inputs: calories_burned, body_weight, activity_level
                         "Generate" button  → calls previewLimits(), shows preview
                         "Fill from profile" → copies profile daily_* values directly
                         "Save" button → calls createLimit() with preview values
  DailyLimitsTable.vue — paginated table of saved records
                         columns: date, weight, activity, calories, proteins, carbs, fats, fiber, salt
                         row click → opens EditLimitModal
  EditLimitModal.vue   — edit any field of existing record
                         "Regenerate" button if input fields are changed
                         calls updateLimit()
```

Router: `/daily-nutrition-limits` → `DailyNutritionLimitsView` (`requiresAuth: true`)

### Updated existing components

**`NutrientTotalsBar.vue`:**
- Remove direct `useHealthStore()` dependency
- Accept `norms` as a required prop (object with `daily_*` fields)
- Becomes purely presentational

**`DayDetailContent.vue`:**
```typescript
const { norms } = useNorms(computed(() => props.date))
// pass norms.value to <NutrientTotalsBar :norms="norms" />
```

**`ConsumedProductsStatsView.vue`:**
```typescript
const { norms } = useNorms()  // today / profile for table row coloring
// replace healthStore.params?.daily_* with norms.value?.daily_*
```

**`RecipesView.vue`**, **`ProductDetailView.vue`:**
```typescript
const { norms } = useNorms()
```

**`ProfileView` / `HealthParameters.vue`:**
Add `calorie_deficit_percent` numeric input (range 0–50, label "% deficit/surplus from TDEE").

### New TypeScript types: `types/nutritionLimit.ts`

```typescript
interface NutritionLimit {
  id: number
  date: string
  calories_burned: number | null
  body_weight: number | null
  activity_level: string | null
  calories: number | null
  proteins: number | null
  carbohydrates: number | null
  carbohydrates_of_sugars: number | null
  fats: number | null
  fats_saturated: number | null
  salt: number | null
  fibers: number | null
}

interface NutrientLimitsPreview {
  calories: number
  proteins: number
  carbohydrates: number
  carbohydrates_of_sugars: number
  fats: number
  fats_saturated: number
  salt: number
  fibers: number
}
```

---

## Integration

### Startup data loading

In `App.vue` after login (or navigation guard), fetch in parallel:
```typescript
await Promise.all([
  healthStore.fetchHealthParams(),
  nutritionLimitsStore.fetchTodayLimit(),
])
```

### Norm resolution by page

| Page | Norm source |
|---|---|
| ConsumedProductsStats — table rows | `useNorms()` → today / profile |
| ConsumedProductsStats — detail panel | `useNorms(selectedDate)` → that day / profile |
| RecipesView, ProductDetailView | `useNorms()` → today / profile |
| DailyNutritionLimitsView | `nutritionLimitsStore` directly |

---

## Tests

### Backend: `tests/core/test_nutrient_calculator.py`
- Each formula independently
- Edge cases: `goal=maintain`, `deficit_percent=None`, `activity=extra_active` + `goal=lose`
- Verify carbs never goes negative (validation guard in service)

### Backend: `tests/api/test_nutrition_limits.py`
- `POST /preview`: correct calculation returned
- `POST /`: record created, `user_id` set from token
- `PUT /{id}`: fields updated; 403 for another user's record
- `GET /today`: returns today's record or null
- `DELETE /{id}`: 204 on success, 403 for another user's record

Uses existing `client` fixture from `conftest.py`.

### Frontend: `tests/store/nutritionLimits.test.ts`
- `fetchTodayLimit`: state updated correctly
- `previewLimits`: stores preview, does not add to `list`
- `createLimit`: appends to `list`, clears `preview`

### Frontend: `tests/composables/useNorms.test.ts`
- Returns `todayLimit` when present
- Falls back to `healthStore.params` when `todayLimit` is null
- Returns `getLimitByDate(date)` result when date is provided

Uses `vi.mock('axios')`, no MSW.

---

## What Does NOT Change

- `DailyNutrition` table and CSV import flow — untouched
- `NutrientGauge.vue` — already receives `value` and `max` as props
- All household endpoints — untouched
- Auth, JWT, encryption — untouched
