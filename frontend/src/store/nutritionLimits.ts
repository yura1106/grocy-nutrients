import { defineStore } from 'pinia'
import axios from 'axios'
import type {
  NutritionLimit,
  NutrientLimitsPreview,
  NutritionLimitCreate,
  NutritionLimitUpdate,
  PreviewRequest,
} from '../types/nutritionLimit'
import { parseApiError } from '../utils/parseApiError'

interface NutritionLimitsState {
  todayLimit: NutritionLimit | null
  preview: NutrientLimitsPreview | null
  list: NutritionLimit[]
  total: number
  loading: boolean
  previewLoading: boolean
  error: string
}

export const useNutritionLimitsStore = defineStore('nutritionLimits', {
  state: (): NutritionLimitsState => ({
    todayLimit: null,
    preview: null,
    list: [],
    total: 0,
    loading: false,
    previewLoading: false,
    error: '',
  }),

  getters: {
    getLimitByDate: (state) => (dateStr: string): NutritionLimit | undefined =>
      state.list.find((l) => l.date === dateStr),
  },

  actions: {
    async fetchTodayLimit(today?: string) {
      this.loading = true
      this.error = ''
      try {
        const params = today ? { today } : {}
        const { data } = await axios.get('/api/nutrition-limits/today', { params })
        this.todayLimit = data
      } catch (err: unknown) {
        this.error = parseApiError(err, 'Failed to load today\'s limit')
      } finally {
        this.loading = false
      }
    },

    async fetchList(skip = 0, limit = 20, dateFrom?: string, dateTo?: string) {
      this.loading = true
      this.error = ''
      try {
        const params: Record<string, unknown> = { skip, limit }
        if (dateFrom) params.date_from = dateFrom
        if (dateTo) params.date_to = dateTo
        const { data } = await axios.get('/api/nutrition-limits', { params })
        this.list = data.items
        this.total = data.total
      } catch (err: unknown) {
        this.error = parseApiError(err, 'Failed to load limits list')
      } finally {
        this.loading = false
      }
    },

    async previewLimits(params: PreviewRequest) {
      this.previewLoading = true
      this.error = ''
      try {
        const { data } = await axios.post('/api/nutrition-limits/preview', params)
        this.preview = data
      } catch (err: unknown) {
        this.error = parseApiError(err, 'Preview failed')
      } finally {
        this.previewLoading = false
      }
    },

    async createLimit(data: NutritionLimitCreate) {
      this.loading = true
      this.error = ''
      try {
        const { data: created } = await axios.post('/api/nutrition-limits', data)
        this.preview = null
        await this.fetchList(0, 20)
        return created as NutritionLimit
      } catch (err: unknown) {
        this.error = parseApiError(err, 'Failed to create limit')
        throw err
      } finally {
        this.loading = false
      }
    },

    async updateLimit(id: number, data: NutritionLimitUpdate) {
      this.loading = true
      this.error = ''
      try {
        const { data: updated } = await axios.put(`/api/nutrition-limits/${id}`, data)
        const idx = this.list.findIndex((l) => l.id === id)
        if (idx !== -1) this.list[idx] = updated
        if (this.todayLimit?.id === id) this.todayLimit = updated
        return updated as NutritionLimit
      } catch (err: unknown) {
        this.error = parseApiError(err, 'Failed to update limit')
        throw err
      } finally {
        this.loading = false
      }
    },

    async deleteLimit(id: number) {
      this.loading = true
      this.error = ''
      try {
        await axios.delete(`/api/nutrition-limits/${id}`)
        this.list = this.list.filter((l) => l.id !== id)
        this.total -= 1
        if (this.todayLimit?.id === id) this.todayLimit = null
      } catch (err: unknown) {
        this.error = parseApiError(err, 'Failed to delete limit')
        throw err
      } finally {
        this.loading = false
      }
    },
  },
})
