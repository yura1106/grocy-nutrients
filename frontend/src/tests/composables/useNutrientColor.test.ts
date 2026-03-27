import { describe, it, expect } from 'vitest'
import { productNutrientColor, productNutrientTextClass } from '@/composables/useNutrientColor'

describe('productNutrientColor', () => {
  it('returns NEUTRAL when norm is null', () => {
    expect(productNutrientColor(20, null).textClass).toBe('')
  })

  it('returns NEUTRAL when norm is 0', () => {
    expect(productNutrientColor(20, 0).textClass).toBe('')
  })

  it('returns NEUTRAL when value is 0', () => {
    expect(productNutrientColor(0, 50).textClass).toBe('')
  })

  it('returns NEUTRAL when share < 5%', () => {
    // 2 / 50 = 4%
    expect(productNutrientColor(2, 50).textClass).toBe('')
  })

  it('returns BLUE when share is exactly 5% (boundary >=)', () => {
    // 2.5 / 50 = 5%
    const result = productNutrientColor(2.5, 50)
    expect(result.textClass).toContain('blue')
  })

  it('returns BLUE when share is between 5% and 15%', () => {
    // 4 / 50 = 8%
    const result = productNutrientColor(4, 50)
    expect(result.textClass).toContain('blue')
  })

  it('returns AMBER when share is exactly 12% (boundary >=)', () => {
    // 6 / 50 = 12%
    const result = productNutrientColor(6, 50)
    expect(result.textClass).toContain('amber')
  })

  it('returns AMBER when share is between 12% and 20%', () => {
    // 8 / 50 = 16%
    const result = productNutrientColor(8, 50)
    expect(result.textClass).toContain('amber')
  })

  it('returns RED when share is exactly 20% (boundary >=)', () => {
    // 10 / 50 = 20%
    const result = productNutrientColor(10, 50)
    expect(result.textClass).toContain('red')
  })

  it('returns RED when share > 20%', () => {
    // 40 / 50 = 80%
    const result = productNutrientColor(40, 50)
    expect(result.textClass).toContain('red')
  })
})

describe('productNutrientTextClass', () => {
  it('returns empty string when norm is null', () => {
    expect(productNutrientTextClass(20, null)).toBe('')
  })

  it('returns amber class for 16% share', () => {
    // 8 / 50 = 16%
    expect(productNutrientTextClass(8, 50)).toContain('amber')
  })

  it('returns red class for 50% share', () => {
    // 25 / 50 = 50%
    expect(productNutrientTextClass(25, 50)).toContain('red')
  })
})
