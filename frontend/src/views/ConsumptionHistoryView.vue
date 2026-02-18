<template>
  <div class="bg-gray-100">
    <div class="py-10">
      <header>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold leading-tight text-gray-900">Consumption History</h1>
          <p class="mt-2 text-sm text-gray-600">Meal plan consumption records</p>
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
              <p class="mt-2 text-sm text-gray-500">Loading history...</p>
            </div>

            <!-- Table -->
            <div v-if="!loading && items.length > 0" class="bg-white shadow overflow-hidden sm:rounded-lg">
              <div class="px-4 py-5 sm:px-6 border-b border-gray-200 flex justify-between items-center">
                <div>
                  <h3 class="text-lg font-medium text-gray-900">Records</h3>
                  <p class="text-sm text-gray-500">Total: {{ total }}</p>
                </div>
              </div>
              <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Recipe</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Recipe Grocy ID</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Meal Plan ID</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created At</th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    <tr v-for="item in items" :key="item.id">
                      <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ item.date }}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ item.recipe_name }}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ item.recipe_grocy_id }}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ item.meal_plan_id }}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatDate(item.created_at) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Pagination -->
              <div v-if="total > limit" class="px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
                <div class="flex-1 flex justify-between sm:hidden">
                  <button @click="prevPage" :disabled="skip === 0" class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50">Previous</button>
                  <button @click="nextPage" :disabled="skip + limit >= total" class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50">Next</button>
                </div>
                <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                  <p class="text-sm text-gray-700">
                    Showing <span class="font-medium">{{ skip + 1 }}</span> to <span class="font-medium">{{ Math.min(skip + limit, total) }}</span> of <span class="font-medium">{{ total }}</span> results
                  </p>
                  <div>
                    <button @click="prevPage" :disabled="skip === 0" class="relative inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-l-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50">Previous</button>
                    <button @click="nextPage" :disabled="skip + limit >= total" class="relative inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-r-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50">Next</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Empty state -->
            <div v-if="!loading && items.length === 0 && !error" class="text-center py-12 bg-white shadow sm:rounded-lg">
              <p class="text-sm text-gray-500">No consumption records yet.</p>
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

interface HistoryItem {
  id: number
  date: string
  meal_plan_id: number
  recipe_grocy_id: number
  recipe_name: string | null
  created_at: string | null
}

const items = ref<HistoryItem[]>([])
const total = ref(0)
const skip = ref(0)
const limit = ref(50)
const loading = ref(false)
const error = ref('')

const fetchHistory = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await axios.get('/api/consumption/history', {
      params: { skip: skip.value, limit: limit.value },
    })
    items.value = response.data.items
    total.value = response.data.total
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to load consumption history.'
  } finally {
    loading.value = false
  }
}

const prevPage = () => {
  skip.value = Math.max(0, skip.value - limit.value)
  fetchHistory()
}

const nextPage = () => {
  if (skip.value + limit.value < total.value) {
    skip.value += limit.value
    fetchHistory()
  }
}

const formatDate = (isoStr: string | null): string => {
  if (!isoStr) return '-'
  const d = new Date(isoStr)
  return d.toLocaleString()
}

onMounted(fetchHistory)
</script>
