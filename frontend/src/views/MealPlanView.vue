<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import flatpickr from 'flatpickr'
import 'flatpickr/dist/flatpickr.min.css'
import { useHouseholdStore } from '../store/household'
import { useMealPlanStore } from '../store/mealPlan'
import MealPlanModal from '../components/MealPlanModal.vue'
import MealPlanDayCard from '../components/MealPlanDayCard.vue'
import PageHeader from '../components/PageHeader.vue'
import type { DraftLine } from '../components/MealPlanLineRow.vue'
import { addDays, startOfWeek, todayLocal } from '../utils/mealPlanFormat'

const householdStore = useHouseholdStore()
const store = useMealPlanStore()

const startDate = ref<string>(startOfWeek(todayLocal()))
const endDate = ref<string>(addDays(startOfWeek(todayLocal()), 6))

const startDateRef = ref<HTMLInputElement | null>(null)
const endDateRef = ref<HTMLInputElement | null>(null)

const showDrawer = ref(false)
const drawerDate = ref<string>(todayLocal())

function makeClientId(): string {
  const c = (globalThis as { crypto?: { randomUUID?: () => string } }).crypto
  if (c?.randomUUID) return c.randomUUID()
  return `d-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function emptyDraft(): DraftLine {
  return {
    clientId: makeClientId(),
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

  if (startDateRef.value) {
    flatpickr(startDateRef.value, {
      dateFormat: 'Y-m-d',
      defaultDate: startDate.value,
      locale: { firstDayOfWeek: 1 },
      onChange: (_dates, dateStr) => {
        startDate.value = dateStr
        reload()
      },
    })
  }
  if (endDateRef.value) {
    flatpickr(endDateRef.value, {
      dateFormat: 'Y-m-d',
      defaultDate: endDate.value,
      locale: { firstDayOfWeek: 1 },
      onChange: (_dates, dateStr) => {
        endDate.value = dateStr
        reload()
      },
    })
  }
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
    drawerDate.value = d || todayLocal()
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
const todayStr = computed(() => todayLocal())
</script>

<template>
  <div class="bg-gray-100">
    <PageHeader title="Meal Plan" />
    <main>
      <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
        <div class="px-4 pb-8 sm:px-0 space-y-4">
          <div class="flex flex-wrap items-end gap-3">
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">From</label>
              <input
                ref="startDateRef"
                :value="startDate"
                type="text"
                readonly
                placeholder="YYYY-MM-DD"
                class="py-1.5 px-2.5 text-sm bg-white border border-gray-300 rounded-md shadow-xs cursor-pointer"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">To</label>
              <input
                ref="endDateRef"
                :value="endDate"
                type="text"
                readonly
                placeholder="YYYY-MM-DD"
                class="py-1.5 px-2.5 text-sm bg-white border border-gray-300 rounded-md shadow-xs cursor-pointer"
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

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 items-start">
            <MealPlanDayCard
              v-for="day in days"
              :key="day"
              :day="day"
              :rows="grouped[day]"
              :sections-by-id="sectionsById"
              :show-consume="day === todayStr"
              @add-clicked="openAdd"
            />
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
      </div>
    </main>
  </div>
</template>
