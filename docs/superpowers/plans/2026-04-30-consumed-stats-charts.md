# Consumed Stats — Range Picker, Summary, Charts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a top-of-page block to `/consumed-stats` with a date-range picker, range-aware nutrient averages (8 cards), a "Charts" modal with line/bar visualizations across the chosen range. The existing daily nutrients table, pagination, and right-panel detail flow must keep working unchanged.

**Architecture:** New composable `useRangeAverages` does all data work (parallel fetch of `/api/consumption/stats` + `/api/nutrition-limits`, gap-fill driven by backend, per-nutrient averaging, per-day effective limit via `normsFromSources` fallback to health profile). Range lives in URL query (`?from=YYYY-MM-DD&to=YYYY-MM-DD`) via `useDateRangeQuery`; missing/invalid → default last-7-days + writeback. New components live under `frontend/src/components/range-summary/`. Charts modal is lazy-loaded via `defineAsyncComponent` to keep Chart.js out of the main bundle. The dashboard `WeeklyAverageSummary` is rewired to call `useRangeAverages` directly with a fixed 7-day window, and the old `useWeeklyAverages` composable is deleted.

**Tech Stack:** Vue 3 + TypeScript, Pinia, Vue Router, Tailwind v4, axios, flatpickr (already installed for range picking on Dashboard), `lucide-vue-next` (already installed). New deps: `chart.js`, `vue-chartjs`, `chartjs-plugin-annotation`. Tests: Vitest + jsdom + `vi.mock('axios')`.

**Range constraint:** `/api/consumption/stats` clamps `date_to - date_from` to ≤365 days server-side (returns 422 otherwise). The picker enforces a hard 365-day max via `useDateRangeQuery.setRange` — invalid (over-365) ranges are rejected silently, no soft warning needed.

---

## File Structure

### New files

| File | Responsibility |
|---|---|
| `frontend/src/composables/useRangeAverages.ts` | Reactive composable: parallel fetch stats + limits, store raw `limitsByDate` map, build effective-limits map (with health-profile fallback), compute 8-nutrient averages, expose `days`, `effectiveLimitsByDate`, `averages`, `loading`, `firstLoading`, `error`, `includedDayCount`, `skippedDayCount`, `rangeDayCount`, `refresh`. Uses `AbortController` to cancel stale fetches. Re-derives effective limits + averages locally (no refetch) when `healthStore.params` changes. Also exports shared constants `NUTRIENT_KEYS`, `NUTRIENT_META`, `NUTRIENT_COLORS`, `STATS_FIELD`, `NORM_FIELD` (single source of truth — chart components import these instead of redefining). |
| `frontend/src/composables/useDateRangeQuery.ts` | URL-driven date range. Reads `route.query.from`/`route.query.to`, validates `YYYY-MM-DD`, defaults to today−6..today. Invalid → silent fallback + writeback to URL. Exposes `from`, `to`, `isDefault`, `setRange`, `clearRange`. Uses `router.replace` (not push) to avoid back-stack pollution. |
| `frontend/src/components/range-summary/DateRangePicker.vue` | Trigger button styled per Figma (calendar icon + label + clear `X`) that programmatically opens flatpickr in range mode. Emits `update:range` with `{ from, to }`. Localized short label `"22 кв – 28 кв"` (same year) or `"22 кв 2026 – 5 січ 2027"` (different years). |
| `frontend/src/components/range-summary/RangeAverageSummary.vue` | The new top-of-page block on `/consumed-stats`. Wires `useDateRangeQuery` + `useRangeAverages`. Renders title + range subtitle + skipped-days notice + legend, picker, "Графіки" button, 8-card grid, lazy-loaded ChartModal. (Range is clamped to ≤365 days inside `useDateRangeQuery`, so no soft warning is needed.) |
| `frontend/src/components/range-summary/ChartModal.vue` | Modal shell. Backdrop click + ✕ + Escape closes. `<Transition>` fade+scale. 9 tabs: Overview + 8 nutrients. Renders the appropriate chart child based on active tab. Props: `:open`, `:days`, `:effective-limits-by-date`, `:nutrient-meta`. |
| `frontend/src/components/range-summary/charts/OverviewChart.vue` | Chart.js `Line` with one dataset per nutrient. Y-axis `% of effective limit`. ReferenceLine at 100% (via Chart.js plugin or custom annotation drawn as second dataset). Days without consumption are excluded from x-axis; days without effective-limit for that nutrient produce a `null` value (Chart.js `spanGaps: false`). |
| `frontend/src/components/range-summary/charts/NutrientBarChart.vue` | Chart.js `Bar` for one nutrient. Per-bar color by % of effective limit using `nutrientColor()`. Horizontal `ReferenceLine` at the average effective limit. Footer with Min/Max/Avg/Limit. Bars get `min-width-per-bar = 12px`; if `12 * dayCount > containerWidth` the chart wraps a horizontally scrollable inner container. |

### Modified files

| File | Change |
|---|---|
| `frontend/src/components/NutrientSummaryCard.vue` | Add optional props `limitCoverageDays?: number` and `includedDayCount?: number`. When both provided and `0 < limitCoverageDays < includedDayCount`, render a small hint "Ліміт: M з N днів" inside the footer area. |
| `frontend/src/components/WeeklyAverageSummary.vue` | Replace `useWeeklyAverages` import with inline `useRangeAverages` call using a fixed 7-day window. No visual changes; cards still get the dashboard look. Health-profile fallback applies as a side benefit. |
| `frontend/src/views/ConsumedProductsStatsView.vue` | Add `<RangeAverageSummary />` as the first block under the page header, before the existing `<div v-if="error">` error notice. **Nothing else changes.** |
| `frontend/package.json` | Add `chart.js` and `vue-chartjs`. |

### Deleted files

| File | Reason |
|---|---|
| `frontend/src/composables/useWeeklyAverages.ts` | Fully replaced by `useRangeAverages` called inline from `WeeklyAverageSummary.vue`. |

### Backend

**No changes.** `/api/consumption/stats?date_from&date_to` and `/api/nutrition-limits?date_from&date_to` are already implemented.

### Test files

| File | Coverage |
|---|---|
| `frontend/src/tests/composables/useRangeAverages.test.ts` | Math (avg per nutrient, denominators), effective-limit fallback (limit → params → null), edge cases (no consumption, partial limit coverage, all empty days, invalid bounds). |
| `frontend/src/tests/composables/useDateRangeQuery.test.ts` | Defaults when query empty, fallback for invalid dates, `setRange` writes to query, `clearRange` removes from query, `isDefault` reflects state, writeback on invalid input. |

---

## Task 1: Add chart.js and vue-chartjs dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Add deps**

Add to `dependencies` (alphabetically near existing entries):

```json
"chart.js": "^4.4.7",
"chartjs-plugin-annotation": "^3.1.0",
"vue-chartjs": "^5.3.2"
```

- [ ] **Step 2: Install (user runs)**

The user runs `make frontend-shell` then `npm install`. Wait for confirmation.

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(frontend): add chart.js, vue-chartjs, chartjs-plugin-annotation"
```

---

## Task 2: useDateRangeQuery composable — failing test

**Files:**
- Create: `frontend/src/tests/composables/useDateRangeQuery.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/tests/composables/useDateRangeQuery.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { useDateRangeQuery } from '@/composables/useDateRangeQuery'

vi.mock('axios', () => ({
  default: {
    get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn(),
    defaults: { withCredentials: false, headers: { common: {} } },
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  },
}))

function buildHarness(initialQuery: Record<string, string> = {}) {
  let composable!: ReturnType<typeof useDateRangeQuery>
  const Probe = defineComponent({
    setup() {
      composable = useDateRangeQuery()
      return () => h('div')
    },
  })
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: Probe }],
  })
  const initialPath = '/' + (Object.keys(initialQuery).length
    ? '?' + new URLSearchParams(initialQuery).toString()
    : '')
  router.push(initialPath)
  const wrapper = mount(Probe, { global: { plugins: [router] } })
  return { wrapper, router, get: () => composable }
}

