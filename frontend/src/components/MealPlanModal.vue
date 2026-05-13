<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import axios from 'axios'
import flatpickr from 'flatpickr'
import type { Instance as FlatpickrInstance } from 'flatpickr/dist/types/instance'
import 'flatpickr/dist/flatpickr.min.css'
import { useHouseholdStore } from '../store/household'
import { buildProductLine, buildRecipeLine, useMealPlanStore } from '../store/mealPlan'
import { useNutritionLimitsStore } from '../store/nutritionLimits'
import NutrientGauge from './NutrientGauge.vue'
import MealPlanLineRow from './MealPlanLineRow.vue'
import type { DraftLine, ProductOption, RecipeOption } from './MealPlanLineRow.vue'
import type { MealPlanLineCreate } from '../types/mealPlan'

const props = defineProps<{
  open: boolean
  date: string
  drafts: DraftLine[]
}>()

const emit = defineEmits<{
  close: []
  'update:date': [date: string]
  'update:drafts': [drafts: DraftLine[]]
  saved: []
}>()

const householdStore = useHouseholdStore()
const mealPlanStore = useMealPlanStore()
const nutritionStore = useNutritionLimitsStore()

const productOptionsByLine = reactive<Record<number, ProductOption[]>>({})
const recipeOptionsByLine = reactive<Record<number, RecipeOption[]>>({})
const productLoadingByLine = reactive<Record<number, boolean>>({})
const recipeLoadingByLine = reactive<Record<number, boolean>>({})
const productDebounceTimers: Record<number, ReturnType<typeof setTimeout>> = {}
const recipeDebounceTimers: Record<number, ReturnType<typeof setTimeout>> = {}
const productRequestSeq: Record<number, number> = {}
const recipeRequestSeq: Record<number, number> = {}

const submitting = ref(false)
const submitError = ref('')

const MIN_QUERY_LEN = 3
const DEBOUNCE_MS = 250
const SEARCH_LIMIT = 20

function emptyDraft(): DraftLine {
  return {
    type: 'product',
    productOption: null,
    recipeOption: null,
    amount: null,
    unit: null,
    section: mealPlanStore.sections[0] || null,
  }
}

function updateDraft(index: number, patch: DraftLine) {
  const next = props.drafts.slice()
  next[index] = patch
  emit('update:drafts', next)
}

function addLine() {
  emit('update:drafts', [...props.drafts, emptyDraft()])
}

function shiftLineMaps(removedIndex: number, total: number) {
  const reindex = <T>(map: Record<number, T>) => {
    for (let i = removedIndex; i < total; i++) {
      map[i] = map[i + 1]
    }
    delete map[total]
  }
  reindex(productOptionsByLine)
  reindex(recipeOptionsByLine)
  reindex(productLoadingByLine)
  reindex(recipeLoadingByLine)
  reindex(productDebounceTimers)
  reindex(recipeDebounceTimers)
  reindex(productRequestSeq)
  reindex(recipeRequestSeq)
}

function removeLine(index: number) {
  const next = props.drafts.slice()
  next.splice(index, 1)
  shiftLineMaps(index, next.length)
  if (next.length === 0) next.push(emptyDraft())
  emit('update:drafts', next)
}

async function searchProducts(lineIndex: number, query: string) {
  if (!householdStore.selectedId) return
  const seq = (productRequestSeq[lineIndex] = (productRequestSeq[lineIndex] || 0) + 1)
  productLoadingByLine[lineIndex] = true
  try {
    const { data } = await axios.get('/api/products', {
      params: {
        household_id: householdStore.selectedId,
        limit: SEARCH_LIMIT,
        search: query,
      },
    })
    if (seq !== productRequestSeq[lineIndex]) return
    productOptionsByLine[lineIndex] = (data.products || []).map(
      (p: {
        grocy_id: number
        name: string
        calories: number | null
        proteins: number | null
        carbohydrates: number | null
        carbohydrates_of_sugars: number | null
        fats: number | null
        fats_saturated: number | null
        fibers: number | null
      }) => ({
        grocy_id: p.grocy_id,
        name: p.name,
        calories: p.calories,
        proteins: p.proteins,
        carbohydrates: p.carbohydrates,
        carbohydrates_of_sugars: p.carbohydrates_of_sugars,
        fats: p.fats,
        fats_saturated: p.fats_saturated,
        fibers: p.fibers,
      }),
    )
  } finally {
    if (seq === productRequestSeq[lineIndex]) productLoadingByLine[lineIndex] = false
  }
}

