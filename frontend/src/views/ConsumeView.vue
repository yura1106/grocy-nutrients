<template>
  <div class="min-h-screen bg-gray-100">
    <div class="py-10">
      <header>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold leading-tight text-gray-900">Consume Daily Plan</h1>
          <p class="mt-2 text-sm text-gray-600">Step-by-step meal plan consumption</p>
        </div>
      </header>
      <main>
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
          <div class="px-4 py-8 sm:px-0">
            <!-- Step 1: Date Selection and Availability Check -->
            <div class="bg-white shadow sm:rounded-lg mb-6">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">
                  Step 1: Select Date and Check Availability
                </h3>
                <div class="flex gap-4 items-end">
                  <div class="flex-1 max-w-sm">
                    <label for="consume-date" class="block text-sm font-medium text-gray-700 mb-2">
                      Date
                    </label>
                    <input
                      id="consume-date"
                      v-model="selectedDate"
                      type="date"
                      class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                      :disabled="step1Loading"
                    />
                  </div>
                  <button
                    @click="checkAvailability"
                    :disabled="step1Loading || !selectedDate"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg v-if="step1Loading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {{ step1Loading ? 'Checking...' : 'Check Availability' }}
                  </button>
                </div>
              </div>
            </div>

            <!-- Error state -->
            <div v-if="error" class="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
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

            <!-- Step 2: Shopping List (if insufficient stock) -->
            <div v-if="availabilityResult && availabilityResult.status === 'insufficient_stock'" class="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
              <div class="flex">
                <div class="flex-shrink-0">
                  <svg class="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="ml-3 flex-1">
                  <h3 class="text-sm font-medium text-yellow-800">Insufficient Stock</h3>
                  <p class="mt-2 text-sm text-yellow-700">
                    Some products are not available in sufficient quantity. Would you like to create a shopping list?
                  </p>

                  <!-- Products to Buy Table -->
                  <div class="mt-4 bg-white rounded-md p-4 shadow-sm">
                    <h4 class="text-sm font-semibold text-gray-900 mb-3">Products Needed:</h4>
                    <div class="overflow-x-auto">
                      <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                          <tr>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Amount Needed</th>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Note</th>
                          </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                          <tr v-for="product in availabilityResult.products_to_buy_detailed" :key="product.product_id">
                            <td class="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">{{ product.name }}</td>
                            <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ product.amount }}</td>
                            <td class="px-4 py-2 text-sm text-gray-700">{{ product.note || '-' }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div class="mt-4">
                    <button
                      @click="createShoppingList"
                      :disabled="step2Loading"
                      class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-yellow-700 bg-yellow-100 hover:bg-yellow-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 mr-3"
                    >
                      {{ step2Loading ? 'Creating...' : 'Yes, Create Shopping List' }}
                    </button>
                    <button
                      @click="skipShoppingList"
                      class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                    >
                      No, Skip
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Step 3: Dry Run Preview (if products available) -->
            <div v-if="availabilityResult && availabilityResult.status === 'success' && !dryRunResult" class="bg-white shadow sm:rounded-lg mb-6">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">
                  Step 2: Preview Consumption
                </h3>
                <div class="bg-green-50 border-l-4 border-green-400 p-4 mb-4">
                  <div class="flex">
                    <div class="flex-shrink-0">
                      <svg class="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                      </svg>
                    </div>
                    <div class="ml-3">
                      <p class="text-sm text-green-700">All products are available!</p>
                    </div>
                  </div>
                </div>

                <!-- Products to Consume Table -->
                <div class="bg-gray-50 rounded-md p-4 mb-4">
                  <h4 class="text-sm font-semibold text-gray-900 mb-3">Products to be Consumed:</h4>
                  <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                      <thead class="bg-white">
                        <tr>
                          <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                          <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                          <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Note</th>
                        </tr>
                      </thead>
                      <tbody class="bg-white divide-y divide-gray-200">
                        <tr v-for="product in availabilityResult.products_to_consume_detailed" :key="product.product_id">
                          <td class="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">{{ product.name }}</td>
                          <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ product.amount }}</td>
                          <td class="px-4 py-2 text-sm text-gray-700">{{ product.note || '-' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <button
                  @click="getDryRun"
                  :disabled="step3Loading"
                  class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                >
                  {{ step3Loading ? 'Loading...' : 'Preview Detailed Nutrition' }}
                </button>
              </div>
            </div>

            <!-- Dry Run Result -->
            <div v-if="dryRunResult" class="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
              <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                <h3 class="text-lg font-medium leading-6 text-gray-900">
                  Consumption Preview
                </h3>
                <p class="mt-1 text-sm text-gray-500">
                  Products that will be consumed on {{ dryRunResult.date }}
                </p>
              </div>
              <div class="px-4 py-5 sm:p-6">
                <!-- Products Table -->
                <div class="overflow-x-auto mb-6">
                  <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Qty</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Calories</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Carbs</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sugars</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Proteins</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fats</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sat Fat</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Salt</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fiber</th>
                      </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                      <tr v-for="product in dryRunResult.products" :key="product.grocy_id">
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ product.name }}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ product.quantity }}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.calories) }}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.carbohydrates) }}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.carbohydrates_of_sugars) }}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.proteins) }}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.fats) }}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.fats_saturated) }}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.salt) }}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatValue(product.fibers) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- Totals -->
                <div class="bg-gray-50 px-4 py-3 rounded-md mb-6">
                  <h4 class="text-sm font-medium text-gray-900 mb-3">Daily Totals</h4>
                  <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p class="text-xs text-gray-500">Calories</p>
                      <p class="text-sm font-semibold text-gray-900">{{ dryRunResult.total_calories.toFixed(2) }} kcal</p>
                    </div>
                    <div>
                      <p class="text-xs text-gray-500">Carbohydrates</p>
                      <p class="text-sm font-semibold text-gray-900">{{ dryRunResult.total_nutrients.carbohydrates.toFixed(2) }}g</p>
                    </div>
                    <div>
                      <p class="text-xs text-gray-500">of which Sugars</p>
                      <p class="text-sm font-semibold text-gray-900">{{ dryRunResult.total_nutrients.carbohydrates_of_sugars.toFixed(2) }}g</p>
                    </div>
                    <div>
                      <p class="text-xs text-gray-500">Proteins</p>
                      <p class="text-sm font-semibold text-gray-900">{{ dryRunResult.total_nutrients.proteins.toFixed(2) }}g</p>
                    </div>
                    <div>
                      <p class="text-xs text-gray-500">Fats</p>
                      <p class="text-sm font-semibold text-gray-900">{{ dryRunResult.total_nutrients.fats.toFixed(2) }}g</p>
                    </div>
                    <div>
                      <p class="text-xs text-gray-500">of which Saturated</p>
                      <p class="text-sm font-semibold text-gray-900">{{ dryRunResult.total_nutrients.fats_saturated.toFixed(2) }}g</p>
                    </div>
                    <div>
                      <p class="text-xs text-gray-500">Salt</p>
                      <p class="text-sm font-semibold text-gray-900">{{ dryRunResult.total_nutrients.salt.toFixed(2) }}g</p>
                    </div>
                    <div>
                      <p class="text-xs text-gray-500">Fiber</p>
                      <p class="text-sm font-semibold text-gray-900">{{ dryRunResult.total_nutrients.fibers.toFixed(2) }}g</p>
                    </div>
                  </div>
                </div>

                <!-- Confirmation -->
                <div class="flex gap-4">
                  <button
                    @click="executeConsumption"
                    :disabled="step4Loading"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                  >
                    {{ step4Loading ? 'Consuming...' : 'Confirm and Execute' }}
                  </button>
                  <button
                    @click="reset"
                    class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>

            <!-- Success Result -->
            <div v-if="executionResult" class="bg-green-50 border-l-4 border-green-400 p-4 mb-6">
              <div class="flex">
                <div class="flex-shrink-0">
                  <svg class="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="ml-3">
                  <h3 class="text-sm font-medium text-green-800">Success!</h3>
                  <p class="mt-2 text-sm text-green-700">{{ executionResult.message }}</p>
                  <p class="mt-1 text-sm text-green-700">Consumed {{ executionResult.products_count }} products</p>
                  <button
                    @click="reset"
                    class="mt-3 inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-green-700 bg-green-100 hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                  >
                    Start New Consumption
                  </button>
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
import { ref } from 'vue'
import axios from 'axios'

