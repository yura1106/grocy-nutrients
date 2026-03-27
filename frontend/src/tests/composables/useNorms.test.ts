// frontend/src/tests/composables/useNorms.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { ref } from 'vue'
import { useNorms } from '@/composables/useNorms'
import { useNutritionLimitsStore } from '@/store/nutritionLimits'
import { useHealthStore } from '@/store/health'

// useNorms only reads from stores — no axios needed
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

const makeLimit = (overrides = {}) => ({
  id: 1,
  date: '2026-03-27',
  calories_burned: null,
  body_weight: null,
  activity_level: null,
  calories: 2000,
  proteins: 150,
  carbohydrates: 200,
  carbohydrates_of_sugars: 50,
  fats: 56,
  fats_saturated: 22,
  salt: 5,
  fibers: 28,
  ...overrides,
})

const makeHealthParams = (overrides = {}) => ({
  gender: null,
  date_of_birth: null,
  height: null,
  weight: null,
  activity_level: null,
  goal: null,
  calorie_deficit_percent: null,
  daily_calories: 1800,
  daily_proteins: 120,
  daily_fats: 50,
  daily_fats_saturated: 18,
  daily_carbohydrates: 220,
  daily_carbohydrates_of_sugars: 45,
  daily_salt: 5,
  daily_fibers: 25,
  ...overrides,
})

describe('useNorms', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('no date arg — uses todayLimit', () => {
    it('returns todayLimit mapped to daily_* shape when todayLimit is set', () => {
      const limitsStore = useNutritionLimitsStore()
      limitsStore.todayLimit = makeLimit()
      const { norms } = useNorms()
      expect(norms.value?.daily_calories).toBe(2000)
      expect(norms.value?.daily_proteins).toBe(150)
    })

    it('falls back to healthStore.params when todayLimit is null', () => {
      const limitsStore = useNutritionLimitsStore()
      limitsStore.todayLimit = null
      const healthStore = useHealthStore()
      healthStore.params = makeHealthParams()
      const { norms } = useNorms()
      expect(norms.value?.daily_calories).toBe(1800)
      expect(norms.value?.daily_proteins).toBe(120)
    })

    it('returns null when both stores are empty', () => {
      const { norms } = useNorms()
      expect(norms.value).toBeNull()
    })
  })

  describe('with date arg — uses getLimitByDate', () => {
    it('returns limit for provided date', () => {
      const limitsStore = useNutritionLimitsStore()
      limitsStore.list = [makeLimit({ date: '2026-03-20', calories: 1900, proteins: 140 })]
      const date = ref('2026-03-20')
      const { norms } = useNorms(date)
      expect(norms.value?.daily_calories).toBe(1900)
      expect(norms.value?.daily_proteins).toBe(140)
    })

    it('falls back to healthStore.params when no record for that date', () => {
      const limitsStore = useNutritionLimitsStore()
      limitsStore.list = []
      const healthStore = useHealthStore()
      healthStore.params = makeHealthParams()
      const date = ref('2026-03-20')
      const { norms } = useNorms(date)
      expect(norms.value?.daily_calories).toBe(1800)
    })

    it('is reactive — updates when date ref changes', () => {
      const limitsStore = useNutritionLimitsStore()
      limitsStore.list = [
        makeLimit({ date: '2026-03-20', calories: 1900 }),
        makeLimit({ id: 2, date: '2026-03-21', calories: 2100 }),
      ]
      const date = ref('2026-03-20')
      const { norms } = useNorms(date)
      expect(norms.value?.daily_calories).toBe(1900)
      date.value = '2026-03-21'
      expect(norms.value?.daily_calories).toBe(2100)
    })
  })
})
