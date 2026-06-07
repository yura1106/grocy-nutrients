<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Check, ClipboardCheck, Notebook, Pencil, Trash2, X } from 'lucide-vue-next'
import { useHouseholdStore } from '../store/household'
import { useMealPlanStore } from '../store/mealPlan'
import { formatAmount } from '../utils/mealPlanFormat'
import { parseNoteNutrients } from '../utils/parseNoteNutrients'
import type { MealPlanLine } from '../types/mealPlan'

const props = withDefaults(
  defineProps<{
    day: string
    rows: Record<number, MealPlanLine[]>
    sectionsById: Record<number, string>
    autoFetchTotals?: boolean
  }>(),
  {
    autoFetchTotals: false,
  },
)

const emit = defineEmits<{
  (e: 'add-clicked', day: string): void
}>()

const router = useRouter()
const householdStore = useHouseholdStore()
const store = useMealPlanStore()

const isEmpty = computed(() => Object.keys(props.rows).length === 0)
const sectionIds = computed(() => Object.keys(props.rows))

const allRows = computed(() => Object.values(props.rows).flat())
const hasConsumable = computed(() =>
  allRows.value.some((r) => r.type !== 'note' && r.status === 'synced' && !r.done),
)
const allDone = computed(
  () => allRows.value.length > 0 && allRows.value.every((r) => r.done),
)

const dayCheck = computed(() => store.dayCheckByDate[props.day])
const dayCheckBusy = computed(() => {
  const s = dayCheck.value?.state
  return s === 'PENDING' || s === 'PROGRESS'
})
const dayCheckDotClass = computed(() => {
  const dc = dayCheck.value
  if (!dc) return null
  if (dc.outcome === 'insufficient_resolved_with_list') return 'bg-blue-500'
  if (dc.outcome === 'insufficient_cancelled') return 'bg-gray-400'
  if (dc.state === 'SUCCESS' && dc.result?.status === 'success') return 'bg-green-500'
  if (dc.state === 'FAILURE') return 'bg-red-500'
  return null
})
const showInsufficientBlock = computed(() =>
  dayCheck.value?.state === 'SUCCESS'
  && dayCheck.value?.result?.status === 'insufficient_stock'
  && !dayCheck.value?.outcome,
)

function grocyProductUrl(grocyId: number): string | null {
  const base = householdStore.selected?.grocy_url
  if (!base) return null
  return `${base.replace(/\/$/, '')}/product/${grocyId}`
}

function grocyRecipeUrl(grocyId: number): string | null {
  const base = householdStore.selected?.grocy_url
  if (!base) return null
  return `${base.replace(/\/$/, '')}/recipe/${grocyId}`
}

function statusBadgeClass(status: string, done: boolean) {
  if (done) return 'bg-green-100 text-green-800'
  switch (status) {
    case 'pending':
      return 'bg-gray-100 text-gray-700'
    case 'syncing':
      return 'bg-blue-100 text-blue-800'
    case 'synced':
      return 'bg-emerald-100 text-emerald-800'
    case 'failed':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-700'
  }
}

function statusLabel(status: string, done: boolean) {
  if (done) return 'done'
  return status
}

function onAdd() {
  emit('add-clicked', props.day)
}

function onConsume() {
  router.push({ path: '/consume', query: { date: props.day } })
}

// Per-row interaction state. Only one row can be in edit-or-confirm mode at a
// time per day card; entering one mode clears the other.
const editingId = ref<number | null>(null)
const editValue = ref<string | number>('')
const editError = ref<string>('')
const editSubmitting = ref(false)
// In a v-for, template refs collect into an array. Only one input is rendered
// at a time (v-if gates by editingId), so the array has exactly one element
// while editing.
const editInputRef = ref<(HTMLInputElement | null)[]>([])

const confirmingDeleteId = ref<number | null>(null)
const deleteSubmitting = ref(false)

