<template>
  <div class="bg-gray-100 min-h-screen">
    <div class="py-10">
      <header>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold leading-tight text-gray-900">Dashboard</h1>
        </div>
      </header>
      <main>
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
          <div class="px-4 py-8 sm:px-0">
            <!-- Consume Daily Plan -->
            <div class="bg-white shadow sm:rounded-lg mb-6">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">Consume Daily Plan</h3>
                <p class="text-sm text-gray-500 mb-4">Select a date and start the consumption flow for your meal plan.</p>
                <div class="flex gap-4 items-end">
                  <div class="flex-1 max-w-sm">
                    <label for="consume-date" class="block text-sm font-medium text-gray-700 mb-2">Date</label>
                    <input
                      id="consume-date"
                      ref="dateInputRef"
                      :value="selectedDate"
                      type="text"
                      readonly
                      placeholder="YYYY-MM-DD"
                      class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md bg-white cursor-pointer"
                    />
                  </div>
                  <button
                    @click="goConsume"
                    :disabled="!selectedDate"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Check &amp; Consume
                  </button>
                </div>
              </div>
            </div>

            <!-- Week Planner -->
            <div class="bg-white shadow sm:rounded-lg mb-6">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">Week Planner</h3>
                <p class="text-sm text-gray-500 mb-4">Select a date range to check product availability and create a shopping list.</p>
                <div class="flex gap-4 items-end">
                  <div class="flex-1 max-w-sm">
                    <label for="range-date" class="block text-sm font-medium text-gray-700 mb-2">Date Range</label>
                    <input
                      id="range-date"
                      ref="rangeDateInputRef"
                      type="text"
                      readonly
                      placeholder="Select date range"
                      class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md bg-white cursor-pointer"
                    />
                  </div>
                  <button
                    @click="checkRangeAvailability"
                    :disabled="!rangeStartDate || !rangeEndDate || rangeLoading"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {{ rangeLoading ? 'Checking...' : 'Check Availability' }}
                  </button>
                </div>

                <!-- Error -->
                <div v-if="rangeError" class="mt-4 bg-red-50 border-l-4 border-red-400 p-4">
                  <p class="text-sm text-red-700">{{ rangeError }}</p>
                </div>

                <!-- All available -->
                <div v-if="rangeResult && rangeResult.status === 'success'" class="mt-4 bg-green-50 border-l-4 border-green-400 p-4">
                  <p class="text-sm text-green-700">All products are available for {{ rangeStartDate }} — {{ rangeEndDate }}.</p>
                </div>

                <!-- Insufficient stock -->
                <div v-if="rangeResult && rangeResult.status === 'insufficient_stock'" class="mt-4">
                  <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                    <h4 class="text-sm font-medium text-yellow-800">Insufficient Stock</h4>
                    <p class="mt-1 text-sm text-yellow-700">
                      Some products are not available for {{ rangeStartDate }} — {{ rangeEndDate }}.
                    </p>

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
                            <tr v-for="product in rangeResult.products_to_buy_detailed" :key="product.product_id">
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
                        v-if="!rangeShoppingListCreated"
                        @click="createRangeShoppingList"
                        :disabled="rangeShoppingListLoading"
                        class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-yellow-700 bg-yellow-100 hover:bg-yellow-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500"
                      >
                        {{ rangeShoppingListLoading ? 'Creating...' : 'Create Shopping List' }}
                      </button>
                      <span v-if="rangeShoppingListCreated" class="text-sm text-green-700 font-medium">
                        Shopping list created!
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Info -->
            <div class="bg-white shadow overflow-hidden sm:rounded-lg">
              <div class="px-4 py-5 sm:px-6">
                <h3 class="text-lg leading-6 font-medium text-gray-900">Welcome, {{ authStore.user?.username }}</h3>
                <p class="mt-1 max-w-2xl text-sm text-gray-500">
                  Manage your Grocy products, recipes and consumption from the navigation menu.
                </p>
              </div>
              <div class="border-t border-gray-200 px-4 py-5 sm:px-6">
                <p class="text-sm text-gray-500">
                  Product and recipe sync is available in
                  <router-link to="/profile" class="text-indigo-600 hover:text-indigo-800 font-medium">Profile &rarr; Households</router-link>
                  (admin only).
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../store/auth'
import { useHouseholdStore } from '../store/household'
import flatpickr from 'flatpickr'
import 'flatpickr/dist/flatpickr.min.css'

const router = useRouter()
const authStore = useAuthStore()
const householdStore = useHouseholdStore()

// Daily consume
const selectedDate = ref<string>(new Date().toISOString().split('T')[0])
const dateInputRef = ref<HTMLInputElement | null>(null)

// Week planner
const rangeDateInputRef = ref<HTMLInputElement | null>(null)
const rangeStartDate = ref('')
const rangeEndDate = ref('')
const rangeLoading = ref(false)
const rangeError = ref('')
const rangeResult = ref<any>(null)
const rangeShoppingListLoading = ref(false)
const rangeShoppingListCreated = ref(false)

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchUser()
  }
  if (dateInputRef.value) {
    flatpickr(dateInputRef.value, {
      dateFormat: 'Y-m-d',
      defaultDate: selectedDate.value,
      locale: { firstDayOfWeek: 1 },
      onChange: (_dates, dateStr) => {
        selectedDate.value = dateStr
      },
    })
  }
  if (rangeDateInputRef.value) {
    flatpickr(rangeDateInputRef.value, {
      mode: 'range',
      dateFormat: 'Y-m-d',
      locale: { firstDayOfWeek: 1 },
      onChange: (_dates, dateStr) => {
        const parts = dateStr.split(' to ')
        if (parts.length === 2) {
          rangeStartDate.value = parts[0]
          rangeEndDate.value = parts[1]
        } else {
          rangeStartDate.value = ''
          rangeEndDate.value = ''
        }
        rangeResult.value = null
        rangeShoppingListCreated.value = false
        rangeError.value = ''
      },
    })
  }
})

const goConsume = () => {
  router.push({ path: '/consume', query: { date: selectedDate.value } })
}

const checkRangeAvailability = async () => {
  rangeLoading.value = true
  rangeError.value = ''
  rangeResult.value = null
  rangeShoppingListCreated.value = false

  try {
    const response = await axios.post('/api/consumption/range-check', {
      start_date: rangeStartDate.value,
      end_date: rangeEndDate.value,
    }, { params: { household_id: householdStore.selectedId } })
    rangeResult.value = response.data
  } catch (err: any) {
    rangeError.value = err.response?.data?.detail || 'Failed to check availability.'
  } finally {
    rangeLoading.value = false
  }
}

const createRangeShoppingList = async () => {
  if (!rangeResult.value) return
  rangeShoppingListLoading.value = true
  rangeError.value = ''

  try {
    await axios.post('/api/consumption/range-shopping-list', {
      start_date: rangeStartDate.value,
      end_date: rangeEndDate.value,
      products_to_buy: rangeResult.value.products_to_buy,
    }, { params: { household_id: householdStore.selectedId } })
    rangeShoppingListCreated.value = true
  } catch (err: any) {
    rangeError.value = err.response?.data?.detail || 'Failed to create shopping list.'
  } finally {
    rangeShoppingListLoading.value = false
  }
}
</script>
