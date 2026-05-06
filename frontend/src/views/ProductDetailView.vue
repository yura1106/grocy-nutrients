<template>
  <div>
    <PageHeader :title="loading ? null : product?.name">
      <template #above-title>
        <router-link
          to="/products"
          class="text-indigo-600 hover:text-indigo-800 inline-block"
        >
          ← Back to Products
        </router-link>
      </template>
      <template
        v-if="product"
        #actions
      >
        <button
          @click="syncProduct"
          :disabled="syncing"
          class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-xs text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg
            v-if="syncing"
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
          {{ syncing ? 'Syncing...' : 'Sync from Grocy' }}
        </button>
      </template>
      <template
        v-if="product"
        #meta
      >
        <div class="text-gray-600">
          <span>Grocy ID: {{ product.grocy_id }}</span>
          <span class="ml-4">QU Stock: {{ product.qu_id_stock ?? 'N/A' }}</span>
          <span class="ml-4">Created: {{ formatDate(product.created_at) }}</span>
          <span class="ml-4">
            <span
              v-if="product.active"
              class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800"
            >Active</span>
            <span
              v-else
              class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800"
            >Inactive</span>
          </span>
        </div>
      </template>
    </PageHeader>

    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8">
      <!-- Sync messages -->
      <div
        v-if="syncError"
        class="bg-red-50 border-l-4 border-red-400 p-4 mb-4"
      >
        <p class="text-sm text-red-700">{{ syncError }}</p>
      </div>
      <div
        v-if="syncSuccess"
        class="bg-green-50 border-l-4 border-green-400 p-4 mb-4"
      >
        <p class="text-sm text-green-700">{{ syncSuccess }}</p>
      </div>

      <!-- Loading State -->
      <div
        v-if="loading"
        class="text-center py-8"
      >
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p class="mt-2 text-gray-600">Loading product details...</p>
      </div>

      <!-- Error State -->
      <div
        v-else-if="error"
        class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6"
      >
        <p class="text-red-800">{{ error }}</p>
      </div>

      <!-- Product Details -->
      <div v-else-if="product">
        <!-- History Table -->
        <div class="bg-white rounded-lg shadow-sm overflow-hidden">
          <div class="px-6 py-4 border-b border-gray-200">
            <h2 class="text-xl font-semibold text-gray-900">Data History ({{ product.total_history }} records)</h2>
          </div>

          <div
            v-if="product.history.length === 0"
            class="px-6 py-8 text-center text-gray-500"
          >
            <p>No data history yet.</p>
            <p class="mt-2 text-sm">Sync the product from Grocy to create the first record.</p>
          </div>

          <div
            v-else
            class="overflow-x-auto"
          >
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-8"></th>
                  <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Calories</th>
                  <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Proteins</th>
                  <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Carbs</th>
                  <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sugars</th>
                  <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fats</th>
                  <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sat. Fats</th>
                  <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Salt</th>
                  <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fibers</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <template
                  v-for="item in product.history"
                  :key="item.id"
                >
                  <tr
                    class="cursor-pointer"
                    :class="expandedRowId === item.id ? 'bg-indigo-50' : 'hover:bg-gray-50'"
                    @click="toggleRow(item.id)"
                  >
                    <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-400">
                      <svg
                        class="w-4 h-4 transition-transform"
                        :class="expandedRowId === item.id ? 'rotate-90' : ''"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M9 5l7 7-7 7"
                      /></svg>
                    </td>
                    <td
                      class="px-3 py-4 whitespace-nowrap text-sm"
                      :class="expandedRowId === item.id ? 'text-indigo-700 font-medium' : 'text-gray-900'"
                    >
                      {{ formatDateTime(item.created_at) }}
                    </td>
                    <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.calories) }}</td>
                    <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.proteins) }}</td>
                    <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.carbohydrates) }}</td>
                    <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.carbohydrates_of_sugars) }}</td>
                    <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.fats) }}</td>
                    <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.fats_saturated) }}</td>
                    <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.salt) }}</td>
                    <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.fibers) }}</td>
                  </tr>
                  <!-- Expanded detail row -->
                  <tr
                    v-if="expandedRowId === item.id"
                    :key="'detail-' + item.id"
                  >
                    <td
                      :colspan="10"
                      class="p-0"
                    >
                      <div class="bg-gray-50 border-t border-b border-gray-200">
                        <!-- Weight input -->
                        <div class="px-6 py-3 border-b border-gray-200 flex items-center gap-3">
                          <label class="text-sm font-medium text-gray-700">Weight:</label>
                          <input
                            v-model.number="customWeight"
                            type="number"
                            min="1"
                            max="10000"
                            step="1"
                            class="w-24 rounded-md border-gray-300 shadow-xs text-sm focus:border-indigo-500 focus:ring-indigo-500"
                          />
                          <span class="text-sm text-gray-500">g</span>
                          <button
                            v-if="customWeight !== 100"
                            @click="customWeight = 100"
                            class="text-xs text-indigo-600 hover:text-indigo-800"
                          >
                            reset to 100g
                          </button>
                        </div>
                        <!-- Nutrient gauges -->
                        <NutrientTotalsBar
                          v-if="expandedNutrients"
                          :totals="expandedNutrients"
                          :norms="norms"
                        />
                      </div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import axios, { isAxiosError } from 'axios'
