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
    patch: vi.fn(),
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

  describe('toggleNoteDone', () => {
    it('POSTs done flag and replaces local line + invalidates totals', async () => {
      const store = useMealPlanStore()
      store.lines = [
        {
          id: 11,
          day: '2026-05-20',
          type: 'note',
          done: false,
          status: 'synced',
        } as unknown as (typeof store.lines)[number],
      ]
      store.totalsByDay['2026-05-20'] = {
        kcal: 200, protein: 0, carbs: 0, sugars: 0, fat: 0, sat_fat: 0, fibers: 0, missing_items: [],
      }
      mockedAxios.post.mockResolvedValueOnce({
        data: { id: 11, day: '2026-05-20', type: 'note', done: true, status: 'synced' },
      })

      await store.toggleNoteDone(11, true)

      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/meal-plan/lines/11/done',
        { done: true },
        { params: { household_id: 1 } },
      )
      expect(store.lines[0].done).toBe(true)
      expect(store.totalsByDay['2026-05-20']).toBeNull()
    })

    it('rethrows and sets store.error on failure', async () => {
      const store = useMealPlanStore()
      mockedAxios.post.mockRejectedValueOnce(new Error('boom'))
      await expect(store.toggleNoteDone(1, true)).rejects.toThrow()
      expect(store.error).toBeTruthy()
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

  describe('submit() — Q1 batch gating + Q2 submitted_days', () => {
    it('captures submitted_days from the lines payload', async () => {
      const store = useMealPlanStore()
      // submit issues an initial reload via _reloadVisibleRange → loadRange,
      // and starts polling via a timer that fires another GET. Stub both.
      mockedAxios.post.mockResolvedValueOnce({
        data: { task_id: 't-abc', line_ids: [1, 2] },
      })
      mockedAxios.get.mockResolvedValue({ data: [] })

      await store.submit([
        { type: 'product', day: '2026-05-13', section_id: 1 },
        { type: 'product', day: '2026-05-15', section_id: 1 },
        { type: 'product', day: '2026-05-13', section_id: 2 },
      ])

      expect(store.currentJob?.submitted_days).toEqual(['2026-05-13', '2026-05-15'])
      store._stopPolling()
    })

    it('rejects a second submit while a batch is in flight', async () => {
      const store = useMealPlanStore()
      // Seed an in-flight job manually rather than running submit() twice
      // (which would tangle the polling timer).
      store.currentJob = {
        task_id: 't-1',
        state: 'PROGRESS',
        current: 1,
        total: 5,
        errors: [],
        summary: null,
        error: null,
        submitted_days: ['2026-05-13'],
      }

      await expect(
        store.submit([{ type: 'product', day: '2026-05-13', section_id: 1 }]),
      ).rejects.toThrow('batch_in_flight')

      // No new POST should have been issued.
      expect(mockedAxios.post).not.toHaveBeenCalled()
      expect(store.error).toMatch(/another batch/i)
    })

    it('isBatchInFlight getter reflects PENDING/PROGRESS only', () => {
      const store = useMealPlanStore()
      expect(store.isBatchInFlight).toBe(false)

      store.currentJob = {
        task_id: 't',
        state: 'PENDING',
        current: 0,
        total: 1,
        errors: [],
        summary: null,
        error: null,
      }
      expect(store.isBatchInFlight).toBe(true)

      store.currentJob = { ...store.currentJob!, state: 'PROGRESS' }
      expect(store.isBatchInFlight).toBe(true)

      store.currentJob = { ...store.currentJob!, state: 'SUCCESS' }
      expect(store.isBatchInFlight).toBe(false)

      store.currentJob = { ...store.currentJob!, state: 'FAILURE' }
      expect(store.isBatchInFlight).toBe(false)
    })
  })

  describe('_rangeOverlaps — Q2 post-job reload guard', () => {
    it('returns true when submitted days fall inside currentRange', () => {
      const store = useMealPlanStore()
      store.currentRange = { start: '2026-05-13', end: '2026-05-19' }
      expect(store._rangeOverlaps(['2026-05-15'])).toBe(true)
    })

    it('returns false when submitted days are entirely after currentRange', () => {
      const store = useMealPlanStore()
      store.currentRange = { start: '2026-05-13', end: '2026-05-19' }
      expect(store._rangeOverlaps(['2026-05-20', '2026-05-21'])).toBe(false)
    })

    it('returns false when submitted days are entirely before currentRange', () => {
      const store = useMealPlanStore()
      store.currentRange = { start: '2026-05-13', end: '2026-05-19' }
      expect(store._rangeOverlaps(['2026-05-10'])).toBe(false)
    })

    it('is permissive when no current range is tracked', () => {
      const store = useMealPlanStore()
      store.currentRange = null
      expect(store._rangeOverlaps(['2026-05-13'])).toBe(true)
    })
  })

  describe('editLine — Group 3 edit synced row', () => {
    it('issues PATCH with patch body + household_id, replaces line, invalidates totals', async () => {
      const store = useMealPlanStore()
      store.lines = [
        // Stub the row with just the fields editLine reads.
        { id: 7, day: '2026-05-18' } as unknown as (typeof store.lines)[number],
      ]
      store.totalsByDay['2026-05-18'] = {
        kcal: 50, protein: 0, carbs: 0, sugars: 0, fat: 0, sat_fat: 0, fibers: 0, missing_items: [],
      }
      const updated = {
        id: 7,
        day: '2026-05-18',
        product_amount: '15',
        product_amount_stock: '15',
        status: 'synced',
      }
      mockedAxios.patch.mockResolvedValueOnce({ data: updated })

      await store.editLine(7, { product_amount: '15', product_amount_stock: '15' })

      expect(mockedAxios.patch).toHaveBeenCalledWith(
        '/api/meal-plan/lines/7',
        { product_amount: '15', product_amount_stock: '15' },
        { params: { household_id: 1 } },
      )
      expect(store.lines[0]).toEqual(updated)
      expect(store.totalsByDay['2026-05-18']).toBeNull()
    })

    it('throws batch_in_flight and does not call PATCH when a batch is running', async () => {
      const store = useMealPlanStore()
      store.currentJob = {
        task_id: 't',
        state: 'PROGRESS',
        current: 0,
        total: 1,
        errors: [],
        summary: null,
        error: null,
      }
      await expect(
        store.editLine(7, { recipe_servings: '2' }),
      ).rejects.toThrow('batch_in_flight')
      expect(mockedAxios.patch).not.toHaveBeenCalled()
    })

    it('rethrows on API error and leaves the existing line untouched', async () => {
      const store = useMealPlanStore()
      const original = {
        id: 7,
        day: '2026-05-18',
        product_amount: '10',
        product_amount_stock: '10',
        status: 'synced',
      } as unknown as (typeof store.lines)[number]
      store.lines = [original]
      mockedAxios.patch.mockRejectedValueOnce(new Error('502 boom'))

      await expect(
        store.editLine(7, { product_amount: '15', product_amount_stock: '15' }),
      ).rejects.toThrow('502 boom')
      expect(store.lines[0]).toEqual(original)
    })
  })

  describe('deleteSynced — Group 3 delete synced row', () => {
    it('issues DELETE with household_id, splices the row, invalidates totals', async () => {
      const store = useMealPlanStore()
      store.lines = [
        { id: 7, day: '2026-05-18' } as unknown as (typeof store.lines)[number],
        { id: 8, day: '2026-05-19' } as unknown as (typeof store.lines)[number],
      ]
      store.totalsByDay['2026-05-18'] = {
        kcal: 50, protein: 0, carbs: 0, sugars: 0, fat: 0, sat_fat: 0, fibers: 0, missing_items: [],
      }
      mockedAxios.delete.mockResolvedValueOnce({ data: {} })

      await store.deleteSynced(7)

      expect(mockedAxios.delete).toHaveBeenCalledWith(
        '/api/meal-plan/lines/7',
        { params: { household_id: 1 } },
      )
      expect(store.lines.map((l) => l.id)).toEqual([8])
      expect(store.totalsByDay['2026-05-18']).toBeNull()
    })

    it('throws batch_in_flight and does not call DELETE when a batch is running', async () => {
      const store = useMealPlanStore()
      store.currentJob = {
        task_id: 't',
        state: 'PENDING',
        current: 0,
        total: 1,
        errors: [],
        summary: null,
        error: null,
      }
      await expect(store.deleteSynced(7)).rejects.toThrow('batch_in_flight')
      expect(mockedAxios.delete).not.toHaveBeenCalled()
    })

    it('rethrows on API error and keeps the row in state.lines', async () => {
      const store = useMealPlanStore()
      const row = { id: 7, day: '2026-05-18' } as unknown as (typeof store.lines)[number]
      store.lines = [row]
      mockedAxios.delete.mockRejectedValueOnce(new Error('502 down'))

      await expect(store.deleteSynced(7)).rejects.toThrow('502 down')
      expect(store.lines).toEqual([row])
    })
  })
})
