import { defineStore } from 'pinia'
import axios from 'axios'
import { parseApiError } from '../utils/parseApiError'
import { useHouseholdStore } from './household'

interface Recipe {
  id: number
  grocy_id: number
  name: string
  created_at: string
  latest_servings: number | null
  latest_price_per_serving: number | null
  latest_calories: number | null
  latest_proteins: number | null
  latest_carbohydrates: number | null
  latest_fats: number | null
  latest_consumed_at: string | null
}

interface RecipesState {
  recipes: Recipe[]
  loading: boolean
  syncingAll: boolean
  syncingRecipes: Set<number>
  error: string
  successMessage: string
  total: number
  skip: number
  limit: number
  searchQuery: string
}

export const useRecipesStore = defineStore('recipes', {
  state: (): RecipesState => ({
    recipes: [],
    loading: false,
    syncingAll: false,
    syncingRecipes: new Set(),
    error: '',
    successMessage: '',
    total: 0,
    skip: 0,
    limit: 10,
    searchQuery: '',
  }),

  actions: {
    async load() {
      const householdStore = useHouseholdStore()
      if (!householdStore.selectedId) return

      this.loading = true
      this.error = ''

      try {
        const params: Record<string, string | number> = {
          skip: this.skip,
          limit: this.limit,
          household_id: householdStore.selectedId,
        }
        if (this.searchQuery.trim()) params.search = this.searchQuery.trim()

        const { data } = await axios.get('/api/recipes/list', { params })
        this.recipes = data.recipes
        this.total = data.total
      } catch (err) {
        this.error = parseApiError(err, 'Failed to load recipes')
      } finally {
        this.loading = false
      }
    },

    async syncAll() {
      const householdStore = useHouseholdStore()
      this.syncingAll = true
      this.error = ''
      this.successMessage = ''

      try {
        const { data } = await axios.post('/api/recipes/sync-all', null, {
          params: { household_id: householdStore.selectedId },
        })
        this.successMessage = data.message
        await this.load()
      } catch (err) {
        this.error = parseApiError(err, 'Failed to sync recipes')
      } finally {
        this.syncingAll = false
      }
    },

    async syncSingle(grocyId: number) {
      const householdStore = useHouseholdStore()
      this.syncingRecipes.add(grocyId)
      this.error = ''
      this.successMessage = ''

      try {
        const { data } = await axios.post(`/api/recipes/sync/${grocyId}`, null, {
          params: { household_id: householdStore.selectedId },
        })
        this.successMessage = data.message
        await this.load()
      } catch (err) {
        this.error = parseApiError(err, 'Failed to sync recipe')
      } finally {
        this.syncingRecipes.delete(grocyId)
      }
    },

    nextPage() {
      if (this.skip + this.limit < this.total) {
        this.skip += this.limit
        this.load()
      }
    },

    previousPage() {
      if (this.skip > 0) {
        this.skip = Math.max(0, this.skip - this.limit)
        this.load()
      }
    },

    search() {
      this.skip = 0
      this.load()
    },

    clearSearch() {
      this.searchQuery = ''
      this.skip = 0
      this.load()
    },
  },
})