function isEditable(row: MealPlanLine): boolean {
  return row.status === 'synced' && !row.done
}

function startEdit(row: MealPlanLine) {
  confirmingDeleteId.value = null
  editingId.value = row.id
  editError.value = ''
  if (row.type === 'note') {
    editValue.value = row.note ?? ''
  } else {
    const raw = row.type === 'product' ? row.product_amount : row.recipe_servings
    if (raw == null || raw === '') {
      editValue.value = ''
    } else {
      const n = Number(raw)
      editValue.value = Number.isFinite(n) ? String(n) : String(raw)
    }
  }
  if (row.type === 'product' && row.product_grocy_id != null) {
    // Warm the units cache so confirm() can compute stock amount without a
    // surprise round-trip on click.
    store.loadUnitsForProduct(row.product_grocy_id)
  }
  nextTick(() => editInputRef.value?.[0]?.focus())
}

function cancelEdit() {
  editingId.value = null
  editValue.value = ''
  editError.value = ''
}

async function confirmEdit(row: MealPlanLine) {
  const raw = String(editValue.value ?? '').trim()
  if (row.type === 'note') {
    if (!raw) {
      editError.value = 'Enter a non-empty note.'
      return
    }
  } else {
    const parsed = Number(raw)
    if (!raw || Number.isNaN(parsed) || parsed <= 0) {
      editError.value = 'Enter a positive number.'
      return
    }
  }
  editSubmitting.value = true
  editError.value = ''
  try {
    if (row.type === 'product') {
      if (row.product_grocy_id == null || row.product_qu_id == null) {
        editError.value = 'Missing product/unit info.'
        return
      }
      const units = await store.loadUnitsForProduct(row.product_grocy_id)
      const unit = units.find((u) => u.qu_id === row.product_qu_id)
      if (!unit) {
        editError.value = 'Unit no longer available; reload the page.'
        return
      }
      const parsed = Number(raw)
      const stockAmount = parsed * unit.factor_to_stock
      await store.editLine(row.id, {
        product_amount: String(parsed),
        product_amount_stock: String(stockAmount),
      })
    } else if (row.type === 'recipe') {
      await store.editLine(row.id, { recipe_servings: String(Number(raw)) })
    } else {
      await store.editLine(row.id, { note: raw })
    }
    cancelEdit()
  } catch (err) {
    // store sets store.error; surface inline message too.
    editError.value = store.error || (err instanceof Error ? err.message : 'Edit failed')
  } finally {
    editSubmitting.value = false
  }
}

function noteNutrientsFor(row: MealPlanLine) {
  if (row.type !== 'note' || !row.note) return null
  const parsed = parseNoteNutrients(row.note)
  if (Object.keys(parsed).length === 0) return null
  return parsed
}

const toggleNoteDoneSubmittingId = ref<number | null>(null)

async function toggleNoteDone(row: MealPlanLine) {
  if (row.type !== 'note') return
  toggleNoteDoneSubmittingId.value = row.id
  try {
    await store.toggleNoteDone(row.id, !row.done)
  } catch {
    // store.error is surfaced at the day-level error UI.
  } finally {
    toggleNoteDoneSubmittingId.value = null
  }
}

function startConfirmDelete(row: MealPlanLine) {
  cancelEdit()
  confirmingDeleteId.value = row.id
}

function cancelConfirmDelete() {
  confirmingDeleteId.value = null
}

async function confirmDelete(row: MealPlanLine) {
  deleteSubmitting.value = true
  try {
    await store.deleteSynced(row.id)
    confirmingDeleteId.value = null
  } catch {
    // store.error already set; UI shows it via the day-level error surface.
    // Keep the confirm panel open so the user can retry or cancel.
  } finally {
    deleteSubmitting.value = false
  }
}

onMounted(() => {
  if (props.autoFetchTotals && !store.totalsByDay[props.day] && !store.totalsLoadingByDay[props.day]) {
    store.fetchDailyTotals(props.day)
  }
})