async function searchRecipes(lineIndex: number, query: string) {
  if (!householdStore.selectedId) return
  const seq = (recipeRequestSeq[lineIndex] = (recipeRequestSeq[lineIndex] || 0) + 1)
  recipeLoadingByLine[lineIndex] = true
  try {
    const { data } = await axios.get('/api/recipes/list', {
      params: {
        household_id: householdStore.selectedId,
        limit: SEARCH_LIMIT,
        skip: 0,
        search: query,
      },
    })
    if (seq !== recipeRequestSeq[lineIndex]) return
    recipeOptionsByLine[lineIndex] = (data.recipes || []).map(
      (r: {
        grocy_id: number
        name: string
        latest_calories: number | null
        latest_proteins: number | null
        latest_carbohydrates: number | null
        latest_carbohydrates_of_sugars: number | null
        latest_fats: number | null
        latest_fats_saturated: number | null
        latest_fibers: number | null
      }) => ({
        grocy_id: r.grocy_id,
        name: r.name,
        latest_calories: r.latest_calories,
        latest_proteins: r.latest_proteins,
        latest_carbohydrates: r.latest_carbohydrates,
        latest_carbohydrates_of_sugars: r.latest_carbohydrates_of_sugars,
        latest_fats: r.latest_fats,
        latest_fats_saturated: r.latest_fats_saturated,
        latest_fibers: r.latest_fibers,
      }),
    )
  } finally {
    if (seq === recipeRequestSeq[lineIndex]) recipeLoadingByLine[lineIndex] = false
  }
}

function onProductQuery(lineIndex: number, query: string) {
  if (productDebounceTimers[lineIndex]) clearTimeout(productDebounceTimers[lineIndex])
  if (query.length < MIN_QUERY_LEN) {
    productOptionsByLine[lineIndex] = []
    productLoadingByLine[lineIndex] = false
    productRequestSeq[lineIndex] = (productRequestSeq[lineIndex] || 0) + 1
    return
  }
  productDebounceTimers[lineIndex] = setTimeout(() => {
    searchProducts(lineIndex, query)
  }, DEBOUNCE_MS)
}

function onRecipeQuery(lineIndex: number, query: string) {
  if (recipeDebounceTimers[lineIndex]) clearTimeout(recipeDebounceTimers[lineIndex])
  if (query.length < MIN_QUERY_LEN) {
    recipeOptionsByLine[lineIndex] = []
    recipeLoadingByLine[lineIndex] = false
    recipeRequestSeq[lineIndex] = (recipeRequestSeq[lineIndex] || 0) + 1
    return
  }
  recipeDebounceTimers[lineIndex] = setTimeout(() => {
    searchRecipes(lineIndex, query)
  }, DEBOUNCE_MS)
}

async function onProductSelected(productGrocyId: number) {
  await mealPlanStore.loadUnitsForProduct(productGrocyId)
}

const totals = computed(() => {
  let kcal = 0, p = 0, c = 0, sugars = 0, f = 0, satF = 0, fib = 0
  for (const d of props.drafts) {
    if (d.type === 'product') {
      const prod = d.productOption
      if (!prod || !d.amount || d.amount <= 0) continue
      const factorToStock = d.unit?.factor_to_stock ?? 1
      const stockToGrams =
        mealPlanStore.stockToGramsByProduct[prod.grocy_id] ?? 1
      const scale = d.amount * factorToStock * stockToGrams
      kcal += (prod.calories ?? 0) * scale
      p += (prod.proteins ?? 0) * scale
      c += (prod.carbohydrates ?? 0) * scale
      sugars += (prod.carbohydrates_of_sugars ?? 0) * scale
      f += (prod.fats ?? 0) * scale
      satF += (prod.fats_saturated ?? 0) * scale
      fib += (prod.fibers ?? 0) * scale
    } else {
      const rec = d.recipeOption
      if (!rec || !d.amount || d.amount <= 0) continue
      const s = d.amount
      kcal += (rec.latest_calories ?? 0) * s
      p += (rec.latest_proteins ?? 0) * s
      c += (rec.latest_carbohydrates ?? 0) * s
      sugars += (rec.latest_carbohydrates_of_sugars ?? 0) * s
      f += (rec.latest_fats ?? 0) * s
      satF += (rec.latest_fats_saturated ?? 0) * s
      fib += (rec.latest_fibers ?? 0) * s
    }
  }
  return { kcal, protein: p, carbs: c, sugars, fat: f, satFat: satF, fibers: fib }
})

