// frontend/src/tests/components/MealPlanLineRow.test.ts
//
// Covers the nutrition math in MealPlanLineRow — especially the bug where
// products stocked in a non-gram unit (e.g. bread → piece) were under-counted
// because the math only converted amount → stock units, not amount → grams.
// The fix multiplies by stock_to_grams_ml as well; these tests pin that.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MealPlanLineRow from '@/components/MealPlanLineRow.vue'
import type { DraftLine, ProductOption, RecipeOption } from '@/components/MealPlanLineRow.vue'
import type { MealPlanSection, MealPlanUnit } from '@/types/mealPlan'

const section: MealPlanSection = { section_id: 1, name: 'Сніданок', sort_number: 1 }

const gramUnit: MealPlanUnit = {
  qu_id: 82,
  name: 'Грам',
  name_plural: null,
  is_stock_default: false,
  factor_to_stock: 1.0,
}

// For a bread slice (30g each) the resolved conversions endpoint returns
// "1 g = 0.0333 piece" when to_qu_id is the stock unit (piece).
const gramUnitForPieceStock: MealPlanUnit = {
  qu_id: 82,
  name: 'Грам',
  name_plural: null,
  is_stock_default: false,
  factor_to_stock: 0.0333333,
}

const pieceUnit: MealPlanUnit = {
  qu_id: 102,
  name: 'Шт',
  name_plural: null,
  is_stock_default: true,
  factor_to_stock: 1.0,
}

const breadProduct: ProductOption = {
  grocy_id: 546,
  name: 'Хліб',
  calories: 2.77, // per 1 g of real weight (process_calories normalizes to g/ml)
  proteins: 0.09,
  carbohydrates: 0.52,
  carbohydrates_of_sugars: 0.04,
  fats: 0.04,
  fats_saturated: 0.01,
  fibers: 0.06,
}

const creamProduct: ProductOption = {
  grocy_id: 200,
  name: 'Вершки',
  calories: 3.2, // per 1 ml (stock = ml, so no normalization needed)
  proteins: 0.02,
  carbohydrates: 0.03,
  carbohydrates_of_sugars: 0.03,
  fats: 0.33,
  fats_saturated: 0.2,
  fibers: 0,
}

const mountRow = (overrides: {
  draft?: Partial<DraftLine>
  units?: MealPlanUnit[]
  stockToGrams?: number | null
}) => {
  const draft: DraftLine = {
    clientId: 'test-row',
    type: 'product',
    productOption: null,
    recipeOption: null,
    amount: null,
    unit: null,
    section,
    note: null,
    collapsed: false,
    ...(overrides.draft || {}),
  }
  return mount(MealPlanLineRow, {
    props: {
      draft,
      sections: [section],
      productOptions: [],
      recipeOptions: [],
      units: overrides.units ?? [],
      stockToGrams: overrides.stockToGrams ?? null,
    },
  })
}

describe('MealPlanLineRow nutrition math', () => {
  it('computes nutrition for a g/ml-stocked product (cream)', () => {
    // 122 ml of cream at 3.2 kcal/ml → ~390 kcal
    const wrapper = mountRow({
      draft: {
        type: 'product',
        productOption: creamProduct,
        recipeOption: null,
        amount: 122,
        unit: { ...gramUnit, name: 'Мілілітр' },
        section,
      },
      units: [{ ...gramUnit, name: 'Мілілітр' }],
      stockToGrams: 1.0,
    })
    const text = wrapper.text()
    expect(text).toContain('~390 kcal')
    expect(text).toContain('40.3g F') // 122 * 0.33 ≈ 40.26 → 40.3
  })

  it('computes nutrition for a piece-stocked product when user enters grams (BUG-FIX REGRESSION)', () => {
    // Bread stocked in pieces (1 piece ≈ 30 g). User enters 22 g.
    // Math: 22 × 0.0333 × 30 = 22 grams of real weight.
    // kcal = 2.77 × 22 ≈ 60.94
    const wrapper = mountRow({
      draft: {
        type: 'product',
        productOption: breadProduct,
        recipeOption: null,
        amount: 22,
        unit: gramUnitForPieceStock,
        section,
      },
      units: [gramUnitForPieceStock, pieceUnit],
      stockToGrams: 30,
    })
    const text = wrapper.text()
    expect(text).toContain('~61 kcal') // Math.round(60.94)
  })

  it('computes nutrition for a piece-stocked product when user enters pieces', () => {
    // Same bread, user picks "Шт" (stock unit) and enters 1.
    // Math: 1 × 1 × 30 = 30 grams. kcal = 2.77 × 30 = 83.1.
    const wrapper = mountRow({
      draft: {
        type: 'product',
        productOption: breadProduct,
        recipeOption: null,
        amount: 1,
        unit: pieceUnit,
        section,
      },
      units: [gramUnitForPieceStock, pieceUnit],
      stockToGrams: 30,
    })
    expect(wrapper.text()).toContain('~83 kcal')
  })

  it('hides nutrition and surfaces a yellow tag when stockToGrams is null', () => {
    // No stock→g/ml conversion → we cannot compute nutrition. Previously this
    // silently used 1 as the multiplier and produced confidently-wrong totals
    // (would have shown ~320 kcal). Now nutrition is suppressed and the row
    // shows an explicit "no nutrition data" tag so the user knows before
    // saving.
    const wrapper = mountRow({
      draft: {
        type: 'product',
        productOption: creamProduct,
        recipeOption: null,
        amount: 100,
        unit: gramUnit,
        section,
      },
      units: [gramUnit],
      stockToGrams: null,
    })
    const text = wrapper.text()
    expect(text).not.toContain('kcal')
    expect(text).toContain('Нема даних нутрієнтів')
  })

  it('renders nothing for the nutrition footer when amount is missing', () => {
    const wrapper = mountRow({
      draft: {
        type: 'product',
        productOption: breadProduct,
        recipeOption: null,
        amount: null,
        unit: gramUnit,
        section,
      },
      units: [gramUnit],
      stockToGrams: 30,
    })
    expect(wrapper.text()).not.toContain('kcal')
  })

  it('computes recipe nutrition by simple servings multiplication', () => {
    const recipe: RecipeOption = {
      grocy_id: 9,
      name: 'Смузі',
      latest_calories: 511,
      latest_proteins: 32.3,
      latest_carbohydrates: 70.1,
      latest_carbohydrates_of_sugars: 52.6,
      latest_fats: 13.0,
      latest_fats_saturated: 6.3,
      latest_fibers: 15.9,
    }
    const wrapper = mountRow({
      draft: {
        type: 'recipe',
        productOption: null,
        recipeOption: recipe,
        amount: 2,
        unit: null,
        section,
      },
      units: [],
      stockToGrams: null,
    })
    const text = wrapper.text()
    expect(text).toContain('~1022 kcal') // 511 * 2
    expect(text).toContain('64.6g P') // 32.3 * 2
  })

  it('shows sub-nutrients (sugars under carbs, sat under fats)', () => {
    const wrapper = mountRow({
      draft: {
        type: 'product',
        productOption: creamProduct,
        recipeOption: null,
        amount: 100,
        unit: gramUnit,
        section,
      },
      units: [gramUnit],
      stockToGrams: 1.0,
    })
    const text = wrapper.text()
    expect(text).toContain('sugars')
    expect(text).toContain('sat')
    expect(text).toContain('fibers')
  })
})
