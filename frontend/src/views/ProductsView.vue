<template>
  <div class="bg-gray-100">
    <PageHeader />
    <main>
      <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
        <div class="px-4 pb-8 sm:px-0">
          <!-- Success message -->
          <div
            v-if="successMessage"
            class="mb-6 bg-green-50 border-l-4 border-green-400 p-4"
          >
            <div class="flex">
              <div class="shrink-0">
                <svg
                  class="h-5 w-5 text-green-400"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fill-rule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clip-rule="evenodd"
                  />
                </svg>
              </div>
              <div class="ml-3">
                <p class="text-sm text-green-700">{{ successMessage }}</p>
              </div>
              <div class="ml-auto pl-3">
                <button
                  @click="successMessage = ''"
                  class="inline-flex text-green-400 hover:text-green-600"
                >
                  <svg
                    class="h-5 w-5"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                      clip-rule="evenodd"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <!-- Error state -->
          <div
            v-if="error"
            class="mb-6 bg-red-50 border-l-4 border-red-400 p-4"
          >
            <div class="flex">
              <div class="shrink-0">
                <svg
                  class="h-5 w-5 text-red-400"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fill-rule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clip-rule="evenodd"
                  />
                </svg>
              </div>
              <div class="ml-3">
                <p class="text-sm text-red-700">{{ error }}</p>
              </div>
              <div class="ml-auto pl-3">
                <button
                  @click="error = ''"
                  class="inline-flex text-red-400 hover:text-red-600"
                >
                  <svg
                    class="h-5 w-5"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                      clip-rule="evenodd"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <!-- Search Bar -->
          <div class="mb-6 bg-white shadow-sm sm:rounded-lg p-4">
            <div class="flex gap-3">
              <div class="flex-1">
                <label
                  for="search"
                  class="sr-only"
                >Search products</label>
                <input
                  v-model="searchQuery"
                  @keyup.enter="handleSearch"
                  type="text"
                  id="search"
                  placeholder="Search by Grocy ID or product name..."
                  class="shadow-xs focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                />
              </div>
              <button
                @click="handleSearch"
                class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-xs text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                <svg
                  class="h-4 w-4 mr-2"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
                Search
              </button>
              <button
                v-if="searchQuery"
                @click="clearSearch"
                class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-xs text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                <svg
                  class="h-4 w-4 mr-2"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
                Clear
              </button>
            </div>
          </div>

          <!-- Sync single product by Grocy ID -->
          <div class="mb-6 bg-white shadow-sm sm:rounded-lg p-4">
            <div class="flex gap-3 items-end">
              <div>
                <label
                  for="syncGrocyId"
                  class="block text-sm font-medium text-gray-700"
                >Sync product by Grocy ID</label>
                <input
                  v-model.number="syncGrocyId"
                  @keyup.enter="syncByGrocyId"
                  type="number"
                  id="syncGrocyId"
                  placeholder="Grocy ID"
                  class="mt-1 shadow-xs focus:ring-indigo-500 focus:border-indigo-500 block w-40 sm:text-sm border-gray-300 rounded-md"
                />
              </div>
              <button
                @click="syncByGrocyId"
                :disabled="!syncGrocyId || syncingSingle"
                class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-xs text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
              >
                <svg
                  v-if="syncingSingle"
                  class="animate-spin -ml-1 mr-2 h-4 w-4"
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
                {{ syncingSingle ? 'Syncing...' : 'Sync' }}
              </button>
            </div>
          </div>

          <!-- Loading state -->
          <div
            v-if="loading"
            class="flex justify-center items-center h-64"
          >
            <svg
              class="animate-spin h-8 w-8 text-indigo-600"
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
          </div>

          <!-- Products table -->
          <div
            v-else
            class="bg-white shadow-sm overflow-hidden sm:rounded-lg"
          >
            <!-- Pagination controls at top -->
            <div class="px-4 py-3 border-b border-gray-200 sm:px-6 flex justify-between items-center">
              <div class="flex items-center gap-4">
                <label
                  for="pageSize"
                  class="text-sm font-medium text-gray-700"
                >Products per page:</label>
                <select
                  id="pageSize"
                  v-model.number="pageSize"
                  @change="onPageSizeChange"
                  class="shadow-xs focus:ring-indigo-500 focus:border-indigo-500 block sm:text-sm border-gray-300 rounded-md"
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
                    <th
                      scope="col"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      ID
                    </th>
                    <th
                      scope="col"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Grocy ID
                    </th>
                    <th
                      scope="col"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Name
                    </th>
                    <th
                      scope="col"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Active
                    </th>
                    <th
                      scope="col"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Calories
                    </th>
                    <th
                      scope="col"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Carbs
                    </th>
                    <th
                      scope="col"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Proteins
                    </th>
                    <th
                      scope="col"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Fats
                    </th>
                    <th
                      scope="col"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Salt
                    </th>
                    <th
                      scope="col"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Fibers
                    </th>
                    <th
                      scope="col"
                      class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr
                    v-for="product in products"
                    :key="product.id"
                    class="hover:bg-gray-50"
                  >
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ product.id }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ product.grocy_id }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <router-link
                        :to="`/products/${product.id}`"
                        class="text-indigo-600 hover:text-indigo-900"
                      >
                        {{ product.name }}
                      </router-link>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span
                        v-if="product.active"
                        class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800"
                      >
                        Active
                      </span>
                      <span
                        v-else
                        class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800"
                      >
                        Inactive
                      </span>
                    </td>
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
                      <router-link
                        :to="`/products/${product.id}`"
                        class="text-indigo-600 hover:text-indigo-900 ml-4"
                      >
                        View
                      </router-link>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <PaginationBar
              :skip="skip"
              :limit="pageSize"
              :total="total"
              @prev="previousPage"
              @next="nextPage"
            />
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import axios, { isAxiosError } from 'axios'
import { useHouseholdStore } from '@/store/household'
import PaginationBar from '@/components/PaginationBar.vue'
import PageHeader from '@/components/PageHeader.vue'

