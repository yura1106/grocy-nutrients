<template>
  <div class="min-h-screen bg-gray-100">
    <div class="py-10">
      <header>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold leading-tight text-gray-900">Dashboard</h1>
        </div>
      </header>
      <main>
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
          <div class="px-4 py-8 sm:px-0">
            <!-- Grocy Sync Section -->
            <div class="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
              <div class="px-4 py-5 sm:px-6">
                <h3 class="text-lg leading-6 font-medium text-gray-900">Grocy Product Sync</h3>
                <p class="mt-1 max-w-2xl text-sm text-gray-500">Synchronize products from your Grocy instance</p>
              </div>
              <div class="border-t border-gray-200 px-4 py-5 sm:px-6">
                <div class="space-y-4">
                  <div v-if="!hasGrocyKey" class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                    <div class="flex">
                      <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                        </svg>
                      </div>
                      <div class="ml-3">
                        <p class="text-sm text-yellow-700">
                          Please set your Grocy API key in Profile before syncing products.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div v-if="syncError" class="bg-red-50 border-l-4 border-red-400 p-4">
                    <div class="flex">
                      <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                        </svg>
                      </div>
                      <div class="ml-3">
                        <p class="text-sm text-red-700">{{ syncError }}</p>
                      </div>
                    </div>
                  </div>

                  <div v-if="syncSuccess" class="bg-green-50 border-l-4 border-green-400 p-4">
                    <div class="flex">
                      <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                        </svg>
                      </div>
                      <div class="ml-3">
                        <p class="text-sm text-green-700">{{ syncSuccess }}</p>
                      </div>
                    </div>
                  </div>

                  <!-- Sync All Products -->
                  <div>
                    <button
                      @click="syncAllProducts"
                      :disabled="syncLoading || !hasGrocyKey"
                      class="inline-flex items-center justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <svg v-if="syncLoading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <svg v-else class="-ml-1 mr-2 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      {{ syncLoading ? syncProgressText : 'Sync All Products' }}
                    </button>
                  </div>

                  <!-- Sync Single Product -->
                  <div class="border-t border-gray-200 pt-4">
                    <label for="productId" class="block text-sm font-medium text-gray-700 mb-2">Sync Single Product by Grocy ID</label>
                    <div class="flex gap-2">
                      <input
                        id="productId"
                        v-model.number="singleProductId"
                        type="number"
                        placeholder="Enter Grocy product ID"
                        class="flex-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                        :disabled="syncSingleLoading || !hasGrocyKey"
                      />
                      <button
                        @click="syncSingleProduct"
                        :disabled="syncSingleLoading || !hasGrocyKey || !singleProductId"
                        class="inline-flex items-center justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <svg v-if="syncSingleLoading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        {{ syncSingleLoading ? 'Syncing...' : 'Sync' }}
                      </button>
                    </div>
                  </div>

                  <!-- Single Product Sync Result -->
                  <div v-if="syncedProductData" class="border-t border-gray-200 pt-4 mt-4">
                    <h4 class="text-md font-medium text-gray-900 mb-3">Sync Result Details</h4>

                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      <!-- Grocy Data -->
                      <div class="bg-blue-50 rounded-lg p-4">
                        <h5 class="text-sm font-semibold text-blue-900 mb-2 flex items-center">
                          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                          </svg>
                          Data from Grocy API
                        </h5>
                        <dl class="space-y-1 text-sm">
                          <div class="flex justify-between">
                            <dt class="text-gray-600">ID:</dt>
                            <dd class="text-gray-900 font-medium">{{ syncedProductData.grocy_data.id }}</dd>
                          </div>
                          <div class="flex justify-between">
                            <dt class="text-gray-600">Name:</dt>
                            <dd class="text-gray-900 font-medium">{{ syncedProductData.grocy_data.name }}</dd>
                          </div>
                          <div class="flex justify-between">
                            <dt class="text-gray-600">Active:</dt>
                            <dd class="text-gray-900 font-medium">{{ syncedProductData.grocy_data.active ? 'Yes' : 'No' }}</dd>
                          </div>
                          <div class="flex justify-between">
                            <dt class="text-gray-600">Product Group:</dt>
                            <dd class="text-gray-900 font-medium">{{ syncedProductData.grocy_data.product_group_id }}</dd>
                          </div>
                          <div class="flex justify-between border-t border-blue-200 pt-1 mt-1">
                            <dt class="text-gray-600 font-semibold">QU Stock ID:</dt>
                            <dd class="text-blue-900 font-bold">{{ syncedProductData.grocy_data.qu_id_stock ?? 'N/A' }}</dd>
                          </div>
                          <div v-if="syncedProductData.grocy_data.calories" class="flex justify-between">
                            <dt class="text-gray-600">Calories:</dt>
                            <dd class="text-gray-900 font-medium">{{ syncedProductData.grocy_data.calories }}</dd>
                          </div>
                        </dl>
                      </div>

                      <!-- Local Database Data -->
                      <div class="bg-green-50 rounded-lg p-4">
                        <h5 class="text-sm font-semibold text-green-900 mb-2 flex items-center">
                          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                          </svg>
                          Data from Local Database
                        </h5>
                        <dl class="space-y-1 text-sm">
                          <div class="flex justify-between">
                            <dt class="text-gray-600">Local ID:</dt>
                            <dd class="text-gray-900 font-medium">{{ syncedProductData.local_data.id }}</dd>
                          </div>
                          <div class="flex justify-between">
                            <dt class="text-gray-600">Grocy ID:</dt>
                            <dd class="text-gray-900 font-medium">{{ syncedProductData.local_data.grocy_id }}</dd>
                          </div>
                          <div class="flex justify-between">
                            <dt class="text-gray-600">Name:</dt>
                            <dd class="text-gray-900 font-medium">{{ syncedProductData.local_data.name }}</dd>
                          </div>
                          <div class="flex justify-between">
                            <dt class="text-gray-600">Active:</dt>
                            <dd class="text-gray-900 font-medium">{{ syncedProductData.local_data.active ? 'Yes' : 'No' }}</dd>
                          </div>
                          <div class="flex justify-between border-t border-green-200 pt-1 mt-1">
                            <dt class="text-gray-600 font-semibold">QU Stock ID:</dt>
                            <dd class="text-green-900 font-bold">{{ syncedProductData.local_data.qu_id_stock ?? 'N/A' }}</dd>
                          </div>
                          <div v-if="syncedProductData.local_data.latest_data?.calories" class="flex justify-between">
                            <dt class="text-gray-600">Calories:</dt>
                            <dd class="text-gray-900 font-medium">{{ syncedProductData.local_data.latest_data.calories }}</dd>
                          </div>
                        </dl>
                      </div>
                    </div>

                    <!-- Nutritional Data (if available) -->
                    <div v-if="syncedProductData.local_data.latest_data" class="mt-4 bg-gray-50 rounded-lg p-4">
                      <h5 class="text-sm font-semibold text-gray-900 mb-2">Latest Nutritional Data</h5>
                      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                        <div v-if="syncedProductData.local_data.latest_data.proteins" class="text-center">
                          <dt class="text-gray-600">Proteins</dt>
                          <dd class="text-gray-900 font-medium text-lg">{{ syncedProductData.local_data.latest_data.proteins }}g</dd>
                        </div>
                        <div v-if="syncedProductData.local_data.latest_data.fats" class="text-center">
                          <dt class="text-gray-600">Fats</dt>
                          <dd class="text-gray-900 font-medium text-lg">{{ syncedProductData.local_data.latest_data.fats }}g</dd>
                        </div>
                        <div v-if="syncedProductData.local_data.latest_data.carbohydrates" class="text-center">
                          <dt class="text-gray-600">Carbs</dt>
                          <dd class="text-gray-900 font-medium text-lg">{{ syncedProductData.local_data.latest_data.carbohydrates }}g</dd>
                        </div>
                        <div v-if="syncedProductData.local_data.latest_data.fibers" class="text-center">
                          <dt class="text-gray-600">Fibers</dt>
                          <dd class="text-gray-900 font-medium text-lg">{{ syncedProductData.local_data.latest_data.fibers }}g</dd>
                        </div>
                      </div>
                    </div>

                    <button
                      @click="clearSyncResult"
                      class="mt-3 text-sm text-gray-600 hover:text-gray-900"
                    >
                      Clear result
                    </button>
                  </div>
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
import { onMounted, ref, computed } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../store/auth'

