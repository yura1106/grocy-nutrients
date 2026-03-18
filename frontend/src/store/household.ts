import { defineStore } from 'pinia'
import axios from 'axios'
import type {
  HouseholdWithRole,
  HouseholdDetail,
  UserSearchItem,
  BackfillCounts,
  DataSummary,
} from '../types/household'

interface HouseholdState {
  households: HouseholdWithRole[]
  selectedId: number | null
  loaded: boolean
  householdDetails: Record<number, HouseholdDetail>
  backfillCounts: Record<number, BackfillCounts>
}

export const useHouseholdStore = defineStore('household', {
  state: (): HouseholdState => {
    const stored = localStorage.getItem('selectedHouseholdId')
    const selectedId = stored ? parseInt(stored, 10) : null
    return {
      households: [],
      selectedId,
      loaded: false,
      householdDetails: {},
      backfillCounts: {},
    }
  },

  getters: {
    selected(): HouseholdWithRole | null {
      return this.households.find((h) => h.id === this.selectedId) || null
    },
  },

  actions: {
    async fetchHouseholds() {
      try {
        const res = await axios.get('/api/households')
        this.households = res.data
        this.loaded = true

        // If stored selection is no longer valid, auto-select first
        if (this.selectedId && !this.households.find((h) => h.id === this.selectedId)) {
          this.selectedId = this.households.length > 0 ? this.households[0].id : null
        }
        // If nothing selected yet, pick the first one
        if (!this.selectedId && this.households.length > 0) {
          this.selectedId = this.households[0].id
        }

        this.persistSelection()
      } catch {
        this.households = []
        this.loaded = true
      }
    },

    async fetchHouseholdDetail(id: number) {
      const res = await axios.get(`/api/households/${id}`)
      this.householdDetails[id] = res.data
    },

    async createHousehold(data: { name: string; grocy_url: string | null; address: string | null }) {
      await axios.post('/api/households', data)
      await this.fetchHouseholds()
    },

    async updateHousehold(id: number, data: { name: string; grocy_url: string | null; address: string | null }) {
      await axios.patch(`/api/households/${id}`, data)
      await this.fetchHouseholds()
    },

    async deleteHousehold(id: number, data: { password: string; confirmation_text: string; export_data: boolean }) {
      await axios.delete(`/api/households/${id}`, { data })
      await this.fetchHouseholds()
    },

    async searchUsers(query: string): Promise<UserSearchItem[]> {
      const res = await axios.get(`/api/households/search-users?q=${encodeURIComponent(query)}`)
      return res.data
    },

    async addMember(householdId: number, userId: number, roleName: string) {
      await axios.post(`/api/households/${householdId}/users`, {
        user_id: userId,
        role_name: roleName,
      })
      await this.fetchHouseholdDetail(householdId)
    },

    async removeMember(householdId: number, userId: number) {
      await axios.delete(`/api/households/${householdId}/users/${userId}?confirm=true`)
    },

    async getUserDataSummary(householdId: number, userId: number): Promise<DataSummary> {
      try {
        const res = await axios.get(`/api/households/${householdId}/users/${userId}/data-summary`)
        return res.data
      } catch {
        return { consumed_products: 0, recipes_data: 0, meal_plan_consumptions: 0, note_nutrients: 0, daily_nutrition: 0, total: 0 }
      }
    },

    async fetchBackfillStatus(householdId: number) {
      try {
        const res = await axios.get(`/api/households/${householdId}/backfill-status`)
        this.backfillCounts[householdId] = res.data
      } catch {
        // If 403 or error, section won't render
      }
    },

    async runBackfill(householdId: number): Promise<{ updated_household_id: number; updated_user_id: number }> {
      const res = await axios.post(`/api/households/${householdId}/backfill`)
      await this.fetchBackfillStatus(householdId)
      return res.data
    },

    async syncProducts(householdId: number, onProgress?: (text: string) => void) {
      const CHUNK_SIZE = 50
      let offset = 0
      let totalProcessed = 0
      let totalUpdated = 0
      let total = 0

      while (true) {
        if (onProgress) {
          onProgress(total > 0 ? `Syncing... ${Math.min(offset, total)}/${total}` : 'Syncing...')
        }

        const response = await axios.post(
          `/api/sync/grocy-products?offset=${offset}&limit=${CHUNK_SIZE}&household_id=${householdId}`,
        )
        const data = response.data
        totalProcessed += data.processed
        totalUpdated += data.updated
        total = data.total || 0

        if (!data.has_more) break
        offset += CHUNK_SIZE
      }

      return { processed: totalProcessed, updated: totalUpdated }
    },

    async syncRecipes(householdId: number): Promise<{ processed: number; synced: number }> {
      const response = await axios.post(`/api/recipes/sync-all?household_id=${householdId}`)
      return response.data
    },

    async getGrocyKey(householdId: number): Promise<string | null> {
      try {
        const res = await axios.get(`/api/households/${householdId}/grocy-key`)
        return res.data.grocy_api_key || null
      } catch {
        return null
      }
    },

    async saveGrocyKey(householdId: number, key: string) {
      await axios.put(`/api/households/${householdId}/grocy-key`, { grocy_api_key: key })
      await this.fetchHouseholdDetail(householdId)
    },

    async fetchBackfillStatusForAdmins() {
      const adminHouseholds = this.households.filter(h => h.role_name === 'admin')
      await Promise.all(adminHouseholds.map(h => this.fetchBackfillStatus(h.id)))
    },

    select(id: number) {
      this.selectedId = id
      this.persistSelection()
    },

    persistSelection() {
      if (this.selectedId !== null) {
        localStorage.setItem('selectedHouseholdId', String(this.selectedId))
      } else {
        localStorage.removeItem('selectedHouseholdId')
      }
    },

    clear() {
      this.households = []
      this.selectedId = null
      this.loaded = false
      this.householdDetails = {}
      this.backfillCounts = {}
      localStorage.removeItem('selectedHouseholdId')
    },
  },
})
