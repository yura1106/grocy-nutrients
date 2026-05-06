<template>
  <section class="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
    <header class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3 mb-4">
      <div class="min-w-0">
        <h2 class="text-sm font-semibold text-gray-900 leading-snug">
          Середнє за {{ rangeDayCount }} {{ daysWord(rangeDayCount) }}
        </h2>
        <p class="text-xs text-gray-500 mt-0.5">{{ rangeSubtitle }}</p>
        <p
          v-if="!loading && !error && skippedDayCount > 0 && includedDayCount > 0"
          class="text-[11px] text-amber-600 mt-1"
        >
          Враховано {{ includedDayCount }} з {{ rangeDayCount }} {{ daysWord(rangeDayCount) }} —
          {{ skippedDayCount }} {{ daysWord(skippedDayCount) }} без споживання пропущено.
        </p>
        <div class="flex gap-3 mt-1.5">
          <div class="flex items-center gap-1">
            <span class="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
            <span class="text-[10px] text-gray-400">±5%</span>
          </div>
          <div class="flex items-center gap-1">
            <span class="inline-block w-2 h-2 rounded-full bg-amber-500"></span>
            <span class="text-[10px] text-gray-400">≥80%</span>
          </div>
          <div class="flex items-center gap-1">
            <span class="inline-block w-2 h-2 rounded-full bg-red-500"></span>
            <span class="text-[10px] text-gray-400">&gt;105%</span>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <DateRangePicker
          :from="from"
          :to="to"
          :is-default="isDefault"
          @update:range="onRangeChange"
          @clear="clearRange"
        />
        <button
          type="button"
          class="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors shadow-sm"
          @click="openChart"
        >
          <BarChart2 :size="14" />
          Графіки
        </button>
      </div>
    </header>

    <div :class="{ 'opacity-50 pointer-events-none transition-opacity': loading && !firstLoading }">
      <div
        v-if="firstLoading"
        class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2"
      >
        <div
          v-for="i in 8"
          :key="i"
          class="h-[88px] rounded-lg bg-gray-100 animate-pulse"
        ></div>
      </div>
      <div
        v-else-if="error"
        class="text-sm text-red-600 px-3 py-6 text-center"
      >
        Не вдалося завантажити середнє: {{ error }}
      </div>
      <div
        v-else-if="includedDayCount === 0"
        class="text-sm text-gray-500 px-3 py-6 text-center"
      >
        Немає даних за обраний період.
      </div>
      <div
        v-else
        class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2"
      >
        <NutrientSummaryCard
          v-for="n in averages"
          :key="n.key"
          :label="n.label"
          :unit="n.unit"
          :avg="n.avg"
          :limit="n.limit"
          :less-is-better="n.lessIsBetter"
          :decimals="n.decimals"
          :limit-coverage-days="n.limitCoverageDays"
          :included-day-count="includedDayCount"
        />
      </div>
    </div>

    <ChartModal
      v-if="chartLoaded"
      :open="chartOpen"
      :days="days"
      :effective-limits-by-date="effectiveLimitsByDate"
      @close="chartOpen = false"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref, defineAsyncComponent } from 'vue'
import { storeToRefs } from 'pinia'
import { BarChart2 } from 'lucide-vue-next'
import { useHouseholdStore } from '@/store/household'
import { useDateRangeQuery } from '@/composables/useDateRangeQuery'
import { useRangeAverages } from '@/composables/useRangeAverages'
import NutrientSummaryCard from '@/components/NutrientSummaryCard.vue'
import DateRangePicker from './DateRangePicker.vue'

const ChartModal = defineAsyncComponent(() => import('./ChartModal.vue'))

const householdStore = useHouseholdStore()
const { selectedId } = storeToRefs(householdStore)
const householdIdRef = computed(() => selectedId.value ?? null)

const { from, to, isDefault, setRange, clearRange } = useDateRangeQuery()

const {
  averages,
  loading,
  firstLoading,
  error,
  days,
  effectiveLimitsByDate,
  includedDayCount,
  skippedDayCount,
  rangeDayCount,
} = useRangeAverages(householdIdRef, from, to)

const chartOpen = ref(false)
const chartLoaded = ref(false)
function openChart(): void {
  chartLoaded.value = true
  chartOpen.value = true
}

function onRangeChange(newFrom: string, newTo: string): void {
  setRange(newFrom, newTo)
}

const rangeSubtitle = computed(() => {
  const fmt = new Intl.DateTimeFormat('uk-UA', { day: 'numeric', month: 'short', year: 'numeric' })
  const f = new Date(from.value + 'T00:00:00')
  const t = new Date(to.value + 'T00:00:00')
  return `${fmt.format(f)} – ${fmt.format(t)}`
})

function daysWord(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'день'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'дні'
  return 'днів'
}
</script>