// If totals were wiped (loadRange after a batch completes, or explicit
// invalidation on retry/delete), re-fetch on the next tick. Without this
// watch the dashboard's totals would stay blank until the next route mount.
watch(
  () => store.totalsByDay[props.day],
  (next) => {
    if (
      props.autoFetchTotals &&
      next == null &&
      !store.totalsLoadingByDay[props.day]
    ) {
      store.fetchDailyTotals(props.day)
    }
  },
)
</script>

<template>
  <div class="border border-gray-200 rounded-md bg-white">
    <div class="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
      <div class="flex items-center gap-1.5">
        <span
          v-if="allDone"
          class="inline-flex text-green-600"
          title="All consumed"
        >
          <Check :size="16" />
        </span>
        <h3 class="font-semibold text-gray-800">{{ day }}</h3>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="hasConsumable"
          class="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded-md hover:bg-green-700"
          @click="onConsume"
        >
          Consume
        </button>
        <button
          v-if="hasConsumable"
          class="relative inline-flex items-center justify-center w-7 h-7 rounded-md border border-gray-300 bg-white text-gray-600 hover:bg-indigo-50 hover:border-indigo-400 hover:text-indigo-600 disabled:opacity-50 disabled:hover:bg-white disabled:hover:border-gray-300 disabled:hover:text-gray-600 transition-colors"
          :disabled="dayCheckBusy"
          :title="`Check availability for ${day}`"
          @click="store.triggerDayCheck(day)"
        >
          <span
            v-if="dayCheckBusy"
            class="animate-spin w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full"
          ></span>
          <ClipboardCheck
            v-else
            :size="14"
          />
          <span
            v-if="dayCheckDotClass"
            class="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full ring-2 ring-white"
            :class="dayCheckDotClass"
          ></span>
        </button>
        <button
          class="inline-flex items-center justify-center w-7 h-7 text-base font-semibold bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
          :title="`Add to ${day}`"
          @click="onAdd"
        >
          +
        </button>
      </div>
    </div>

    <div class="px-4 py-2 bg-gray-50/60 border-b-2 border-gray-200 text-xs flex items-center gap-2 flex-wrap">
      <button
        v-if="!store.totalsByDay[day] && !store.totalsLoadingByDay[day] && !store.totalsErrorByDay[day]"
        class="px-2.5 py-1 text-xs border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50"
        @click="store.fetchDailyTotals(day)"
      >
        Check nutrition
      </button>
      <button
        v-else-if="store.totalsLoadingByDay[day]"
        class="px-2.5 py-1 text-xs border border-gray-300 rounded-md text-gray-400 bg-white"
        disabled
      >
        Checking…
      </button>
      <template v-else-if="store.totalsByDay[day]">
        <span class="text-gray-500">
          {{ Math.round(store.totalsByDay[day]!.kcal) }} kcal
          · P {{ store.totalsByDay[day]!.protein.toFixed(1) }}
          · C {{ store.totalsByDay[day]!.carbs.toFixed(1) }}<span
            v-if="store.totalsByDay[day]!.sugars > 0"
            class="text-gray-400"
          > (s {{ store.totalsByDay[day]!.sugars.toFixed(1) }})</span>
          · F {{ store.totalsByDay[day]!.fat.toFixed(1) }}<span
            v-if="store.totalsByDay[day]!.sat_fat > 0"
            class="text-gray-400"
          > (sat {{ store.totalsByDay[day]!.sat_fat.toFixed(1) }})</span>
          · Fib {{ store.totalsByDay[day]!.fibers.toFixed(1) }}
        </span>
        <span
          v-if="store.totalsByDay[day]!.missing_items.length > 0"
          class="group relative text-amber-500 cursor-help"
        >
          ⚠
          <span
            class="invisible group-hover:visible absolute left-1/2 -translate-x-1/2 top-full mt-1 z-20 w-max max-w-xs whitespace-normal rounded-md bg-gray-900 text-white text-xs px-2 py-1.5 shadow-lg pointer-events-none"
          >
            <span class="block font-semibold mb-0.5">Без даних:</span>
            <span
              v-for="m in store.totalsByDay[day]!.missing_items"
              :key="`${m.type}-${m.grocy_id}`"
              class="block"
            >{{ m.type === 'product' ? 'Продукт' : 'Рецепт' }}: {{ m.name }}</span>
          </span>
        </span>
        <button
          v-if="store.totalsByDay[day]!.missing_items.length > 0"
          class="px-2 py-0.5 text-[11px] border border-amber-300 rounded-md text-amber-700 bg-amber-50 hover:bg-amber-100 disabled:opacity-50"
          :disabled="store.totalsLoadingByDay[day]"
          title="Re-sync missing products/recipes from Grocy and recompute totals."
          @click="store.syncMissingForDay(day)"
        >
          Sync now
        </button>
      </template>
      <template v-else-if="store.totalsErrorByDay[day]">
        <span class="text-red-600">Failed</span>
        <button
          class="px-2.5 py-1 text-xs border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50"
          @click="store.fetchDailyTotals(day)"
        >
          Retry
        </button>
      </template>
    </div>

    <div
      v-if="showInsufficientBlock"
      class="px-4 py-3 bg-amber-50 border-b border-amber-200 text-sm"
    >
      <p class="font-medium text-amber-800 mb-2">
        Insufficient stock for {{ day }}:
      </p>
      <ul class="text-amber-900 mb-3 space-y-0.5">
        <li
          v-for="p in dayCheck!.result!.products_to_buy_detailed"
          :key="p.product_id"
        >
          {{ p.name }} — {{ p.amount }}
          <span
            v-if="p.note"
            class="text-amber-700 text-xs"
          >({{ p.note }})</span>
        </li>
      </ul>
      <div class="flex gap-2">
        <button
          class="px-2.5 py-1 text-xs bg-amber-600 text-white rounded-md hover:bg-amber-700"
          @click="store.createDayCheckShoppingList(day)"
        >
          Create shopping list
        </button>
        <button
          class="px-2.5 py-1 text-xs border border-gray-300 rounded-md bg-white text-gray-700 hover:bg-gray-50"
          @click="store.cancelDayCheck(day)"
        >
          Cancel
        </button>
      </div>
      <p
        v-if="dayCheck?.error"
        class="text-xs text-red-600 mt-2"
      >
        {{ dayCheck.error }}
      </p>
    </div>

    <div
      v-if="isEmpty"
      class="px-4 py-3 text-sm text-gray-400"
    >
      No meals planned.
    </div>

    <div
      v-for="sectionId in sectionIds"
      v-else
      :key="sectionId"
      class="px-4 py-2 border-b border-gray-100 last:border-b-0"
    >
      <p class="text-xs uppercase tracking-wide text-gray-400 mb-1">
        {{ sectionsById[Number(sectionId)] || `Section #${sectionId}` }}
      </p>
      <ul class="space-y-1">
        <li
          v-for="row in rows[Number(sectionId)]"
          :key="row.id"
          class="flex items-start gap-3 text-sm"
        >
          <span
            class="inline-block px-2 py-0.5 text-[10px] rounded font-medium mt-0.5"
            :class="statusBadgeClass(row.status, row.done)"
          >{{ statusLabel(row.status, row.done) }}</span>
          <span class="flex-1 leading-snug">
            <template v-if="row.type === 'product'">
              <RouterLink
                v-if="row.product_name && row.product_local_id"
                :to="`/products/${row.product_local_id}`"
                class="text-indigo-600 hover:text-indigo-800 hover:underline"
              >{{ row.product_name }}</RouterLink>
              <span v-else>{{ row.product_name || `Product #${row.product_grocy_id}` }}</span>
              <a
                v-if="row.product_grocy_id && grocyProductUrl(row.product_grocy_id)"
                :href="grocyProductUrl(row.product_grocy_id)!"
                target="_blank"
                rel="noopener noreferrer"
                class="ml-1 text-gray-400 hover:text-gray-700 text-xs"
                title="Open in Grocy"
              >↗</a>
              <span
                v-if="editingId !== row.id"
                class="ml-1 text-gray-600"
              >— {{ formatAmount(row.product_amount) }} {{ row.product_qu_name || `qu ${row.product_qu_id}` }}</span>
              <span
                v-else
                class="ml-1 inline-flex items-center gap-1"
              >
                <input
                  ref="editInputRef"
                  v-model="editValue"
                  type="number"
                  step="any"
                  min="0"
                  class="w-20 px-1.5 py-0.5 text-sm border border-gray-300 rounded"
                  :disabled="editSubmitting"
                  @keydown.enter.prevent="confirmEdit(row)"
                  @keydown.esc.prevent="cancelEdit()"
                />
                <span class="text-gray-600 text-xs">{{ row.product_qu_name || `qu ${row.product_qu_id}` }}</span>
              </span>
            </template>
            <template v-else-if="row.type === 'recipe'">
              <RouterLink
                v-if="row.recipe_name && row.recipe_local_id"
                :to="`/recipes/${row.recipe_local_id}`"
                class="text-indigo-600 hover:text-indigo-800 hover:underline"
              >{{ row.recipe_name }}</RouterLink>
              <span v-else>{{ row.recipe_name || `Recipe #${row.recipe_grocy_id}` }}</span>
              <a
                v-if="row.recipe_grocy_id && grocyRecipeUrl(row.recipe_grocy_id)"
                :href="grocyRecipeUrl(row.recipe_grocy_id)!"
                target="_blank"
                rel="noopener noreferrer"
                class="ml-1 text-gray-400 hover:text-gray-700 text-xs"
                title="Open in Grocy"
              >↗</a>
              <span
                v-if="editingId !== row.id"
                class="ml-1 text-gray-600"
              >— {{ formatAmount(row.recipe_servings) }} servings</span>
              <span
                v-else
                class="ml-1 inline-flex items-center gap-1"
              >
                <input
                  ref="editInputRef"
                  v-model="editValue"
                  type="number"
                  step="any"
                  min="0"
                  class="w-20 px-1.5 py-0.5 text-sm border border-gray-300 rounded"
                  :disabled="editSubmitting"
                  @keydown.enter.prevent="confirmEdit(row)"
                  @keydown.esc.prevent="cancelEdit()"
                />
                <span class="text-gray-600 text-xs">servings</span>
              </span>
            </template>
            <template v-else>
              <Notebook
                :size="14"
                class="inline-block text-gray-400 mr-1 -mt-0.5"
              />
              <span
                v-if="editingId !== row.id"
                class="text-gray-800 whitespace-pre-wrap"
                :class="{ 'line-through text-gray-500': row.done }"
              >{{ row.note }}</span>
              <span
                v-else
                class="inline-flex items-center gap-1"
              >
                <input
                  ref="editInputRef"
                  v-model="editValue"
                  type="text"
                  class="flex-1 min-w-[200px] px-1.5 py-0.5 text-sm border border-gray-300 rounded"
                  :disabled="editSubmitting"
                  @keydown.enter.prevent="confirmEdit(row)"
                  @keydown.esc.prevent="cancelEdit()"
                />
              </span>
              <span
                v-if="noteNutrientsFor(row)"
                class="ml-2 text-xs text-gray-500"
              >
                <template v-if="noteNutrientsFor(row)!.kcal != null">~{{ Math.round(noteNutrientsFor(row)!.kcal!) }} kcal</template>
                <template v-if="noteNutrientsFor(row)!.protein != null"> · {{ noteNutrientsFor(row)!.protein!.toFixed(1) }}g P</template>
                <template v-if="noteNutrientsFor(row)!.carbs != null"> · {{ noteNutrientsFor(row)!.carbs!.toFixed(1) }}g C</template>
                <template v-if="noteNutrientsFor(row)!.fat != null"> · {{ noteNutrientsFor(row)!.fat!.toFixed(1) }}g F</template>
              </span>
            </template>
            <span
              v-if="editingId === row.id && editError"
              class="block text-xs text-red-600 mt-0.5"
            >{{ editError }}</span>
          </span>

          <!-- Failed-row actions (unchanged) -->
          <template v-if="row.status === 'failed'">
            <button
              class="text-xs text-indigo-600 hover:text-indigo-800"
              :title="row.error_message || ''"
              @click="store.retry(row.id)"
            >
              Retry
            </button>
            <button
              class="text-xs text-red-600 hover:text-red-800"
              @click="store.deleteLocal(row.id)"
            >
              Delete
            </button>
          </template>

          <!-- Synced + !done actions -->
          <template v-else-if="isEditable(row)">
            <template v-if="editingId === row.id">
              <button
                class="inline-flex items-center justify-center w-6 h-6 text-emerald-600 hover:text-emerald-800 disabled:opacity-50"
                :disabled="editSubmitting"
                title="Confirm"
                @click="confirmEdit(row)"
              >
                <Check :size="16" />
              </button>
              <button
                class="inline-flex items-center justify-center w-6 h-6 text-gray-500 hover:text-gray-700 disabled:opacity-50"
                :disabled="editSubmitting"
                title="Cancel"
                @click="cancelEdit()"
              >
                <X :size="16" />
              </button>
            </template>
            <template v-else-if="confirmingDeleteId === row.id">
              <span class="text-xs text-red-700 mr-1">Delete this row?</span>
              <button
                class="text-xs text-red-700 hover:text-red-900 font-semibold disabled:opacity-50"
                :disabled="deleteSubmitting"
                @click="confirmDelete(row)"
              >
                Yes
              </button>
              <button
                class="text-xs text-gray-600 hover:text-gray-800 disabled:opacity-50"
                :disabled="deleteSubmitting"
                @click="cancelConfirmDelete()"
              >
                No
              </button>
            </template>
            <template v-else>
              <button
                v-if="row.type === 'note'"
                class="inline-flex items-center justify-center w-6 h-6 text-gray-500 hover:text-emerald-600 disabled:opacity-50"
                :disabled="toggleNoteDoneSubmittingId === row.id"
                title="Mark done"
                @click="toggleNoteDone(row)"
              >
                <Check :size="14" />
              </button>
              <button
                class="inline-flex items-center justify-center w-6 h-6 text-gray-500 hover:text-indigo-600"
                :title="row.type === 'note' ? 'Edit note' : 'Edit amount'"
                @click="startEdit(row)"
              >
                <Pencil :size="14" />
              </button>
              <button
                class="inline-flex items-center justify-center w-6 h-6 text-gray-500 hover:text-red-600"
                title="Delete row"
                @click="startConfirmDelete(row)"
              >
                <Trash2 :size="14" />
              </button>
            </template>
          </template>
          <template v-else-if="row.type === 'note' && row.done && row.status === 'synced'">
            <button
              class="inline-flex items-center justify-center w-6 h-6 text-emerald-600 hover:text-gray-500 disabled:opacity-50"
              :disabled="toggleNoteDoneSubmittingId === row.id"
              title="Mark not done"
              @click="toggleNoteDone(row)"
            >
              <Check :size="14" />
            </button>
            <button
              class="inline-flex items-center justify-center w-6 h-6 text-gray-500 hover:text-red-600"
              title="Delete note"
              @click="startConfirmDelete(row)"
            >
              <Trash2 :size="14" />
            </button>
          </template>
        </li>
      </ul>
    </div>
  </div>
</template>
