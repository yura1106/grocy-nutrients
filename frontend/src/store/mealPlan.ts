import { defineStore } from 'pinia'
import axios from 'axios'
import { parseApiError } from '../utils/parseApiError'
import { useHouseholdStore } from './household'
import type {
  MealPlanJobStatus,
  MealPlanLine,
  MealPlanLineCreate,
  MealPlanSection,
  MealPlanUnit,
} from '../types/mealPlan'

/**
 * Convert a product draft's user-entered amount into stock units (what Grocy
 * actually stores). Mirrors Grocy UI behaviour: the form shows `22 Грам` but
 * POSTs `product_amount=0.0667` (in packs, the product's stock unit).
 */
export function buildProductLine(args: {
  day: string
  section_id: number
  product_grocy_id: number
  amount: number
  unit: MealPlanUnit
}): MealPlanLineCreate {
  const stockAmount = args.amount * args.unit.factor_to_stock
  return {
    type: 'product',
    day: args.day,
    section_id: args.section_id,
    product_id: args.product_grocy_id,
    product_amount: String(args.amount),
    product_amount_stock: String(stockAmount),
    product_qu_id: args.unit.qu_id,
    product_qu_name: args.unit.name,
  }
}

export function buildRecipeLine(args: {
  day: string
  section_id: number
  recipe_grocy_id: number
  servings: number
}): MealPlanLineCreate {
  return {
    type: 'recipe',
    day: args.day,
    section_id: args.section_id,
    recipe_id: args.recipe_grocy_id,
    recipe_servings: String(args.servings),
  }
}

interface MealPlanState {
  lines: MealPlanLine[]
  loading: boolean
  error: string
  currentJob: MealPlanJobStatus | null
  sections: MealPlanSection[]
  unitsByProduct: Record<number, MealPlanUnit[]>
  stockToGramsByProduct: Record<number, number | null>
  pollHandle: number | null
  pollBackoffMs: number
}

const POLL_INTERVAL_MS = 1500
const POLL_BACKOFF_CAP_MS = 12000

