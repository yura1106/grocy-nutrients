import { defineStore } from 'pinia'
import axios from 'axios'
import { parseApiError } from '../utils/parseApiError'
import { useHouseholdStore } from './household'
import type {
  DayCheckStatusResponse,
  MealPlanDailyTotals,
  MealPlanJobStatus,
  MealPlanLine,
  MealPlanLineCreate,
  MealPlanLineEdit,
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
    product_grocy_id: args.product_grocy_id,
    product_amount: String(args.amount),
    product_amount_stock: String(stockAmount),
    product_qu_id: args.unit.qu_id,
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
    recipe_grocy_id: args.recipe_grocy_id,
    recipe_servings: String(args.servings),
  }
}

interface MealPlanState {
  lines: MealPlanLine[]
  loading: boolean
  error: string
  currentJob: MealPlanJobStatus | null
  // The visible date range currently held in `lines`. Used to decide whether
  // a completed job's reload still applies after the user navigates away.
  currentRange: { start: string; end: string } | null
  sections: MealPlanSection[]
  unitsByProduct: Record<number, MealPlanUnit[]>
  stockToGramsByProduct: Record<number, number | null>
  pollHandle: number | null
  pollBackoffMs: number
  totalsByDay: Record<string, MealPlanDailyTotals | null>
  totalsLoadingByDay: Record<string, boolean>
  totalsErrorByDay: Record<string, string>
  // Single-day availability check (background). Keyed by date; today is the
  // only day with a button, so at most one is in flight at a time — hence one
  // global polling handle.
  dayCheckByDate: Record<string, DayCheckStatusResponse>
  dayCheckPollHandle: number | null
  dayCheckPollingDate: string | null
  dayCheckBackoffMs: number
}

const POLL_INTERVAL_MS = 1500
const POLL_BACKOFF_CAP_MS = 12000