function isoDaysAgo(n: number): string {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

describe('useDateRangeQuery', () => {
  beforeEach(async () => {
    await nextTick()
  })

  it('defaults to last 7 days when query empty', async () => {
    const { get, router } = buildHarness({})
    await router.isReady()
    const { from, to, isDefault } = get()
    expect(isDefault.value).toBe(true)
    expect(from.value).toBe(isoDaysAgo(6))
    expect(to.value).toBe(isoDaysAgo(0))
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

User runs: `make test-frontend` (or `docker compose exec frontend npx vitest run src/tests/composables/useDateRangeQuery.test.ts`)

Expected: FAIL with `Cannot find module '@/composables/useDateRangeQuery'`.

---

## Task 3: useDateRangeQuery — minimal default

**Files:**
- Create: `frontend/src/composables/useDateRangeQuery.ts`

- [ ] **Step 1: Write minimal implementation**

```ts
// frontend/src/composables/useDateRangeQuery.ts
import { computed, type ComputedRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/
/** Backend `/api/consumption/stats` rejects ranges wider than this. Realistic
 *  usage is 60–90 days; the bound just prevents accidental URL tampering. */
export const MAX_RANGE_DAYS = 365

function isoDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function isValidIsoDate(s: unknown): s is string {
  if (typeof s !== 'string' || !ISO_DATE_RE.test(s)) return false
  const d = new Date(s + 'T00:00:00')
  return !Number.isNaN(d.getTime())
}

function daysBetweenInclusive(fromIso: string, toIso: string): number {
  const f = new Date(fromIso + 'T00:00:00').getTime()
  const t = new Date(toIso + 'T00:00:00').getTime()
  return Math.round((t - f) / 86_400_000) + 1
}

function defaultRange(): { from: string; to: string } {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const from = new Date(today)
  from.setDate(from.getDate() - 6)
  return { from: isoDate(from), to: isoDate(today) }
}

export interface UseDateRangeQueryReturn {
  from: ComputedRef<string>
  to: ComputedRef<string>
  isDefault: ComputedRef<boolean>
  setRange: (from: string, to: string) => void
  clearRange: () => void
}

export function useDateRangeQuery(): UseDateRangeQueryReturn {
  const route = useRoute()
  const router = useRouter()

  const parsed = computed(() => {
    const qFrom = route.query.from
    const qTo = route.query.to
    const validFrom = isValidIsoDate(qFrom) ? qFrom : null
    const validTo = isValidIsoDate(qTo) ? qTo : null
    if (
      validFrom &&
      validTo &&
      validFrom <= validTo &&
      daysBetweenInclusive(validFrom, validTo) <= MAX_RANGE_DAYS
    ) {
      return { from: validFrom, to: validTo, isDefault: false }
    }
    const def = defaultRange()
    return { from: def.from, to: def.to, isDefault: true }
  })

  const from = computed(() => parsed.value.from)
  const to = computed(() => parsed.value.to)
  const isDefault = computed(() => parsed.value.isDefault)

  function setRange(newFrom: string, newTo: string): void {
    if (!isValidIsoDate(newFrom) || !isValidIsoDate(newTo)) return
    if (newFrom > newTo) return
    if (daysBetweenInclusive(newFrom, newTo) > MAX_RANGE_DAYS) return
    router.replace({ query: { ...route.query, from: newFrom, to: newTo } })
  }

  function clearRange(): void {
    const next = { ...route.query }
    delete next.from
    delete next.to
    router.replace({ query: next })
  }

  return { from, to, isDefault, setRange, clearRange }
}
```

- [ ] **Step 2: Run the failing test — it should now pass**

User runs: `make test-frontend`
Expected: the default-range test passes.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useDateRangeQuery.ts frontend/src/tests/composables/useDateRangeQuery.test.ts
git commit -m "feat(frontend): add useDateRangeQuery with last-7-days default"
```

---

## Task 4: useDateRangeQuery — invalid query fallback test

**Files:**
- Modify: `frontend/src/tests/composables/useDateRangeQuery.test.ts`

- [ ] **Step 1: Append test for invalid input**

Append inside the `describe` block:

```ts
  it('falls back to default when from is invalid', async () => {
    const { get, router } = buildHarness({ from: 'not-a-date', to: '2026-04-30' })
    await router.isReady()
    const { from, to, isDefault } = get()
    expect(isDefault.value).toBe(true)
    expect(from.value).toBe(isoDaysAgo(6))
    expect(to.value).toBe(isoDaysAgo(0))
  })

  it('falls back when from > to', async () => {
    const { get, router } = buildHarness({ from: '2026-05-01', to: '2026-04-01' })
    await router.isReady()
    const { isDefault } = get()
    expect(isDefault.value).toBe(true)
  })

  it('returns valid range from query', async () => {
    const { get, router } = buildHarness({ from: '2026-04-01', to: '2026-04-30' })
    await router.isReady()
    const { from, to, isDefault } = get()
    expect(isDefault.value).toBe(false)
    expect(from.value).toBe('2026-04-01')
    expect(to.value).toBe('2026-04-30')
  })

  it('falls back to default when range exceeds 365 days', async () => {
    const { get, router } = buildHarness({ from: '2024-01-01', to: '2026-01-01' })
    await router.isReady()
    expect(get().isDefault.value).toBe(true)
  })
```

- [ ] **Step 2: Run tests — should pass**

User runs: `make test-frontend`
Expected: all 4 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tests/composables/useDateRangeQuery.test.ts
git commit -m "test(frontend): cover invalid date-range query fallback"
```

---

## Task 5: useDateRangeQuery — setRange and clearRange tests

**Files:**
- Modify: `frontend/src/tests/composables/useDateRangeQuery.test.ts`

- [ ] **Step 1: Append tests for mutations**

```ts
  it('setRange writes valid dates to query', async () => {
    const { get, router } = buildHarness({})
    await router.isReady()
    get().setRange('2026-04-01', '2026-04-30')
    await nextTick()
    expect(router.currentRoute.value.query.from).toBe('2026-04-01')
    expect(router.currentRoute.value.query.to).toBe('2026-04-30')
    expect(get().isDefault.value).toBe(false)
  })

  it('setRange ignores invalid dates', async () => {
    const { get, router } = buildHarness({ from: '2026-04-01', to: '2026-04-30' })
    await router.isReady()
    get().setRange('garbage', '2026-04-30')
    await nextTick()
    expect(router.currentRoute.value.query.from).toBe('2026-04-01')
  })

  it('setRange ignores ranges over 365 days', async () => {
    const { get, router } = buildHarness({ from: '2026-04-01', to: '2026-04-30' })
    await router.isReady()
    get().setRange('2024-01-01', '2026-01-01')
    await nextTick()
    expect(router.currentRoute.value.query.from).toBe('2026-04-01')
  })

  it('clearRange removes from/to from query', async () => {
    const { get, router } = buildHarness({ from: '2026-04-01', to: '2026-04-30' })
    await router.isReady()
    get().clearRange()
    await nextTick()
    expect(router.currentRoute.value.query.from).toBeUndefined()
    expect(router.currentRoute.value.query.to).toBeUndefined()
    expect(get().isDefault.value).toBe(true)
  })
```

- [ ] **Step 2: Run tests — should pass**

User runs: `make test-frontend`
Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tests/composables/useDateRangeQuery.test.ts
git commit -m "test(frontend): cover setRange and clearRange"
```

---

## Task 6: useRangeAverages — failing math test

**Files:**
- Create: `frontend/src/tests/composables/useRangeAverages.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/tests/composables/useRangeAverages.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { ref, nextTick } from 'vue'
import axios from 'axios'
import { useHealthStore } from '@/store/health'

vi.mock('axios', () => ({
  default: {
    get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn(),
    isAxiosError: (e: unknown): boolean =>
      typeof e === 'object' && e !== null && 'isAxiosError' in e,
    defaults: { withCredentials: false, headers: { common: {} } },
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  },
}))

import { useRangeAverages } from '@/composables/useRangeAverages'

const makeDay = (date: string, withConsumption: boolean) => ({
  date,
  total_calories: withConsumption ? 2000 : 0,
  total_carbohydrates: withConsumption ? 200 : 0,
  total_carbohydrates_of_sugars: withConsumption ? 40 : 0,
  total_proteins: withConsumption ? 100 : 0,
  total_fats: withConsumption ? 70 : 0,
  total_fats_saturated: withConsumption ? 20 : 0,
  total_salt: withConsumption ? 4 : 0,
  total_fibers: withConsumption ? 25 : 0,
  products_count: withConsumption ? 5 : 0,
  total_cost: withConsumption ? 100 : null,
})

describe('useRangeAverages — averaging', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(axios.get).mockReset()
  })

  it('averages calories over days with consumption only', async () => {
    vi.mocked(axios.get).mockImplementation(async (url: string) => {
      if (url === '/api/consumption/stats') {
        return {
          data: {
            days: [
              makeDay('2026-04-30', true),
              makeDay('2026-04-29', false),
              makeDay('2026-04-28', true),
            ],
            total: 3,
          },
        }
      }
      if (url === '/api/nutrition-limits') {
        return { data: { items: [], total: 0 } }
      }
      throw new Error('unexpected ' + url)
    })

    const householdId = ref<number | null>(1)
    const from = ref('2026-04-28')
    const to = ref('2026-04-30')
    const c = useRangeAverages(householdId, from, to)
    await c.refresh()
    await nextTick()

    const cal = c.averages.value.find(n => n.key === 'calories')!
    expect(cal.avg).toBe(2000) // 4000 / 2 days
    expect(c.includedDayCount.value).toBe(2)
    expect(c.skippedDayCount.value).toBe(1)
    expect(c.rangeDayCount.value).toBe(3)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

User runs: `make test-frontend`
Expected: FAIL with `Cannot find module '@/composables/useRangeAverages'`.

---

## Task 7: useRangeAverages — minimal implementation

**Files:**
- Create: `frontend/src/composables/useRangeAverages.ts`

- [ ] **Step 1: Write minimal implementation**

```ts
// frontend/src/composables/useRangeAverages.ts
import { ref, watch, type Ref } from 'vue'
import axios from 'axios'
import { useHealthStore } from '@/store/health'
import { normsFromSources, type NormValues } from '@/composables/useNorms'
import type { NutritionLimit } from '@/types/nutritionLimit'

export type NutrientKey =
  | 'calories'
  | 'carbohydrates'
  | 'carbohydrates_of_sugars'
  | 'proteins'
  | 'fats'
  | 'fats_saturated'
  | 'salt'
  | 'fibers'

export interface NutrientMeta {
  label: string
  unit: string
  lessIsBetter: boolean
  decimals: number
}

export const NUTRIENT_META: Record<NutrientKey, NutrientMeta> = {
  calories: { label: 'Калорії', unit: 'ккал', lessIsBetter: false, decimals: 0 },
  carbohydrates: { label: 'Вуглеводи', unit: 'г', lessIsBetter: false, decimals: 1 },
  carbohydrates_of_sugars: { label: 'Цукри', unit: 'г', lessIsBetter: true, decimals: 1 },
  proteins: { label: 'Білки', unit: 'г', lessIsBetter: false, decimals: 1 },
  fats: { label: 'Жири', unit: 'г', lessIsBetter: false, decimals: 1 },
  fats_saturated: { label: 'Насичені жири', unit: 'г', lessIsBetter: true, decimals: 1 },
  salt: { label: 'Сіль', unit: 'г', lessIsBetter: true, decimals: 2 },
  fibers: { label: 'Клітковина', unit: 'г', lessIsBetter: false, decimals: 1 },
}

export const NUTRIENT_KEYS = Object.keys(NUTRIENT_META) as NutrientKey[]

/** Single source of truth — chart components import these. Do NOT redefine elsewhere. */
export const NUTRIENT_COLORS: Record<NutrientKey, string> = {
  calories: '#f59e0b',
  carbohydrates: '#6366f1',
  carbohydrates_of_sugars: '#a855f7',
  proteins: '#10b981',
  fats: '#f97316',
  fats_saturated: '#ef4444',
  salt: '#0ea5e9',
  fibers: '#8b5cf6',
}

export const STATS_FIELD: Record<NutrientKey, keyof DailyStatsRow> = {
  calories: 'total_calories',
  carbohydrates: 'total_carbohydrates',
  carbohydrates_of_sugars: 'total_carbohydrates_of_sugars',
  proteins: 'total_proteins',
  fats: 'total_fats',
  fats_saturated: 'total_fats_saturated',
  salt: 'total_salt',
  fibers: 'total_fibers',
}

export const NORM_FIELD: Record<NutrientKey, keyof NormValues> = {
  calories: 'daily_calories',
  carbohydrates: 'daily_carbohydrates',
  carbohydrates_of_sugars: 'daily_carbohydrates_of_sugars',
  proteins: 'daily_proteins',
  fats: 'daily_fats',
  fats_saturated: 'daily_fats_saturated',
  salt: 'daily_salt',
  fibers: 'daily_fibers',
}

/** Backend caps `/api/nutrition-limits?limit` at 100. Range is clamped to ≤365 days
 *  (see useDateRangeQuery), and limits are sparse, so 100 is sufficient in practice
 *  for the realistic 60–90 day window. */
const NUTRITION_LIMITS_PAGE_SIZE = 100

export interface DailyStatsRow {
  date: string
  total_calories: number
  total_carbohydrates: number
  total_carbohydrates_of_sugars: number
  total_proteins: number
  total_fats: number
  total_fats_saturated: number
  total_salt: number
  total_fibers: number
  products_count: number
  total_cost: number | null
}

interface StatsResponse { days: DailyStatsRow[]; total: number }
interface LimitsResponse { items: NutritionLimit[]; total: number }

export interface NutrientAverage {
  key: NutrientKey
  label: string
  unit: string
  avg: number
  limit: number | null
  lessIsBetter: boolean
  decimals: number
  limitCoverageDays: number
}

export interface UseRangeAveragesReturn {
  averages: Ref<NutrientAverage[]>
  loading: Ref<boolean>
  firstLoading: Ref<boolean>
  error: Ref<string | null>
  days: Ref<DailyStatsRow[]>
  effectiveLimitsByDate: Ref<Map<string, NormValues | null>>
  includedDayCount: Ref<number>
  skippedDayCount: Ref<number>
  rangeDayCount: Ref<number>
  refresh: () => Promise<void>
}

export function useRangeAverages(
  householdId: Ref<number | null>,
  from: Ref<string>,
  to: Ref<string>,
): UseRangeAveragesReturn {
  const averages = ref<NutrientAverage[]>([])
  const days = ref<DailyStatsRow[]>([])
  /** Raw limits from the backend, indexed by date. Kept so that health-profile
   *  changes can re-derive `effectiveLimitsByDate` locally without refetching. */
  const rawLimitsByDate = ref<Map<string, NutritionLimit>>(new Map())
  const effectiveLimitsByDate = ref<Map<string, NormValues | null>>(new Map())
  const loading = ref(false)
  const firstLoading = ref(true)
  const error = ref<string | null>(null)
  const includedDayCount = ref(0)
  const skippedDayCount = ref(0)
  const rangeDayCount = ref(0)

  const healthStore = useHealthStore()

  let activeController: AbortController | null = null

  function rebuildEffectiveLimits(): void {
    const effective = new Map<string, NormValues | null>()
    for (const d of days.value) {
      effective.set(
        d.date,
        normsFromSources(rawLimitsByDate.value.get(d.date) ?? null, healthStore.params),
      )
    }
    effectiveLimitsByDate.value = effective
  }

  function recompute(): void {
    const consumed = days.value.filter(d => d.products_count > 0)
    includedDayCount.value = consumed.length
    rangeDayCount.value = days.value.length
    skippedDayCount.value = days.value.length - consumed.length

    const denom = Math.max(consumed.length, 1)
    const result: NutrientAverage[] = NUTRIENT_KEYS.map((key) => {
      const meta = NUTRIENT_META[key]
      const totalField = STATS_FIELD[key]
      const normField = NORM_FIELD[key]

      const avg =
        consumed.reduce((sum, d) => sum + (d[totalField] as number), 0) / denom

      let limitSum = 0
      let limitCount = 0
      for (const d of consumed) {
        const norm = effectiveLimitsByDate.value.get(d.date)
        const v = norm?.[normField] ?? null
        if (v != null) {
          limitSum += v
          limitCount += 1
        }
      }
      const limit = limitCount > 0 ? limitSum / limitCount : null

      return {
        key,
        label: meta.label,
        unit: meta.unit,
        avg,
        limit,
        lessIsBetter: meta.lessIsBetter,
        decimals: meta.decimals,
        limitCoverageDays: limitCount,
      }
    })

    averages.value = result
  }

  async function refresh(): Promise<void> {
    const id = householdId.value
    if (id == null) {
      days.value = []
      rawLimitsByDate.value = new Map()
      effectiveLimitsByDate.value = new Map()
      averages.value = []
      includedDayCount.value = 0
      skippedDayCount.value = 0
      rangeDayCount.value = 0
      return
    }

    if (activeController) activeController.abort()
    const controller = new AbortController()
    activeController = controller

    loading.value = true
    error.value = null

    try {
      const [statsRes, limitsRes] = await Promise.all([
        axios.get<StatsResponse>('/api/consumption/stats', {
          params: { household_id: id, date_from: from.value, date_to: to.value },
          signal: controller.signal,
        }),
        axios.get<LimitsResponse>('/api/nutrition-limits', {
          params: { date_from: from.value, date_to: to.value, limit: NUTRITION_LIMITS_PAGE_SIZE },
          signal: controller.signal,
        }),
      ])

      if (controller.signal.aborted) return

      days.value = statsRes.data.days
      const limitsByDate = new Map<string, NutritionLimit>()
      for (const row of limitsRes.data.items) {
        limitsByDate.set(row.date, row)
      }
      rawLimitsByDate.value = limitsByDate
      rebuildEffectiveLimits()
      recompute()
      firstLoading.value = false
    } catch (e: unknown) {
      if (axios.isAxiosError(e) && e.code === 'ERR_CANCELED') return
      if (controller.signal.aborted) return
      const msg =
        axios.isAxiosError(e) ? (e.response?.data?.detail ?? e.message) :
        e instanceof Error ? e.message :
        String(e)
      error.value = msg
      days.value = []
      rawLimitsByDate.value = new Map()
      effectiveLimitsByDate.value = new Map()
      averages.value = []
      includedDayCount.value = 0
      skippedDayCount.value = 0
      rangeDayCount.value = 0
      firstLoading.value = false
    } finally {
      if (activeController === controller) {
        activeController = null
        loading.value = false
      }
    }
  }

  watch([householdId, from, to], refresh, { immediate: true })
  // Health-profile changes only affect the fallback when no daily limit exists for
  // that date. Re-derive locally from `rawLimitsByDate` — no network call needed.
  watch(
    () => healthStore.params,
    () => {
      if (days.value.length === 0) return
      rebuildEffectiveLimits()
      recompute()
    },
  )

  return {
    averages,
    loading,
    firstLoading,
    error,
    days,
    effectiveLimitsByDate,
    includedDayCount,
    skippedDayCount,
    rangeDayCount,
    refresh,
  }
}
```

- [ ] **Step 2: Run test — should pass**

User runs: `make test-frontend`
Expected: averaging test passes.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useRangeAverages.ts frontend/src/tests/composables/useRangeAverages.test.ts
git commit -m "feat(frontend): add useRangeAverages composable"
```

---

## Task 8: useRangeAverages — limit + health-profile fallback test

**Files:**
- Modify: `frontend/src/tests/composables/useRangeAverages.test.ts`

- [ ] **Step 1: Append fallback test**

```ts
const makeLimit = (date: string, overrides: Record<string, number | null> = {}) => ({
  id: 1,
  date,
  calories_burned: null,
  body_weight: null,
  activity_level: null,
  calories: 2200,
  proteins: 110,
  carbohydrates: 250,
  carbohydrates_of_sugars: 50,
  fats: 70,
  fats_saturated: 22,
  salt: 5,
  fibers: 28,
  ...overrides,
})

const makeHealthParams = (overrides: Record<string, unknown> = {}) => ({
  gender: null,
  date_of_birth: null,
  height: null,
  weight: null,
  activity_level: null,
  goal: null,
  calorie_deficit_percent: null,
  daily_calories: 2000,
  daily_proteins: 100,
  daily_fats: 60,
  daily_fats_saturated: 20,
  daily_carbohydrates: 220,
  daily_carbohydrates_of_sugars: 45,
  daily_salt: 4,
  daily_fibers: 25,
  ...overrides,
})

describe('useRangeAverages — effective limit fallback', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(axios.get).mockReset()
  })

  it('uses daily limit when present, falls back to health params otherwise', async () => {
    vi.mocked(axios.get).mockImplementation(async (url: string) => {
      if (url === '/api/consumption/stats') {
        return {
          data: {
            days: [
              makeDay('2026-04-30', true),  // has daily limit
              makeDay('2026-04-29', true),  // no daily limit, health params apply
              makeDay('2026-04-28', true),  // no daily limit, no params for sugars
            ],
            total: 3,
          },
        }
      }
      if (url === '/api/nutrition-limits') {
        return {
          data: { items: [makeLimit('2026-04-30')], total: 1 },
        }
      }
      throw new Error('unexpected ' + url)
    })

    const health = useHealthStore()
    health.params = makeHealthParams({ daily_carbohydrates_of_sugars: null })

    const householdId = ref<number | null>(1)
    const from = ref('2026-04-28')
    const to = ref('2026-04-30')
    const c = useRangeAverages(householdId, from, to)
    await c.refresh()
    await nextTick()

    const cal = c.averages.value.find(n => n.key === 'calories')!
    // limit avg: (2200 from daily + 2000 from params + 2000 from params) / 3
    expect(cal.limit).toBeCloseTo((2200 + 2000 + 2000) / 3, 1)
    expect(cal.limitCoverageDays).toBe(3)

    const sugars = c.averages.value.find(n => n.key === 'carbohydrates_of_sugars')!
    // params has no sugars, daily limit only on day 1
    expect(sugars.limit).toBeCloseTo(50, 1)
    expect(sugars.limitCoverageDays).toBe(1)
  })

  it('returns null limit when no day has any source', async () => {
    vi.mocked(axios.get).mockImplementation(async (url: string) => {
      if (url === '/api/consumption/stats') {
        return { data: { days: [makeDay('2026-04-30', true)], total: 1 } }
      }
      if (url === '/api/nutrition-limits') {
        return { data: { items: [], total: 0 } }
      }
      throw new Error('unexpected ' + url)
    })
    const health = useHealthStore()
    health.params = null

    const c = useRangeAverages(ref(1), ref('2026-04-30'), ref('2026-04-30'))
    await c.refresh()
    await nextTick()

    expect(c.averages.value.find(n => n.key === 'calories')!.limit).toBeNull()
  })
})
```

- [ ] **Step 2: Run tests — should pass**

User runs: `make test-frontend`
Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tests/composables/useRangeAverages.test.ts
git commit -m "test(frontend): cover limit + health-profile fallback in useRangeAverages"
```

---

## Task 9: useRangeAverages — empty range and household=null tests

**Files:**
- Modify: `frontend/src/tests/composables/useRangeAverages.test.ts`

- [ ] **Step 1: Append edge-case tests**

```ts
describe('useRangeAverages — edge cases', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(axios.get).mockReset()
  })

  it('does not fetch when householdId is null', async () => {
    const c = useRangeAverages(ref<number | null>(null), ref('2026-04-30'), ref('2026-04-30'))
    await c.refresh()
    expect(vi.mocked(axios.get)).not.toHaveBeenCalled()
    expect(c.averages.value).toEqual([])
  })

  it('all days zero consumption -> includedDayCount=0, all avg=0, limits computed but unused', async () => {
    vi.mocked(axios.get).mockImplementation(async (url: string) => {
      if (url === '/api/consumption/stats') {
        return {
          data: {
            days: [makeDay('2026-04-30', false), makeDay('2026-04-29', false)],
            total: 2,
          },
        }
      }
      if (url === '/api/nutrition-limits') {
        return { data: { items: [], total: 0 } }
      }
      throw new Error('unexpected ' + url)
    })

    const c = useRangeAverages(ref(1), ref('2026-04-29'), ref('2026-04-30'))
    await c.refresh()
    await nextTick()

    expect(c.includedDayCount.value).toBe(0)
    expect(c.skippedDayCount.value).toBe(2)
    expect(c.averages.value.every(n => n.avg === 0)).toBe(true)
    expect(c.averages.value.every(n => n.limitCoverageDays === 0)).toBe(true)
  })
})
```

- [ ] **Step 2: Run tests — should pass**

User runs: `make test-frontend`
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tests/composables/useRangeAverages.test.ts
git commit -m "test(frontend): cover null household and empty consumption"
```

---

## Task 10: Extend NutrientSummaryCard with coverage hint

**Files:**
- Modify: `frontend/src/components/NutrientSummaryCard.vue`

- [ ] **Step 1: Add props and hint render**

Replace the `defineProps` block with:

```ts
const props = withDefaults(
  defineProps<{
    label: string
    unit: string
    avg: number
    limit: number | null
    lessIsBetter?: boolean
    decimals?: number
    limitCoverageDays?: number
    includedDayCount?: number
  }>(),
  {
    lessIsBetter: false,
    decimals: 1,
  },
)
```

Add this computed near the others:

```ts
const showCoverageHint = computed(() => {
  const m = props.limitCoverageDays
  const n = props.includedDayCount
  return m != null && n != null && m > 0 && m < n
})
```

Replace the `<footer>` block with:

```html
<footer class="flex items-center justify-between">
  <span class="text-[10px] text-gray-400">
    {{ showCoverageHint ? `Ліміт: ${limitCoverageDays} з ${includedDayCount} днів` : 'Факт / Ліміт' }}
  </span>
  <span :class="['text-[11px] font-semibold', textClass || 'text-gray-400']">
    {{ limit != null ? `${pct}%` : '—' }}
  </span>
</footer>
```

- [ ] **Step 2: Verify dashboard still renders correctly**

User runs the app and visits `/dashboard`. The card layout should be unchanged because new props are optional. (If a Vitest snapshot exists for this component, run `make test-frontend`.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/NutrientSummaryCard.vue
git commit -m "feat(frontend): add optional limit-coverage hint to NutrientSummaryCard"
```

---

## Task 11: Replace WeeklyAverageSummary's composable usage

**Files:**
- Modify: `frontend/src/components/WeeklyAverageSummary.vue`

- [ ] **Step 1: Rewire to useRangeAverages**

Replace the entire `<script setup>` section with:

```ts
<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useHouseholdStore } from '../store/household'
import { useRangeAverages } from '../composables/useRangeAverages'
import NutrientSummaryCard from './NutrientSummaryCard.vue'

const householdStore = useHouseholdStore()
const { selectedId } = storeToRefs(householdStore)
const householdIdRef = computed(() => selectedId.value ?? null)

const WINDOW_DAYS = 7

function isoDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const fromRef = computed(() => {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() - (WINDOW_DAYS - 1))
  return isoDate(d)
})

const toRef = computed(() => {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return isoDate(d)
})

const {
  averages,
  loading,
  error,
  includedDayCount,
  skippedDayCount,
} = useRangeAverages(householdIdRef, fromRef, toRef)

const windowDays = WINDOW_DAYS

function daysWord(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'день'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'дні'
  return 'днів'
}
</script>
```

- [ ] **Step 2: Verify dashboard still works**

User runs the app and visits `/dashboard`. Block should render the same way as before (cards may now show limits via health-profile fallback).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/WeeklyAverageSummary.vue
git commit -m "refactor(frontend): switch WeeklyAverageSummary to useRangeAverages"
```

---

## Task 12: Delete the obsolete useWeeklyAverages composable

**Files:**
- Delete: `frontend/src/composables/useWeeklyAverages.ts`

- [ ] **Step 1: Confirm no other consumers**

```bash
grep -rn "useWeeklyAverages" frontend/src
```

Expected: no matches.

- [ ] **Step 2: Delete file**

```bash
git rm frontend/src/composables/useWeeklyAverages.ts
```

- [ ] **Step 3: Commit**

```bash
git commit -m "refactor(frontend): remove obsolete useWeeklyAverages composable"
```

---

## Task 13: Create DateRangePicker component

**Files:**
- Create: `frontend/src/components/range-summary/DateRangePicker.vue`

- [ ] **Step 1: Implement picker**

```vue
<!-- frontend/src/components/range-summary/DateRangePicker.vue -->
<template>
  <div
    class="inline-flex items-stretch rounded-lg border transition-colors"
    :class="hasRange
      ? 'bg-blue-50 border-blue-200'
      : 'bg-white border-gray-200 hover:bg-gray-50'"
  >
    <button
      ref="triggerRef"
      type="button"
      class="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-l-lg"
      :class="[
        hasRange ? 'text-blue-700' : 'text-gray-700',
        !hasRange && 'rounded-r-lg',
      ]"
      :aria-label="hasRange ? `Період: ${label}. Натисніть, щоб змінити.` : 'Обрати період'"
      @click="openPicker"
    >
      <Calendar :size="13" :class="hasRange ? 'text-blue-500' : 'text-gray-400'" />
      <span class="max-w-[220px] truncate">{{ label }}</span>
      <ChevronDown
        v-if="!hasRange"
        :size="12"
        class="text-gray-400"
      />
    </button>
    <button
      v-if="hasRange"
      type="button"
      class="px-2 py-1.5 rounded-r-lg text-blue-400 hover:text-blue-700 transition-colors border-l border-blue-200"
      aria-label="Скинути період"
      @click="onClear"
    >
      <X :size="12" />
    </button>
    <input
      ref="inputRef"
      type="text"
      class="sr-only"
      aria-hidden="true"
      tabindex="-1"
      readonly
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { Calendar, ChevronDown, X } from 'lucide-vue-next'
import flatpickr from 'flatpickr'
import { Ukrainian } from 'flatpickr/dist/l10n/uk'
import 'flatpickr/dist/flatpickr.min.css'
import type { Instance as FlatpickrInstance } from 'flatpickr/dist/types/instance'

const props = defineProps<{
  from: string
  to: string
  isDefault: boolean
}>()
const emit = defineEmits<{
  'update:range': [from: string, to: string]
  clear: []
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const triggerRef = ref<HTMLButtonElement | null>(null)
let fp: FlatpickrInstance | null = null

const hasRange = computed(() => !props.isDefault)

const MONTHS_SHORT = ['січ', 'лют', 'бер', 'кв', 'трав', 'черв', 'лип', 'серп', 'вер', 'жовт', 'лист', 'груд']

function formatDay(s: string, withYear: boolean): string {
  const [y, m, d] = s.split('-').map(Number)
  const month = MONTHS_SHORT[m - 1]
  return withYear ? `${d} ${month} ${y}` : `${d} ${month}`
}

const label = computed(() => {
  const fromYear = props.from.slice(0, 4)
  const toYear = props.to.slice(0, 4)
  const sameYear = fromYear === toYear
  return `${formatDay(props.from, !sameYear)} – ${formatDay(props.to, true)}`
})

function openPicker(): void {
  fp?.open()
}

function onClear(): void {
  emit('clear')
}

onMounted(() => {
  if (!inputRef.value) return
  fp = flatpickr(inputRef.value, {
    mode: 'range',
    dateFormat: 'Y-m-d',
    defaultDate: [props.from, props.to],
    locale: Ukrainian,
    positionElement: triggerRef.value ?? undefined,
    clickOpens: false,
    allowInput: false,
    onClose: (selectedDates) => {
      if (selectedDates.length === 2) {
        const [a, b] = selectedDates
        const fromIso = formatIso(a < b ? a : b)
        const toIso = formatIso(a < b ? b : a)
        emit('update:range', fromIso, toIso)
      }
    },
  })
})

watch(
  () => [props.from, props.to],
  ([f, t]) => {
    if (fp) fp.setDate([f, t], false)
  },
)

onBeforeUnmount(() => {
  fp?.destroy()
  fp = null
})

function formatIso(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/range-summary/DateRangePicker.vue
git commit -m "feat(frontend): add Figma-styled DateRangePicker over flatpickr"
```

---

## Task 14: Create chart components — OverviewChart

**Files:**
- Create: `frontend/src/components/range-summary/charts/chartSetup.ts`
- Create: `frontend/src/components/range-summary/charts/OverviewChart.vue`
- Modify: `frontend/src/composables/useRangeAverages.ts` (add `formatDayShortUk` export)

- [ ] **Step 1: Add Ukrainian short-date formatter to useRangeAverages**

Append to the bottom of `useRangeAverages.ts`:

```ts
const MONTHS_SHORT_UK = [
  'січ', 'лют', 'бер', 'кв', 'трав', 'черв',
  'лип', 'серп', 'вер', 'жовт', 'лист', 'груд',
]

export function formatDayShortUk(isoDate: string): string {
  const [, m, d] = isoDate.split('-')
  return `${parseInt(d, 10)} ${MONTHS_SHORT_UK[parseInt(m, 10) - 1]}`
}
```

- [ ] **Step 2: Create chart setup module (one-time global registration)**

```ts
// frontend/src/components/range-summary/charts/chartSetup.ts
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  BarElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend,
} from 'chart.js'
import annotationPlugin from 'chartjs-plugin-annotation'

let registered = false

/** Idempotent. Imported once from each chart component to register Chart.js
 *  components and the annotation plugin globally. */
export function ensureChartJsRegistered(): void {
  if (registered) return
  ChartJS.register(
    LineElement,
    PointElement,
    BarElement,
    LinearScale,
    CategoryScale,
    Tooltip,
    Legend,
    annotationPlugin,
  )
  registered = true
}
```

- [ ] **Step 3: Implement overview chart**

```vue
<!-- frontend/src/components/range-summary/charts/OverviewChart.vue -->
<template>
  <div class="w-full">
    <p class="text-xs text-gray-500 mb-3">
      Усі нутрієнти як <span class="font-medium text-gray-700">% ефективного ліміту</span>. Лінія 100% — норма.
    </p>
    <div class="h-[320px]" role="img" :aria-label="ariaLabel">
      <Line :data="chartData" :options="chartOptions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import type { TooltipItem } from 'chart.js'
import {
  type DailyStatsRow,
  NUTRIENT_KEYS,
  NUTRIENT_META,
  NUTRIENT_COLORS,
  STATS_FIELD,
  NORM_FIELD,
  formatDayShortUk,
} from '@/composables/useRangeAverages'
import type { NormValues } from '@/composables/useNorms'
import { ensureChartJsRegistered } from './chartSetup'

ensureChartJsRegistered()

const props = defineProps<{
  days: DailyStatsRow[]
  effectiveLimitsByDate: Map<string, NormValues | null>
}>()

const consumedDays = computed(() =>
  [...props.days].filter(d => d.products_count > 0).reverse(), // oldest -> newest
)

const labels = computed(() => consumedDays.value.map(d => formatDayShortUk(d.date)))

const ariaLabel = computed(
  () => `Лінійний графік: % ефективного ліміту для 8 нутрієнтів за ${consumedDays.value.length} днів.`,
)

const chartData = computed(() => {
  const datasets = NUTRIENT_KEYS.map((key) => {
    const color = NUTRIENT_COLORS[key]
    const data = consumedDays.value.map((d) => {
      const norm = props.effectiveLimitsByDate.get(d.date)
      const limit = norm?.[NORM_FIELD[key]] ?? null
      const value = d[STATS_FIELD[key]] as number
      if (limit == null || limit === 0) return null
      return Math.round((value / limit) * 100)
    })
    return {
      label: NUTRIENT_META[key].label,
      data,
      borderColor: color,
      backgroundColor: color,
      tension: 0.3,
      pointRadius: 3,
      pointHoverRadius: 5,
      spanGaps: false,
    }
  })

  return { labels: labels.value, datasets }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: { font: { size: 11 }, color: '#6b7280', boxWidth: 12 },
    },
    tooltip: {
      callbacks: {
        label: (ctx: TooltipItem<'line'>) => {
          if (ctx.parsed.y == null) return `${ctx.dataset.label}: —`
          return `${ctx.dataset.label}: ${ctx.parsed.y}%`
        },
      },
    },
    annotation: {
      annotations: {
        target: {
          type: 'line' as const,
          yMin: 100,
          yMax: 100,
          borderColor: '#9ca3af',
          borderWidth: 1.5,
          borderDash: [5, 4],
          label: {
            display: true,
            content: '100%',
            position: 'end' as const,
            backgroundColor: 'transparent',
            color: '#6b7280',
            font: { size: 10 },
          },
        },
      },
    },
  },
  scales: {
    x: { grid: { color: '#f0f0f0' }, ticks: { color: '#9ca3af', font: { size: 11 } } },
    y: {
      beginAtZero: true,
      grid: { color: '#f0f0f0' },
      ticks: { color: '#9ca3af', font: { size: 11 }, callback: (v: number | string) => `${v}%` },
    },
  },
}))
</script>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/composables/useRangeAverages.ts \
        frontend/src/components/range-summary/charts/chartSetup.ts \
        frontend/src/components/range-summary/charts/OverviewChart.vue
