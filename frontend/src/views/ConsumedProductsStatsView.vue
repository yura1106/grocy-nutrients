<template>
  <div class="bg-gray-100 min-h-screen">
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

            <div v-if="!loading && days.length > 0" class="sm:flex sm:gap-6">
              <!-- Left: summary table -->
              <div class="flex-1 min-w-0">
                <div class="bg-white shadow overflow-hidden sm:rounded-lg">
                  <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                    <h3 class="text-lg font-medium text-gray-900">Daily Nutrients</h3>
                    <p class="text-sm text-gray-500">Total days: {{ total }}. Click a row to see details.</p>
                  </div>
                  <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                      <thead class="bg-gray-50">
                        <tr>
                          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                          <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Items</th>
                          <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Kcal</th>
                          <th class="hidden sm:table-cell px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Carbs</th>
                          <th class="hidden sm:table-cell px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Prot</th>
                          <th class="hidden sm:table-cell px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Fats</th>
                          <th class="hidden sm:table-cell px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Fiber</th>
                        </tr>
                      </thead>
                      <tbody class="bg-white divide-y divide-gray-200">
                        <tr
                          v-for="day in days"
                          :key="day.date"
                          @click="selectDay(day.date)"
                          class="cursor-pointer hover:bg-indigo-50 transition-colors"
                          :class="selectedDate === day.date ? 'bg-indigo-50 ring-2 ring-inset ring-indigo-400' : ''"
                        >
                          <td class="px-4 py-3 whitespace-nowrap text-sm font-medium" :class="selectedDate === day.date ? 'text-indigo-700' : 'text-gray-900'">
                            {{ day.date }}
                          </td>
                          <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500 text-right">{{ day.products_count }}</td>
                          <td class="px-4 py-3 whitespace-nowrap text-sm font-semibold text-right" :class="selectedDate === day.date ? 'text-indigo-700' : 'text-gray-900'">{{ fmt(day.total_calories) }}</td>
                          <td class="hidden sm:table-cell px-4 py-3 whitespace-nowrap text-sm text-gray-700 text-right">{{ fmt(day.total_carbohydrates) }}</td>
                          <td class="hidden sm:table-cell px-4 py-3 whitespace-nowrap text-sm text-gray-700 text-right">{{ fmt(day.total_proteins) }}</td>
                          <td class="hidden sm:table-cell px-4 py-3 whitespace-nowrap text-sm text-gray-700 text-right">{{ fmt(day.total_fats) }}</td>
                          <td class="hidden sm:table-cell px-4 py-3 whitespace-nowrap text-sm text-gray-500 text-right">{{ fmt(day.total_fibers) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <!-- Pagination -->
                  <div v-if="total > limit" class="px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
                    <p class="text-sm text-gray-700">
                      Showing <span class="font-medium">{{ skip + 1 }}</span>–<span class="font-medium">{{ Math.min(skip + limit, total) }}</span> of <span class="font-medium">{{ total }}</span>
                    </p>
                    <div>
                      <button @click="prevPage" :disabled="skip === 0" class="relative inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-l-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50">Previous</button>
                      <button @click="nextPage" :disabled="skip + limit >= total" class="relative inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-r-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50">Next</button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Desktop: right panel -->
              <div v-if="selectedDate" class="hidden sm:block w-[520px] shrink-0">
                <div class="bg-white shadow sm:rounded-lg sticky top-6">
                  <div class="px-4 py-4 border-b border-gray-200 flex items-center justify-between">
                    <div>
                      <h3 class="text-base font-semibold text-gray-900">{{ selectedDate }}</h3>
                      <p class="text-xs text-gray-500 mt-0.5">Detailed consumption</p>
                    </div>
                    <button @click="selectedDate = null; detail = null" class="text-gray-400 hover:text-gray-600">
                      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                    </button>
                  </div>
                  <div v-if="detailLoading" class="px-4 py-8 text-center">
                    <svg class="animate-spin h-6 w-6 text-indigo-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                  <template v-else-if="detail">
                    <DayDetailContent :detail="detail" />
                  </template>
                </div>
              </div>
            </div>

            <!-- Mobile: bottom sheet overlay -->
            <Teleport to="body">
              <div
                v-if="selectedDate"
                class="sm:hidden fixed inset-0 z-50 flex flex-col justify-end"
              >
                <!-- Backdrop -->
                <div class="absolute inset-0 bg-black/40" @click="selectedDate = null; detail = null"></div>
                <!-- Sheet -->
                <div class="relative bg-white rounded-t-2xl max-h-[85vh] flex flex-col shadow-xl">
                  <!-- Handle -->
                  <div class="flex justify-center pt-3 pb-1 shrink-0">
                    <div class="w-10 h-1 rounded-full bg-gray-300"></div>
                  </div>
                  <!-- Header -->
                  <div class="px-4 py-3 border-b border-gray-200 flex items-center justify-between shrink-0">
                    <div>
                      <h3 class="text-base font-semibold text-gray-900">{{ selectedDate }}</h3>
                      <p class="text-xs text-gray-500">Detailed consumption</p>
                    </div>
                    <button @click="selectedDate = null; detail = null" class="text-gray-400 hover:text-gray-600 p-1">
                      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                    </button>
                  </div>
                  <!-- Loading -->
                  <div v-if="detailLoading" class="px-4 py-8 text-center">
                    <svg class="animate-spin h-6 w-6 text-indigo-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                  <!-- Content -->
                  <div v-else-if="detail" class="overflow-y-auto flex-1">
                    <DayDetailContent :detail="detail" />
                  </div>
                </div>
              </div>
            </Teleport>

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
import DayDetailContent from '../components/DayDetailContent.vue'

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

interface ConsumedProductDetailItem {
  id: number
  product_name: string
  quantity: number
  recipe_grocy_id: number | null
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
}

const days = ref<DailyNutrientStats[]>([])
const total = ref(0)
const skip = ref(0)
const limit = ref(60)
const loading = ref(false)
const error = ref('')

const selectedDate = ref<string | null>(null)
const detail = ref<ConsumedDayDetail | null>(null)
const detailLoading = ref(false)

const fmt = (val: number): string => val.toFixed(1)

const fmtQty = (qty: number): string => {
  if (qty >= 1000) return `${(qty / 1000).toFixed(2)} kg`
  return `${qty.toFixed(1)} g`
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

const selectDay = async (date: string) => {
  if (selectedDate.value === date) {
    selectedDate.value = null
    detail.value = null
    return
  }
  selectedDate.value = date
  detail.value = null
  detailLoading.value = true
  try {
    const response = await axios.get(`/api/consumption/stats/${date}`)
    detail.value = response.data
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to load day detail.'
    selectedDate.value = null
  } finally {
    detailLoading.value = false
  }
}

const prevPage = () => {
  skip.value = Math.max(0, skip.value - limit.value)
  selectedDate.value = null
  detail.value = null
  fetchStats()
}

const nextPage = () => {
  if (skip.value + limit.value < total.value) {
    skip.value += limit.value
    selectedDate.value = null
    detail.value = null
    fetchStats()
  }
}

onMounted(fetchStats)
</script>
