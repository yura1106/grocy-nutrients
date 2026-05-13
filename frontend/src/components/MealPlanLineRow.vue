<script setup lang="ts">
import { computed, watch } from 'vue'
import AppCombobox from './ui/AppCombobox.vue'
import AppSelect from './ui/AppSelect.vue'
import type { MealPlanSection, MealPlanUnit } from '../types/mealPlan'

export interface DraftLine {
  type: 'product' | 'recipe'
  productOption: ProductOption | null
  recipeOption: RecipeOption | null
  amount: number | null
  unit: MealPlanUnit | null
  section: MealPlanSection | null
}

export interface ProductOption {
  grocy_id: number
  name: string
  calories: number | null
  proteins: number | null
  carbohydrates: number | null
  carbohydrates_of_sugars: number | null
  fats: number | null
  fats_saturated: number | null
  fibers: number | null
}

export interface RecipeOption {
  grocy_id: number
  name: string
  latest_calories: number | null
  latest_proteins: number | null
  latest_carbohydrates: number | null
  latest_carbohydrates_of_sugars: number | null
  latest_fats: number | null
  latest_fats_saturated: number | null
  latest_fibers: number | null
}

const props = defineProps<{
  draft: DraftLine
  sections: MealPlanSection[]
  productOptions: ProductOption[]
  recipeOptions: RecipeOption[]
  units: MealPlanUnit[]
  stockToGrams: number | null
  productLoading?: boolean
  recipeLoading?: boolean
}>()

const emit = defineEmits<{
  remove: []
  'product-selected': [productGrocyId: number]
  'update:draft': [draft: DraftLine]
  'update:product-query': [query: string]
  'update:recipe-query': [query: string]
}>()

function update(patch: Partial<DraftLine>) {
  emit('update:draft', { ...props.draft, ...patch })
}

const typeOptions = [
  { value: 'product', label: 'Product' },
  { value: 'recipe', label: 'Recipe' },
]
const selectedType = computed({
  get: () => typeOptions.find((o) => o.value === props.draft.type) || typeOptions[0],
  set: (val) => {
    update({
      type: val.value as 'product' | 'recipe',
      productOption: null,
      recipeOption: null,
      unit: null,
      amount: null,
    })
  },
})

watch(
  () => props.draft.productOption,
  (p) => {
    if (p) emit('product-selected', p.grocy_id)
  },
)

const stockUnit = computed(() => props.units.find((u) => u.is_stock_default) || null)
watch(
  () => props.units,
  (us) => {
    if (props.draft.type === 'product' && !props.draft.unit && us.length > 0) {
      update({ unit: us.find((u) => u.is_stock_default) || us[0] })
    }
  },
  { immediate: true },
)

const productOption = computed({
  get: () => props.draft.productOption,
  set: (v) => update({ productOption: v }),
})
const recipeOption = computed({
  get: () => props.draft.recipeOption,
  set: (v) => update({ recipeOption: v }),
})
const amount = computed({
  get: () => props.draft.amount,
  set: (v) => update({ amount: v }),
})
const unit = computed({
  get: () => props.draft.unit,
  set: (v) => update({ unit: v }),
})
const section = computed({
  get: () => props.draft.section,
  set: (v) => update({ section: v }),
})

const nutrition = computed(() => {
  if (props.draft.type === 'product') {
    const p = props.draft.productOption
    if (!p || props.draft.amount == null || props.draft.amount <= 0) return null
    const factorToStock = props.draft.unit?.factor_to_stock ?? 1
    const stockToGrams = props.stockToGrams ?? 1
    // product.calories is per 1 g/ml of real weight. Convert amount → grams/ml.
    const scale = props.draft.amount * factorToStock * stockToGrams
    return {
      kcal: (p.calories ?? 0) * scale,
      protein: (p.proteins ?? 0) * scale,
      carbs: (p.carbohydrates ?? 0) * scale,
      sugars: (p.carbohydrates_of_sugars ?? 0) * scale,
      fat: (p.fats ?? 0) * scale,
      satFat: (p.fats_saturated ?? 0) * scale,
      fibers: (p.fibers ?? 0) * scale,
    }
  } else {
    const r = props.draft.recipeOption
    if (!r || props.draft.amount == null || props.draft.amount <= 0) return null
    const s = props.draft.amount
    return {
      kcal: (r.latest_calories ?? 0) * s,
      protein: (r.latest_proteins ?? 0) * s,
      carbs: (r.latest_carbohydrates ?? 0) * s,
      sugars: (r.latest_carbohydrates_of_sugars ?? 0) * s,
      fat: (r.latest_fats ?? 0) * s,
      satFat: (r.latest_fats_saturated ?? 0) * s,
      fibers: (r.latest_fibers ?? 0) * s,
    }
  }
})

defineExpose({ stockUnit })
</script>

<template>
  <div class="border border-gray-200 rounded-md p-3 space-y-2 bg-white">
    <div class="flex flex-wrap gap-2 items-center">
      <div class="w-28">
        <AppSelect
          v-model="selectedType"
          :options="typeOptions"
          label-key="label"
          track-by="value"
        />
      </div>

      <div class="flex-1 min-w-[220px]">
        <AppCombobox
          v-if="draft.type === 'product'"
          v-model="productOption"
          :options="productOptions"
          label-key="name"
          track-by="grocy_id"
          placeholder="Search product..."
          server-side
          :loading="productLoading"
          min-query-hint="Type at least 3 characters"
          @update:query="(q) => emit('update:product-query', q)"
        />
        <AppCombobox
          v-else
          v-model="recipeOption"
          :options="recipeOptions"
          label-key="name"
          track-by="grocy_id"
          placeholder="Search recipe..."
          server-side
          :loading="recipeLoading"
          min-query-hint="Type at least 3 characters"
          @update:query="(q) => emit('update:recipe-query', q)"
        />
      </div>

      <div class="w-44">
        <AppSelect
          v-model="section"
          :options="sections"
          label-key="name"
          track-by="section_id"
          placeholder="Section"
        />
      </div>

      <button
        class="text-gray-400 hover:text-red-600 text-lg leading-none px-2"
        title="Remove line"
        @click="emit('remove')"
      >
        ✕
      </button>
    </div>

    <div class="flex flex-wrap gap-2 items-center">
      <input
        v-model.number="amount"
        type="number"
        step="0.01"
        min="0"
        placeholder="Amount"
        class="w-24 py-1.5 px-2.5 text-sm bg-white border border-gray-300 rounded-md shadow-xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
      />

      <div
        v-if="draft.type === 'product'"
        class="w-28"
      >
        <AppSelect
          v-model="unit"
          :options="units"
          label-key="name"
          track-by="qu_id"
          placeholder="Unit"
        />
      </div>
    </div>

    <div
      v-if="nutrition"
      class="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500 pl-1"
    >
      <span>~{{ Math.round(nutrition.kcal) }} kcal</span>
      <span>{{ nutrition.protein.toFixed(1) }}g P</span>
      <span>{{ nutrition.carbs.toFixed(1) }}g C
        <span
          v-if="nutrition.sugars > 0"
          class="text-gray-400"
        >({{ nutrition.sugars.toFixed(1) }}g sugars)</span>
      </span>
      <span>{{ nutrition.fat.toFixed(1) }}g F
        <span
          v-if="nutrition.satFat > 0"
          class="text-gray-400"
        >({{ nutrition.satFat.toFixed(1) }}g sat)</span>
      </span>
      <span>{{ nutrition.fibers.toFixed(1) }}g fibers</span>
    </div>
  </div>
</template>
