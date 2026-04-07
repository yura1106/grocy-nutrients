<template>
  <div
    v-if="products.length > 0"
    class="divide-y divide-gray-100"
  >
    <div
      v-for="p in products"
      :key="p.id"
      class="px-4 py-3 border-l-2 transition-colors"
      :class="productClassesMap.get(p.id)!.border"
    >
      <div class="flex items-start justify-between gap-2">
        <div class="flex-1 min-w-0">
          <p
            class="text-sm font-medium truncate"
            :class="productClassesMap.get(p.id)!.name"
            :title="p.product_name"
          >
            {{ p.product_name }}
          </p>
          <p class="text-xs text-gray-400 mt-0.5">{{ fmtQty(p.quantity) }}</p>
        </div>
        <div class="text-right shrink-0">
          <span
            class="text-sm font-semibold"
            :class="productNutrientTextClass(p.total_calories, norms?.daily_calories) || 'text-gray-800'"
          >{{ fmt(p.total_calories) }} kcal</span>
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
        <div>
          <span
            class="font-medium"
            :class="productNutrientTextClass(p.total_carbohydrates_of_sugars, norms?.daily_carbohydrates_of_sugars) || 'text-gray-500'"
          >{{ fmt(p.total_carbohydrates_of_sugars) }}</span> sugars
        </div>
        <div>
          <span
            class="font-medium"
            :class="productNutrientTextClass(p.total_fats_saturated, norms?.daily_fats_saturated) || 'text-gray-500'"
          >{{ fmt(p.total_fats_saturated) }}</span> sat.fat
        </div>
        <div>
          <span
            class="font-medium"
            :class="productNutrientTextClass(p.total_salt, norms?.daily_salt) || 'text-gray-500'"
          >{{ fmt(p.total_salt) }}</span> salt
        </div>
        <div></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { NormValues } from '../composables/useNorms'
import { productNutrientColor, productNutrientTextClass } from '../composables/useNutrientColor'

interface ConsumedProduct {
  id: number
  product_name: string
  quantity: number
  cost: number | null
  total_calories: number
  total_proteins: number
  total_carbohydrates: number
  total_carbohydrates_of_sugars: number
  total_fats: number
  total_fats_saturated: number
  total_salt: number
  total_fibers: number
}

const props = defineProps<{
  products: ConsumedProduct[]
  norms?: NormValues | null
}>()

function productClasses(p: ConsumedProduct): { border: string; name: string } {
  if (!props.norms) return { border: 'border-transparent', name: 'text-gray-900' }
  const colors = [
    productNutrientColor(p.total_carbohydrates_of_sugars, props.norms.daily_carbohydrates_of_sugars),
    productNutrientColor(p.total_fats_saturated, props.norms.daily_fats_saturated),
    productNutrientColor(p.total_salt, props.norms.daily_salt),
    productNutrientColor(p.total_calories, props.norms.daily_calories),
  ]
  const hasRed = colors.some(c => c.severity === 'red')
  const hasAmber = colors.some(c => c.severity === 'amber')
  return {
    border: hasRed ? 'border-red-400' : hasAmber ? 'border-amber-300' : 'border-transparent',
    name: hasRed ? 'text-red-600' : 'text-gray-900',
  }
}

const productClassesMap = computed(() => {
  const map = new Map<number, { border: string; name: string }>()
  for (const p of props.products) {
    map.set(p.id, productClasses(p))
  }
  return map
})

const fmt = (val: number): string => val.toFixed(1)

const fmtQty = (qty: number): string => {
  if (qty >= 1000) return `${(qty / 1000).toFixed(2)} kg`
  return `${qty.toFixed(1)} g`
}
</script>
