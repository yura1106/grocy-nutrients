// frontend/src/tests/store/nutritionLimits.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useNutritionLimitsStore } from '@/store/nutritionLimits'
import axios from 'axios'

vi.mock('axios', () => {
  const mockAxios = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    defaults: { withCredentials: false, headers: { common: {} as Record<string, string> } },
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  }
  return { default: mockAxios, isAxiosError: (e: unknown) => e instanceof Error && 'isAxiosError' in e }
})

const mockedAxios = vi.mocked(axios, true)

const makeLimit = (id = 1, dateStr = '2026-03-27') => ({
  id,
  date: dateStr,
  calories_burned: 2500,
  body_weight: 80,
  activity_level: 'moderately_active',
  calories: 2125,
  proteins: 148,
  carbohydrates: 250,
  carbohydrates_of_sugars: 53,
  fats: 59,
  fats_saturated: 23,
  salt: 5.5,
  fibers: 29,
})

describe('NutritionLimits Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('fetchTodayLimit', () => {
    it('sets todayLimit on success', async () => {
      const limit = makeLimit()
      mockedAxios.get.mockResolvedValueOnce({ data: limit })
      const store = useNutritionLimitsStore()
      await store.fetchTodayLimit()
      expect(store.todayLimit).toEqual(limit)
    })

    it('sets todayLimit to null when API returns null', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: null })
      const store = useNutritionLimitsStore()
      await store.fetchTodayLimit()
      expect(store.todayLimit).toBeNull()
    })

    it('sets error on failure', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Network error'))
      const store = useNutritionLimitsStore()
      await store.fetchTodayLimit()
      expect(store.error).not.toBe('')
    })
  })

  describe('previewLimits', () => {
    it('stores preview result', async () => {
      const preview = {
        calories: 2000, proteins: 150, carbohydrates: 200,
        carbohydrates_of_sugars: 50, fats: 56, fats_saturated: 22,
        salt: 5, fibers: 28,
      }
      mockedAxios.post.mockResolvedValueOnce({ data: preview })
      const store = useNutritionLimitsStore()
      await store.previewLimits({ calories_burned: 2000, body_weight: 75, activity_level: 'sedentary' })
      expect(store.preview).toEqual(preview)
    })

    it('does not add preview to list', async () => {
      mockedAxios.post.mockResolvedValueOnce({ data: { calories: 2000 } })
      const store = useNutritionLimitsStore()
      await store.previewLimits({ calories_burned: 2000, body_weight: 75, activity_level: 'sedentary' })
      expect(store.list).toHaveLength(0)
    })
  })

  describe('createLimit', () => {
    it('prepends created record to list', async () => {
      const created = makeLimit(42)
      mockedAxios.post.mockResolvedValueOnce({ data: created })
      const store = useNutritionLimitsStore()
      await store.createLimit({ date: '2026-03-27' })
      expect(store.list[0]).toEqual(created)
      expect(store.total).toBe(1)
    })

    it('clears preview after create', async () => {
      mockedAxios.post.mockResolvedValueOnce({ data: makeLimit() })
      const store = useNutritionLimitsStore()
      store.preview = { calories: 2000, proteins: 150, carbohydrates: 200,
        carbohydrates_of_sugars: 50, fats: 56, fats_saturated: 22, salt: 5, fibers: 28 }
      await store.createLimit({ date: '2026-03-27' })
      expect(store.preview).toBeNull()
    })
  })

  describe('getLimitByDate getter', () => {
    it('returns matching limit by date', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: { items: [makeLimit(1, '2026-03-27'), makeLimit(2, '2026-03-26')], total: 2 },
      })
      const store = useNutritionLimitsStore()
      await store.fetchList()
      expect(store.getLimitByDate('2026-03-27')?.id).toBe(1)
      expect(store.getLimitByDate('2026-03-26')?.id).toBe(2)
    })

    it('returns undefined for unknown date', () => {
      const store = useNutritionLimitsStore()
      expect(store.getLimitByDate('2099-01-01')).toBeUndefined()
    })
  })
})