const dayLimit = computed(() => nutritionStore.getLimitByDate(props.date))

const validDrafts = computed(() =>
  props.drafts.filter((d) => {
    if (d.section == null) return false
    if (!d.amount || d.amount <= 0) return false
    if (d.type === 'product') {
      return d.productOption !== null && d.unit !== null
    }
    return d.recipeOption !== null
  }),
)

const unitsForProduct = (productGrocyId: number | undefined) => {
  if (!productGrocyId) return []
  return mealPlanStore.unitsByProduct[productGrocyId] || []
}

const stockToGramsForProduct = (productGrocyId: number | undefined): number | null => {
  if (!productGrocyId) return null
  const v = mealPlanStore.stockToGramsByProduct[productGrocyId]
  return v === undefined ? null : v
}

function onDateInput(e: Event) {
  const v = (e.target as HTMLInputElement).value
  emit('update:date', v)
}

const desktopDateRef = ref<HTMLInputElement | null>(null)
const mobileDateRef = ref<HTMLInputElement | null>(null)
const flatpickrInstances: FlatpickrInstance[] = []

function teardownFlatpickr() {
  while (flatpickrInstances.length) {
    flatpickrInstances.pop()?.destroy()
  }
}

function initFlatpickr() {
  teardownFlatpickr()
  const targets = [desktopDateRef.value, mobileDateRef.value].filter(
    (el): el is HTMLInputElement => el !== null,
  )
  for (const el of targets) {
    const instance = flatpickr(el, {
      dateFormat: 'Y-m-d',
      defaultDate: props.date,
      locale: { firstDayOfWeek: 1 },
      onChange: (_dates, dateStr) => emit('update:date', dateStr),
    })
    flatpickrInstances.push(instance as FlatpickrInstance)
  }
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      // Wait for the v-if Transition to mount the input element.
      requestAnimationFrame(() => initFlatpickr())
    } else {
      teardownFlatpickr()
    }
  },
)

watch(
  () => props.date,
  (newDate) => {
    for (const inst of flatpickrInstances) {
      inst.setDate(newDate, false)
    }
  },
)

async function submit() {
  submitError.value = ''
  if (validDrafts.value.length === 0) {
    submitError.value = 'Add at least one valid line.'
    return
  }
  const lines: MealPlanLineCreate[] = validDrafts.value.map((d) =>
    d.type === 'product'
      ? buildProductLine({
          day: props.date,
          section_id: d.section!.section_id,
          product_grocy_id: d.productOption!.grocy_id,
          amount: Number(d.amount),
          unit: d.unit!,
        })
      : buildRecipeLine({
          day: props.date,
          section_id: d.section!.section_id,
          recipe_grocy_id: d.recipeOption!.grocy_id,
          servings: Number(d.amount),
        }),
  )
  submitting.value = true
  try {
    await mealPlanStore.submit(lines)
    emit('saved')
    emit('close')
  } catch {
    submitError.value = mealPlanStore.error || 'Submit failed'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    mealPlanStore.loadSections(),
    nutritionStore.fetchList(0, 100),
  ])
})

function handleKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault()
    submit()
  }
}
</script>

