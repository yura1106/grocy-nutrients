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
            <!-- Today's Meal Plan -->
            <div class="bg-white shadow sm:rounded-lg mb-6">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium leading-6 text-gray-900 mb-3">Today's Meal Plan</h3>
                <div
                  v-if="mealPlanLoading"
                  class="flex items-center gap-2 text-sm text-gray-500"
                >
                  <svg
                    class="animate-spin h-4 w-4 text-indigo-500"
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
                  Loading...
                </div>
                <div
                  v-else-if="mealPlanError"
                  class="text-sm text-red-600"
                >
                  {{ mealPlanError }}
                </div>
                <div
                  v-else-if="mealPlanItems.length === 0"
                  class="text-sm text-gray-400"
                >
                  No meals planned for today.
                </div>
                <ul
                  v-else
                  class="divide-y divide-gray-100"
                >
                  <li
                    v-for="(item, idx) in mealPlanItems"
                    :key="idx"
                    class="flex items-center gap-2 py-2"
                  >
                    <span
                      v-if="item.type !== 'note'"
                      class="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium"
                      :class="item.type === 'recipe' ? 'bg-indigo-50 text-indigo-700' : 'bg-green-50 text-green-700'"
                    >{{ item.type === 'recipe' ? 'Recipe' : 'Product' }}</span>
                    <span class="text-sm text-gray-800">{{ item.name }}</span>
                  </li>
                </ul>
              </div>
            </div>

            <!-- Consume Daily Plan -->
            <div class="bg-white shadow sm:rounded-lg mb-6">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">Consume Daily Plan</h3>
                <p class="text-sm text-gray-500 mb-4">Select a date and start the consumption flow for your meal plan.</p>
                <div class="flex gap-4 items-end">
                  <div class="flex-1 max-w-sm">
                    <label
                      for="consume-date"
                      class="block text-sm font-medium text-gray-700 mb-2"
                    >Date</label>
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

                <!-- Date picker + button (idle state) -->
                <div
                  v-if="rangeState === 'idle'"
                  class="flex gap-4 items-end"
                >
                  <div class="flex-1 max-w-sm">
                    <label
                      for="range-date"
                      class="block text-sm font-medium text-gray-700 mb-2"
                    >Date Range</label>
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
                    :disabled="!rangeStartDate || !rangeEndDate"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Check Availability
                  </button>
                </div>

                <!-- Loading / Polling -->
                <div
                  v-if="rangeState === 'loading' || rangeState === 'polling'"
                  class="mt-2"
                >
                  <div class="flex items-center gap-3 mb-3">
                    <svg
                      class="animate-spin h-5 w-5 text-indigo-600 shrink-0"
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
                    <span class="text-sm font-medium text-gray-700">
                      {{ rangeCheckData?.step || 'Processing...' }}
                    </span>
                  </div>
                  <p class="text-xs text-gray-400">
                    Checking {{ rangeCheckData?.start_date }} — {{ rangeCheckData?.end_date }}.
                    You can close the page — the check will continue in the background.
                  </p>
                </div>

                <!-- Error -->
                <div
                  v-if="rangeError"
                  class="mt-4 bg-red-50 border-l-4 border-red-400 p-4"
                >
                  <div class="flex justify-between items-start">
                    <p class="text-sm text-red-700">{{ rangeError }}</p>
                    <button
                      @click="dismissRange"
                      class="ml-4 text-sm text-red-600 hover:text-red-800 font-medium"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>

                <!-- Success: all available -->
                <div
                  v-if="rangeState === 'done' && rangeCheckData?.state === 'SUCCESS' && rangeCheckData.result?.status === 'success'"
                  class="mt-4 bg-green-50 border-l-4 border-green-400 p-4"
                >
                  <div class="flex justify-between items-start">
                    <p class="text-sm text-green-700">All products are available for {{ rangeCheckData.start_date }} — {{ rangeCheckData.end_date }}.</p>
                    <button
                      @click="dismissRange"
                      class="ml-4 text-sm text-green-600 hover:text-green-800 font-medium"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>

                <!-- Success: insufficient stock -->
                <div
                  v-if="rangeState === 'done' && rangeCheckData?.state === 'SUCCESS' && rangeCheckData.result?.status === 'insufficient_stock'"
                  class="mt-4"
                >
                  <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                    <h4 class="text-sm font-medium text-yellow-800">Insufficient Stock</h4>
                    <p class="mt-1 text-sm text-yellow-700">
                      Some products are not available for {{ rangeCheckData.start_date }} — {{ rangeCheckData.end_date }}.
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
                            <tr
                              v-for="product in rangeCheckData.result.products_to_buy_detailed"
                              :key="product.product_id"
                            >
                              <td class="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">{{ product.name }}</td>
                              <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{{ product.amount }}</td>
                              <td class="px-4 py-2 text-sm text-gray-700">{{ product.note || '-' }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>

                    <div class="mt-4 flex gap-3">
                      <button
                        @click="createRangeShoppingList"
                        :disabled="rangeShoppingListLoading"
                        class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-yellow-700 bg-yellow-100 hover:bg-yellow-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500"
                      >
                        {{ rangeShoppingListLoading ? 'Creating...' : 'Create Shopping List' }}
                      </button>
                      <button
                        @click="rejectRange"
                        class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                </div>

                <!-- Failure from task -->
                <div
                  v-if="rangeState === 'done' && rangeCheckData?.state === 'FAILURE'"
                  class="mt-4 bg-red-50 border-l-4 border-red-400 p-4"
                >
                  <div class="flex justify-between items-start">
                    <p class="text-sm text-red-700">{{ rangeCheckData.error || 'Check failed.' }}</p>
                    <button
                      @click="dismissRange"
                      class="ml-4 text-sm text-red-600 hover:text-red-800 font-medium"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>

                <!-- Shopping list created confirmation -->
                <div
                  v-if="rangeShoppingListCreated"
                  class="mt-4 bg-green-50 border-l-4 border-green-400 p-4"
                >
                  <p class="text-sm text-green-700 font-medium">Shopping list created!</p>
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
                  <router-link
                    to="/profile"
                    class="text-indigo-600 hover:text-indigo-800 font-medium"
                  >
                    Profile &rarr; Households
                  </router-link>
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
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios, { isAxiosError } from 'axios'
import { useAuthStore } from '../store/auth'
import { useHouseholdStore } from '../store/household'
import flatpickr from 'flatpickr'
import 'flatpickr/dist/flatpickr.min.css'

const router = useRouter()
const authStore = useAuthStore()
const householdStore = useHouseholdStore()

// Today's meal plan
interface MealPlanItem {
  name: string
  type: string
}
const mealPlanItems = ref<MealPlanItem[]>([])
const mealPlanLoading = ref(false)
const mealPlanError = ref('')

// Daily consume
const selectedDate = ref<string>(new Date().toISOString().split('T')[0])
const dateInputRef = ref<HTMLInputElement | null>(null)

// Week planner
const rangeDateInputRef = ref<HTMLInputElement | null>(null)
const rangeStartDate = ref('')
const rangeEndDate = ref('')
const rangeState = ref<'idle' | 'loading' | 'polling' | 'done' | 'error'>('idle')
interface RangeCheckData {
  state: string
  start_date?: string
  end_date?: string
  step?: string
  error?: string
  result?: {
    status: string
    products_to_buy: Record<string, unknown>
    products_to_buy_detailed?: Array<{ product_id: number; name: string; amount: number; note?: string }>
  }
}

const rangeCheckData = ref<RangeCheckData | null>(null)
const rangeError = ref('')
const rangeShoppingListLoading = ref(false)
const rangeShoppingListCreated = ref(false)
let rangePollTimer: ReturnType<typeof setTimeout> | null = null

const stopRangePolling = () => {
  if (rangePollTimer !== null) {
    clearTimeout(rangePollTimer)
    rangePollTimer = null
  }
}

onUnmounted(() => {
  stopRangePolling()
})

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
      },
    })
  }

  // Fetch today's meal plan
  if (householdStore.selectedId) {
    mealPlanLoading.value = true
    try {
      const res = await axios.get('/api/consumption/today-meal-plan', {
        params: { household_id: householdStore.selectedId },
      })
      mealPlanItems.value = res.data.items
    } catch {
      mealPlanError.value = 'Failed to load meal plan.'
    } finally {
      mealPlanLoading.value = false
    }
  }

  // Check for existing cached range check result
  await loadCachedRangeResult()
})