git commit -m "feat(frontend): add OverviewChart with annotation plugin"
```

---

## Task 15: Create chart components — NutrientBarChart

**Files:**
- Create: `frontend/src/components/range-summary/charts/NutrientBarChart.vue`

- [ ] **Step 1: Implement bar chart**

```vue
<!-- frontend/src/components/range-summary/charts/NutrientBarChart.vue -->
<template>
  <div class="w-full">
    <p class="text-xs text-gray-500 mb-3">
      Денний показник <span class="font-medium" :style="{ color: NUTRIENT_COLOR }">
        {{ NUTRIENT_META[nutrientKey].label }}
      </span>
      vs середній ліміт ({{ avgLimit != null ? avgLimit.toFixed(NUTRIENT_META[nutrientKey].decimals) : '—' }}
      {{ NUTRIENT_META[nutrientKey].unit }}). Кольори барів — за статусом.
    </p>
    <div ref="containerRef" class="h-[280px] overflow-x-auto" role="img" :aria-label="ariaLabel">
      <div
        :style="{
          height: '100%',
          minWidth: minChartWidth + 'px',
          width: '100%',
        }"
      >
        <Bar :data="chartData" :options="chartOptions" />
      </div>
    </div>
    <div class="grid grid-cols-4 gap-2 mt-3 pt-3 border-t border-gray-100">
      <StatBlock label="Min" :value="stats.min" :unit="NUTRIENT_META[nutrientKey].unit" :limit="avgLimit" :decimals="NUTRIENT_META[nutrientKey].decimals" :less-is-better="NUTRIENT_META[nutrientKey].lessIsBetter" />
      <StatBlock label="Max" :value="stats.max" :unit="NUTRIENT_META[nutrientKey].unit" :limit="avgLimit" :decimals="NUTRIENT_META[nutrientKey].decimals" :less-is-better="NUTRIENT_META[nutrientKey].lessIsBetter" />
      <StatBlock label="Avg" :value="stats.avg" :unit="NUTRIENT_META[nutrientKey].unit" :limit="avgLimit" :decimals="NUTRIENT_META[nutrientKey].decimals" :less-is-better="NUTRIENT_META[nutrientKey].lessIsBetter" />
      <StatBlock label="Limit" :value="avgLimit ?? 0" :unit="NUTRIENT_META[nutrientKey].unit" :limit="null" :decimals="NUTRIENT_META[nutrientKey].decimals" :less-is-better="false" :force-neutral="true" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Bar } from 'vue-chartjs'