<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <Transition
      enter-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-40 bg-black/40"
        @click="emit('close')"
      ></div>
    </Transition>

    <!-- Desktop drawer (right slide-in) -->
    <Transition
      enter-active-class="transition-transform duration-200 ease-out"
      enter-from-class="translate-x-full"
      enter-to-class="translate-x-0"
      leave-active-class="transition-transform duration-200 ease-in"
      leave-from-class="translate-x-0"
      leave-to-class="translate-x-full"
    >
      <div
        v-if="open"
        class="hidden sm:flex fixed inset-y-0 right-0 z-50 w-full sm:max-w-[760px] bg-white shadow-2xl flex-col"
        @keydown="handleKeydown"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 shrink-0">
          <h3 class="text-base font-semibold text-gray-900">Add to meal plan</h3>
          <button
            class="text-gray-400 hover:text-gray-600 text-lg leading-none"
            @click="emit('close')"
          >
            ✕
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          <div class="flex items-center gap-3">
            <label class="text-sm text-gray-600">Date</label>
            <input
              ref="desktopDateRef"
              :value="date"
              type="text"
              readonly
              placeholder="YYYY-MM-DD"
              class="py-1.5 px-2.5 text-sm bg-white border border-gray-300 rounded-md shadow-xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 cursor-pointer"
              @change="onDateInput"
            />
          </div>

          <div class="space-y-2">
            <MealPlanLineRow
              v-for="(d, i) in drafts"
              :key="i"
              :draft="d"
              :sections="mealPlanStore.sections"
              :product-options="productOptionsByLine[i] || []"
              :recipe-options="recipeOptionsByLine[i] || []"
              :product-loading="productLoadingByLine[i] || false"
              :recipe-loading="recipeLoadingByLine[i] || false"
              :units="d.type === 'product' ? unitsForProduct(d.productOption?.grocy_id) : []"
              :stock-to-grams="d.type === 'product' ? stockToGramsForProduct(d.productOption?.grocy_id) : null"
              @update:draft="(patch) => updateDraft(i, patch)"
              @remove="removeLine(i)"
              @product-selected="onProductSelected"
              @update:product-query="(q) => onProductQuery(i, q)"
              @update:recipe-query="(q) => onRecipeQuery(i, q)"
            />
            <button
              class="text-sm text-indigo-600 hover:text-indigo-800"
              @click="addLine"
            >
              + Add line
            </button>
          </div>

          <div class="border-t border-gray-200 pt-4">
            <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Total for day</p>
            <div class="grid grid-cols-4 gap-3">
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.kcal"
                  :max="dayLimit?.calories ?? null"
                />
                <p class="text-xs text-gray-600 mt-1">Cal {{ Math.round(totals.kcal) }}<span v-if="dayLimit?.calories">/{{ dayLimit.calories }}</span></p>
              </div>
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.protein"
                  :max="dayLimit?.proteins ?? null"
                />
                <p class="text-xs text-gray-600 mt-1">P {{ totals.protein.toFixed(1) }}<span v-if="dayLimit?.proteins">/{{ dayLimit.proteins }}</span>g</p>
              </div>
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.carbs"
                  :max="dayLimit?.carbohydrates ?? null"
                />
                <p class="text-xs text-gray-600 mt-1">C {{ totals.carbs.toFixed(1) }}<span v-if="dayLimit?.carbohydrates">/{{ dayLimit.carbohydrates }}</span>g</p>
              </div>
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.fat"
                  :max="dayLimit?.fats ?? null"
                />
                <p class="text-xs text-gray-600 mt-1">F {{ totals.fat.toFixed(1) }}<span v-if="dayLimit?.fats">/{{ dayLimit.fats }}</span>g</p>
              </div>
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.sugars"
                  :max="dayLimit?.carbohydrates_of_sugars ?? null"
                  less-is-better
                />
                <p class="text-xs text-gray-600 mt-1">Sug {{ totals.sugars.toFixed(1) }}<span v-if="dayLimit?.carbohydrates_of_sugars">/{{ dayLimit.carbohydrates_of_sugars }}</span>g</p>
              </div>
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.satFat"
                  :max="dayLimit?.fats_saturated ?? null"
                  less-is-better
                />
                <p class="text-xs text-gray-600 mt-1">SatF {{ totals.satFat.toFixed(1) }}<span v-if="dayLimit?.fats_saturated">/{{ dayLimit.fats_saturated }}</span>g</p>
              </div>
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.fibers"
                  :max="dayLimit?.fibers ?? null"
                />
                <p class="text-xs text-gray-600 mt-1">Fib {{ totals.fibers.toFixed(1) }}<span v-if="dayLimit?.fibers">/{{ dayLimit.fibers }}</span>g</p>
              </div>
            </div>
          </div>

          <div
            v-if="submitError"
            class="text-sm text-red-600"
          >
            {{ submitError }}
          </div>
        </div>

        <div class="flex justify-end gap-2 px-6 py-4 border-t border-gray-200 shrink-0">
          <button
            class="px-3 py-1.5 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            @click="emit('close')"
          >
            Cancel
          </button>
          <button
            class="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            :disabled="submitting || validDrafts.length === 0"
            @click="submit"
          >
            Save ({{ validDrafts.length }})
          </button>
        </div>
      </div>
    </Transition>

    <!-- Mobile bottom sheet -->
    <Transition
      enter-active-class="transition-transform duration-200 ease-out"
      enter-from-class="translate-y-full"
      enter-to-class="translate-y-0"
      leave-active-class="transition-transform duration-200 ease-in"
      leave-from-class="translate-y-0"
      leave-to-class="translate-y-full"
    >
      <div
        v-if="open"
        class="sm:hidden fixed inset-x-0 bottom-0 z-50 max-h-[90vh] flex flex-col bg-white rounded-t-2xl shadow-2xl"
        @keydown="handleKeydown"
      >
        <div class="flex justify-center pt-3 pb-1 shrink-0">
          <div class="w-10 h-1 rounded-full bg-gray-300"></div>
        </div>
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 shrink-0">
          <h3 class="text-base font-semibold text-gray-900">Add to meal plan</h3>
          <button
            class="text-gray-400 hover:text-gray-600 text-lg leading-none"
            @click="emit('close')"
          >
            ✕
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-4 py-3 space-y-4">
          <div class="flex items-center gap-3">
            <label class="text-sm text-gray-600">Date</label>
            <input
              ref="mobileDateRef"
              :value="date"
              type="text"
              readonly
              placeholder="YYYY-MM-DD"
              class="py-1.5 px-2.5 text-sm bg-white border border-gray-300 rounded-md shadow-xs cursor-pointer"
              @change="onDateInput"
            />
          </div>

          <div class="space-y-2">
            <MealPlanLineRow
              v-for="(d, i) in drafts"
              :key="i"
              :draft="d"
              :sections="mealPlanStore.sections"
              :product-options="productOptionsByLine[i] || []"
              :recipe-options="recipeOptionsByLine[i] || []"
              :product-loading="productLoadingByLine[i] || false"
              :recipe-loading="recipeLoadingByLine[i] || false"
              :units="d.type === 'product' ? unitsForProduct(d.productOption?.grocy_id) : []"
              :stock-to-grams="d.type === 'product' ? stockToGramsForProduct(d.productOption?.grocy_id) : null"
              @update:draft="(patch) => updateDraft(i, patch)"
              @remove="removeLine(i)"
              @product-selected="onProductSelected"
              @update:product-query="(q) => onProductQuery(i, q)"
              @update:recipe-query="(q) => onRecipeQuery(i, q)"
            />
            <button
              class="text-sm text-indigo-600 hover:text-indigo-800"
              @click="addLine"
            >
              + Add line
            </button>
          </div>

          <div class="border-t border-gray-200 pt-4">
            <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Total for day</p>
            <div class="grid grid-cols-2 gap-3">
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.kcal"
                  :max="dayLimit?.calories ?? null"
                />
                <p class="text-xs text-gray-600 mt-1">Cal {{ Math.round(totals.kcal) }}</p>
              </div>
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.protein"
                  :max="dayLimit?.proteins ?? null"
                />
                <p class="text-xs text-gray-600 mt-1">P {{ totals.protein.toFixed(1) }}g</p>
              </div>
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.carbs"
                  :max="dayLimit?.carbohydrates ?? null"
                />
                <p class="text-xs text-gray-600 mt-1">C {{ totals.carbs.toFixed(1) }}g</p>
              </div>
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.fat"
                  :max="dayLimit?.fats ?? null"
                />
                <p class="text-xs text-gray-600 mt-1">F {{ totals.fat.toFixed(1) }}g</p>
              </div>
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.sugars"
                  :max="dayLimit?.carbohydrates_of_sugars ?? null"
                  less-is-better
                />
                <p class="text-xs text-gray-600 mt-1">Sug {{ totals.sugars.toFixed(1) }}g</p>
              </div>
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.satFat"
                  :max="dayLimit?.fats_saturated ?? null"
                  less-is-better
                />
                <p class="text-xs text-gray-600 mt-1">SatF {{ totals.satFat.toFixed(1) }}g</p>
              </div>
              <div class="flex flex-col items-center">
                <NutrientGauge
                  :value="totals.fibers"
                  :max="dayLimit?.fibers ?? null"
                />
                <p class="text-xs text-gray-600 mt-1">Fib {{ totals.fibers.toFixed(1) }}g</p>
              </div>
            </div>
          </div>

          <div
            v-if="submitError"
            class="text-sm text-red-600"
          >
            {{ submitError }}
          </div>
        </div>

        <div class="flex justify-end gap-2 px-4 py-3 border-t border-gray-200 shrink-0">
          <button
            class="px-3 py-1.5 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            @click="emit('close')"
          >
            Cancel
          </button>
          <button
            class="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            :disabled="submitting || validDrafts.length === 0"
            @click="submit"
          >
            Save ({{ validDrafts.length }})
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