const goConsume = () => {
  router.push({ path: '/consume', query: { date: selectedDate.value } })
}

// --- Week Planner ---

const loadCachedRangeResult = async () => {
  if (!householdStore.selectedId) return
  try {
    const response = await axios.get('/api/consumption/range-check/status', {
      params: { household_id: householdStore.selectedId },
    })
    const data = response.data

    if (data.state === 'NONE') {
      rangeState.value = 'idle'
      return
    }

    rangeCheckData.value = data
    if (data.start_date) rangeStartDate.value = data.start_date
    if (data.end_date) rangeEndDate.value = data.end_date

    if (data.state === 'SUCCESS' || data.state === 'FAILURE') {
      rangeState.value = 'done'
    } else if (data.state === 'PENDING' || data.state === 'PROGRESS') {
      rangeState.value = 'polling'
      startRangePolling()
    }
  } catch {
    rangeState.value = 'idle'
  }
}

const checkRangeAvailability = async () => {
  rangeState.value = 'loading'
  rangeError.value = ''
  rangeCheckData.value = null
  rangeShoppingListCreated.value = false

  try {
    await axios.post('/api/consumption/range-check', {
      start_date: rangeStartDate.value,
      end_date: rangeEndDate.value,
    }, { params: { household_id: householdStore.selectedId } })
    rangeState.value = 'polling'
    startRangePolling()
  } catch (err: unknown) {
    rangeState.value = 'error'
    rangeError.value = isAxiosError(err) && err.response?.data?.detail || 'Failed to start availability check.'
  }
}