import type { TooltipItem } from 'chart.js'
import {
  type DailyStatsRow,
  type NutrientKey,
  NUTRIENT_META,
  NUTRIENT_COLORS,
  STATS_FIELD,
  NORM_FIELD,
  formatDayShortUk,
} from '@/composables/useRangeAverages'
import type { NormValues } from '@/composables/useNorms'
import { nutrientHex } from '@/composables/useNutrientColor'
import { ensureChartJsRegistered } from './chartSetup'
import StatBlock from './StatBlock.vue'

ensureChartJsRegistered()

const props = defineProps<{
  nutrientKey: NutrientKey
  days: DailyStatsRow[]
  effectiveLimitsByDate: Map<string, NormValues | null>
}>()

const containerRef = ref<HTMLElement | null>(null)
const NUTRIENT_COLOR = computed(() => NUTRIENT_COLORS[props.nutrientKey])

const consumedDays = computed(() =>
  [...props.days].filter(d => d.products_count > 0).reverse(),
)

const values = computed(() =>
  consumedDays.value.map(d => d[STATS_FIELD[props.nutrientKey]] as number),
)

const avgLimit = computed(() => {
  let sum = 0
  let count = 0
  for (const d of consumedDays.value) {
    const norm = props.effectiveLimitsByDate.get(d.date)
    const v = norm?.[NORM_FIELD[props.nutrientKey]] ?? null
    if (v != null) {
      sum += v
      count += 1
    }
  }
  return count > 0 ? sum / count : null
})

