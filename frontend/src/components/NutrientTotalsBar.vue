<template>
  <div class="px-4 py-3 bg-indigo-50 border-b border-indigo-100">
    <div class="grid grid-cols-4 gap-2 text-center">
      <!-- Calories -->
      <div :class="cellClass">
        <NutrientGauge
          v-if="norms?.daily_calories"
          :value="totals.calories"
          :max="norms?.daily_calories"
          :size="sizes.primary.gauge"
          :stroke-width="sizes.primary.stroke"
        />
        <div>
          <div
            :class="sizes.primary.label"
          >
            kcal
          </div>
          <div
            :class="[sizes.primary.text, 'font-bold', nutrientTextClass(totals.calories, norms?.daily_calories) || 'text-indigo-700']"
          >
            {{ fmt(totals.calories) }}
          </div>
        </div>
      </div>
      <!-- Proteins -->
      <div :class="cellClass">
        <NutrientGauge
          v-if="norms?.daily_proteins"
          :value="totals.proteins"
          :max="norms?.daily_proteins"
          :size="sizes.primary.gauge"
        />
        <div>
          <div
            :class="sizes.primary.label"
          >
            protein
          </div>
          <div
            :class="[sizes.primary.text, 'font-semibold', nutrientTextClass(totals.proteins, norms?.daily_proteins) || 'text-gray-800']"
          >
            {{ fmt(totals.proteins) }}
          </div>
        </div>
      </div>
      <!-- Carbs -->
      <div :class="cellClass">
        <NutrientGauge
          v-if="norms?.daily_carbohydrates"
          :value="totals.carbohydrates"
          :max="norms?.daily_carbohydrates"
          :size="sizes.primary.gauge"
        />
        <div>
          <div
            :class="sizes.primary.label"
          >
            carbs
          </div>
          <div
            :class="[sizes.primary.text, 'font-semibold', nutrientTextClass(totals.carbohydrates, norms?.daily_carbohydrates) || 'text-gray-800']"
          >
            {{ fmt(totals.carbohydrates) }}
          </div>
        </div>
      </div>
      <!-- Fats -->
      <div :class="cellClass">
        <NutrientGauge
          v-if="norms?.daily_fats"
          :value="totals.fats"
          :max="norms?.daily_fats"
          :size="sizes.primary.gauge"
        />
        <div>
          <div
            :class="sizes.primary.label"
          >
            fats
          </div>
          <div
            :class="[sizes.primary.text, 'font-semibold', nutrientTextClass(totals.fats, norms?.daily_fats) || 'text-gray-800']"
          >
            {{ fmt(totals.fats) }}
          </div>
        </div>
      </div>
    </div>
    <div class="grid grid-cols-4 gap-2 text-center mt-2 pt-2 border-t border-indigo-100">
      <!-- Sugars -->
      <div :class="cellClass">
        <NutrientGauge
          v-if="norms?.daily_carbohydrates_of_sugars"
          :value="totals.carbohydrates_of_sugars"
          :max="norms?.daily_carbohydrates_of_sugars"
          :size="sizes.secondary.gauge"
          :stroke-width="sizes.secondary.stroke"
          :less-is-better="true"
        />
        <div>
          <div
            :class="sizes.secondary.label"
          >
            sugars
          </div>
          <div
            :class="[sizes.secondary.text, 'font-medium', nutrientTextClass(totals.carbohydrates_of_sugars, norms?.daily_carbohydrates_of_sugars, true) || 'text-gray-700']"
          >
            {{ fmt(totals.carbohydrates_of_sugars) }}
          </div>
        </div>
      </div>
      <!-- Sat. fat -->
      <div :class="cellClass">
        <NutrientGauge
          v-if="norms?.daily_fats_saturated"
          :value="totals.fats_saturated"
          :max="norms?.daily_fats_saturated"
          :size="sizes.secondary.gauge"
          :stroke-width="sizes.secondary.stroke"
          :less-is-better="true"
        />
        <div>
          <div
            :class="sizes.secondary.label"
          >
            sat.fat
          </div>
          <div
            :class="[sizes.secondary.text, 'font-medium', nutrientTextClass(totals.fats_saturated, norms?.daily_fats_saturated, true) || 'text-gray-700']"
          >
            {{ fmt(totals.fats_saturated) }}
          </div>
        </div>
      </div>
      <!-- Fiber -->
      <div :class="cellClass">
        <NutrientGauge
          v-if="norms?.daily_fibers"
          :value="totals.fibers"
          :max="norms?.daily_fibers"
          :size="sizes.secondary.gauge"
          :stroke-width="sizes.secondary.stroke"
        />
        <div>
          <div
            :class="sizes.secondary.label"
          >
            fiber
          </div>
          <div
            :class="[sizes.secondary.text, 'font-medium', nutrientTextClass(totals.fibers, norms?.daily_fibers) || 'text-gray-700']"
          >
            {{ fmt(totals.fibers) }}
          </div>
        </div>
      </div>
      <!-- Salt -->
      <div :class="cellClass">
        <NutrientGauge
          v-if="norms?.daily_salt"
          :value="totals.salt"
          :max="norms?.daily_salt"
          :size="sizes.secondary.gauge"
          :stroke-width="sizes.secondary.stroke"
          :less-is-better="true"
        />
        <div>
          <div
            :class="sizes.secondary.label"
          >
            salt
          </div>
          <div
            :class="[sizes.secondary.text, 'font-medium', nutrientTextClass(totals.salt, norms?.daily_salt, true) || 'text-gray-700']"
          >
            {{ fmt(totals.salt) }}
          </div>
        </div>
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
import type { NormValues } from '../composables/useNorms'
import { nutrientTextClass } from '../composables/useNutrientColor'
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

const props = withDefaults(defineProps<{
  totals: NutrientTotals
  norms?: NormValues | null
  layout?: 'vertical' | 'horizontal'
}>(), {
  norms: null,
  layout: 'vertical',
})

const isHorizontal = computed(() => props.layout === 'horizontal')

const cellClass = computed(() =>
  isHorizontal.value
    ? 'flex flex-row items-center justify-center gap-2'
    : 'flex flex-col items-center',
)

const sizes = computed(() =>
  isHorizontal.value
    ? {
        primary: { gauge: 56, stroke: 5, text: 'text-2xl', label: 'text-xs text-gray-500' },
        secondary: { gauge: 44, stroke: 4, text: 'text-lg', label: 'text-xs text-gray-400' },
      }
    : {
        primary: { gauge: 48, stroke: 4, text: 'text-xl', label: 'text-sm text-gray-500' },
        secondary: { gauge: 36, stroke: 3, text: 'text-base', label: 'text-xs text-gray-400' },
      },
)

const norms = computed(() => props.norms)

const fmt = (val: number): string => val.toFixed(1)
</script>