export const useMealPlanStore = defineStore('mealPlan', {
  state: (): MealPlanState => ({
    lines: [],
    loading: false,
    error: '',
    currentJob: null,
    currentRange: null,
    sections: [],
    unitsByProduct: {},
    stockToGramsByProduct: {},
    pollHandle: null,
    pollBackoffMs: POLL_INTERVAL_MS,
    totalsByDay: {},
    totalsLoadingByDay: {},
    totalsErrorByDay: {},
    dayCheckByDate: {},
    dayCheckPollHandle: null,
    dayCheckPollingDate: null,
    dayCheckBackoffMs: POLL_INTERVAL_MS,
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
    /** True while a batch task is still pending/progressing. Consumed by the
     * modal to disable the Save button so concurrent batches don't trample
     * each other's progress state. */
    isBatchInFlight(state): boolean {
      const job = state.currentJob
      if (!job) return false
      return job.state === 'PENDING' || job.state === 'PROGRESS'
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
      this.totalsByDay = {}
      this.totalsLoadingByDay = {}
      this.totalsErrorByDay = {}
      this.currentRange = { start, end }
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

    _invalidateTotalsForDay(day: string | null | undefined) {
      if (!day) return
      this.totalsByDay[day] = null
      delete this.totalsErrorByDay[day]
    },

    async fetchDailyTotals(day: string) {
      const household_id = this._hh()
      if (!household_id) return
      this.totalsLoadingByDay[day] = true
      delete this.totalsErrorByDay[day]
      try {
        const { data } = await axios.get<MealPlanDailyTotals>(
          '/api/meal-plan/daily-totals',
          { params: { household_id, day } },
        )
        this.totalsByDay[day] = data
      } catch (err) {
        this.totalsErrorByDay[day] = parseApiError(err, 'Failed to load totals')
      } finally {
        this.totalsLoadingByDay[day] = false
      }
    },

    async submit(lines: MealPlanLineCreate[]) {
      const household_id = this._hh()
      if (!household_id) return null
      if (this.isBatchInFlight) {
        this.error = 'Another batch is still syncing. Wait for it to finish before saving again.'
        throw new Error('batch_in_flight')
      }
      this.error = ''
      const submittedDays = Array.from(new Set(lines.map((l) => l.day))).sort()
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
          submitted_days: submittedDays,
        }
        // Optimistically reload to surface the new pending rows.
        // Reload the full visible range so other days don't disappear from the
        // UI while the user is still in this view. loadRange itself wipes
        // totalsByDay, so no explicit invalidation here.
        await this._reloadVisibleRange()
        this._startPolling()
        return data
      } catch (err) {
        this.error = parseApiError(err, 'Failed to submit meal plan')
        throw err
      }
    },

    async _reloadVisibleRange() {
      const range = this.currentRange
      if (!range) return
      await this.loadRange(range.start, range.end)
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
      const submittedDays = this.currentJob.submitted_days
      try {
        const { data } = await axios.get<MealPlanJobStatus>(
          `/api/meal-plan/job/${taskId}`,
        )
        // Preserve the client-side submitted_days through the server response,
        // which does not echo it back.
        this.currentJob = { ...data, submitted_days: submittedDays }
        this.pollBackoffMs = POLL_INTERVAL_MS

        if (data.state === 'SUCCESS' || data.state === 'FAILURE') {
          // Reload the full visible range (not just the submitted days) so
          // other days stay rendered. Skip when the user has navigated away
          // from a range that overlaps the submitted days — their new view's
          // loadRange will fetch fresh data on mount.
          if (submittedDays && submittedDays.length && this._rangeOverlaps(submittedDays)) {
            await this._reloadVisibleRange()
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

    _rangeOverlaps(days: string[]): boolean {
      const range = this.currentRange
      if (!range) return true // no current range tracked — be permissive
      const sorted = [...days].sort()
      const minDay = sorted[0]
      const maxDay = sorted[sorted.length - 1]
      return maxDay >= range.start && minDay <= range.end
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
        this._invalidateTotalsForDay(data.line.day)
      } catch (err) {
        this.error = parseApiError(err, 'Retry failed')
      }
    },

    async deleteLocal(lineId: number) {
      const household_id = this._hh()
      if (!household_id) return
      const target = this.lines.find((l) => l.id === lineId)
      try {
        await axios.delete(`/api/meal-plan/lines/${lineId}/local`, {
          params: { household_id },
        })
        this.lines = this.lines.filter((l) => l.id !== lineId)
        this._invalidateTotalsForDay(target?.day)
      } catch (err) {
        this.error = parseApiError(err, 'Delete failed')
      }
    },

    /** Edit a synced row's amount/servings. Backend PUTs to Grocy first; on
     * success replaces the local row and invalidates that day's totals.
     * Refuses while a batch is in flight (same gate as `submit`). Rethrows
     * on failure so the inline edit UI can show the error.
     */
    async editLine(lineId: number, patch: MealPlanLineEdit): Promise<void> {
      const household_id = this._hh()
      if (!household_id) return
      if (this.isBatchInFlight) {
        this.error = 'Batch sync in progress; please wait and retry.'
        throw new Error('batch_in_flight')
      }
      this.error = ''
      try {
        const { data } = await axios.patch<MealPlanLine>(
          `/api/meal-plan/lines/${lineId}`,
          patch,
          { params: { household_id } },
        )
        const idx = this.lines.findIndex((l) => l.id === lineId)
        if (idx !== -1) this.lines[idx] = data
        this._invalidateTotalsForDay(data.day)
      } catch (err) {
        this.error = parseApiError(err, 'Edit failed')
        throw err
      }
    },

    /** Delete a synced row: DELETE on Grocy, then drop locally. Refuses
     * while a batch is in flight. Rethrows on failure.
     */
    async deleteSynced(lineId: number): Promise<void> {
      const household_id = this._hh()
      if (!household_id) return
      if (this.isBatchInFlight) {
        this.error = 'Batch sync in progress; please wait and retry.'
        throw new Error('batch_in_flight')
      }
      this.error = ''
      const target = this.lines.find((l) => l.id === lineId)
      try {
        await axios.delete(`/api/meal-plan/lines/${lineId}`, {
          params: { household_id },
        })
        this.lines = this.lines.filter((l) => l.id !== lineId)
        this._invalidateTotalsForDay(target?.day)
      } catch (err) {
        this.error = parseApiError(err, 'Delete failed')
        throw err
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

    /** Force re-sync of every missing item in `missing_items[day]`, then
     * recompute totals. Used by the "Sync now" affordance on the day card
     * when the user wants to break out of the daily background-sync cadence
     * (e.g. they just created a product in Grocy and want it on today's
     * plan immediately).
     */
    async syncMissingForDay(day: string): Promise<void> {
      const household_id = this._hh()
      if (!household_id) return
      const totals = this.totalsByDay[day]
      if (!totals || !totals.missing_items.length) return

      const productIds = totals.missing_items
        .filter((m) => m.type === 'product')
        .map((m) => m.grocy_id)
      const recipeIds = totals.missing_items
        .filter((m) => m.type === 'recipe')
        .map((m) => m.grocy_id)

      const productCalls = productIds.map((gid) =>
        axios
          .post(`/api/sync/grocy-product/${gid}`, null, { params: { household_id } })
          .catch(() => null),
      )
      const recipeCalls = recipeIds.map((gid) =>
        axios
          .post(`/api/recipes/sync/${gid}`, null, { params: { household_id } })
          .catch(() => null),
      )
      await Promise.all([...productCalls, ...recipeCalls])
      // Also drop the unit cache for the affected products so a new
      // stock-unit conversion is fetched.
      for (const gid of productIds) {
        delete this.unitsByProduct[gid]
        delete this.stockToGramsByProduct[gid]
      }
      this._invalidateTotalsForDay(day)
      await this.fetchDailyTotals(day)
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
          params: { household_id, product_grocy_id: productId },
        })
        this.unitsByProduct[productId] = data.units
        this.stockToGramsByProduct[productId] = data.stock_to_grams_ml
        return data.units
      } catch (err) {
        this.error = parseApiError(err, 'Failed to load units')
        return []
      }
    },

    async fetchDayCheckStatus(date: string): Promise<void> {
      const household_id = this._hh()
      if (!household_id) return
      try {
        const { data } = await axios.get<DayCheckStatusResponse>(
          '/api/consumption/day-check/status',
          { params: { household_id, date } },
        )
        this.dayCheckByDate[date] = data
        if (data.state === 'PENDING' || data.state === 'PROGRESS') {
          this._startDayCheckPolling(date)
        }
      } catch {
        // Silently ignore — the check is a non-critical affordance.
      }
    },

    async triggerDayCheck(date: string): Promise<void> {
      const household_id = this._hh()
      if (!household_id) return
      try {
        const { data } = await axios.post<{ task_id: string; status: string }>(
          '/api/consumption/day-check',
          { date },
          { params: { household_id } },
        )
        // Optimistically reflect the queued state so the spinner shows up
        // before the first poll lands.
        this.dayCheckByDate[date] = {
          state: 'PENDING',
          task_id: data.task_id,
          date,
          outcome: null,
        }
        this._startDayCheckPolling(date)
      } catch (err) {
        this.error = parseApiError(err, 'Failed to start availability check')
      }
    },

    _startDayCheckPolling(date: string): void {
      this._stopDayCheckPolling()
      this.dayCheckPollingDate = date
      this.dayCheckBackoffMs = POLL_INTERVAL_MS
      this.dayCheckPollHandle = window.setTimeout(
        () => this._pollDayCheckOnce(),
        POLL_INTERVAL_MS,
      )
    },

    _stopDayCheckPolling(): void {
      if (this.dayCheckPollHandle !== null) {
        window.clearTimeout(this.dayCheckPollHandle)
        this.dayCheckPollHandle = null
      }
      this.dayCheckPollingDate = null
    },

    async _pollDayCheckOnce(): Promise<void> {
      const date = this.dayCheckPollingDate
      const household_id = this._hh()
      if (!date || !household_id) return
      try {
        const { data } = await axios.get<DayCheckStatusResponse>(
          '/api/consumption/day-check/status',
          { params: { household_id, date } },
        )
        this.dayCheckByDate[date] = data
        this.dayCheckBackoffMs = POLL_INTERVAL_MS

        if (data.state === 'SUCCESS' || data.state === 'FAILURE' || data.state === 'NONE') {
          this._stopDayCheckPolling()
          return
        }
        this.dayCheckPollHandle = window.setTimeout(
          () => this._pollDayCheckOnce(),
          POLL_INTERVAL_MS,
        )
      } catch {
        this.dayCheckBackoffMs = Math.min(this.dayCheckBackoffMs * 2, POLL_BACKOFF_CAP_MS)
        if (this.dayCheckBackoffMs >= POLL_BACKOFF_CAP_MS) {
          this._stopDayCheckPolling()
          return
        }
        this.dayCheckPollHandle = window.setTimeout(
          () => this._pollDayCheckOnce(),
          this.dayCheckBackoffMs,
        )
      }
    },

    async cancelDayCheck(date: string): Promise<void> {
      const household_id = this._hh()
      if (!household_id) return
      try {
        await axios.delete('/api/consumption/day-check', {
          params: { household_id, date, reason: 'cancelled' },
        })
        await this.fetchDayCheckStatus(date)
      } catch (err) {
        this.error = parseApiError(err, 'Failed to cancel check')
      }
    },

    async createDayCheckShoppingList(date: string): Promise<void> {
      const household_id = this._hh()
      if (!household_id) return
      const result = this.dayCheckByDate[date]?.result
      if (!result || !result.products_to_buy) return
      try {
        await axios.post(
          '/api/consumption/shopping-list',
          { date, products_to_buy: result.products_to_buy },
          { params: { household_id } },
        )
        await axios.delete('/api/consumption/day-check', {
          params: { household_id, date, reason: 'resolved' },
        })
        await this.fetchDayCheckStatus(date)
      } catch (err) {
        this.error = parseApiError(err, 'Failed to create shopping list')
      }
    },
  },
})
