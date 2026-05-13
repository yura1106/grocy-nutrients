<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useHouseholdStore } from '../store/household'
import { useMealPlanStore } from '../store/mealPlan'
import MealPlanModal from '../components/MealPlanModal.vue'
import PageHeader from '../components/PageHeader.vue'
import type { DraftLine } from '../components/MealPlanLineRow.vue'
import { addDays, formatAmount, startOfWeek } from '../utils/mealPlanFormat'

const householdStore = useHouseholdStore()
const store = useMealPlanStore()

const today = () => new Date().toISOString().slice(0, 10)

const startDate = ref<string>(startOfWeek(today()))
const endDate = ref<string>(addDays(startOfWeek(today()), 6))

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

const showDrawer = ref(false)
const drawerDate = ref<string>(today())

function emptyDraft(): DraftLine {
  return {
    type: 'product',
    productOption: null,
    recipeOption: null,
    amount: null,
    unit: null,
    section: store.sections[0] || null,
  }
}

const drafts = ref<DraftLine[]>([emptyDraft()])

function hasMeaningfulDrafts(): boolean {
  return drafts.value.some((d) => {
    if (d.type === 'product') return d.productOption !== null
    return d.recipeOption !== null
  })
}

async function reload() {
  await store.loadRange(startDate.value, endDate.value)
}

watch(
  () => householdStore.selectedId,
  (v) => {
    if (v) reload()
  },
)

onMounted(() => {
  if (householdStore.selectedId) reload()
})

watch(
  () => store.sections,
  (sections) => {
    if (sections.length === 0) return
    drafts.value.forEach((d) => {
      if (d.section == null) d.section = sections[0]
    })
  },
  { deep: false },
)

function openAdd(d?: string) {
  // Per-day buttons set initial date only when current draft is empty;
  // otherwise we preserve the user's in-progress draft and its date.
  if (d && !hasMeaningfulDrafts()) {
    drawerDate.value = d
  } else if (!hasMeaningfulDrafts()) {
    drawerDate.value = d || today()
  }
  showDrawer.value = true
}

function onDateChange(newDate: string) {
  // Changing the date wipes the draft per design decision.
  if (drawerDate.value !== newDate) {
    drawerDate.value = newDate
    drafts.value = [emptyDraft()]
  }
}

function onSaved() {
  drafts.value = [emptyDraft()]
  reload()
}

function onClose() {
  showDrawer.value = false
}

const sectionsById = computed(() => {
  const map: Record<number, string> = {}
  for (const s of store.sections) map[s.section_id] = s.name
  return map
})

const grouped = computed(() => store.linesByDayAndSection)
const days = computed(() => Object.keys(grouped.value).sort())

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
</script>

<template>
  <div class="p-6 space-y-4">
    <PageHeader title="Meal Plan" />

    <div class="flex flex-wrap items-end gap-3">
      <div>
        <label class="block text-xs font-medium text-gray-500 mb-1">From</label>
        <input
          v-model="startDate"
          type="date"
          class="py-1.5 px-2.5 text-sm bg-white border border-gray-300 rounded-md shadow-xs"
          @change="reload"
        />
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-500 mb-1">To</label>
        <input
          v-model="endDate"
          type="date"
          class="py-1.5 px-2.5 text-sm bg-white border border-gray-300 rounded-md shadow-xs"
          @change="reload"
        />
      </div>
      <button
        class="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        @click="openAdd()"
      >
        + Add to plan
      </button>
    </div>

    <div
      v-if="store.currentJob && (store.currentJob.state === 'PENDING' || store.currentJob.state === 'PROGRESS')"
      class="bg-blue-50 border border-blue-200 rounded-md p-3 text-sm"
    >
      Syncing {{ store.currentJob.current }}/{{ store.currentJob.total }}...
      <div class="w-full bg-blue-100 rounded-full h-2 mt-2">
        <div
          class="bg-blue-600 h-2 rounded-full transition-all"
          :style="{ width: store.currentJob.total ? `${(store.currentJob.current / store.currentJob.total) * 100}%` : '0%' }"
        ></div>
      </div>
    </div>

    <div
      v-if="store.error"
      class="text-sm text-red-600"
    >
      {{ store.error }}
    </div>

    <div
      v-if="!store.loading && days.length === 0"
      class="text-sm text-gray-500"
    >
      No meal plan entries in this date range.
    </div>

    <div
      v-for="day in days"
      :key="day"
      class="border border-gray-200 rounded-md"
    >
      <div class="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
        <h3 class="font-semibold text-gray-800">{{ day }}</h3>
        <button
          class="text-xs text-indigo-600 hover:text-indigo-800"
          @click="openAdd(day)"
        >
          + Add to {{ day }}
        </button>
      </div>

      <div
        v-for="(rows, sectionId) in grouped[day]"
        :key="sectionId"
        class="px-4 py-2 border-b border-gray-100 last:border-b-0"
      >
        <p class="text-xs uppercase tracking-wide text-gray-400 mb-1">
          {{ sectionsById[Number(sectionId)] || `Section #${sectionId}` }}
        </p>
        <ul class="space-y-1">
          <li
            v-for="row in rows"
            :key="row.id"
            class="flex items-center gap-3 text-sm"
          >
            <span
              class="inline-block px-2 py-0.5 text-[10px] rounded font-medium"
              :class="statusBadgeClass(row.status, row.done)"
            >{{ statusLabel(row.status, row.done) }}</span>
            <span class="flex-1 flex items-center gap-1 flex-wrap">
              <template v-if="row.type === 'product'">
                <RouterLink
                  v-if="row.product_name && row.product_id"
                  :to="`/products/${row.product_id}`"
                  class="text-indigo-600 hover:text-indigo-800 hover:underline"
                >{{ row.product_name }}</RouterLink>
                <span v-else>Product #{{ row.product_id }}</span>
                <a
                  v-if="row.product_id && grocyProductUrl(row.product_id)"
                  :href="grocyProductUrl(row.product_id)!"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-gray-400 hover:text-gray-700 text-xs"
                  title="Open in Grocy"
                >↗</a>
                <span class="text-gray-600">— {{ formatAmount(row.product_amount) }} {{ row.product_qu_name || `qu ${row.product_qu_id}` }}</span>
              </template>
              <template v-else>
                <RouterLink
                  v-if="row.recipe_name && row.recipe_id"
                  :to="`/recipes/${row.recipe_id}`"
                  class="text-indigo-600 hover:text-indigo-800 hover:underline"
                >{{ row.recipe_name }}</RouterLink>
                <span v-else>Recipe #{{ row.recipe_id }}</span>
                <a
                  v-if="row.recipe_id && grocyRecipeUrl(row.recipe_id)"
                  :href="grocyRecipeUrl(row.recipe_id)!"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-gray-400 hover:text-gray-700 text-xs"
                  title="Open in Grocy"
                >↗</a>
                <span class="text-gray-600">— {{ formatAmount(row.recipe_servings) }} servings</span>
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

    <MealPlanModal
      :open="showDrawer"
      :date="drawerDate"
      :drafts="drafts"
      @close="onClose"
      @update:date="onDateChange"
      @update:drafts="(d) => (drafts = d)"
      @saved="onSaved"
    />
  </div>
</template>
