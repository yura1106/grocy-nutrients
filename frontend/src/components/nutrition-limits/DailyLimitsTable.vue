<!-- frontend/src/components/nutrition-limits/DailyLimitsTable.vue -->
<template>
  <div class="bg-white shadow sm:rounded-lg overflow-hidden">
    <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
      <h3 class="text-lg font-medium text-gray-900">Saved Daily Limits</h3>
      <p class="text-sm text-gray-500">Total: {{ store.total }}</p>
    </div>

    <div
      v-if="store.loading"
      class="text-center py-8 text-sm text-gray-500"
    >
      Loading...
    </div>
    <div
      v-else-if="store.list.length === 0"
      class="text-center py-8 text-sm text-gray-400"
    >
      No records yet.
    </div>
    <div
      v-else
      class="overflow-x-auto"
    >
      <table class="min-w-full divide-y divide-gray-200 text-sm">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Weight</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Activity</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Kcal</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Prot</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Carbs</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Sugars</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Fats</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Sat.Fat</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Fiber</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Salt</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="item in store.list"
            :key="item.id"
            class="cursor-pointer hover:bg-indigo-50 transition-colors"
            @click="emit('edit', item)"
          >
            <td class="px-4 py-3 font-medium text-gray-900">{{ item.date }}</td>
            <td class="px-4 py-3 text-right text-gray-700">{{ item.body_weight ?? '—' }}</td>
            <td class="px-4 py-3 text-right text-gray-500 text-xs">{{ item.activity_level ?? '—' }}</td>
            <td class="px-4 py-3 text-right font-semibold text-indigo-700">{{ fmt(item.calories) }}</td>
            <td class="px-4 py-3 text-right text-gray-700">{{ fmt(item.proteins) }}</td>
            <td class="px-4 py-3 text-right text-gray-700">{{ fmt(item.carbohydrates) }}</td>
            <td class="px-4 py-3 text-right text-gray-700">{{ fmt(item.carbohydrates_of_sugars) }}</td>
            <td class="px-4 py-3 text-right text-gray-700">{{ fmt(item.fats) }}</td>
            <td class="px-4 py-3 text-right text-gray-700">{{ fmt(item.fats_saturated) }}</td>
            <td class="px-4 py-3 text-right text-gray-700">{{ fmt(item.fibers) }}</td>
            <td class="px-4 py-3 text-right text-gray-700">{{ fmt(item.salt) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <PaginationBar
      v-if="store.total > pageSize"
      :total="store.total"
      :skip="skip"
      :limit="pageSize"
      @update:skip="onSkipChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useNutritionLimitsStore } from '../../store/nutritionLimits'
import type { NutritionLimit } from '../../types/nutritionLimit'
import PaginationBar from '../PaginationBar.vue'

const store = useNutritionLimitsStore()
const pageSize = 20
const skip = ref(0)

const emit = defineEmits<{ edit: [item: NutritionLimit] }>()

const fmt = (val: number | null) => (val !== null ? val.toFixed(1) : '—')

async function onSkipChange(newSkip: number) {
  skip.value = newSkip
  await store.fetchList(newSkip, pageSize)
}

onMounted(() => store.fetchList(0, pageSize))
</script>
