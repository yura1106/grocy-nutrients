// frontend/src/tests/store/mealPlan.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import axios from 'axios'
import { useMealPlanStore } from '@/store/mealPlan'
import { useHouseholdStore } from '@/store/household'

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

describe('MealPlan Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    // Ensure a household is selected so the store doesn't short-circuit.
    const hh = useHouseholdStore()
    hh.selectedId = 1
  })

  describe('loadSections', () => {
    it('substitutes friendly label for section_id=-1 with empty name', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: {
          sections: [
            { section_id: -1, name: '', sort_number: null },
            { section_id: 1, name: 'Сніданок', sort_number: 1 },
          ],
        },
      })
      const store = useMealPlanStore()
      await store.loadSections()
      expect(store.sections).toEqual([
        { section_id: -1, name: '— Не обрано —', sort_number: null },
        { section_id: 1, name: 'Сніданок', sort_number: 1 },
      ])
    })

    it('leaves real section names untouched', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: {
          sections: [
            { section_id: 1, name: 'Сніданок', sort_number: 1 },
            { section_id: 2, name: 'Обід', sort_number: 2 },
          ],
        },
      })
      const store = useMealPlanStore()
      await store.loadSections()
      expect(store.sections.map((s) => s.name)).toEqual(['Сніданок', 'Обід'])
    })

    it('does not overwrite -1 section that already has a name from Grocy', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: {
          sections: [{ section_id: -1, name: 'Unsorted', sort_number: null }],
        },
      })
      const store = useMealPlanStore()
      await store.loadSections()
      expect(store.sections[0].name).toBe('Unsorted')
    })
  })

  describe('loadUnitsForProduct', () => {
    it('stores units and stock_to_grams_ml', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: {
          units: [
            { qu_id: 102, name: 'Шт', name_plural: null, is_stock_default: true, factor_to_stock: 1.0 },
            { qu_id: 82, name: 'Грам', name_plural: null, is_stock_default: false, factor_to_stock: 0.0333 },
          ],
          stock_to_grams_ml: 30,
        },
      })
      const store = useMealPlanStore()
      const units = await store.loadUnitsForProduct(546)
      expect(units).toHaveLength(2)
      expect(store.unitsByProduct[546]).toEqual(units)
      expect(store.stockToGramsByProduct[546]).toBe(30)
    })

    it('caches units and avoids a second network call', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: { units: [], stock_to_grams_ml: 1 },
      })
      const store = useMealPlanStore()
      await store.loadUnitsForProduct(10)
      await store.loadUnitsForProduct(10)
      expect(mockedAxios.get).toHaveBeenCalledTimes(1)
    })

    it('handles null stock_to_grams_ml (no conversion known)', async () => {
      mockedAxios.get.mockResolvedValueOnce({
        data: { units: [], stock_to_grams_ml: null },
      })
      const store = useMealPlanStore()
      await store.loadUnitsForProduct(99)
      expect(store.stockToGramsByProduct[99]).toBeNull()
    })
  })

  describe('fetchDailyTotals', () => {
    it('stores totals under totalsByDay[day]', async () => {
      const payload = {
        kcal: 1840,
        protein: 95,
        carbs: 210,
        sugars: 30,
        fat: 65,
        sat_fat: 20,
        fibers: 25,
        missing_items: [],
      }
      mockedAxios.get.mockResolvedValueOnce({ data: payload })
      const store = useMealPlanStore()
      await store.fetchDailyTotals('2026-05-13')
      expect(store.totalsByDay['2026-05-13']).toEqual(payload)
      expect(store.totalsLoadingByDay['2026-05-13']).toBe(false)
      expect(store.totalsErrorByDay['2026-05-13']).toBeUndefined()
    })

    it('records an error message when the request fails', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('boom'))
      const store = useMealPlanStore()
      await store.fetchDailyTotals('2026-05-13')
      expect(store.totalsByDay['2026-05-13']).toBeUndefined()
      expect(store.totalsErrorByDay['2026-05-13']).toBeTruthy()
    })
  })

  describe('totals invalidation', () => {
    it('clears totalsByDay when loadRange runs', async () => {
      const store = useMealPlanStore()
      store.totalsByDay['2026-05-13'] = {
        kcal: 1, protein: 0, carbs: 0, sugars: 0, fat: 0, sat_fat: 0, fibers: 0, missing_items: [],
      }
      mockedAxios.get.mockResolvedValueOnce({ data: [] })
      await store.loadRange('2026-05-13', '2026-05-19')
      expect(store.totalsByDay).toEqual({})
    })

    it('invalidates totals for the affected day when retry returns the updated line', async () => {
      const store = useMealPlanStore()
      store.totalsByDay['2026-05-13'] = {
        kcal: 99, protein: 0, carbs: 0, sugars: 0, fat: 0, sat_fat: 0, fibers: 0, missing_items: [],
      }
      mockedAxios.post.mockResolvedValueOnce({
        data: { line: { id: 1, day: '2026-05-13', status: 'pending' } },
      })
      await store.retry(1)
      expect(store.totalsByDay['2026-05-13']).toBeNull()
    })

    it('invalidates totals for the deleted line day', async () => {
      const store = useMealPlanStore()
      store.lines = [
        // Minimal stub — only the fields the action reads.
        { id: 42, day: '2026-05-14' } as unknown as (typeof store.lines)[number],
      ]
      store.totalsByDay['2026-05-14'] = {
        kcal: 77, protein: 0, carbs: 0, sugars: 0, fat: 0, sat_fat: 0, fibers: 0, missing_items: [],
      }
      mockedAxios.delete.mockResolvedValueOnce({ data: {} })
      await store.deleteLocal(42)
      expect(store.totalsByDay['2026-05-14']).toBeNull()
    })
  })
})
