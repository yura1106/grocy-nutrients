import { defineStore } from 'pinia'
import axios from 'axios'

interface HouseholdOption {
  id: number
  name: string
  grocy_url: string | null
  role_name: string
}

interface HouseholdState {
  households: HouseholdOption[]
  selectedId: number | null
  loaded: boolean
}

export const useHouseholdStore = defineStore('household', {
  state: (): HouseholdState => {
    const stored = localStorage.getItem('selectedHouseholdId')
    const selectedId = stored ? parseInt(stored, 10) : null
    return { households: [], selectedId, loaded: false }
  },

  getters: {
    selected(): HouseholdOption | null {
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
      localStorage.removeItem('selectedHouseholdId')
    },
  },
})
