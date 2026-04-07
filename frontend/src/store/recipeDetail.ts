import { defineStore } from 'pinia'
import axios from 'axios'
import { parseApiError } from '../utils/parseApiError'
import { useHouseholdStore } from './household'

export interface RecipeHistoryItem {
  id: number
  servings: number
  weight_per_serving: number | null
  price_per_serving: number | null
  calories: number | null
  proteins: number | null
  carbohydrates: number | null
  carbohydrates_of_sugars: number | null
  fats: number | null
  fats_saturated: number | null
  salt: number | null
  fibers: number | null
  consumed_at: string
  consumed_date: string | null
  has_products: boolean
}

interface RecipeConsumedProductItem {
  id: number
  product_name: string
  quantity: number
  cost: number | null
  total_calories: number
  total_carbohydrates: number
  total_carbohydrates_of_sugars: number
  total_proteins: number
  total_fats: number
  total_fats_saturated: number
  total_salt: number
  total_fibers: number
}

interface RecipeConsumedProductsResponse {
  recipe_data_id: number
  products: RecipeConsumedProductItem[]
  total_cost: number | null
}

export interface RecipeDetail {
  id: number
  grocy_id: number
  name: string
  created_at: string
  history: RecipeHistoryItem[]
  total_history: number
}

interface RecipeDetailState {
  recipe: RecipeDetail | null
  loading: boolean
  error: string | null
  expandedRowId: number | null
  productsDetail: RecipeConsumedProductsResponse | null
  productsLoading: boolean
}

export const useRecipeDetailStore = defineStore('recipeDetail', {
  state: (): RecipeDetailState => ({
    recipe: null,
    loading: false,
    error: null,
    expandedRowId: null,
    productsDetail: null,
    productsLoading: false,
  }),

  getters: {
    averageCalories(state): number {
      if (!state.recipe || state.recipe.history.length === 0) return 0
      const total = state.recipe.history.reduce((sum, item) => sum + (item.calories || 0), 0)
      return total / state.recipe.history.length
    },

    averagePrice(state): number {
      if (!state.recipe || state.recipe.history.length === 0) return 0
      const items = state.recipe.history.filter(item => item.price_per_serving !== null)
      if (items.length === 0) return 0
      const total = items.reduce((sum, item) => sum + (item.price_per_serving || 0), 0)
      return total / items.length
    },

    expandedNutrients(state) {
      const item = state.recipe?.history.find(h => h.id === state.expandedRowId)
      if (!item) return null
      return {
        calories: item.calories ?? 0,
        proteins: item.proteins ?? 0,
        carbohydrates: item.carbohydrates ?? 0,
        carbohydrates_of_sugars: item.carbohydrates_of_sugars ?? 0,
        fats: item.fats ?? 0,
        fats_saturated: item.fats_saturated ?? 0,
        fibers: item.fibers ?? 0,
        salt: item.salt ?? 0,
        cost: state.productsDetail?.total_cost ?? null,
      }
    },
  },

  actions: {
    async load(recipeId: string | string[]) {
      const householdStore = useHouseholdStore()
      this.loading = true
      this.error = null
      this.expandedRowId = null
      this.productsDetail = null

      try {
        const { data } = await axios.get(`/api/recipes/${recipeId}`, {
          params: { household_id: householdStore.selectedId },
        })
        this.recipe = data
      } catch (err) {
        this.error = parseApiError(err, 'Failed to load recipe details')
      } finally {
        this.loading = false
      }
    },

    async toggleProducts(item: RecipeHistoryItem) {
      const householdStore = useHouseholdStore()
      if (!item.has_products) return
      if (this.expandedRowId === item.id) {
        this.expandedRowId = null
        this.productsDetail = null
        return
      }
      this.expandedRowId = item.id
      this.productsDetail = null
      this.productsLoading = true
      try {
        const { data } = await axios.get(`/api/recipes/data/${item.id}/products`, {
          params: { household_id: householdStore.selectedId },
        })
        this.productsDetail = data
      } catch (err) {
        this.error = parseApiError(err, 'Failed to load product details.')
        this.expandedRowId = null
      } finally {
        this.productsLoading = false
      }
    },

    reset() {
      this.recipe = null
      this.loading = false
      this.error = null
      this.expandedRowId = null
      this.productsDetail = null
      this.productsLoading = false
    },
  },
})
