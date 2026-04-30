import { ref, watch, type Ref } from 'vue'
import axios from 'axios'

export type NutrientKey =
  | 'calories'
  | 'carbohydrates'
  | 'carbohydrates_of_sugars'
  | 'proteins'
  | 'fats'
  | 'fats_saturated'
  | 'salt'
  | 'fibers'

export interface WeeklyAverage {
  key: NutrientKey
  label: string
  unit: string
  avg: number
  limit: number | null
  lessIsBetter: boolean
  decimals: number
}

interface NutrientMeta {
  label: string
  unit: string
  lessIsBetter: boolean
  decimals: number
}

interface DailyStatsRow {
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

interface StatsResponse {
  days: DailyStatsRow[]
  total: number
}

interface NutritionLimitRow {
  date: string
  calories: number | null
  carbohydrates: number | null
  carbohydrates_of_sugars: number | null
  proteins: number | null
  fats: number | null
  fats_saturated: number | null
  salt: number | null
  fibers: number | null
}

interface LimitsResponse {
  items: NutritionLimitRow[]
  total: number
}

const NUTRIENT_META: Record<NutrientKey, NutrientMeta> = {
  calories: { label: 'Калорії', unit: 'ккал', lessIsBetter: false, decimals: 0 },
  carbohydrates: { label: 'Вуглеводи', unit: 'г', lessIsBetter: false, decimals: 1 },
  carbohydrates_of_sugars: { label: 'Цукри', unit: 'г', lessIsBetter: true, decimals: 1 },
  proteins: { label: 'Білки', unit: 'г', lessIsBetter: false, decimals: 1 },
  fats: { label: 'Жири', unit: 'г', lessIsBetter: false, decimals: 1 },
  fats_saturated: { label: 'Насичені жири', unit: 'г', lessIsBetter: true, decimals: 1 },
  salt: { label: 'Сіль', unit: 'г', lessIsBetter: true, decimals: 2 },
  fibers: { label: 'Клітковина', unit: 'г', lessIsBetter: false, decimals: 1 },
}

const NUTRIENT_KEYS = Object.keys(NUTRIENT_META) as NutrientKey[]

const STATS_TOTAL_FIELD: Record<NutrientKey, keyof DailyStatsRow> = {
  calories: 'total_calories',
  carbohydrates: 'total_carbohydrates',
  carbohydrates_of_sugars: 'total_carbohydrates_of_sugars',
  proteins: 'total_proteins',
  fats: 'total_fats',
  fats_saturated: 'total_fats_saturated',
  salt: 'total_salt',
  fibers: 'total_fibers',
}

const WINDOW_DAYS = 7

function isoDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export interface UseWeeklyAveragesReturn {
  averages: Ref<WeeklyAverage[]>
  loading: Ref<boolean>
  error: Ref<string | null>
  windowDays: number
  includedDayCount: Ref<number>
  skippedDayCount: Ref<number>
  refresh: () => Promise<void>
}

export function useWeeklyAverages(
  householdId: Ref<number | null>,
): UseWeeklyAveragesReturn {
  const averages = ref<WeeklyAverage[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const includedDayCount = ref(0)
  const skippedDayCount = ref(0)

  const refresh = async (): Promise<void> => {
    const id = householdId.value
    if (id == null) {
      averages.value = []
      includedDayCount.value = 0
      skippedDayCount.value = 0
      return
    }

    loading.value = true
    error.value = null

    const today = new Date()
    const start = new Date(today)
    start.setDate(start.getDate() - (WINDOW_DAYS - 1))
    const dateFrom = isoDate(start)
    const dateTo = isoDate(today)

    try {
      const [statsRes, limitsRes] = await Promise.all([
        axios.get<StatsResponse>('/api/consumption/stats', {
          params: { household_id: id, date_from: dateFrom, date_to: dateTo },
        }),
        axios.get<LimitsResponse>('/api/nutrition-limits', {
          params: { date_from: dateFrom, date_to: dateTo, limit: WINDOW_DAYS },
        }),
      ])

      const days = statsRes.data.days
      const limitsByDate = new Map<string, NutritionLimitRow>()
      for (const row of limitsRes.data.items) {
        limitsByDate.set(row.date, row)
      }

      const daysWithConsumption = days.filter((d) => d.products_count > 0)
      includedDayCount.value = daysWithConsumption.length
      skippedDayCount.value = WINDOW_DAYS - daysWithConsumption.length

      const denominator = Math.max(daysWithConsumption.length, 1)

      averages.value = NUTRIENT_KEYS.map((key) => {
        const meta = NUTRIENT_META[key]
        const totalField = STATS_TOTAL_FIELD[key]

        const avg =
          daysWithConsumption.reduce((acc, d) => acc + (d[totalField] as number), 0) /
          denominator

        let limitSum = 0
        let limitDays = 0
        for (const d of daysWithConsumption) {
          const lim = limitsByDate.get(d.date)
          const v = lim?.[key]
          if (v != null) {
            limitSum += v
            limitDays += 1
          }
        }
        const limit = limitDays > 0 ? limitSum / limitDays : null

        return {
          key,
          label: meta.label,
          unit: meta.unit,
          avg,
          limit,
          lessIsBetter: meta.lessIsBetter,
          decimals: meta.decimals,
        }
      })
    } catch (e) {
      const msg = axios.isAxiosError(e)
        ? (e.response?.data?.detail ?? e.message)
        : e instanceof Error
          ? e.message
          : String(e)
      error.value = msg
      averages.value = []
      includedDayCount.value = 0
      skippedDayCount.value = 0
    } finally {
      loading.value = false
    }
  }

  watch(householdId, refresh, { immediate: true })

  return {
    averages,
    loading,
    error,
    windowDays: WINDOW_DAYS,
    includedDayCount,
    skippedDayCount,
    refresh,
  }
}
