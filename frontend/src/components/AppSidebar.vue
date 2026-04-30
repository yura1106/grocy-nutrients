<template>
  <aside
    class="fixed lg:static z-40 inset-y-0 left-0 w-56 bg-white shadow-md flex flex-col shrink-0 transition-transform duration-200 ease-in-out lg:translate-x-0 lg:min-h-screen"
    :class="isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'"
  >
    <!-- Desktop title -->
    <div class="hidden lg:flex px-4 py-5 border-b border-gray-200 items-center gap-2">
      <Leaf
        :size="18"
        class="text-emerald-600 shrink-0"
      />
      <h1 class="text-lg font-bold text-gray-900">Grocy Nutrients</h1>
    </div>
    <!-- Spacer for mobile top bar -->
    <div class="lg:hidden h-14 shrink-0"></div>

    <!-- Household selector -->
    <div
      v-if="householdStore.households.length > 0"
      class="px-3 py-3 border-b border-gray-200"
    >
      <label class="block text-xs font-medium text-gray-500 mb-1">Household</label>
      <select
        :value="householdStore.selectedId"
        @change="onHouseholdChange"
        class="block w-full text-sm border-gray-300 rounded-md shadow-xs focus:ring-indigo-500 focus:border-indigo-500"
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
        class="flex items-center gap-2.5 px-3 py-2.5 text-sm font-medium rounded-md transition-colors"
        :class="$route.path === item.to
          ? 'bg-indigo-50 text-indigo-700'
          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'"
        @click="$emit('close')"
      >
        <component
          :is="item.icon"
          :size="17"
          class="shrink-0"
          :class="$route.path === item.to ? 'text-indigo-600' : 'text-gray-400'"
        />
        <span class="truncate">{{ item.label }}</span>
      </router-link>
    </nav>

    <div class="px-3 py-4 border-t border-gray-200">
      <button
        @click="onLogout"
        class="w-full inline-flex justify-center items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
      >
        Logout
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import {
  BarChart2,
  BookOpen,
  ClipboardList,
  History,
  LayoutDashboard,
  Leaf,
  ShoppingBag,
  Target,
  User,
} from 'lucide-vue-next'

import { useAuthStore } from '../store/auth'
import { useHouseholdStore } from '../store/household'
import { useNutritionLimitsStore } from '../store/nutritionLimits'

defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const router = useRouter()
const authStore = useAuthStore()
const householdStore = useHouseholdStore()
const limitsStore = useNutritionLimitsStore()

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/consumed-stats', label: 'Nutrient Stats', icon: BarChart2 },
  { to: '/daily-nutrition-limits', label: 'Daily Limits', icon: Target },
  { to: '/recipes', label: 'Recipes', icon: BookOpen },
  { to: '/products', label: 'Products', icon: ShoppingBag },
  { to: '/consumption-history', label: 'Consumption Log', icon: ClipboardList },
  { to: '/history-import', label: 'History', icon: History },
  { to: '/profile', label: 'Profile', icon: User },
]

const onHouseholdChange = (e: Event) => {
  const id = parseInt((e.target as HTMLSelectElement).value, 10)
  householdStore.select(id)
}

const onLogout = async () => {
  await authStore.logout()
  householdStore.clear()
  limitsStore.$reset()
  emit('close')
  router.push('/login')
}
</script>
