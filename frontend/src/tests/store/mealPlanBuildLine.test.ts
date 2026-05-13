import { describe, it, expect } from 'vitest'
import { buildProductLine, buildRecipeLine } from '@/store/mealPlan'
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
    expect(line.product_id).toBe(546)
    expect(line.product_qu_id).toBe(82)
    expect(line.product_qu_name).toBe('Грам')
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
    expect(line.product_qu_name).toBe('Пачка')
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
    expect(line.recipe_id).toBe(75)
    expect(line.recipe_servings).toBe('2')
    expect(line.product_id).toBeUndefined()
    expect(line.product_amount_stock).toBeUndefined()
    expect(line.product_qu_name).toBeUndefined()
  })
})