const householdStore = useHouseholdStore()

interface Product {
  id: number
  grocy_id: number
  name: string
  active: boolean
  product_group_id: number
  created_at: string
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
const successMessage = ref('')
const products = ref<Product[]>([])
const total = ref(0)
const skip = ref(0)
const pageSize = ref(10)
const searchQuery = ref('')
const syncingProducts = ref(new Set<number>())
const syncGrocyId = ref<number | null>(null)
const syncingSingle = ref(false)

const currentPage = computed(() => Math.floor(skip.value / pageSize.value) + 1)
const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

const fetchProducts = async () => {
  loading.value = true
  error.value = ''

  try {
    const params: Record<string, string | number | null> = {
      skip: skip.value,
      limit: pageSize.value,
      household_id: householdStore.selectedId,
    }

    if (searchQuery.value.trim()) {
      params.search = searchQuery.value.trim()
    }

    const response = await axios.get<ProductsResponse>('/api/products', { params })

    products.value = response.data.products
    total.value = response.data.total
    skip.value = response.data.skip
  } catch (err: unknown) {
    const detail = isAxiosError(err) && err.response?.data?.detail
    if (detail) {
      error.value = detail
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

const handleSearch = () => {
  skip.value = 0
  fetchProducts()
}

const clearSearch = () => {
  searchQuery.value = ''
  skip.value = 0
  fetchProducts()
}

const syncProduct = async (grocyId: number) => {
  syncingProducts.value.add(grocyId)
  error.value = ''
  successMessage.value = ''
  try {
    const response = await axios.post(`/api/sync/grocy-product/${grocyId}`, null, {
      params: { household_id: householdStore.selectedId },
    })
    successMessage.value = `Product synced! Updated: ${response.data.updated}, New history records: ${response.data.new_history_records}`
    await fetchProducts()
  } catch (err: unknown) {
    error.value = isAxiosError(err) && err.response?.data?.detail || `Failed to sync product ${grocyId}`
  } finally {
    syncingProducts.value.delete(grocyId)
  }
}

const syncByGrocyId = async () => {
  if (!syncGrocyId.value) return
  syncingSingle.value = true
  error.value = ''
  successMessage.value = ''
  try {
    const response = await axios.post(`/api/sync/grocy-product/${syncGrocyId.value}`, null, {
      params: { household_id: householdStore.selectedId },
    })
    successMessage.value = `Product synced! Updated: ${response.data.updated}, New history records: ${response.data.new_history_records}`
    await fetchProducts()
  } catch (err: unknown) {
    error.value = isAxiosError(err) && err.response?.data?.detail || `Failed to sync product ${syncGrocyId.value}`
  } finally {
    syncingSingle.value = false
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
