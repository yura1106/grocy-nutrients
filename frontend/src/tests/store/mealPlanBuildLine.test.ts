import { describe, it, expect } from 'vitest'
import { buildNoteLine, buildProductLine, buildRecipeLine } from '@/store/mealPlan'
import type { MealPlanUnit } from '@/types/mealPlan'

const gramOfBread: MealPlanUnit = {
  qu_id: 82,
  name: 'Грам',
  name_plural: null,
  is_stock_default: false,
  // 1 g of bread = 1/350 of a "пачка" (the product's stock unit).
  factor_to_stock: 1 / 350,
}

const packOfBread: MealPlanUnit = {
  qu_id: 85,
  name: 'Пачка',
  name_plural: null,
  is_stock_default: true,
  factor_to_stock: 1,
}

describe('buildProductLine', () => {
  it('converts user-entered grams to stock units (the Grocy UI behaviour)', () => {
    const line = buildProductLine({
      day: '2026-05-13',
      section_id: 2,
      product_grocy_id: 546,
      amount: 22,
      unit: gramOfBread,
    })

    expect(line.type).toBe('product')
    expect(line.product_grocy_id).toBe(546)
    expect(line.product_qu_id).toBe(82)
    expect(line.product_amount).toBe('22')
    // 22 / 350 ≈ 0.0628571428...
    expect(Number(line.product_amount_stock)).toBeCloseTo(0.06286, 4)
  })

  it('keeps amount unchanged when entered in the stock unit', () => {
    const line = buildProductLine({
      day: '2026-05-13',
      section_id: 2,
      product_grocy_id: 546,
      amount: 1,
      unit: packOfBread,
    })

    expect(line.product_amount).toBe('1')
    expect(Number(line.product_amount_stock)).toBe(1)
    expect(line.product_qu_id).toBe(85)
  })
})

describe('buildRecipeLine', () => {
  it('produces a recipe line with no product fields', () => {
    const line = buildRecipeLine({
      day: '2026-05-13',
      section_id: 3,
      recipe_grocy_id: 75,
      servings: 2,
    })

    expect(line.type).toBe('recipe')
    expect(line.recipe_grocy_id).toBe(75)
    expect(line.recipe_servings).toBe('2')
    expect(line.product_grocy_id).toBeUndefined()
    expect(line.product_amount_stock).toBeUndefined()
    expect(line.product_qu_id).toBeUndefined()
  })
})

describe('buildNoteLine', () => {
  it('produces a note line with only day/section/note fields', () => {
    const line = buildNoteLine({
      day: '2026-05-20',
      section_id: 2,
      note: 'buy bread',
    })

    expect(line.type).toBe('note')
    expect(line.day).toBe('2026-05-20')
    expect(line.section_id).toBe(2)
    expect(line.note).toBe('buy bread')
    expect(line.product_grocy_id).toBeUndefined()
    expect(line.recipe_grocy_id).toBeUndefined()
  })
})
