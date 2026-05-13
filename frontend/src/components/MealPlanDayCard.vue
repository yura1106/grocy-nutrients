<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useHouseholdStore } from '../store/household'
import { useMealPlanStore } from '../store/mealPlan'
import { formatAmount } from '../utils/mealPlanFormat'
import type { MealPlanLine } from '../types/mealPlan'

const props = withDefaults(
  defineProps<{
    day: string
    rows: Record<number, MealPlanLine[]>
    sectionsById: Record<number, string>
    showConsume?: boolean
    autoFetchTotals?: boolean
  }>(),
  {
    showConsume: false,
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

onMounted(() => {
  if (props.autoFetchTotals && !store.totalsByDay[props.day] && !store.totalsLoadingByDay[props.day]) {
    store.fetchDailyTotals(props.day)
  }
})
</script>

<template>
  <div class="border border-gray-200 rounded-md bg-white">
    <div class="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
      <h3 class="font-semibold text-gray-800">{{ day }}</h3>
      <div class="flex items-center gap-2">
        <button
          v-if="showConsume && !isEmpty"
          class="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded-md hover:bg-green-700"
          @click="onConsume"
        >
          Consume
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
              <span v-else>{{ row.product_name || `Product #${row.product_id}` }}</span>
              <a
                v-if="row.product_id && grocyProductUrl(row.product_id)"
                :href="grocyProductUrl(row.product_id)!"
                target="_blank"
                rel="noopener noreferrer"
                class="ml-1 text-gray-400 hover:text-gray-700 text-xs"
                title="Open in Grocy"
              >↗</a>
              <span class="ml-1 text-gray-600">— {{ formatAmount(row.product_amount) }} {{ row.product_qu_name || `qu ${row.product_qu_id}` }}</span>
            </template>
            <template v-else>
              <RouterLink
                v-if="row.recipe_name && row.recipe_local_id"
                :to="`/recipes/${row.recipe_local_id}`"
                class="text-indigo-600 hover:text-indigo-800 hover:underline"
              >{{ row.recipe_name }}</RouterLink>
              <span v-else>{{ row.recipe_name || `Recipe #${row.recipe_id}` }}</span>
              <a
                v-if="row.recipe_id && grocyRecipeUrl(row.recipe_id)"
                :href="grocyRecipeUrl(row.recipe_id)!"
                target="_blank"
                rel="noopener noreferrer"
                class="ml-1 text-gray-400 hover:text-gray-700 text-xs"
                title="Open in Grocy"
              >↗</a>
              <span class="ml-1 text-gray-600">— {{ formatAmount(row.recipe_servings) }} servings</span>
            </template>
          </span>
          <button
            v-if="row.status === 'failed'"
            class="text-xs text-indigo-600 hover:text-indigo-800"
            :title="row.error_message || ''"
            @click="store.retry(row.id)"
          >
            Retry
          </button>
          <button
            v-if="row.status === 'failed'"
            class="text-xs text-red-600 hover:text-red-800"
            @click="store.deleteLocal(row.id)"
          >
            Delete
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>
