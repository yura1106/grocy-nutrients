<template>
  <section class="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
    <div class="flex flex-col lg:flex-row gap-4">
      <div class="lg:w-56 shrink-0 flex flex-col gap-1">
        <h2 class="text-sm font-semibold text-gray-900 leading-snug">
          Середнє споживання нутрієнтів за останні {{ windowDays }} {{ daysWord(windowDays) }}
        </h2>
        <p class="text-xs text-gray-500 leading-relaxed">
          Порівняння факту з лімітами за останні
          <span class="font-medium text-gray-700">{{ windowDays }} {{ daysWord(windowDays) }}</span>.
        </p>
        <p
          v-if="!loading && !error && skippedDayCount > 0 && includedDayCount > 0"
          class="text-[11px] text-amber-600 mt-1"
        >
          Враховано {{ includedDayCount }} з {{ windowDays }} днів —
          {{ skippedDayCount }} {{ daysWord(skippedDayCount) }} без споживання пропущено.
        </p>

        <div class="flex gap-3 mt-1">
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

        <router-link
          to="/consumed-stats"
          class="text-xs text-indigo-600 hover:underline mt-2"
        >
          Детальніше →
        </router-link>
      </div>

      <div class="lg:w-px lg:h-auto h-px bg-gray-200 shrink-0"></div>

      <div class="flex-1 min-w-0">
        <div
          v-if="loading"
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
          class="flex items-center justify-center h-full text-sm text-red-600 px-3 py-6"
        >
          Не вдалося завантажити середнє за тиждень: {{ error }}
        </div>

        <div
          v-else-if="includedDayCount === 0"
          class="flex items-center justify-center h-full text-sm text-gray-500 px-3 py-6"
        >
          Немає даних за останні {{ windowDays }} {{ daysWord(windowDays) }}.
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
          />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useHouseholdStore } from '../store/household'
import { useWeeklyAverages } from '../composables/useWeeklyAverages'
import NutrientSummaryCard from './NutrientSummaryCard.vue'

const householdStore = useHouseholdStore()
const { selectedId } = storeToRefs(householdStore)

const householdIdRef = computed(() => selectedId.value ?? null)

const {
  averages,
  loading,
  error,
  windowDays,
  includedDayCount,
  skippedDayCount,
} = useWeeklyAverages(householdIdRef)

function daysWord(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'день'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'дні'
  return 'днів'
}
</script>
