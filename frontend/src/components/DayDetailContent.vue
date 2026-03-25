<template>
  <!-- Day totals bar -->
  <NutrientTotalsBar :totals="nutrientTotals" />

  <!-- Products list -->
  <div
    v-if="detail.products.length > 0"
    class="divide-y divide-gray-100 sm:max-h-[60vh] sm:overflow-y-auto"
  >
    <div
      v-for="p in detail.products"
      :key="p.id"
      class="px-4 py-3"
    >
      <div class="flex items-start justify-between gap-2">
        <div class="flex-1 min-w-0">
          <p
            class="text-sm font-medium text-gray-900 truncate"
            :title="p.product_name"
          >
            {{ p.product_name }}
          </p>
          <p class="text-xs text-gray-400 mt-0.5">{{ fmtQty(p.quantity) }}</p>
        </div>
        <div class="text-right shrink-0">
          <span class="text-sm font-semibold text-gray-800">{{ fmt(p.total_calories) }} kcal</span>
          <div
            v-if="p.cost != null"
            class="text-xs text-green-600 mt-0.5"
          >
            {{ p.cost.toFixed(2) }} ₴
          </div>
        </div>
      </div>
      <div class="mt-1.5 grid grid-cols-4 gap-x-3 text-xs text-gray-500">
        <div><span class="font-medium text-gray-700">{{ fmt(p.total_proteins) }}</span> prot</div>
        <div><span class="font-medium text-gray-700">{{ fmt(p.total_carbohydrates) }}</span> carbs</div>
        <div><span class="font-medium text-gray-700">{{ fmt(p.total_fats) }}</span> fat</div>
        <div><span class="font-medium text-gray-700">{{ fmt(p.total_fibers) }}</span> fiber</div>
      </div>
      <div class="mt-1 grid grid-cols-4 gap-x-3 text-xs text-gray-400">
        <div><span class="font-medium">{{ fmt(p.total_carbohydrates_of_sugars) }}</span> sugars</div>
        <div><span class="font-medium">{{ fmt(p.total_fats_saturated) }}</span> sat.fat</div>
        <div><span class="font-medium">{{ fmt(p.total_salt) }}</span> salt</div>
        <div></div>
      </div>
    </div>
  </div>

  <!-- Notes -->
  <div
    v-if="detail.notes.length > 0"
    class="border-t border-gray-200"
  >
    <div class="px-4 py-2 bg-amber-50 border-b border-amber-100">
      <p class="text-xs font-semibold text-amber-700 uppercase tracking-wide">Notes</p>
    </div>
    <div class="divide-y divide-gray-100">
      <div
        v-for="n in detail.notes"
        :key="n.id"
        class="px-4 py-3"
      >
        <p
          v-if="n.note"
          class="text-xs text-gray-500 mb-1.5 italic"
        >
          {{ n.note }}
        </p>
        <div class="grid grid-cols-4 gap-x-3 text-xs text-gray-500">
          <div><span class="font-semibold text-gray-800">{{ fmt(n.calories ?? 0) }}</span> kcal</div>
          <div><span class="font-medium text-gray-700">{{ fmt(n.proteins ?? 0) }}</span> prot</div>
          <div><span class="font-medium text-gray-700">{{ fmt(n.carbohydrates ?? 0) }}</span> carbs</div>
          <div><span class="font-medium text-gray-700">{{ fmt(n.fats ?? 0) }}</span> fat</div>
        </div>
        <div class="grid grid-cols-4 gap-x-3 text-xs text-gray-400 mt-1">
          <div><span class="font-medium">{{ fmt(n.carbohydrates_of_sugars ?? 0) }}</span> sugars</div>
          <div><span class="font-medium">{{ fmt(n.fats_saturated ?? 0) }}</span> sat.fat</div>
          <div><span class="font-medium">{{ fmt(n.fibers ?? 0) }}</span> fiber</div>
          <div><span class="font-medium">{{ fmt(n.salt ?? 0) }}</span> salt</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ConsumedDayDetail } from '../types/consumed'
import NutrientTotalsBar from './NutrientTotalsBar.vue'

const props = defineProps<{ detail: ConsumedDayDetail }>()

const nutrientTotals = computed(() => ({
  calories: props.detail.total_calories,
  proteins: props.detail.total_proteins,
  carbohydrates: props.detail.total_carbohydrates,
  carbohydrates_of_sugars: props.detail.total_carbohydrates_of_sugars,
  fats: props.detail.total_fats,
  fats_saturated: props.detail.total_fats_saturated,
  fibers: props.detail.total_fibers,
  salt: props.detail.total_salt,
  cost: props.detail.total_cost,
}))

const fmt = (val: number): string => val.toFixed(1)

const fmtQty = (qty: number): string => {
  if (qty >= 1000) return `${(qty / 1000).toFixed(2)} kg`
  return `${qty.toFixed(1)} g`
}
</script>
