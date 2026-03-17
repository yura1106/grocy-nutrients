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
import { useAuthStore } from '../store/auth'
import flatpickr from 'flatpickr'
import 'flatpickr/dist/flatpickr.min.css'

const router = useRouter()
const authStore = useAuthStore()

const selectedDate = ref<string>(new Date().toISOString().split('T')[0])
const dateInputRef = ref<HTMLInputElement | null>(null)

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
})

const goConsume = () => {
  router.push({ path: '/consume', query: { date: selectedDate.value } })
}
</script>
