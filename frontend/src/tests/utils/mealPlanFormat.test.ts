import { describe, it, expect } from 'vitest'
import {
  addDays,
  formatAmount,
  formatLocalDate,
  parseLocalDate,
  startOfWeek,
} from '@/utils/mealPlanFormat'

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

describe('formatLocalDate / parseLocalDate', () => {
  it('round-trips a local-midnight Date via YYYY-MM-DD', () => {
    const d = parseLocalDate('2026-05-13')
    expect(formatLocalDate(d)).toBe('2026-05-13')
    // The Date itself is at local midnight, not UTC midnight.
    expect(d.getHours()).toBe(0)
    expect(d.getMinutes()).toBe(0)
  })

  it('formatLocalDate pads month and day to two digits', () => {
    expect(formatLocalDate(new Date(2026, 0, 5))).toBe('2026-01-05')
  })

  it('parseLocalDate produces the same calendar date the user typed', () => {
    const d = parseLocalDate('2026-01-01')
    expect(d.getFullYear()).toBe(2026)
    expect(d.getMonth()).toBe(0)
    expect(d.getDate()).toBe(1)
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