export const useMealPlanStore = defineStore('mealPlan', {
  state: (): MealPlanState => ({
    lines: [],
    loading: false,
    error: '',
    currentJob: null,
    sections: [],
    unitsByProduct: {},
    stockToGramsByProduct: {},
    pollHandle: null,
    pollBackoffMs: POLL_INTERVAL_MS,
  }),

  getters: {
    linesByDay(state): Record<string, MealPlanLine[]> {
      const grouped: Record<string, MealPlanLine[]> = {}
      for (const l of state.lines) {
        if (!grouped[l.day]) grouped[l.day] = []
        grouped[l.day].push(l)
      }
      return grouped
    },
    linesByDayAndSection(state): Record<string, Record<number, MealPlanLine[]>> {
      const grouped: Record<string, Record<number, MealPlanLine[]>> = {}
      for (const l of state.lines) {
        if (!grouped[l.day]) grouped[l.day] = {}
        if (!grouped[l.day][l.section_id]) grouped[l.day][l.section_id] = []
        grouped[l.day][l.section_id].push(l)
      }
      return grouped
    },
  },

  actions: {
    _hh(): number | null {
      return useHouseholdStore().selectedId
    },

    async loadRange(start: string, end: string) {
      const household_id = this._hh()
      if (!household_id) return
      this.loading = true
      this.error = ''
      try {
        const { data } = await axios.get<MealPlanLine[]>('/api/meal-plan/lines', {
          params: { household_id, start_date: start, end_date: end },
        })
        this.lines = data
      } catch (err) {
        this.error = parseApiError(err, 'Failed to load meal plan')
      } finally {
        this.loading = false
      }
    },

    async submit(lines: MealPlanLineCreate[]) {
      const household_id = this._hh()
      if (!household_id) return null
      this.error = ''
      try {
        const { data } = await axios.post<{ task_id: string; line_ids: number[] }>(
          '/api/meal-plan/lines',
          { lines },
          { params: { household_id } },
        )
        this.currentJob = {
          task_id: data.task_id,
          state: 'PENDING',
          current: 0,
          total: data.line_ids.length,
          errors: [],
          summary: null,
          error: null,
        }
        // Optimistically reload to surface the new pending rows.
        await this._reloadAroundLines(lines)
        this._startPolling()
        return data
      } catch (err) {
        this.error = parseApiError(err, 'Failed to submit meal plan')
        throw err
      }
    },

    async _reloadAroundLines(lines: MealPlanLineCreate[]) {
      if (!lines.length) return
      const days = lines.map((l) => l.day).sort()
      await this.loadRange(days[0], days[days.length - 1])
    },

    _startPolling() {
      this._stopPolling()
      this.pollBackoffMs = POLL_INTERVAL_MS
      this.pollHandle = window.setTimeout(() => this._pollJobOnce(), POLL_INTERVAL_MS)
    },

    _stopPolling() {
      if (this.pollHandle !== null) {
        window.clearTimeout(this.pollHandle)
        this.pollHandle = null
      }
    },

    async _pollJobOnce() {
      if (!this.currentJob) return
      const taskId = this.currentJob.task_id
      try {
        const { data } = await axios.get<MealPlanJobStatus>(
          `/api/meal-plan/job/${taskId}`,
        )
        this.currentJob = data
        this.pollBackoffMs = POLL_INTERVAL_MS

        if (data.state === 'SUCCESS' || data.state === 'FAILURE') {
          // Final reload pulls in synced/failed status updates.
          if (this.lines.length) {
            const days = this.lines.map((l) => l.day).sort()
            await this.loadRange(days[0], days[days.length - 1])
          }
          this._stopPolling()
          return
        }

        this.pollHandle = window.setTimeout(() => this._pollJobOnce(), POLL_INTERVAL_MS)
      } catch {
        this.pollBackoffMs = Math.min(this.pollBackoffMs * 2, POLL_BACKOFF_CAP_MS)
        if (this.pollBackoffMs >= POLL_BACKOFF_CAP_MS) {
          this.error = 'Lost connection to job status. Stopping polling.'
          this._stopPolling()
          return
        }
        this.pollHandle = window.setTimeout(() => this._pollJobOnce(), this.pollBackoffMs)
      }
    },

    async retry(lineId: number) {
      const household_id = this._hh()
      if (!household_id) return
      try {
        const { data } = await axios.post<{ line: MealPlanLine }>(
          `/api/meal-plan/lines/${lineId}/retry`,
          null,
          { params: { household_id } },
        )
        const idx = this.lines.findIndex((l) => l.id === lineId)
        if (idx !== -1) this.lines[idx] = data.line
      } catch (err) {
        this.error = parseApiError(err, 'Retry failed')
      }
    },

    async deleteLocal(lineId: number) {
      const household_id = this._hh()
      if (!household_id) return
      try {
        await axios.delete(`/api/meal-plan/lines/${lineId}/local`, {
          params: { household_id },
        })
        this.lines = this.lines.filter((l) => l.id !== lineId)
      } catch (err) {
        this.error = parseApiError(err, 'Delete failed')
      }
    },

    async loadSections() {
      const household_id = this._hh()
      if (!household_id) return
      try {
        const { data } = await axios.get<{ sections: MealPlanSection[] }>(
          '/api/meal-plan/sections',
          { params: { household_id } },
        )
        this.sections = data.sections.map((s) =>
          s.section_id === -1 && !s.name ? { ...s, name: '— Не обрано —' } : s,
        )
      } catch (err) {
        this.error = parseApiError(err, 'Failed to load sections')
      }
    },

    async loadUnitsForProduct(productId: number): Promise<MealPlanUnit[]> {
      const household_id = this._hh()
      if (!household_id) return []
      const cached = this.unitsByProduct[productId]
      if (cached) return cached
      try {
        const { data } = await axios.get<{
          units: MealPlanUnit[]
          stock_to_grams_ml: number | null
        }>('/api/meal-plan/units', {
          params: { household_id, product_id: productId },
        })
        this.unitsByProduct[productId] = data.units
        this.stockToGramsByProduct[productId] = data.stock_to_grams_ml
        return data.units
      } catch (err) {
        this.error = parseApiError(err, 'Failed to load units')
        return []
      }
    },
  },
})
