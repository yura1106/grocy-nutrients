<template>
  <div class="bg-gray-100">
    <div class="py-10">
      <header>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold leading-tight text-gray-900">Dashboard</h1>
        </div>
      </header>
      <main>
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
          <div class="px-4 py-8 sm:px-0">
            <div class="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
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
import { onMounted } from 'vue'
import { useAuthStore } from '../store/auth'

const authStore = useAuthStore()

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchUser()
  }
})
</script>
