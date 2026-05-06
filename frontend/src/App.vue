<template>
  <div>
    <!-- Mobile top bar — outside flex, truly full-width -->
    <header
      v-if="authStore.isAuthenticated"
      class="lg:hidden fixed top-0 left-0 right-0 w-full z-50 bg-white shadow-sm flex items-center justify-between px-4 h-14"
    >
      <h1 class="text-base font-bold text-gray-900">Grocy Nutrients</h1>
      <button
        @click="mobileOpen = !mobileOpen"
        class="p-2 rounded-md text-gray-500 hover:bg-gray-100"
      >
        <svg
          v-if="!mobileOpen"
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 6h16M4 12h16M4 18h16"
          />
        </svg>
        <svg
          v-else
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </header>

    <!-- Mobile overlay -->
    <div
      v-if="authStore.isAuthenticated && mobileOpen"
      class="lg:hidden fixed inset-0 z-30 bg-black/40"
      @click="mobileOpen = false"
    ></div>

    <div class="min-h-screen bg-gray-50 flex">
      <AppSidebar
        v-if="authStore.isAuthenticated"
        :is-open="mobileOpen"
        @close="mobileOpen = false"
      />

      <!-- Main content -->
      <main
        class="flex-1 min-w-0"
        :class="authStore.isAuthenticated ? 'mt-14 lg:mt-0' : ''"
      >
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import AppSidebar from './components/AppSidebar.vue'
import { useAuthStore } from './store/auth'
import { useHouseholdStore } from './store/household'
import { useNutritionLimitsStore } from './store/nutritionLimits'
import { useHealthStore } from './store/health'

const authStore = useAuthStore()
const householdStore = useHouseholdStore()
const limitsStore = useNutritionLimitsStore()
const healthStore = useHealthStore()
const mobileOpen = ref(false)

// Load households, today's limit and health params when user becomes authenticated
watch(
  () => authStore.user,
  (user, oldUser) => {
    if (user) {
      householdStore.fetchHouseholds()
      limitsStore.fetchTodayLimit()
      healthStore.fetchHealthParams()
    } else if (oldUser) {
      // Only clear on actual logout (user was set, now null), not on initial load
      householdStore.clear()
      limitsStore.$reset()
    }
  },
  { immediate: true }
)
</script>
