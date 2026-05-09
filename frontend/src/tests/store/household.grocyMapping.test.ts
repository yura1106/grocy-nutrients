/**
 * Tests for the new Grocy-mapping actions/state on the household Pinia store.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import axios from 'axios'
import { useHouseholdStore } from '@/store/household'

vi.mock('axios', () => {
  const mockAxios = {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    defaults: { withCredentials: false, headers: { common: {} as Record<string, string> } },
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  }
  return { default: mockAxios }
})

const mockedAxios = vi.mocked(axios, true)

describe('household store — Grocy mapping', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('has null grocyMappingRegistry', () => {
      const store = useHouseholdStore()
      expect(store.grocyMappingRegistry).toBeNull()
    })

    it('has null missingSettingKey', () => {
      const store = useHouseholdStore()
      expect(store.missingSettingKey).toBeNull()
    })
  })

  describe('fetchGrocyMappingRegistry', () => {
    it('GETs the registry and stores the result', async () => {
      const store = useHouseholdStore()
      mockedAxios.get.mockResolvedValueOnce({
        data: [
          { key: 'gram_unit_id', type: 'int' },
          { key: 'ml_unit_id', type: 'int' },
          { key: 'portion_unit_id', type: 'int' },
        ],
      })

      const result = await store.fetchGrocyMappingRegistry()

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/grocy-mapping/registry')
      expect(result).toHaveLength(3)
      expect(store.grocyMappingRegistry).toHaveLength(3)
    })

    it('caches the registry — second call does not hit the network', async () => {
      const store = useHouseholdStore()
      mockedAxios.get.mockResolvedValueOnce({
        data: [{ key: 'gram_unit_id', type: 'int' }],
      })

      await store.fetchGrocyMappingRegistry()
      await store.fetchGrocyMappingRegistry()

      expect(mockedAxios.get).toHaveBeenCalledTimes(1)
    })

    it('returns null on error and leaves state untouched', async () => {
      const store = useHouseholdStore()
      mockedAxios.get.mockRejectedValueOnce(new Error('boom'))

      const result = await store.fetchGrocyMappingRegistry()

      expect(result).toBeNull()
      expect(store.grocyMappingRegistry).toBeNull()
    })
  })

  describe('getGrocyMapping', () => {
    it('GETs from the household-scoped path', async () => {
      const store = useHouseholdStore()
      mockedAxios.get.mockResolvedValueOnce({
        data: [{ key: 'gram_unit_id', value: '82' }],
      })

      const items = await store.getGrocyMapping(7)

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/households/7/grocy-mapping')
      expect(items).toEqual([{ key: 'gram_unit_id', value: '82' }])
    })
  })

  describe('updateGrocyMapping', () => {
    it('PUTs the items wrapped in {items: ...}', async () => {
      const store = useHouseholdStore()
      const items = [
        { key: 'gram_unit_id', value: '82' },
        { key: 'ml_unit_id', value: '85' },
        { key: 'portion_unit_id', value: '9' },
      ]
      mockedAxios.put.mockResolvedValueOnce({ data: items })

      const result = await store.updateGrocyMapping(3, items)

      expect(mockedAxios.put).toHaveBeenCalledWith('/api/households/3/grocy-mapping', { items })
      expect(result).toEqual(items)
    })
  })

  describe('getGrocyQuantityUnits', () => {
    it('GETs with household_id query param', async () => {
      const store = useHouseholdStore()
      mockedAxios.get.mockResolvedValueOnce({
        data: [
          { id: 82, name: 'g' },
          { id: 85, name: 'ml' },
        ],
      })

      const units = await store.getGrocyQuantityUnits(11)

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/api/households/grocy/quantity-units?household_id=11',
      )
      expect(units).toEqual([
        { id: 82, name: 'g' },
        { id: 85, name: 'ml' },
      ])
    })
  })

  describe('setMissingSetting', () => {
    it('stores the key', () => {
      const store = useHouseholdStore()
      store.setMissingSetting('gram_unit_id')
      expect(store.missingSettingKey).toBe('gram_unit_id')
    })

    it('clears with null', () => {
      const store = useHouseholdStore()
      store.setMissingSetting('ml_unit_id')
      store.setMissingSetting(null)
      expect(store.missingSettingKey).toBeNull()
    })
  })

  describe('clear', () => {
    it('resets grocyMappingRegistry and missingSettingKey', () => {
      const store = useHouseholdStore()
      store.grocyMappingRegistry = [{ key: 'gram_unit_id', type: 'int' }]
      store.missingSettingKey = 'gram_unit_id'

      store.clear()

      expect(store.grocyMappingRegistry).toBeNull()
      expect(store.missingSettingKey).toBeNull()
    })
  })
})
