import { describe, it, expect } from 'vitest'
import { addDays, formatAmount, startOfWeek } from '@/utils/mealPlanFormat'

describe('startOfWeek', () => {
  it('Wednesday 2026-05-13 → Monday 2026-05-11', () => {
    expect(startOfWeek('2026-05-13')).toBe('2026-05-11')
  })

  it('Monday is its own week start', () => {
    expect(startOfWeek('2026-05-11')).toBe('2026-05-11')
  })

  it('Sunday rolls back to the previous Monday (ISO week)', () => {
    expect(startOfWeek('2026-05-17')).toBe('2026-05-11')
  })
})

describe('addDays', () => {
  it('adds 6 days to a Monday → Sunday', () => {
    expect(addDays('2026-05-11', 6)).toBe('2026-05-17')
  })
})

describe('formatAmount', () => {
  it('strips trailing zeros from whole numbers', () => {
    expect(formatAmount('22.000000')).toBe('22')
    expect(formatAmount(22)).toBe('22')
  })

  it('keeps up to 3 significant fractional digits', () => {
    expect(formatAmount('0.062857')).toBe('0.063')
    expect(formatAmount(0.067)).toBe('0.067')
  })

  it('returns empty string for null/undefined', () => {
    expect(formatAmount(null)).toBe('')
    expect(formatAmount(undefined)).toBe('')
  })
})
