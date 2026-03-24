<template>
  <div class="bg-gray-100">
    <div class="py-10">
      <header>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold leading-tight text-gray-900">History Import</h1>
          <p class="mt-2 text-sm text-gray-600">Import historical daily nutrition data from CSV</p>
        </div>
      </header>
      <main>
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
          <div class="px-4 py-8 sm:px-0">
            <!-- CSV Upload -->
            <div class="bg-white shadow sm:rounded-lg mb-6">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">Upload CSV File</h3>
                <p class="text-sm text-gray-500 mb-4 break-all">
                  CSV format: day,calories,proteins,carbohydrates,carbohydrates_of_sugars,fats,fats_saturated,salt,fibers
                </p>
                <div class="flex gap-4 items-end">
                  <div class="flex-1 max-w-sm">
                    <input
                      type="file"
                      accept=".csv"
                      @change="onFileSelected"
                      ref="fileInput"
                      class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                    />
                  </div>
                </div>
              </div>
            </div>

            <!-- Error -->
            <div
              v-if="error"
              class="bg-red-50 border-l-4 border-red-400 p-4 mb-6"
            >
              <div class="flex">
                <div class="ml-3">
                  <p class="text-sm text-red-700">{{ error }}</p>
                </div>
              </div>
            </div>

            <!-- Success -->
            <div
              v-if="successMessage"
              class="bg-green-50 border-l-4 border-green-400 p-4 mb-6"
            >
              <div class="flex">
                <div class="ml-3">
                  <p class="text-sm text-green-700">{{ successMessage }}</p>
                </div>
              </div>
            </div>

            <!-- Preview Table -->
            <div
              v-if="previewRows.length > 0"
              class="bg-white shadow sm:rounded-lg mb-6"
            >
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">
                  Preview ({{ previewRows.length }} rows)
                </h3>
                <div class="overflow-x-auto">
                  <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Calories</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Proteins</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Carbs</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sugars</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fats</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sat. Fat</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Salt</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fiber</th>
                      </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                      <tr
                        v-for="(row, idx) in previewRows"
                        :key="idx"
                      >
                        <td class="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">{{ row.day }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ row.calories.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ row.proteins.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ row.carbohydrates.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ row.carbohydrates_of_sugars.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ row.fats.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ row.fats_saturated.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ row.salt.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ row.fibers.toFixed(2) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div class="mt-4">
                  <button
                    @click="importData"
                    :disabled="importing"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg
                      v-if="importing"
                      class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        class="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        stroke-width="4"
                      />
                      <path
                        class="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    {{ importing ? 'Importing...' : 'Import Data' }}
                  </button>
                  <button
                    @click="clearPreview"
                    class="ml-3 inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Clear
                  </button>
                </div>
              </div>
            </div>

            <!-- Existing Records -->
            <div class="bg-white shadow sm:rounded-lg">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">
                  Imported Records
                  <span
                    v-if="totalRecords > 0"
                    class="text-sm font-normal text-gray-500"
                  >({{ totalRecords }} total)</span>
                </h3>

                <div
                  v-if="loadingRecords"
                  class="text-center py-8"
                >
                  <p class="text-sm text-gray-500">Loading...</p>
                </div>

                <div
                  v-else-if="records.length === 0"
                  class="text-center py-8"
                >
                  <p class="text-sm text-gray-500">No records imported yet.</p>
                </div>

                <div
                  v-else
                  class="overflow-x-auto"
                >
                  <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Calories</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Proteins</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Carbs</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sugars</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fats</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sat. Fat</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Salt</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fiber</th>
                      </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                      <tr
                        v-for="record in records"
                        :key="record.id"
                      >
                        <td class="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">{{ record.day }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ record.calories.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ record.proteins.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ record.carbohydrates.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ record.carbohydrates_of_sugars.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ record.fats.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ record.fats_saturated.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ record.salt.toFixed(2) }}</td>
                        <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ record.fibers.toFixed(2) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import axios, { isAxiosError } from 'axios'
import { useHouseholdStore } from '@/store/household'

const householdStore = useHouseholdStore()

interface NutritionRow {
  day: string
  calories: number
  proteins: number
  carbohydrates: number
  carbohydrates_of_sugars: number
  fats: number
  fats_saturated: number
  salt: number
  fibers: number
}

interface NutritionRecord extends NutritionRow {
  id: number
}

const fileInput = ref<HTMLInputElement | null>(null)
const previewRows = ref<NutritionRow[]>([])
const records = ref<NutritionRecord[]>([])
const totalRecords = ref(0)
const loadingRecords = ref(false)
const importing = ref(false)
const error = ref('')
const successMessage = ref('')

const onFileSelected = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (!input.files || !input.files[0]) return

  error.value = ''
  successMessage.value = ''

  const file = input.files[0]
  const reader = new FileReader()

  reader.onload = (e) => {
    try {
      const text = e.target?.result as string
      const lines = text.trim().split('\n')

      // Skip header row
      const rows: NutritionRow[] = []
      for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim()
        if (!line) continue

        const parts = line.split(',')
        if (parts.length < 9) {
          error.value = `Row ${i + 1}: expected 9 columns, got ${parts.length}`
          return
        }

        rows.push({
          day: parts[0],
          calories: parseFloat(parts[1]),
          proteins: parseFloat(parts[2]),
          carbohydrates: parseFloat(parts[3]),
          carbohydrates_of_sugars: parseFloat(parts[4]),
          fats: parseFloat(parts[5]),
          fats_saturated: parseFloat(parts[6]),
          salt: parseFloat(parts[7]),
          fibers: parseFloat(parts[8]),
        })
      }

      if (rows.length === 0) {
        error.value = 'No data rows found in CSV file.'
        return
      }

      previewRows.value = rows
    } catch {
      error.value = 'Failed to parse CSV file.'
    }
  }

  reader.readAsText(file)
}

const importData = async () => {
  if (previewRows.value.length === 0) return

  importing.value = true
  error.value = ''
  successMessage.value = ''

  try {
    const response = await axios.post('/api/daily-nutrition/import', {
      rows: previewRows.value,
    }, { params: { household_id: householdStore.selectedId } })
    successMessage.value = response.data.message
    previewRows.value = []
    if (fileInput.value) {
      fileInput.value.value = ''
    }
    await loadRecords()
  } catch (err: unknown) {
    const detail = isAxiosError(err) && err.response?.data?.detail
    if (detail) {
      error.value = detail
    } else {
      error.value = 'Failed to import data. Please try again.'
    }
  } finally {
    importing.value = false
  }
}

const clearPreview = () => {
  previewRows.value = []
  error.value = ''
  successMessage.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const loadRecords = async () => {
  loadingRecords.value = true
  try {
    const response = await axios.get('/api/daily-nutrition', {
      params: { skip: 0, limit: 200, household_id: householdStore.selectedId },
    })
    records.value = response.data.records
    totalRecords.value = response.data.total
  } catch (err: unknown) {
    console.error('Failed to load records:', err)
  } finally {
    loadingRecords.value = false
  }
}

watch(() => householdStore.selectedId, (id) => {
  if (id !== null) loadRecords()
}, { immediate: true })
</script>
