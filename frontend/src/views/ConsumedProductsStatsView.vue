<template>
  <div class="bg-gray-100">
    <div class="py-10">
      <header>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold leading-tight text-gray-900">Consumed Products Statistics</h1>
          <p class="mt-2 text-sm text-gray-600">Daily nutrient totals from consumed products</p>
        </div>
      </header>
      <main>
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
          <div class="px-4 py-8 sm:px-0">
            <!-- Error -->
            <div v-if="error" class="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
              <p class="text-sm text-red-700">{{ error }}</p>
            </div>

            <!-- Loading -->
            <div v-if="loading" class="text-center py-12">
              <svg class="animate-spin h-8 w-8 text-indigo-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p class="mt-2 text-sm text-gray-500">Loading statistics...</p>
            </div>

            <!-- Table -->
            <div v-if="!loading && days.length > 0" class="bg-white shadow overflow-hidden sm:rounded-lg">
              <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                <h3 class="text-lg font-medium text-gray-900">Daily Nutrients</h3>
                <p class="text-sm text-gray-500">Total days: {{ total }}</p>
              </div>
              <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                      <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Products</th>
                      <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Calories</th>
                      <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Carbs</th>
                      <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Sugars</th>
                      <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Proteins</th>
                      <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Fats</th>
                      <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Sat. Fats</th>
                      <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Salt</th>
                      <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Fiber</th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    <tr v-for="day in days" :key="day.date">
                      <td class="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ day.date }}</td>
                      <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 text-right">{{ day.products_count }}</td>
                      <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-900 text-right font-medium">{{ fmt(day.total_calories) }}</td>
                      <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-700 text-right">{{ fmt(day.total_carbohydrates) }}</td>
                      <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 text-right">{{ fmt(day.total_carbohydrates_of_sugars) }}</td>
                      <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-700 text-right">{{ fmt(day.total_proteins) }}</td>
                      <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-700 text-right">{{ fmt(day.total_fats) }}</td>
                      <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 text-right">{{ fmt(day.total_fats_saturated) }}</td>
                      <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 text-right">{{ fmt(day.total_salt) }}</td>
                      <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-500 text-right">{{ fmt(day.total_fibers) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Pagination -->
              <div v-if="total > limit" class="px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
                <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                  <p class="text-sm text-gray-700">
                    Showing <span class="font-medium">{{ skip + 1 }}</span> to <span class="font-medium">{{ Math.min(skip + limit, total) }}</span> of <span class="font-medium">{{ total }}</span> days
                  </p>
                  <div>
                    <button @click="prevPage" :disabled="skip === 0" class="relative inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-l-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50">Previous</button>
                    <button @click="nextPage" :disabled="skip + limit >= total" class="relative inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-r-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50">Next</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Empty state -->
            <div v-if="!loading && days.length === 0 && !error" class="text-center py-12 bg-white shadow sm:rounded-lg">
              <p class="text-sm text-gray-500">No consumed products data yet.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

interface DailyNutrientStats {
  date: string
  total_calories: number
  total_carbohydrates: number
  total_carbohydrates_of_sugars: number
  total_proteins: number
  total_fats: number
  total_fats_saturated: number
  total_salt: number
  total_fibers: number
  products_count: number
}

const days = ref<DailyNutrientStats[]>([])
const total = ref(0)
const skip = ref(0)
const limit = ref(60)
const loading = ref(false)
const error = ref('')

const fmt = (val: number): string => {
  return val.toFixed(1)
}

const fetchStats = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await axios.get('/api/consumption/stats', {
      params: { skip: skip.value, limit: limit.value },
    })
    days.value = response.data.days
    total.value = response.data.total
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to load statistics.'
  } finally {
    loading.value = false
  }
}

const prevPage = () => {
  skip.value = Math.max(0, skip.value - limit.value)
  fetchStats()
}

const nextPage = () => {
  if (skip.value + limit.value < total.value) {
    skip.value += limit.value
    fetchStats()
  }
}

onMounted(fetchStats)
</script>
