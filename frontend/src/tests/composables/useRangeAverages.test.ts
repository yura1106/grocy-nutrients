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
