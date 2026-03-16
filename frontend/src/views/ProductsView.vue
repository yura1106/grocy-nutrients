<template>
  <div class="bg-gray-100">
    <div class="py-10">
      <header>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold leading-tight text-gray-900">Products</h1>
        </div>
      </header>
      <main>
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
          <div class="px-4 py-8 sm:px-0">
            <!-- Loading state -->
            <div v-if="loading" class="flex justify-center items-center h-64">
              <svg class="animate-spin h-8 w-8 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </div>

            <!-- Error state -->
            <div v-else-if="error" class="bg-red-50 border-l-4 border-red-400 p-4">
              <div class="flex">
                <div class="flex-shrink-0">
                  <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="ml-3">
                  <p class="text-sm text-red-700">{{ error }}</p>
                </div>
              </div>
            </div>

            <!-- Products table -->
            <div v-else class="bg-white shadow overflow-hidden sm:rounded-lg">
              <!-- Pagination controls at top -->
              <div class="px-4 py-3 border-b border-gray-200 sm:px-6 flex justify-between items-center">
                <div class="flex items-center gap-4">
                  <label for="pageSize" class="text-sm font-medium text-gray-700">Products per page:</label>
                  <select
                    id="pageSize"
                    v-model.number="pageSize"
                    @change="onPageSizeChange"
                    class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block sm:text-sm border-gray-300 rounded-md"
                  >
                    <option :value="10">10</option>
                    <option :value="25">25</option>
                    <option :value="50">50</option>
                    <option :value="100">100</option>
                  </select>
                </div>
                <div class="text-sm text-gray-700">
                  Showing {{ skip + 1 }} to {{ Math.min(skip + pageSize, total) }} of {{ total }} products
                </div>
              </div>

              <!-- Table -->
              <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Grocy ID</th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Active</th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Calories</th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Carbs</th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Proteins</th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fats</th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Salt</th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fibers</th>
                      <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    <tr v-for="product in products" :key="product.id" class="hover:bg-gray-50">
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ product.id }}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ product.grocy_id }}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <router-link :to="`/products/${product.id}`" class="text-indigo-600 hover:text-indigo-900">{{ product.name }}</router-link>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <span v-if="product.active" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          Active
                        </span>
                        <span v-else class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                          Inactive
                        </span>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.price) }}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.calories) }}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.carbohydrates) }}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.proteins) }}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.fats) }}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.salt) }}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.fibers) }}</td>
                      <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          @click="syncProduct(product.grocy_id)"
                          :disabled="syncingProducts.has(product.grocy_id)"
                          class="text-green-600 hover:text-green-900 disabled:opacity-50"
                        >
                          {{ syncingProducts.has(product.grocy_id) ? 'Syncing...' : 'Sync' }}
                        </button>
                        <router-link :to="`/products/${product.id}`" class="text-indigo-600 hover:text-indigo-900 ml-4">
                          View
                        </router-link>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Pagination controls at bottom -->
              <div class="px-4 py-3 border-t border-gray-200 sm:px-6">
                <nav class="flex items-center justify-between" aria-label="Pagination">
                  <div class="hidden sm:block">
                    <p class="text-sm text-gray-700">
                      Page {{ currentPage }} of {{ totalPages }}
                    </p>
                  </div>
                  <div class="flex-1 flex justify-between sm:justify-end gap-2">
                    <button
                      @click="previousPage"
                      :disabled="currentPage === 1"
                      class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <button
                      @click="nextPage"
                      :disabled="currentPage >= totalPages"
                      class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </div>
                </nav>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import axios from 'axios'
import { useHouseholdStore } from '@/store/household'

const householdStore = useHouseholdStore()

interface Product {
  id: number
  grocy_id: number
  name: string
  active: boolean
  product_group_id: number
  created_at: string
  price: number | null
  calories: number | null
  carbohydrates: number | null
  carbohydrates_of_sugars: number | null
  proteins: number | null
  fats: number | null
  fats_saturated: number | null
  salt: number | null
  fibers: number | null
  data_created_at: string | null
}

interface ProductsResponse {
  products: Product[]
  total: number
  skip: number
  limit: number
}

const loading = ref(true)
const error = ref('')
const products = ref<Product[]>([])
const total = ref(0)
const skip = ref(0)
const pageSize = ref(10)
const syncingProducts = ref(new Set<number>())

const currentPage = computed(() => Math.floor(skip.value / pageSize.value) + 1)
const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

const fetchProducts = async () => {
  loading.value = true
  error.value = ''

  try {
    const response = await axios.get<ProductsResponse>('/api/products', {
      params: {
        skip: skip.value,
        limit: pageSize.value,
        household_id: householdStore.selectedId,
      },
    })

    products.value = response.data.products
    total.value = response.data.total
    skip.value = response.data.skip
  } catch (err: any) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'Failed to load products. Please try again.'
    }
  } finally {
    loading.value = false
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    skip.value += pageSize.value
    fetchProducts()
  }
}

const previousPage = () => {
  if (currentPage.value > 1) {
    skip.value = Math.max(0, skip.value - pageSize.value)
    fetchProducts()
  }
}

const onPageSizeChange = () => {
  skip.value = 0
  fetchProducts()
}

const syncProduct = async (grocyId: number) => {
  syncingProducts.value.add(grocyId)
  try {
    await axios.post(`/api/sync/grocy-product/${grocyId}`, null, {
      params: { household_id: householdStore.selectedId },
    })
    await fetchProducts()
  } catch (err: any) {
    error.value = err.response?.data?.detail || `Failed to sync product ${grocyId}`
  } finally {
    syncingProducts.value.delete(grocyId)
  }
}

const formatValue = (value: number | null): string => {
  if (value === null || value === undefined) {
    return '-'
  }
  return value.toFixed(2)
}

watch(() => householdStore.selectedId, (id) => {
  if (id !== null) fetchProducts()
}, { immediate: true })
</script>