interface ProductDetail {
  product_id: number
  name: string
  amount: number
  note: string
}

interface AvailabilityResult {
  status: string
  products_to_consume: Record<string, any>
  products_to_buy: Record<string, any>
  products_to_buy_detailed: ProductDetail[]
  products_to_consume_detailed: ProductDetail[]
  message: string
}

interface ProductPreview {
  grocy_id: number
  product_id: number | null
  name: string
  quantity: number
  note: string
  calories: number | null
  carbohydrates: number | null
  carbohydrates_of_sugars: number | null
  proteins: number | null
  fats: number | null
  fats_saturated: number | null
  salt: number | null
  fibers: number | null
}

interface DryRunResult {
  status: string
  date: string
  products: ProductPreview[]
  total_calories: number
  total_nutrients: {
    carbohydrates: number
    carbohydrates_of_sugars: number
    proteins: number
    fats: number
    fats_saturated: number
    salt: number
    fibers: number
  }
  products_count: number
}

interface ExecutionResult {
  status: string
  date: string
  consumed_products: Array<any>
  products_count: number
  message: string
}

const selectedDate = ref<string>(new Date().toISOString().split('T')[0])
const step1Loading = ref(false)
const step2Loading = ref(false)
const step3Loading = ref(false)
const step4Loading = ref(false)
const error = ref('')

