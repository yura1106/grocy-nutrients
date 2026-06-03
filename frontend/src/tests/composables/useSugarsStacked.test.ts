/**
 * Unit tests for buildSugarsStackedView — the data-shaping behind the stacked
 * fresh-vs-harmful sugars chart. Pure logic, no Chart.js / canvas.
 */
import { describe, it, expect } from 'vitest'
import { buildSugarsStackedView } from '@/composables/useSugarsStacked'
import type { DailyStatsRow } from '@/composables/useRangeAverages'
import type { NormValues } from '@/composables/useNorms'

const makeDay = (overrides: Partial<DailyStatsRow> = {}): DailyStatsRow => ({
  date: '2024-09-01',
  total_calories: 0,
  total_carbohydrates: 0,
  total_carbohydrates_of_sugars: 0,
  total_fresh_sugars: 0,
  total_proteins: 0,
  total_fats: 0,
  total_fats_saturated: 0,
  total_salt: 0,
  total_fibers: 0,
  products_count: 1,
  total_cost: null,
  ...overrides,
})

describe('buildSugarsStackedView', () => {
  it('splits harmful and fresh sugars per day', () => {
    const view = buildSugarsStackedView(
      [makeDay({ total_carbohydrates_of_sugars: 20, total_fresh_sugars: 10 })],
      new Map(),
    )
    expect(view.harmful).toEqual([20])
    expect(view.fresh).toEqual([10])
  })

  it('keeps only consumed days, oldest-first', () => {
    const view = buildSugarsStackedView(
      [
        makeDay({ date: '2024-09-03', total_carbohydrates_of_sugars: 3 }),
        makeDay({ date: '2024-09-02', products_count: 0, total_carbohydrates_of_sugars: 99 }),
        makeDay({ date: '2024-09-01', total_carbohydrates_of_sugars: 1 }),
      ],
      new Map(),
    )
    expect(view.days.map(d => d.date)).toEqual(['2024-09-01', '2024-09-03'])
    expect(view.harmful).toEqual([1, 3])
  })

  it('treats a missing total_fresh_sugars as 0', () => {
    const day = makeDay({ total_carbohydrates_of_sugars: 5 }) as Record<string, unknown>
    delete day.total_fresh_sugars
    const view = buildSugarsStackedView([day as DailyStatsRow], new Map())
    expect(view.fresh).toEqual([0])
  })

  it('averages the per-day sugar limit across days that have one', () => {
    const limits = new Map<string, NormValues | null>([
      ['2024-09-01', { daily_carbohydrates_of_sugars: 40 } as NormValues],
      ['2024-09-02', { daily_carbohydrates_of_sugars: 60 } as NormValues],
    ])
    const view = buildSugarsStackedView(
      [
        makeDay({ date: '2024-09-01', total_carbohydrates_of_sugars: 10 }),
        makeDay({ date: '2024-09-02', total_carbohydrates_of_sugars: 10 }),
      ],
      limits,
    )
    expect(view.avgLimit).toBe(50)
  })

  it('returns null avgLimit when no day has a limit', () => {
    const view = buildSugarsStackedView(
      [makeDay({ total_carbohydrates_of_sugars: 10 })],
      new Map(),
    )
    expect(view.avgLimit).toBeNull()
  })

  it('computes average harmful and fresh', () => {
    const view = buildSugarsStackedView(
      [
        makeDay({ date: '2024-09-01', total_carbohydrates_of_sugars: 10, total_fresh_sugars: 4 }),
        makeDay({ date: '2024-09-02', total_carbohydrates_of_sugars: 20, total_fresh_sugars: 6 }),
      ],
      new Map(),
    )
    expect(view.avgHarmful).toBe(15)
    expect(view.avgFresh).toBe(5)
  })
})
