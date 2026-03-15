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
            <!-- CSV Import -->
            <div class="bg-white shadow sm:rounded-lg mb-6">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium leading-6 text-gray-900 mb-1">Import consumed_recipes.csv</h3>
                <p class="text-sm text-gray-500 mb-4">
                  Format: <code class="bg-gray-100 px-1 rounded">day,meal_plan_id,recipe_id</code>
                </p>
                <input
                  type="file"
                  accept=".csv"
                  @change="onFileSelected"
                  ref="fileInput"
                  class="block text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                />
              </div>
            </div>

            <!-- Import error -->
            <div v-if="importError" class="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
              <p class="text-sm text-red-700">{{ importError }}</p>
            </div>

            <!-- Import success -->
            <div v-if="importSuccess" class="bg-green-50 border-l-4 border-green-400 p-4 mb-6">
              <p class="text-sm text-green-700">{{ importSuccess }}</p>
            </div>

            <!-- Import preview -->
            <div v-if="previewRows.length > 0" class="bg-white shadow sm:rounded-lg mb-6">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">
                  Preview ({{ previewRows.length }} rows)
                </h3>
                <div class="overflow-x-auto">
                  <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Meal Plan ID</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Recipe ID</th>
                      </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                      <tr v-for="(row, idx) in previewRows" :key="idx">
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-400">{{ idx + 1 }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">{{ row.day }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ row.meal_plan_id }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ row.recipe_id }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div class="mt-4 flex gap-3">
                  <button
                    @click="importData"
                    :disabled="importing"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg v-if="importing" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    {{ importing ? 'Importing...' : 'Import Data' }}
                  </button>
                  <button
                    @click="clearPreview"
                    class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Clear
                  </button>
                </div>
              </div>
            </div>

            <!-- Fetch error -->
            <div v-if="error" class="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
              <p class="text-sm text-red-700">{{ error }}</p>
            </div>

            <!-- Loading -->
            <div v-if="loading" class="text-center py-12">
              <svg class="animate-spin h-8 w-8 text-indigo-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
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

interface ImportRow {
  day: string
  meal_plan_id: number
  recipe_id: number
}

// History list
const items = ref<HistoryItem[]>([])
const total = ref(0)
const skip = ref(0)
const limit = ref(50)
const loading = ref(false)
const error = ref('')

// Import
const fileInput = ref<HTMLInputElement | null>(null)
const previewRows = ref<ImportRow[]>([])
const importing = ref(false)
const importError = ref('')
const importSuccess = ref('')

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
  return new Date(isoStr).toLocaleString()
}

const onFileSelected = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (!input.files || !input.files[0]) return

  importError.value = ''
  importSuccess.value = ''

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const text = e.target?.result as string
      const lines = text.trim().split('\n')
      const rows: ImportRow[] = []

      for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim()
        if (!line) continue

        const parts = line.split(',')
        if (parts.length < 3) {
          importError.value = `Row ${i + 1}: expected 3 columns, got ${parts.length}`
          return
        }

        const meal_plan_id = parseInt(parts[1])
        const recipe_id = parseInt(parts[2])

        if (isNaN(meal_plan_id) || isNaN(recipe_id)) {
          importError.value = `Row ${i + 1}: meal_plan_id and recipe_id must be integers`
          return
        }

        rows.push({ day: parts[0].trim(), meal_plan_id, recipe_id })
      }

      if (rows.length === 0) {
        importError.value = 'No data rows found in CSV file.'
        return
      }

      previewRows.value = rows
    } catch {
      importError.value = 'Failed to parse CSV file.'
    }
  }
  reader.readAsText(input.files[0])
}

const importData = async () => {
  if (previewRows.value.length === 0) return

  importing.value = true
  importError.value = ''
  importSuccess.value = ''

  try {
    const response = await axios.post('/api/consumption/import-history', {
      rows: previewRows.value,
    })
    importSuccess.value = response.data.message
    previewRows.value = []
    if (fileInput.value) fileInput.value.value = ''
    skip.value = 0
    await fetchHistory()
  } catch (err: any) {
    importError.value = err.response?.data?.detail ?? 'Failed to import data. Please try again.'
  } finally {
    importing.value = false
  }
}

const clearPreview = () => {
  previewRows.value = []
  importError.value = ''
  importSuccess.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

onMounted(fetchHistory)
</script>
