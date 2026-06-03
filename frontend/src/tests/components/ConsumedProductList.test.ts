/**
 * Unit tests for src/components/ConsumedProductList.vue
 *
 * Focus on the fresh-products behavior:
 * - the fresh toggle emits Product.id (product_id), NOT the consumed-row id
 *   (this was the bug that made the "Свіжий" checkbox silently fail to persist)
 * - recipe-sourced rows show a "counts toward total" hint
 * - excluded (fresh + standalone) rows tag their sugars as "свіжі"
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ConsumedProductList from '@/components/ConsumedProductList.vue'

const makeProduct = (overrides: Record<string, unknown> = {}) => ({
  id: 1,
  product_id: 1,
  product_name: 'Banana',
  quantity: 120,
  recipe_grocy_id: null,
  is_fresh: false,
  cost: null,
  total_calories: 100,
  total_proteins: 1,
  total_carbohydrates: 25,
  total_carbohydrates_of_sugars: 12,
  total_fats: 0,
  total_fats_saturated: 0,
  total_salt: 0,
  total_fibers: 2,
  ...overrides,
})

describe('ConsumedProductList — fresh toggle', () => {
  it('emits product_id (not the consumed-row id) when the checkbox is toggled', async () => {
    // Consumed-row id (5) differs from the Product.id (42): the PATCH must target 42.
    const product = makeProduct({ id: 5, product_id: 42, is_fresh: false })
    const wrapper = mount(ConsumedProductList, {
      props: { products: [product], freshToggleable: true },
    })

    const checkbox = wrapper.find('input[type="checkbox"]')
    expect(checkbox.exists()).toBe(true)
    await checkbox.setValue(true)

    const emitted = wrapper.emitted('fresh-toggled')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toEqual({ product_id: 42, is_fresh: true })
  })

  it('does not render the toggle when freshToggleable is false', () => {
    const wrapper = mount(ConsumedProductList, {
      props: { products: [makeProduct()], freshToggleable: false },
    })
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(false)
  })
})

describe('ConsumedProductList — recipe vs standalone', () => {
  it('shows the "з рецепта" hint for recipe-sourced rows', () => {
    const wrapper = mount(ConsumedProductList, {
      props: {
        products: [makeProduct({ recipe_grocy_id: 7, is_fresh: true })],
        freshToggleable: true,
      },
    })
    expect(wrapper.text()).toContain('з рецепта')
  })

  it('does not show the recipe hint for standalone rows', () => {
    const wrapper = mount(ConsumedProductList, {
      props: {
        products: [makeProduct({ recipe_grocy_id: null, is_fresh: true })],
        freshToggleable: true,
      },
    })
    expect(wrapper.text()).not.toContain('з рецепта')
  })

  it('tags sugars as "свіжі" only for fresh standalone rows', () => {
    const excluded = mount(ConsumedProductList, {
      props: {
        products: [makeProduct({ is_fresh: true, recipe_grocy_id: null })],
        freshToggleable: true,
      },
    })
    expect(excluded.text()).toContain('свіжі')

    const recipeFresh = mount(ConsumedProductList, {
      props: {
        products: [makeProduct({ is_fresh: true, recipe_grocy_id: 7 })],
        freshToggleable: true,
      },
    })
    expect(recipeFresh.text()).not.toContain('свіжі')

    const nonFresh = mount(ConsumedProductList, {
      props: {
        products: [makeProduct({ is_fresh: false, recipe_grocy_id: null })],
        freshToggleable: true,
      },
    })
    expect(nonFresh.text()).not.toContain('свіжі')
  })
})
