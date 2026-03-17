<template>
  <!-- Day totals bar -->
  <div class="px-4 py-3 bg-indigo-50 border-b border-indigo-100">
    <div class="grid grid-cols-4 gap-2 text-center">
      <div>
        <div class="text-lg font-bold text-indigo-700">{{ fmt(detail.total_calories) }}</div>
        <div class="text-xs text-gray-500">kcal</div>
      </div>
      <div>
        <div class="text-base font-semibold text-gray-800">{{ fmt(detail.total_proteins) }}</div>
        <div class="text-xs text-gray-500">protein</div>
      </div>
      <div>
        <div class="text-base font-semibold text-gray-800">{{ fmt(detail.total_carbohydrates) }}</div>
        <div class="text-xs text-gray-500">carbs</div>
      </div>
      <div>
        <div class="text-base font-semibold text-gray-800">{{ fmt(detail.total_fats) }}</div>
        <div class="text-xs text-gray-500">fats</div>
      </div>
    </div>
    <div class="grid grid-cols-4 gap-2 text-center mt-2 pt-2 border-t border-indigo-100">
      <div>
        <div class="text-sm font-medium text-gray-700">{{ fmt(detail.total_carbohydrates_of_sugars) }}</div>
        <div class="text-xs text-gray-400">sugars</div>
      </div>
      <div>
        <div class="text-sm font-medium text-gray-700">{{ fmt(detail.total_fats_saturated) }}</div>
        <div class="text-xs text-gray-400">sat.fat</div>
      </div>
      <div>
        <div class="text-sm font-medium text-gray-700">{{ fmt(detail.total_fibers) }}</div>
        <div class="text-xs text-gray-400">fiber</div>
      </div>
      <div>
        <div class="text-sm font-medium text-gray-700">{{ fmt(detail.total_salt) }}</div>
        <div class="text-xs text-gray-400">salt</div>
      </div>
    </div>
    <div v-if="detail.total_cost != null" class="mt-2 pt-2 border-t border-indigo-100 text-center">
      <div class="text-base font-semibold text-green-700">{{ detail.total_cost.toFixed(2) }} ₴</div>
      <div class="text-xs text-gray-500">total cost</div>
    </div>
  </div>

  <!-- Products list -->
  <div v-if="detail.products.length > 0" class="divide-y divide-gray-100 sm:max-h-[60vh] sm:overflow-y-auto">
    <div v-for="p in detail.products" :key="p.id" class="px-4 py-3">
      <div class="flex items-start justify-between gap-2">
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-gray-900 truncate" :title="p.product_name">{{ p.product_name }}</p>
          <p class="text-xs text-gray-400 mt-0.5">{{ fmtQty(p.quantity) }}</p>
        </div>
        <div class="text-right shrink-0">
          <span class="text-sm font-semibold text-gray-800">{{ fmt(p.total_calories) }} kcal</span>
          <div v-if="p.cost != null" class="text-xs text-green-600 mt-0.5">{{ p.cost.toFixed(2) }} ₴</div>
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
  <div v-if="detail.notes.length > 0" class="border-t border-gray-200">
    <div class="px-4 py-2 bg-amber-50 border-b border-amber-100">
      <p class="text-xs font-semibold text-amber-700 uppercase tracking-wide">Notes</p>
    </div>
    <div class="divide-y divide-gray-100">
      <div v-for="n in detail.notes" :key="n.id" class="px-4 py-3">
        <p v-if="n.note" class="text-xs text-gray-500 mb-1.5 italic">{{ n.note }}</p>
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
interface ConsumedProductDetailItem {
  id: number
  product_name: string
  quantity: number
  recipe_grocy_id: number | null
  cost: number | null
  total_calories: number
  total_carbohydrates: number
  total_carbohydrates_of_sugars: number
  total_proteins: number
  total_fats: number
  total_fats_saturated: number
  total_salt: number
  total_fibers: number
}

interface NoteDetailItem {
  id: number
  note: string | null
  calories: number | null
  proteins: number | null
  carbohydrates: number | null
  carbohydrates_of_sugars: number | null
  fats: number | null
  fats_saturated: number | null
  salt: number | null
  fibers: number | null
}

interface ConsumedDayDetail {
  date: string
  products: ConsumedProductDetailItem[]
  notes: NoteDetailItem[]
  total_calories: number
  total_carbohydrates: number
  total_carbohydrates_of_sugars: number
  total_proteins: number
  total_fats: number
  total_fats_saturated: number
  total_salt: number
  total_fibers: number
  total_cost: number | null
}

defineProps<{ detail: ConsumedDayDetail }>()

const fmt = (val: number): string => val.toFixed(1)

const fmtQty = (qty: number): string => {
  if (qty >= 1000) return `${(qty / 1000).toFixed(2)} kg`
  return `${qty.toFixed(1)} g`
}
</script>