const stats = computed(() => {
  const v = values.value
  if (v.length === 0) return { min: 0, max: 0, avg: 0 }
  const min = Math.min(...v)
  const max = Math.max(...v)
  const avg = v.reduce((a, b) => a + b, 0) / v.length
  return { min, max, avg }
})

const labels = computed(() => consumedDays.value.map(d => formatDayShortUk(d.date)))

const minChartWidth = computed(() => Math.max(consumedDays.value.length * 12, 200))

const ariaLabel = computed(() => {
  const meta = NUTRIENT_META[props.nutrientKey]
  return `Стовпчастий графік: ${meta.label} (${meta.unit}) за ${consumedDays.value.length} днів.`
})

const chartData = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      label: NUTRIENT_META[props.nutrientKey].label,
      data: values.value,
      backgroundColor: consumedDays.value.map((d, i) => {
        const norm = props.effectiveLimitsByDate.get(d.date)
        const limit = norm?.[NORM_FIELD[props.nutrientKey]] ?? null
        if (limit == null) return '#6b7280'
        return nutrientHex(values.value[i], limit, NUTRIENT_META[props.nutrientKey].lessIsBetter)
      }),
      borderRadius: 4,
      maxBarThickness: 42,
    },
  ],
}))

const chartOptions = computed(() => {
  const meta = NUTRIENT_META[props.nutrientKey]
  const limit = avgLimit.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx: TooltipItem<'bar'>) => {
            const v = ctx.parsed.y
            const pct = limit ? Math.round((v / limit) * 100) : null
            return [
              `Значення: ${v.toFixed(meta.decimals)} ${meta.unit}`,
              limit != null ? `% ліміту: ${pct}%` : '',
            ].filter(Boolean) as string[]
          },
        },
      },
      annotation: limit != null
        ? {
            annotations: {
              avgLimit: {
                type: 'line' as const,
                yMin: limit,
                yMax: limit,
                borderColor: '#6b7280',
                borderWidth: 2,
                borderDash: [5, 4],
                label: {
                  display: true,
                  content: `Ліміт: ${limit.toFixed(meta.decimals)} ${meta.unit}`,
                  position: 'end' as const,
                  backgroundColor: 'transparent',
                  color: '#6b7280',
                  font: { size: 10 },
                },
              },
            },
          }
        : { annotations: {} },
    },
    scales: {
      x: { grid: { color: '#f0f0f0' }, ticks: { color: '#9ca3af', font: { size: 11 } } },
      y: { beginAtZero: true, grid: { color: '#f0f0f0' }, ticks: { color: '#9ca3af', font: { size: 11 } } },
    },
  }
})
</script>
```

- [ ] **Step 2: Create StatBlock helper**

Create `frontend/src/components/range-summary/charts/StatBlock.vue`:

```vue
<template>
  <div class="flex flex-col items-center gap-0.5 bg-gray-50 rounded-lg px-3 py-2">
    <span class="text-[10px] text-gray-400 uppercase tracking-wide">{{ label }}</span>
    <span class="text-sm font-semibold" :class="textClass">
      {{ value.toFixed(decimals) }}
      <span class="text-xs text-gray-400 ml-0.5">{{ unit }}</span>
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { nutrientColor } from '@/composables/useNutrientColor'

