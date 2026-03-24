<template>
  <div>
    <!-- Mobile top bar — outside flex, truly full-width -->
    <header
      v-if="authStore.isAuthenticated"
      class="lg:hidden fixed top-0 left-0 right-0 w-full z-50 bg-white shadow flex items-center justify-between px-4 h-14"
    >
      <h1 class="text-base font-bold text-gray-900">Grocy Stat</h1>
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
      <!-- Sidebar -->
      <aside
        v-if="authStore.isAuthenticated"
        class="fixed lg:static z-40 inset-y-0 left-0 w-56 bg-white shadow-md flex flex-col flex-shrink-0 transition-transform duration-200 ease-in-out lg:translate-x-0 lg:min-h-screen"
        :class="mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'"
      >
        <!-- Desktop title -->
        <div class="hidden lg:flex px-4 py-5 border-b border-gray-200 items-center">
          <h1 class="text-lg font-bold text-gray-900">Grocy Stat</h1>
        </div>
        <!-- Spacer for mobile top bar -->
        <div class="lg:hidden h-14 flex-shrink-0"></div>

        <!-- Household selector -->
        <div
          v-if="householdStore.households.length > 0"
          class="px-3 py-3 border-b border-gray-200"
        >
          <label class="block text-xs font-medium text-gray-500 mb-1">Household</label>
          <select
            :value="householdStore.selectedId"
            @change="onHouseholdChange"
            class="block w-full text-sm border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option
              v-for="h in householdStore.households"
              :key="h.id"
              :value="h.id"
            >
              {{ h.name }}
            </option>
          </select>
          <p
            v-if="householdStore.selected?.grocy_url"
            class="mt-1 text-xs text-gray-400 truncate"
            :title="householdStore.selected.grocy_url"
          >
            {{ householdStore.selected.grocy_url }}
          </p>
        </div>

        <nav class="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
          <router-link
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors"
            :class="[$route.path === item.to
              ? 'bg-indigo-50 text-indigo-700'
              : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900']"
            @click="mobileOpen = false"
          >
            {{ item.label }}
          </router-link>
        </nav>

        <div class="px-3 py-4 border-t border-gray-200">
          <button
            @click="logout"
            class="w-full inline-flex justify-center items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
          >
            Logout
          </button>
        </div>
      </aside>

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
import { useRouter } from 'vue-router'
import { useAuthStore } from './store/auth'
import { useHouseholdStore } from './store/household'

const router = useRouter()
const authStore = useAuthStore()
const householdStore = useHouseholdStore()
const mobileOpen = ref(false)

// Load households when user becomes authenticated
watch(
  () => authStore.user,
  (user, oldUser) => {
    if (user) {
      householdStore.fetchHouseholds()
    } else if (oldUser) {
      // Only clear on actual logout (user was set, now null), not on initial load
      householdStore.clear()
    }
  },
  { immediate: true }
)

const onHouseholdChange = (e: Event) => {
  const id = parseInt((e.target as HTMLSelectElement).value, 10)
  householdStore.select(id)
}

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/consumed-stats', label: 'Nutrient Stats' },
  { to: '/recipes', label: 'Recipes' },
  { to: '/products', label: 'Products' },
  { to: '/consumption-history', label: 'Consumption Log' },
  { to: '/history-import', label: 'History' },
  { to: '/profile', label: 'Profile' },
]

const logout = async () => {
  await authStore.logout()
  householdStore.clear()
  router.push('/login')
}
</script>