const availabilityResult = ref<AvailabilityResult | null>(null)
const dryRunResult = ref<DryRunResult | null>(null)
const executionResult = ref<ExecutionResult | null>(null)

const checkAvailability = async () => {
  step1Loading.value = true
  error.value = ''
  availabilityResult.value = null
  dryRunResult.value = null
  executionResult.value = null

  try {
    const response = await axios.post<AvailabilityResult>('/api/consumption/check', {
      date: selectedDate.value,
    })
    availabilityResult.value = response.data
  } catch (err: any) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'Failed to check availability. Please try again.'
    }
  } finally {
    step1Loading.value = false
  }
}

const createShoppingList = async () => {
  if (!availabilityResult.value) return

  step2Loading.value = true
  error.value = ''

  try {
    await axios.post('/api/consumption/shopping-list', {
      date: selectedDate.value,
      products_to_buy: availabilityResult.value.products_to_buy,
    })
    // After creating shopping list, user needs to go shopping or skip
    alert('Shopping list created! Please purchase the items or skip to continue.')
    skipShoppingList()
  } catch (err: any) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'Failed to create shopping list. Please try again.'
    }
  } finally {
    step2Loading.value = false
  }
}

const skipShoppingList = () => {
  // User decided to skip shopping list creation
  // Reset to allow them to start over or handle differently
  error.value = 'Cannot proceed without sufficient stock. Please sync products or adjust meal plan.'
  availabilityResult.value = null
}

const getDryRun = async () => {
  step3Loading.value = true
  error.value = ''

  try {
    const response = await axios.post<DryRunResult>('/api/consumption/dry-run', {
      date: selectedDate.value,
    })
    dryRunResult.value = response.data
  } catch (err: any) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'Failed to get consumption preview. Please try again.'
    }
  } finally {
    step3Loading.value = false
  }
}

const executeConsumption = async () => {
  step4Loading.value = true
  error.value = ''

  try {
    const response = await axios.post<ExecutionResult>('/api/consumption/execute', {
      date: selectedDate.value,
    })
    executionResult.value = response.data
    dryRunResult.value = null
  } catch (err: any) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'Failed to execute consumption. Please try again.'
    }
  } finally {
    step4Loading.value = false
  }
}

const reset = () => {
  availabilityResult.value = null
  dryRunResult.value = null
  executionResult.value = null
  error.value = ''
}

const formatValue = (value: number | null | undefined): string => {
  if (value === null || value === undefined) {
    return '-'
  }
  return value.toFixed(2)
}
</script>