const props = withDefaults(
  defineProps<{
    label: string
    value: number
    unit: string
    limit: number | null
    decimals: number
    lessIsBetter: boolean
    forceNeutral?: boolean
  }>(),
  { forceNeutral: false },
)

const textClass = computed(() => {
  if (props.forceNeutral || props.limit == null) return 'text-gray-700'
  return nutrientColor(props.value, props.limit, props.lessIsBetter).textClass || 'text-gray-700'
})
</script>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/range-summary/charts/NutrientBarChart.vue frontend/src/components/range-summary/charts/StatBlock.vue
git commit -m "feat(frontend): add NutrientBarChart and StatBlock"
```

---

## Task 16: Create ChartModal

**Files:**
- Create: `frontend/src/components/range-summary/ChartModal.vue`

- [ ] **Step 1: Implement modal**

```vue
<!-- frontend/src/components/range-summary/ChartModal.vue -->
<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
        @click.self="onClose"
      >
        <Transition
          enter-active-class="transition duration-150 ease-out"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition duration-100 ease-in"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
          appear
        >
          <div
            ref="dialogRef"
            class="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden"
            role="dialog"
            aria-modal="true"
            aria-labelledby="chart-modal-title"
            tabindex="-1"
            @keydown.tab="onTabKey"
          >
            <header class="px-5 pt-4 pb-3 border-b border-gray-100 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <BarChart2 :size="16" class="text-blue-500" />
                <h3 id="chart-modal-title" class="text-sm font-semibold text-gray-900">Тренди нутрієнтів</h3>
                <span class="text-xs text-gray-400 ml-1">{{ days.length }} {{ daysWord(days.length) }}</span>
              </div>
              <button
                ref="closeButtonRef"
                class="text-gray-400 hover:text-gray-600 text-lg leading-none"
                aria-label="Закрити"
                @click="onClose"
              >
                ✕
              </button>
            </header>

            <nav class="flex items-center gap-0.5 px-5 pt-3 pb-0 border-b border-gray-100 overflow-x-auto">
              <button
                v-for="tab in TABS"
                :key="tab.key"
                type="button"
                class="px-3 py-1.5 text-xs rounded-t transition-colors border-b-2 -mb-px shrink-0"
                :class="activeTab === tab.key
                  ? 'text-blue-600 border-blue-500 bg-blue-50/60'
                  : 'text-gray-500 border-transparent hover:text-gray-800 hover:bg-gray-50'"
                @click="activeTab = tab.key"
              >
                <component
                  v-if="tab.key === 'overview'"
                  :is="TrendingUp"
                  :size="11"
                  class="inline mr-1 align-middle"
                />
                <span
                  v-else
                  class="inline-block w-1.5 h-1.5 rounded-full mr-1.5 align-middle"
                  :style="{ background: NUTRIENT_COLORS[tab.key as NutrientKey] }"
                />
                {{ tab.label }}
              </button>
            </nav>

            <div class="px-5 pt-4 pb-5 overflow-y-auto">
              <OverviewChart
                v-if="activeTab === 'overview'"
                :days="days"
                :effective-limits-by-date="effectiveLimitsByDate"
              />
              <NutrientBarChart
                v-else
                :nutrient-key="activeTab as NutrientKey"
                :days="days"
                :effective-limits-by-date="effectiveLimitsByDate"
              />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { BarChart2, TrendingUp } from 'lucide-vue-next'
