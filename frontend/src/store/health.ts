import { defineStore } from 'pinia'
import axios from 'axios'
import type { HealthParameters } from '../types/health'
import { parseApiError } from '../utils/parseApiError'

interface HealthState {
  params: HealthParameters | null
  loading: boolean
  error: string
  success: string
}

export const useHealthStore = defineStore('health', {
  state: (): HealthState => ({
    params: null,
    loading: false,
    error: '',
    success: '',
  }),

  actions: {
    async fetchHealthParams() {
      this.loading = true
      this.error = ''
      try {
        const { data } = await axios.get('/api/users/me/health')
        this.params = data
      } catch (err: any) {
        this.error = parseApiError(err, 'Failed to load health parameters')
      } finally {
        this.loading = false
      }
    },

    async updateHealthParams(data: Partial<HealthParameters>) {
      this.loading = true
      this.error = ''
      this.success = ''
      try {
        const { data: result } = await axios.put('/api/users/me/health', data)
        this.params = result
        this.success = 'Health parameters saved successfully'
      } catch (err: any) {
        this.error = parseApiError(err, 'Failed to save health parameters')
        throw err
      } finally {
        this.loading = false
      }
    },
  },
})
