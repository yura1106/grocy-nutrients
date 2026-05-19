<script setup lang="ts">
import { computed, watch } from 'vue'
import { Check, Notebook, Pencil, X } from 'lucide-vue-next'
import AppCombobox from './ui/AppCombobox.vue'
import AppSelect from './ui/AppSelect.vue'
import type { MealPlanSection, MealPlanUnit } from '../types/mealPlan'
import { parseNoteNutrients } from '../utils/parseNoteNutrients'

export interface DraftLine {
  /** Stable client-side id. Used as the v-for key and as the key for the
   * parent modal's per-line reactive maps (search options, debounce timers,
   * request sequence numbers). Survives line reordering/removal so Vue
   * doesn't remount rows onto neighbouring drafts. */
  clientId: string
  type: 'product' | 'recipe' | 'note'
  productOption: ProductOption | null
  recipeOption: RecipeOption | null
  amount: number | null
  unit: MealPlanUnit | null
  section: MealPlanSection | null
  note: string | null
  collapsed: boolean
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
  { value: 'note', label: 'Note' },
]
const selectedType = computed({
  get: () => typeOptions.find((o) => o.value === props.draft.type) || typeOptions[0],
  set: (val) => {
    update({
      type: val.value as 'product' | 'recipe' | 'note',
      productOption: null,
      recipeOption: null,
      unit: null,
      amount: null,
      note: val.value === 'note' ? '' : null,
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
const noteText = computed({
  get: () => props.draft.note ?? '',
  set: (v) => update({ note: v }),
})

/** True for a product draft that has all selections made but its stock unit
 * cannot be resolved to grams/ml. Such drafts cannot have nutrition computed
 * — neither modal totals nor day-card daily totals can use them. Surfaced
 * inline as a yellow tag so the user knows before saving. */
const nutritionUnavailable = computed(() => {
  if (props.draft.type !== 'product') return false
  const p = props.draft.productOption
  if (!p || props.draft.unit == null) return false
  if (props.draft.amount == null || props.draft.amount <= 0) return false
  return props.stockToGrams == null
})

const nutrition = computed(() => {
  if (props.draft.type === 'product') {
    const p = props.draft.productOption
    if (!p || props.draft.amount == null || props.draft.amount <= 0) return null
    if (props.draft.unit == null) return null
    if (props.stockToGrams == null) return null
    const factorToStock = props.draft.unit.factor_to_stock
    const stockToGrams = props.stockToGrams
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
  } else if (props.draft.type === 'recipe') {
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
  } else {
    // note: derive nutrients from the "Калорій:.../Білків:..." format if
    // present. Returns null when nothing parses — note still saves, but no
    // inline nutrient strip is shown.
    if (!props.draft.note?.trim()) return null
    const parsed = parseNoteNutrients(props.draft.note)
    if (Object.keys(parsed).length === 0) return null
    return {
      kcal: parsed.kcal ?? 0,
      protein: parsed.protein ?? 0,
      carbs: parsed.carbs ?? 0,
      sugars: parsed.sugars ?? 0,
      fat: parsed.fat ?? 0,
      satFat: parsed.satFat ?? 0,
      fibers: parsed.fibers ?? 0,
    }
  }
})

const canCollapse = computed(() => {
  // Note drafts collapse once a non-empty note + section are picked, even when
  // nutrients didn't parse — saving a plain note is the common case.
  if (props.draft.type === 'note') {
    return !!props.draft.note?.trim() && props.draft.section != null
  }
  return nutrition.value !== null || nutritionUnavailable.value
})

function toggleCollapsed() {
  if (!props.draft.collapsed && !canCollapse.value) return
  update({ collapsed: !props.draft.collapsed })
}

const itemName = computed(() => {
  if (props.draft.type === 'product') return props.draft.productOption?.name ?? ''
  if (props.draft.type === 'recipe') return props.draft.recipeOption?.name ?? ''
  return props.draft.note ?? ''
})

const amountLabel = computed(() => {
  if (props.draft.type === 'note') return ''
  if (props.draft.amount == null) return ''
  if (props.draft.type === 'recipe') return `${props.draft.amount} порц.`
  return `${props.draft.amount} ${props.draft.unit?.name ?? ''}`.trim()
})

const sectionLabel = computed(() => props.draft.section?.name ?? '—')

defineExpose({ stockUnit })
</script>

<template>
  <div class="border border-gray-200 rounded-md p-3 bg-white">
    <!-- VIEW MODE -->
    <div
      v-if="draft.collapsed"
      class="flex items-center gap-x-1.5 gap-y-1 flex-wrap"
    >
      <span class="inline-flex items-center px-2 py-0.5 text-xs rounded bg-indigo-50 text-indigo-700 border border-indigo-100 shrink-0">
        {{ sectionLabel }}
      </span>
      <Notebook
        v-if="draft.type === 'note'"
        :size="14"
        class="text-gray-400 shrink-0"
      />
      <span class="font-medium text-sm text-gray-900">{{ itemName }}</span>
      <template v-if="draft.type !== 'note'">
        <span class="text-xs text-gray-400">·</span>
        <span class="text-xs text-gray-600">{{ amountLabel }}</span>
      </template>
      <template v-if="nutrition">
        <span class="text-xs text-gray-400">·</span>
        <span class="text-xs text-gray-500">~{{ Math.round(nutrition.kcal) }} kcal</span>
        <span class="text-xs text-gray-400">·</span>
        <span class="text-xs text-gray-500">{{ nutrition.protein.toFixed(1) }}g P</span>
        <span class="text-xs text-gray-400">·</span>
        <span class="text-xs text-gray-500">{{ nutrition.carbs.toFixed(1) }}g C<span
          v-if="nutrition.sugars > 0"
          class="text-gray-400"
        > ({{ nutrition.sugars.toFixed(1) }}g sugars)</span></span>
        <span class="text-xs text-gray-400">·</span>
        <span class="text-xs text-gray-500">{{ nutrition.fat.toFixed(1) }}g F<span
          v-if="nutrition.satFat > 0"
          class="text-gray-400"
        > ({{ nutrition.satFat.toFixed(1) }}g sat)</span></span>
        <span class="text-xs text-gray-400">·</span>
        <span class="text-xs text-gray-500">{{ nutrition.fibers.toFixed(1) }}g fibers</span>
      </template>
      <span
        v-else-if="nutritionUnavailable"
        class="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded bg-amber-100 text-amber-800"
        title="Нема конверсії одиниці зберігання в грами/мл — нутрієнти неможливо порахувати."
      >
        ⚠ Нема даних нутрієнтів
      </span>
      <div class="flex items-center gap-1.5 shrink-0 ml-auto">
        <button
          type="button"
          title="Редагувати"
          class="inline-flex items-center justify-center w-8 h-8 text-gray-600 bg-white border border-gray-300 rounded-md shadow-xs hover:bg-gray-50 hover:text-indigo-600 hover:border-gray-400"
          @click="toggleCollapsed"
        >
          <Pencil :size="14" />
        </button>
        <button
          type="button"
          title="Видалити рядок"
          class="inline-flex items-center justify-center w-8 h-8 text-gray-500 bg-white border border-gray-300 rounded-md shadow-xs hover:bg-red-50 hover:text-red-600 hover:border-red-300"
          @click="emit('remove')"
        >
          <X :size="14" />
        </button>
      </div>
    </div>

    <!-- EDIT MODE -->
    <div
      v-else
      class="space-y-2"
    >
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
            v-else-if="draft.type === 'recipe'"
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
          <input
            v-else
            v-model="noteText"
            type="text"
            placeholder="Note text..."
            class="w-full py-1.5 px-2.5 text-sm bg-white border border-gray-300 rounded-md shadow-xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
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

        <div class="flex items-center gap-1.5 shrink-0 ml-auto">
          <button
            type="button"
            :disabled="!canCollapse"
            :title="canCollapse ? 'Згорнути' : 'Заповніть всі поля'"
            class="inline-flex items-center justify-center w-8 h-8 text-white bg-indigo-600 border border-indigo-600 rounded-md shadow-xs hover:bg-indigo-700 hover:border-indigo-700 disabled:bg-gray-200 disabled:border-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed"
            @click="toggleCollapsed"
          >
            <Check :size="14" />
          </button>
          <button
            type="button"
            title="Видалити рядок"
            class="inline-flex items-center justify-center w-8 h-8 text-gray-500 bg-white border border-gray-300 rounded-md shadow-xs hover:bg-red-50 hover:text-red-600 hover:border-red-300"
            @click="emit('remove')"
          >
            <X :size="14" />
          </button>
        </div>
      </div>

      <div
        v-if="draft.type !== 'note'"
        class="flex flex-wrap gap-2 items-center"
      >
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
        v-if="nutritionUnavailable"
        class="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded bg-amber-100 text-amber-800"
        title="Нема конверсії одиниці зберігання в грами/мл — нутрієнти неможливо порахувати."
      >
        ⚠ Нема даних нутрієнтів для цієї одиниці
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
  </div>
</template>