import { useHouseholdStore } from '@/store/household'
import NutrientTotalsBar from '../components/NutrientTotalsBar.vue'
import PageHeader from '../components/PageHeader.vue'
import { useNorms } from '@/composables/useNorms'

const householdStore = useHouseholdStore()
const { norms } = useNorms()

interface ProductHistoryItem {
  id: number
  calories: number | null
  carbohydrates: number | null
  carbohydrates_of_sugars: number | null
  proteins: number | null
  fats: number | null
  fats_saturated: number | null
  salt: number | null
  fibers: number | null
  created_at: string
}

interface ProductDetail {
  id: number
  grocy_id: number
  name: string
  active: boolean
  product_group_id: number
  qu_id_stock: number | null
  created_at: string
  history: ProductHistoryItem[]
  total_history: number
}

const route = useRoute()
const product = ref<ProductDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const syncing = ref(false)
const syncError = ref('')
const syncSuccess = ref('')

const expandedRowId = ref<number | null>(null)
const customWeight = ref(100)

const toggleRow = (id: number) => {
  if (expandedRowId.value === id) {
    expandedRowId.value = null
  } else {
    expandedRowId.value = id
    customWeight.value = 100
  }
}

const expandedNutrients = computed(() => {
  const item = product.value?.history.find(h => h.id === expandedRowId.value)
  if (!item) return null
  const w = customWeight.value || 0
  return {
    calories: (item.calories ?? 0) * w,
    proteins: (item.proteins ?? 0) * w,
    carbohydrates: (item.carbohydrates ?? 0) * w,
    carbohydrates_of_sugars: (item.carbohydrates_of_sugars ?? 0) * w,
    fats: (item.fats ?? 0) * w,
    fats_saturated: (item.fats_saturated ?? 0) * w,
    fibers: (item.fibers ?? 0) * w,
    salt: (item.salt ?? 0) * w,
  }
})

const loadProduct = async () => {
  loading.value = true
  error.value = null

  try {
    const productId = route.params.id
    const response = await axios.get(`/api/products/${productId}`, {
      params: { household_id: householdStore.selectedId },
    })
    product.value = response.data
  } catch (err: unknown) {
    error.value = isAxiosError(err) && err.response?.data?.detail || 'Failed to load product details'
  } finally {
    loading.value = false
  }
}

const syncProduct = async () => {
  if (!product.value) return

  syncing.value = true
  syncError.value = ''
  syncSuccess.value = ''

  try {
    const response = await axios.post(`/api/sync/grocy-product/${product.value.grocy_id}`, null, {
      params: { household_id: householdStore.selectedId },
    })
    const data = response.data
    syncSuccess.value = `Synced! Updated: ${data.updated}, New history records: ${data.new_history_records}`
    await loadProduct()
  } catch (err: unknown) {
    syncError.value = isAxiosError(err) && err.response?.data?.detail || 'Failed to sync product'
  } finally {
    syncing.value = false
  }
}

const formatDate = (dateString: string): string => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('uk-UA', { year: 'numeric', month: 'long', day: 'numeric' })
}

const formatDateTime = (dateString: string): string => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleString('uk-UA', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const formatNumber = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '-'
  return value.toFixed(2)
}

watch(() => route.params.id, () => {
  product.value = null
})

watch(() => householdStore.selectedId, (id) => {
  if (id !== null) loadProduct()
}, { immediate: true })
</script>