const authStore = useAuthStore()
const loading = ref(true)

// Sync state
const syncLoading = ref(false)
const syncSingleLoading = ref(false)
const syncError = ref('')
const syncSuccess = ref('')
const singleProductId = ref<number | null>(null)
const syncedProductData = ref<any>(null)

const hasGrocyKey = computed(() => {
  return !!(authStore.user as any)?.grocy_api_key
})

onMounted(async () => {
  try {
    if (!authStore.user) {
      await authStore.fetchUser()
    }
  } catch (error) {
    console.error('Error fetching user data:', error)
  } finally {
    loading.value = false
  }
})

const syncProgressText = ref('Syncing...')

const syncAllProducts = async () => {
  syncLoading.value = true
  syncError.value = ''
  syncSuccess.value = ''

  const CHUNK_SIZE = 50
  let offset = 0
  let totalProcessed = 0
  let totalUpdated = 0
  let totalNewRecords = 0
  let total = 0

  try {
    while (true) {
      syncProgressText.value = total > 0
        ? `Syncing... ${Math.min(offset, total)}/${total}`
        : 'Syncing...'

      const response = await axios.post(`/api/sync/grocy-products?offset=${offset}&limit=${CHUNK_SIZE}`)
      const data = response.data

      totalProcessed += data.processed
      totalUpdated += data.updated
      totalNewRecords += data.new_history_records
      total = data.total || 0

      if (!data.has_more) break
      offset += CHUNK_SIZE
    }

    syncSuccess.value = `Successfully synced! Processed: ${totalProcessed}, Updated: ${totalUpdated}, New history records: ${totalNewRecords}`
  } catch (err: any) {
    if (err.response?.data?.detail) {
      syncError.value = err.response.data.detail
    } else {
      syncError.value = 'Failed to sync products. Please check your Grocy API key and try again.'
    }
  } finally {
    syncLoading.value = false
  }
}

const syncSingleProduct = async () => {
  if (!singleProductId.value) return

  syncSingleLoading.value = true
  syncError.value = ''
  syncSuccess.value = ''
  syncedProductData.value = null

  try {
    const response = await axios.post(`/api/sync/grocy-product/${singleProductId.value}`)
    const data = response.data

    // Store detailed sync data
    syncedProductData.value = data

    syncSuccess.value = `Product ${singleProductId.value} synced! Updated: ${data.updated}, New history records: ${data.new_history_records}`
    singleProductId.value = null
  } catch (err: any) {
    if (err.response?.data?.detail) {
      syncError.value = err.response.data.detail
    } else {
      syncError.value = `Failed to sync product ${singleProductId.value}. Please check the product ID and try again.`
    }
  } finally {
    syncSingleLoading.value = false
  }
}

const clearSyncResult = () => {
  syncedProductData.value = null
  syncSuccess.value = ''
}
</script>