import OverviewChart from './charts/OverviewChart.vue'
import NutrientBarChart from './charts/NutrientBarChart.vue'
import {
  type DailyStatsRow,
  type NutrientKey,
  NUTRIENT_KEYS,
  NUTRIENT_META,
  NUTRIENT_COLORS,
} from '@/composables/useRangeAverages'
import type { NormValues } from '@/composables/useNorms'

type TabKey = 'overview' | NutrientKey

const TABS: { key: TabKey; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  ...NUTRIENT_KEYS.map(k => ({ key: k as TabKey, label: NUTRIENT_META[k].label })),
]

const props = defineProps<{
  open: boolean
  days: DailyStatsRow[]
  effectiveLimitsByDate: Map<string, NormValues | null>
}>()

const emit = defineEmits<{ close: [] }>()

const activeTab = ref<TabKey>('overview')
const dialogRef = ref<HTMLElement | null>(null)
const closeButtonRef = ref<HTMLElement | null>(null)
let openerEl: HTMLElement | null = null

function onClose(): void {
  emit('close')
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape' && props.open) {
    e.preventDefault()
    onClose()
  }
}

function getFocusable(root: HTMLElement): HTMLElement[] {
  const sel = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  return Array.from(root.querySelectorAll<HTMLElement>(sel))
    .filter(el => !el.hasAttribute('disabled') && el.offsetParent !== null)
}

function onTabKey(e: KeyboardEvent): void {
  if (e.key !== 'Tab' || !dialogRef.value) return
  const focusables = getFocusable(dialogRef.value)
  if (focusables.length === 0) return
  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  const active = document.activeElement as HTMLElement | null
  if (e.shiftKey && active === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && active === last) {
    e.preventDefault()
    first.focus()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})

watch(
  () => props.open,
  async (v) => {
    if (v) {
      openerEl = document.activeElement as HTMLElement | null
      activeTab.value = 'overview'
      await nextTick()
      closeButtonRef.value?.focus()
    } else if (openerEl && typeof openerEl.focus === 'function') {
      openerEl.focus()
      openerEl = null
    }
  },
)

