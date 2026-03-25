/**
 * Unit tests for src/components/DayDetailContent.vue
 *
 * Tests for daily nutrition stats display:
 * - rendering with empty data
 * - nutrient display in the header
 * - product list
 * - notes section
 * - number formatting
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DayDetailContent from '@/components/DayDetailContent.vue'

// Test data factory with sensible defaults
const makeDetail = (overrides: Record<string, unknown> = {}) => ({
  date: '2024-03-01',
  products: [] as never[],
  notes: [] as never[],
  total_calories: 0,
  total_carbohydrates: 0,
  total_carbohydrates_of_sugars: 0,
  total_proteins: 0,
  total_fats: 0,
  total_fats_saturated: 0,
  total_salt: 0,
  total_fibers: 0,
  total_cost: null,
  ...overrides,
})

const makeProduct = (overrides: Record<string, unknown> = {}) => ({
  id: 1,
  product_name: 'Chicken Breast',
  quantity: 200,
  recipe_grocy_id: null,
  cost: null,
  total_calories: 330,
  total_proteins: 62,
  total_carbohydrates: 0,
  total_carbohydrates_of_sugars: 0,
  total_fats: 7,
  total_fats_saturated: 2,
  total_salt: 0.3,
  total_fibers: 0,
  ...overrides,
})

const makeNote = (overrides: Record<string, unknown> = {}) => ({
  id: 1,
  note: 'Protein shake',
  calories: 200,
  proteins: 30,
  carbohydrates: 10,
  carbohydrates_of_sugars: 5,
  fats: 3,
  fats_saturated: 1,
  salt: 0.1,
  fibers: 2,
  ...overrides,
})

describe('DayDetailContent', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('rendering with empty data', () => {
    it('renders without errors with empty data', () => {
      const wrapper = mount(DayDetailContent, {
        props: { detail: makeDetail() },
      })
      expect(wrapper.exists()).toBe(true)
    })

    it('always displays the nutrient header', () => {
      const wrapper = mount(DayDetailContent, {
        props: { detail: makeDetail() },
      })
      // Stats header is always visible
      expect(wrapper.find('.bg-indigo-50').exists()).toBe(true)
    })

    it('does NOT display the product list when products is empty', () => {
      const wrapper = mount(DayDetailContent, {
        props: { detail: makeDetail({ products: [] }) },
      })
      // v-if="detail.products.length > 0" directive hides the list
      const productDivs = wrapper.findAll('.divide-y')
      const hasProductList = productDivs.some((el) => !el.element.closest('.border-t'))
      expect(hasProductList).toBe(false)
    })

    it('does NOT display the notes section when notes is empty', () => {
      const wrapper = mount(DayDetailContent, {
        props: { detail: makeDetail({ notes: [] }) },
      })
      expect(wrapper.text()).not.toContain('Notes')
    })
  })

  describe('nutrient header', () => {
    it('displays the total calorie count', () => {
      const wrapper = mount(DayDetailContent, {
        props: { detail: makeDetail({ total_calories: 2150.5 }) },
      })
      expect(wrapper.text()).toContain('2150.5')
    })

    it('displays the kcal label', () => {
      const wrapper = mount(DayDetailContent, {
        props: { detail: makeDetail() },
      })
      expect(wrapper.text()).toContain('kcal')
    })

    it('displays the protein label', () => {
      const wrapper = mount(DayDetailContent, {
        props: { detail: makeDetail() },
      })
      expect(wrapper.text()).toContain('protein')
    })

    it('displays the carbs label', () => {
      const wrapper = mount(DayDetailContent, {
        props: { detail: makeDetail() },
      })
      expect(wrapper.text()).toContain('carbs')
    })

    it('displays the fats label', () => {
      const wrapper = mount(DayDetailContent, {
        props: { detail: makeDetail() },
      })
      expect(wrapper.text()).toContain('fats')
    })

    it('formats numbers to one decimal place', () => {
      // fmt() uses .toFixed(1) → 1234.567 → "1234.6"
      const wrapper = mount(DayDetailContent, {
        props: { detail: makeDetail({ total_calories: 1234.567 }) },
      })
      expect(wrapper.text()).toContain('1234.6')
    })

    it('displays zero for empty data', () => {
      const wrapper = mount(DayDetailContent, {
        props: { detail: makeDetail({ total_calories: 0 }) },
      })
      expect(wrapper.text()).toContain('0.0')
    })
  })

  describe('product list', () => {
    it('displays the product list when products is non-empty', () => {
      const detail = makeDetail({ products: [makeProduct()] })
      const wrapper = mount(DayDetailContent, { props: { detail } })
      expect(wrapper.text()).toContain('Chicken Breast')
    })

    it('displays the name of each product', () => {
      const detail = makeDetail({
        products: [
          makeProduct({ id: 1, product_name: 'Apple' }),
          makeProduct({ id: 2, product_name: 'Banana' }),
        ],
      })
      const wrapper = mount(DayDetailContent, { props: { detail } })
      expect(wrapper.text()).toContain('Apple')
      expect(wrapper.text()).toContain('Banana')
    })

    it('displays product calories', () => {
      const detail = makeDetail({
        products: [makeProduct({ total_calories: 330 })],
      })
      const wrapper = mount(DayDetailContent, { props: { detail } })
      expect(wrapper.text()).toContain('330')
    })

    it('displays product quantity in fmtQty format', () => {
      // quantity = 200 → "200.0 g"
      const detail = makeDetail({
        products: [makeProduct({ quantity: 200 })],
      })
      const wrapper = mount(DayDetailContent, { props: { detail } })
      expect(wrapper.text()).toContain('200.0 g')
    })

    it('displays quantity in kg for large quantities', () => {
      // quantity = 1500 → "1.50 kg"
      const detail = makeDetail({
        products: [makeProduct({ quantity: 1500 })],
      })
      const wrapper = mount(DayDetailContent, { props: { detail } })
      expect(wrapper.text()).toContain('kg')
    })
  })

  describe('notes section', () => {
    it('displays the Notes section when notes exist', () => {
      const detail = makeDetail({ notes: [makeNote()] })
      const wrapper = mount(DayDetailContent, { props: { detail } })
      expect(wrapper.text()).toContain('Notes')
    })

    it('displays the note text', () => {
      const detail = makeDetail({
        notes: [makeNote({ note: 'Morning coffee' })],
      })
      const wrapper = mount(DayDetailContent, { props: { detail } })
      expect(wrapper.text()).toContain('Morning coffee')
    })

    it('displays note calories', () => {
      const detail = makeDetail({
        notes: [makeNote({ calories: 200 })],
      })
      const wrapper = mount(DayDetailContent, { props: { detail } })
      // Verify that the value 200 is displayed
      expect(wrapper.text()).toContain('200')
    })

    it('does NOT display a null note', () => {
      const detail = makeDetail({
        notes: [makeNote({ note: null })],
      })
      const wrapper = mount(DayDetailContent, { props: { detail } })
      // v-if="n.note" directive hides the element
      const noteText = wrapper.findAll('p').filter((el) =>
        el.classes().includes('italic'),
      )
      expect(noteText).toHaveLength(0)
    })
  })
})