const startRangePolling = () => {
  rangePollTimer = setTimeout(pollRangeStatus, 1000)
}

const pollRangeStatus = async () => {
  try {
    const response = await axios.get('/api/consumption/range-check/status', {
      params: { household_id: householdStore.selectedId },
    })
    const data = response.data
    rangeCheckData.value = data

    if (data.state === 'PENDING' || data.state === 'PROGRESS') {
      rangePollTimer = setTimeout(pollRangeStatus, 2000)
    } else {
      rangeState.value = 'done'
    }
  } catch {
    rangeState.value = 'error'
    rangeError.value = 'Failed to get check status.'
  }
}

const createRangeShoppingList = async () => {
  if (!rangeCheckData.value?.result) return
  rangeShoppingListLoading.value = true
  rangeError.value = ''

  try {
    await axios.post('/api/consumption/range-shopping-list', {
      start_date: rangeCheckData.value.start_date,
      end_date: rangeCheckData.value.end_date,
      products_to_buy: rangeCheckData.value.result.products_to_buy,
    }, { params: { household_id: householdStore.selectedId } })
    // Backend clears Redis key; reset UI
    rangeState.value = 'idle'
    rangeCheckData.value = null
    rangeShoppingListCreated.value = true
  } catch (err: unknown) {
    rangeError.value = isAxiosError(err) && err.response?.data?.detail || 'Failed to create shopping list.'
  } finally {
    rangeShoppingListLoading.value = false
  }
}

const rejectRange = async () => {
  try {
    await axios.delete('/api/consumption/range-check', {
      params: { household_id: householdStore.selectedId },
    })
  } catch { /* ignore */ }
  rangeState.value = 'idle'
  rangeCheckData.value = null
}

const dismissRange = async () => {
  await rejectRange()
}
</script>