function daysWord(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'день'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'дні'
  return 'днів'
}
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/range-summary/ChartModal.vue
git commit -m "feat(frontend): add ChartModal with 9 tabs"
```

---

## Task 17: Create RangeAverageSummary block

**Files:**
- Create: `frontend/src/components/range-summary/RangeAverageSummary.vue`

- [ ] **Step 1: Implement block**

```vue
<!-- frontend/src/components/range-summary/RangeAverageSummary.vue -->
<template>
  <section class="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
    <header class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3 mb-4">
      <div class="min-w-0">
        <h2 class="text-sm font-semibold text-gray-900 leading-snug">
          Середнє за {{ rangeDayCount }} {{ daysWord(rangeDayCount) }}
        </h2>
        <p class="text-xs text-gray-500 mt-0.5">{{ rangeSubtitle }}</p>
        <p
          v-if="!loading && !error && skippedDayCount > 0 && includedDayCount > 0"
          class="text-[11px] text-amber-600 mt-1"
        >
          Враховано {{ includedDayCount }} з {{ rangeDayCount }} {{ daysWord(rangeDayCount) }} —
          {{ skippedDayCount }} {{ daysWord(skippedDayCount) }} без споживання пропущено.
        </p>
        <div class="flex gap-3 mt-1.5">
          <div class="flex items-center gap-1">
            <span class="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
            <span class="text-[10px] text-gray-400">±5%</span>
          </div>
          <div class="flex items-center gap-1">
            <span class="inline-block w-2 h-2 rounded-full bg-amber-500"></span>
            <span class="text-[10px] text-gray-400">≥80%</span>
          </div>
          <div class="flex items-center gap-1">
            <span class="inline-block w-2 h-2 rounded-full bg-red-500"></span>
            <span class="text-[10px] text-gray-400">&gt;105%</span>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <DateRangePicker
          :from="from"
          :to="to"
          :is-default="isDefault"
          @update:range="onRangeChange"
          @clear="clearRange"
        />
        <button
          type="button"
          class="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors shadow-sm"
          @click="openChart"
        >
          <BarChart2 :size="14" />
          Графіки
        </button>
      </div>
    </header>

    <div :class="{ 'opacity-50 pointer-events-none transition-opacity': loading && !firstLoading }">
      <div
        v-if="firstLoading"
        class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2"
      >
        <div
          v-for="i in 8"
          :key="i"
          class="h-[88px] rounded-lg bg-gray-100 animate-pulse"
        ></div>
      </div>
      <div
        v-else-if="error"
        class="text-sm text-red-600 px-3 py-6 text-center"
      >
        Не вдалося завантажити середнє: {{ error }}
      </div>
      <div
        v-else-if="includedDayCount === 0"
        class="text-sm text-gray-500 px-3 py-6 text-center"
      >
        Немає даних за обраний період.
      </div>
      <div
        v-else
        class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2"
      >
        <NutrientSummaryCard
          v-for="n in averages"
          :key="n.key"
          :label="n.label"
          :unit="n.unit"
          :avg="n.avg"
          :limit="n.limit"
          :less-is-better="n.lessIsBetter"
          :decimals="n.decimals"
          :limit-coverage-days="n.limitCoverageDays"
          :included-day-count="includedDayCount"
        />
      </div>
    </div>

    <ChartModal
      v-if="chartLoaded"
      :open="chartOpen"
      :days="days"
      :effective-limits-by-date="effectiveLimitsByDate"
      @close="chartOpen = false"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref, defineAsyncComponent } from 'vue'
import { storeToRefs } from 'pinia'
import { BarChart2 } from 'lucide-vue-next'
import { useHouseholdStore } from '@/store/household'
import { useDateRangeQuery } from '@/composables/useDateRangeQuery'
import { useRangeAverages } from '@/composables/useRangeAverages'
import NutrientSummaryCard from '@/components/NutrientSummaryCard.vue'
import DateRangePicker from './DateRangePicker.vue'

const ChartModal = defineAsyncComponent(() => import('./ChartModal.vue'))

const householdStore = useHouseholdStore()
const { selectedId } = storeToRefs(householdStore)
const householdIdRef = computed(() => selectedId.value ?? null)

const { from, to, isDefault, setRange, clearRange } = useDateRangeQuery()

const {
  averages,
  loading,
  firstLoading,
  error,
  days,
  effectiveLimitsByDate,
  includedDayCount,
  skippedDayCount,
  rangeDayCount,
} = useRangeAverages(householdIdRef, from, to)

const chartOpen = ref(false)
const chartLoaded = ref(false)
function openChart(): void {
  chartLoaded.value = true
  chartOpen.value = true
}

function onRangeChange(newFrom: string, newTo: string): void {
  setRange(newFrom, newTo)
}

const rangeSubtitle = computed(() => {
  const fmt = new Intl.DateTimeFormat('uk-UA', { day: 'numeric', month: 'short', year: 'numeric' })
  const f = new Date(from.value + 'T00:00:00')
  const t = new Date(to.value + 'T00:00:00')
  return `${fmt.format(f)} – ${fmt.format(t)}`
})

function daysWord(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'день'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'дні'
  return 'днів'
}
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/range-summary/RangeAverageSummary.vue
git commit -m "feat(frontend): add RangeAverageSummary top block"
```

---

## Task 18: Mount RangeAverageSummary on /consumed-stats

**Files:**
- Modify: `frontend/src/views/ConsumedProductsStatsView.vue`

- [ ] **Step 1: Add import and mount**

In `<script setup>`, add after the other component imports (around line 311):

```ts
import RangeAverageSummary from '@/components/range-summary/RangeAverageSummary.vue'
```

In the template, find the line `<div class="px-4 py-8 sm:px-0">` (around line 12) and insert the new block as the first child, before the existing `<div v-if="error">`:

```html
<div class="px-4 py-8 sm:px-0">
  <RangeAverageSummary class="mb-6" />

  <!-- Error -->
  <div
    v-if="error"
    class="bg-red-50 border-l-4 border-red-400 p-4 mb-6"
  >
    ...
```

- [ ] **Step 2: Verify in browser**

User starts the stack, visits `/consumed-stats`. Block should appear above the table; the table should keep its existing behavior (clicks still open detail panel, pagination still works).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/ConsumedProductsStatsView.vue
git commit -m "feat(frontend): mount RangeAverageSummary on /consumed-stats"
```

---

## Task 19: Self-review pass

- [ ] **Step 1: Lint**

User runs: `make lint-fix-js` and `make lint-js`. Fix any reported issues.

- [ ] **Step 2: Type-check**

`make lint-js` runs `vue-tsc --noEmit` already. If TS errors appear in any new file, fix them inline.

- [ ] **Step 3: Manual smoke test**

User opens the stack and verifies:
- `/dashboard`: WeeklyAverageSummary still renders 7-day cards.
- `/consumed-stats`: new block appears at top with last-7-days default; picker opens flatpickr; selecting a range updates URL `?from&to`; cards re-render; "Графіки" button opens modal; tabs render charts; Escape closes modal; refresh keeps the range; clearing the range returns to default.
- The existing daily-nutrients table is unchanged below the new block.

- [ ] **Step 4: Commit any lint/type fixes**

```bash
git add -u
git commit -m "chore(frontend): lint and type fixes for range-summary"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** All 32 grilled decisions are reflected — URL-driven range with last-7 default, hard 365-day cap inside `useDateRangeQuery`, AbortController-cancelled fetches, health-profile fallback per-nutrient (re-derived locally on params change — no refetch), "M з N" hint, lazy-loaded chart modal with 9 tabs (Overview line + 8 bar charts) using `chartjs-plugin-annotation` for reference lines, shared `NUTRIENT_COLORS`/`STATS_FIELD`/`NORM_FIELD` exported from `useRangeAverages`, kept existing table untouched, scrollable bar chart for many days, transition fade+scale, Escape + backdrop close, focus trap + focus return on the modal, role=dialog/aria-modal, no scroll lock, no backend changes.
- [x] **Placeholder scan:** All steps contain actual code, file paths, and commands. No "TBD"/"implement later"/"add validation".
- [x] **Type consistency:** `NutrientKey`, `NutrientAverage`, `DailyStatsRow`, `NormValues` are imported consistently from `useRangeAverages`/`useNorms` across composable, modal, and chart components. `useDateRangeQuery` exposes `from/to/isDefault/setRange/clearRange` consistently. Method names match between Tasks 17 (`onRangeChange` → `setRange`, `clearRange`) and Tasks 3/13 (component's `@clear` and `@update:range`).
