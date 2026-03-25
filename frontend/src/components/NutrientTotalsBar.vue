<template>
  <div class="px-4 py-3 bg-indigo-50 border-b border-indigo-100">
    <div class="grid grid-cols-4 gap-2 text-center">
      <div class="flex flex-col items-center">
        <NutrientGauge
          v-if="norms.daily_calories"
          :value="totals.calories"
          :max="norms.daily_calories"
          :size="44"
          :stroke-width="4"
        />
        <div
          class="text-lg font-bold text-indigo-700"
          :class="{ 'mt-1': norms.daily_calories }"
        >
          {{ fmt(totals.calories) }}
        </div>
        <div class="text-xs text-gray-500">kcal</div>
      </div>
      <div class="flex flex-col items-center">
        <NutrientGauge
          v-if="norms.daily_proteins"
          :value="totals.proteins"
          :max="norms.daily_proteins"
          :size="38"
        />
        <div
          class="text-base font-semibold text-gray-800"
          :class="{ 'mt-1': norms.daily_proteins }"
        >
          {{ fmt(totals.proteins) }}
        </div>
        <div class="text-xs text-gray-500">protein</div>
      </div>
      <div class="flex flex-col items-center">
        <NutrientGauge
          v-if="norms.daily_carbohydrates"
          :value="totals.carbohydrates"
          :max="norms.daily_carbohydrates"
          :size="38"
        />
        <div
          class="text-base font-semibold text-gray-800"
          :class="{ 'mt-1': norms.daily_carbohydrates }"
        >
          {{ fmt(totals.carbohydrates) }}
        </div>
        <div class="text-xs text-gray-500">carbs</div>
      </div>
      <div class="flex flex-col items-center">
        <NutrientGauge
          v-if="norms.daily_fats"
          :value="totals.fats"
          :max="norms.daily_fats"
          :size="38"
        />
        <div
          class="text-base font-semibold text-gray-800"
          :class="{ 'mt-1': norms.daily_fats }"
        >
          {{ fmt(totals.fats) }}
        </div>
        <div class="text-xs text-gray-500">fats</div>
      </div>
    </div>
    <div class="grid grid-cols-4 gap-2 text-center mt-2 pt-2 border-t border-indigo-100">
      <div class="flex flex-col items-center">
        <NutrientGauge
          v-if="norms.daily_carbohydrates_of_sugars"
          :value="totals.carbohydrates_of_sugars"
          :max="norms.daily_carbohydrates_of_sugars"
          :size="32"
          :stroke-width="3"
        />
        <div
          class="text-sm font-medium text-gray-700"
          :class="{ 'mt-0.5': norms.daily_carbohydrates_of_sugars }"
        >
          {{ fmt(totals.carbohydrates_of_sugars) }}
        </div>
        <div class="text-xs text-gray-400">sugars</div>
      </div>
      <div class="flex flex-col items-center">
        <NutrientGauge
          v-if="norms.daily_fats_saturated"
          :value="totals.fats_saturated"
          :max="norms.daily_fats_saturated"
          :size="32"
          :stroke-width="3"
        />
        <div
          class="text-sm font-medium text-gray-700"
          :class="{ 'mt-0.5': norms.daily_fats_saturated }"
        >
          {{ fmt(totals.fats_saturated) }}
        </div>
        <div class="text-xs text-gray-400">sat.fat</div>
      </div>
      <div class="flex flex-col items-center">
        <NutrientGauge
          v-if="norms.daily_fibers"
          :value="totals.fibers"
          :max="norms.daily_fibers"
          :size="32"
          :stroke-width="3"
        />
        <div
          class="text-sm font-medium text-gray-700"
          :class="{ 'mt-0.5': norms.daily_fibers }"
        >
          {{ fmt(totals.fibers) }}
        </div>
        <div class="text-xs text-gray-400">fiber</div>
      </div>
      <div class="flex flex-col items-center">
        <NutrientGauge
          v-if="norms.daily_salt"
          :value="totals.salt"
          :max="norms.daily_salt"
          :size="32"
          :stroke-width="3"
        />
        <div
          class="text-sm font-medium text-gray-700"
          :class="{ 'mt-0.5': norms.daily_salt }"
        >
          {{ fmt(totals.salt) }}
        </div>
        <div class="text-xs text-gray-400">salt</div>
      </div>
    </div>
    <div
      v-if="totals.cost != null"
      class="mt-2 pt-2 border-t border-indigo-100 text-center"
    >
      <div class="text-base font-semibold text-green-700">{{ totals.cost.toFixed(2) }} ₴</div>
      <div class="text-xs text-gray-500">total cost</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useHealthStore } from '../store/health'
import NutrientGauge from './NutrientGauge.vue'

export interface NutrientTotals {
  calories: number
  proteins: number
  carbohydrates: number
  carbohydrates_of_sugars: number
  fats: number
  fats_saturated: number
  fibers: number
  salt: number
  cost?: number | null
}

defineProps<{ totals: NutrientTotals }>()

const healthStore = useHealthStore()

const norms = computed(() => ({
  daily_calories: healthStore.params?.daily_calories ?? null,
  daily_proteins: healthStore.params?.daily_proteins ?? null,
  daily_fats: healthStore.params?.daily_fats ?? null,
  daily_carbohydrates: healthStore.params?.daily_carbohydrates ?? null,
  daily_carbohydrates_of_sugars: healthStore.params?.daily_carbohydrates_of_sugars ?? null,
  daily_fats_saturated: healthStore.params?.daily_fats_saturated ?? null,
  daily_fibers: healthStore.params?.daily_fibers ?? null,
  daily_salt: healthStore.params?.daily_salt ?? null,
}))

const fmt = (val: number): string => val.toFixed(1)
</script>
