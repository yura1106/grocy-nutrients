<template>
  <div class="container mx-auto px-4 py-8">
    <!-- Header -->
    <div class="mb-6">
      <router-link to="/products" class="text-blue-600 hover:text-blue-800 mb-4 inline-block">
        ← Back to Products
      </router-link>
      <div class="flex items-center justify-between">
        <h1 class="text-3xl font-bold text-gray-900">{{ product?.name || 'Loading...' }}</h1>
        <button
          v-if="product"
          @click="syncProduct"
          :disabled="syncing"
          class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg v-if="syncing" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          {{ syncing ? 'Syncing...' : 'Sync from Grocy' }}
        </button>
      </div>
      <div v-if="product" class="mt-2 text-gray-600">
        <span>Grocy ID: {{ product.grocy_id }}</span>
        <span class="ml-4">QU Stock: {{ product.qu_id_stock ?? 'N/A' }}</span>
        <span class="ml-4">Created: {{ formatDate(product.created_at) }}</span>
        <span class="ml-4">
          <span v-if="product.active" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">Active</span>
          <span v-else class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">Inactive</span>
        </span>
      </div>
    </div>

    <!-- Sync messages -->
    <div v-if="syncError" class="bg-red-50 border-l-4 border-red-400 p-4 mb-4">
      <p class="text-sm text-red-700">{{ syncError }}</p>
    </div>
    <div v-if="syncSuccess" class="bg-green-50 border-l-4 border-green-400 p-4 mb-4">
      <p class="text-sm text-green-700">{{ syncSuccess }}</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <p class="mt-2 text-gray-600">Loading product details...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
      <p class="text-red-800">{{ error }}</p>
    </div>

    <!-- Product Details -->
    <div v-else-if="product">
      <!-- Current Nutrients Card -->
      <div v-if="product.history.length > 0" class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-6">
        <div class="bg-orange-50 rounded-lg p-4 text-center">
          <div class="text-orange-600 text-xs font-medium">Calories</div>
          <div class="text-xl font-bold text-orange-900">{{ formatNumber(product.history[0]?.calories) }}</div>
        </div>
        <div class="bg-red-50 rounded-lg p-4 text-center">
          <div class="text-red-600 text-xs font-medium">Proteins</div>
          <div class="text-xl font-bold text-red-900">{{ formatNumber(product.history[0]?.proteins) }}</div>
        </div>
        <div class="bg-yellow-50 rounded-lg p-4 text-center">
          <div class="text-yellow-600 text-xs font-medium">Carbs</div>
          <div class="text-xl font-bold text-yellow-900">{{ formatNumber(product.history[0]?.carbohydrates) }}</div>
        </div>
        <div class="bg-blue-50 rounded-lg p-4 text-center">
          <div class="text-blue-600 text-xs font-medium">Sugars</div>
          <div class="text-xl font-bold text-blue-900">{{ formatNumber(product.history[0]?.carbohydrates_of_sugars) }}</div>
        </div>
        <div class="bg-purple-50 rounded-lg p-4 text-center">
          <div class="text-purple-600 text-xs font-medium">Fats</div>
          <div class="text-xl font-bold text-purple-900">{{ formatNumber(product.history[0]?.fats) }}</div>
        </div>
        <div class="bg-pink-50 rounded-lg p-4 text-center">
          <div class="text-pink-600 text-xs font-medium">Sat. Fats</div>
          <div class="text-xl font-bold text-pink-900">{{ formatNumber(product.history[0]?.fats_saturated) }}</div>
        </div>
        <div class="bg-teal-50 rounded-lg p-4 text-center">
          <div class="text-teal-600 text-xs font-medium">Salt</div>
          <div class="text-xl font-bold text-teal-900">{{ formatNumber(product.history[0]?.salt) }}</div>
        </div>
        <div class="bg-green-50 rounded-lg p-4 text-center">
          <div class="text-green-600 text-xs font-medium">Fibers</div>
          <div class="text-xl font-bold text-green-900">{{ formatNumber(product.history[0]?.fibers) }}</div>
        </div>
      </div>

      <!-- History Table -->
      <div class="bg-white rounded-lg shadow overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-xl font-semibold text-gray-900">Data History ({{ product.total_history }} records)</h2>
        </div>

        <div v-if="product.history.length === 0" class="px-6 py-8 text-center text-gray-500">
          <p>No data history yet.</p>
          <p class="mt-2 text-sm">Sync the product from Grocy to create the first record.</p>
        </div>

        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Calories</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Proteins</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Carbs</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sugars</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fats</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sat. Fats</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Salt</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fibers</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="item in product.history" :key="item.id" class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatDateTime(item.created_at) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.calories) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.proteins) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.carbohydrates) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.carbohydrates_of_sugars) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.fats) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.fats_saturated) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.salt) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.fibers) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { useHouseholdStore } from '@/store/household'

const householdStore = useHouseholdStore()

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

const loadProduct = async () => {
  loading.value = true
  error.value = null

  try {
    const productId = route.params.id
    const response = await axios.get(`/api/products/${productId}`, {
      params: { household_id: householdStore.selectedId },
    })
    product.value = response.data
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to load product details'
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
  } catch (err: any) {
    syncError.value = err.response?.data?.detail || 'Failed to sync product'
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

watch(() => householdStore.selectedId, (id) => {
  if (id !== null) loadProduct()
}, { immediate: true })
</script>
