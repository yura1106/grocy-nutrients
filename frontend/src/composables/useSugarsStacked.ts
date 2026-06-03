/**
 * Pure data-shaping for the stacked fresh-vs-harmful sugars chart.
 *
 * Kept out of the SFC so it can be unit-tested without mounting Chart.js
 * (which needs a canvas, unsupported in jsdom).
 */
import { type DailyStatsRow, NORM_FIELD } from '@/composables/useRangeAverages'
import type { NormValues } from '@/composables/useNorms'

export interface SugarsStackedView {
  /** Consumed days only, oldest-first. */
  days: DailyStatsRow[]
  /** Sugars that count toward the limit, per day. */
  harmful: number[]
  /** Fresh (excluded) sugars, per day; missing field treated as 0. */
  fresh: number[]
  /** Average per-day sugar limit across days that have one, or null. */
  avgLimit: number | null
  avgHarmful: number
  avgFresh: number
}

function average(arr: number[]): number {
  return arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0
}

export function buildSugarsStackedView(
  days: DailyStatsRow[],
  effectiveLimitsByDate: Map<string, NormValues | null>,
): SugarsStackedView {
  const consumed = [...days].filter(d => d.products_count > 0).reverse()
  const harmful = consumed.map(d => d.total_carbohydrates_of_sugars)
  const fresh = consumed.map(d => d.total_fresh_sugars ?? 0)

  let sum = 0
  let count = 0
  for (const d of consumed) {
    const v = effectiveLimitsByDate.get(d.date)?.[NORM_FIELD.carbohydrates_of_sugars] ?? null
    if (v != null) {
      sum += v
      count += 1
    }
  }
  const avgLimit = count > 0 ? sum / count : null

  return {
    days: consumed,
    harmful,
    fresh,
    avgLimit,
    avgHarmful: average(harmful),
    avgFresh: average(fresh),
  }
}
