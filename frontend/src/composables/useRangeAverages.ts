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
      // Cancel any in-flight request and clear loading flags so consumers
      // mounted with householdId=null don't see a stuck spinner/skeleton.
      if (activeController) {
        activeController.abort()
        activeController = null
      }
      days.value = []
      rawLimitsByDate.value = new Map()
      effectiveLimitsByDate.value = new Map()
      averages.value = []
      includedDayCount.value = 0
      skippedDayCount.value = 0
      rangeDayCount.value = 0
      loading.value = false
      firstLoading.value = false
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

const MONTHS_SHORT_UK = [
  'січ', 'лют', 'бер', 'кв', 'трав', 'черв',
  'лип', 'серп', 'вер', 'жовт', 'лист', 'груд',
]

export function formatDayShortUk(isoDate: string): string {
  const [, m, d] = isoDate.split('-')
  return `${parseInt(d, 10)} ${MONTHS_SHORT_UK[parseInt(m, 10) - 1]}`
}
