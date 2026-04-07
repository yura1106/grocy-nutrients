<template>
  <div class="container mx-auto px-4 py-8">
    <!-- Header -->
    <div class="mb-6">
      <router-link
        to="/recipes"
        class="text-blue-600 hover:text-blue-800 mb-4 inline-block"
      >
        ← Back to Recipes
      </router-link>
      <h1 class="text-3xl font-bold text-gray-900">{{ store.recipe?.name || 'Loading...' }}</h1>
      <div
        v-if="store.recipe"
        class="mt-2 text-gray-600"
      >
        <span>Grocy ID: {{ store.recipe.grocy_id }}</span>
        <span class="ml-4">Created: {{ formatDate(store.recipe.created_at) }}</span>
      </div>
    </div>

    <!-- Loading State -->
    <div
      v-if="store.loading"
      class="text-center py-8"
    >
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <p class="mt-2 text-gray-600">Loading recipe details...</p>
    </div>

    <!-- Error State -->
    <div
      v-else-if="store.error"
      class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6"
    >
      <p class="text-red-800">{{ store.error }}</p>
    </div>

    <!-- Recipe Details -->
    <div v-else-if="store.recipe">
      <!-- Statistics Cards -->
      <div
        v-if="store.recipe.history.length > 0"
        class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6"
      >
        <div class="bg-blue-50 rounded-lg p-4">
          <div class="text-blue-600 text-sm font-medium">Total Preparations</div>
          <div class="text-2xl font-bold text-blue-900">{{ store.recipe.total_history }}</div>
        </div>
        <div class="bg-green-50 rounded-lg p-4">
          <div class="text-green-600 text-sm font-medium">Avg Calories/Serving</div>
          <div class="text-2xl font-bold text-green-900">{{ formatNumber(store.averageCalories) }}</div>
        </div>
        <div class="bg-purple-50 rounded-lg p-4">
          <div class="text-purple-600 text-sm font-medium">Avg Price/Serving</div>
          <div class="text-2xl font-bold text-purple-900">{{ formatPrice(store.averagePrice) }}</div>
        </div>
        <div class="bg-orange-50 rounded-lg p-4">
          <div class="text-orange-600 text-sm font-medium">Last Prepared</div>
          <div class="text-2xl font-bold text-orange-900">{{ formatDateShort(store.recipe.history[0]?.consumed_date || store.recipe.history[0]?.consumed_at) }}</div>
        </div>
      </div>

      <!-- Actions -->
      <div class="mb-6 flex gap-4">
        <router-link
          :to="`/recipe-nutrients?id=${store.recipe.grocy_id}`"
          class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          Calculate & Consume
        </router-link>
      </div>

      <!-- History Table -->
      <div class="bg-white rounded-lg shadow overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-xl font-semibold text-gray-900">Consumption History</h2>
        </div>

        <div
          v-if="store.recipe.history.length === 0"
          class="px-6 py-8 text-center text-gray-500"
        >
          <p>No consumption history yet.</p>
          <p class="mt-2 text-sm">Use "Calculate & Consume" to add your first entry.</p>
        </div>

        <div
          v-else
          class="overflow-x-auto"
        >
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-8"></th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Servings</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Weight/serving</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Price/serving</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Calories</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Proteins</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Carbs</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">of sugars</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fats</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">saturated</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Salt</th>
                <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fiber</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <template
                v-for="item in store.recipe.history"
                :key="item.id"
              >
                <tr
                  :class="[
                    item.has_products ? 'cursor-pointer' : '',
                    store.expandedRowId === item.id ? 'bg-indigo-50' : 'hover:bg-gray-50',
                  ]"
                  @click="store.toggleProducts(item)"
                >
                  <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-400">
                    <svg
                      v-if="item.has_products"
                      class="w-4 h-4 transition-transform"
                      :class="store.expandedRowId === item.id ? 'rotate-90' : ''"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    ><path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 5l7 7-7 7"
                    /></svg>
                  </td>
                  <td
                    class="px-3 py-4 whitespace-nowrap text-sm"
                    :class="store.expandedRowId === item.id ? 'text-indigo-700 font-medium' : 'text-gray-900'"
                  >
                    {{ item.consumed_date ? formatDate(item.consumed_date) : formatDateTime(item.consumed_at) }}
                  </td>
                  <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ item.servings }}</td>
                  <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.weight_per_serving) }}g</td>
                  <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatPrice(item.price_per_serving) }}</td>
                  <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.calories) }}</td>
                  <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.proteins) }}g</td>
                  <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.carbohydrates) }}g</td>
                  <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatNumber(item.carbohydrates_of_sugars) }}g</td>
                  <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.fats) }}g</td>
                  <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatNumber(item.fats_saturated) }}g</td>
                  <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.salt) }}g</td>
                  <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatNumber(item.fibers) }}g</td>
                </tr>
                <!-- Expanded products row -->
                <tr
                  v-if="store.expandedRowId === item.id"
                  :key="'detail-' + item.id"
                >
                  <td
                    :colspan="13"
                    class="p-0"
                  >
                    <div
                      v-if="store.productsLoading"
                      class="py-6 text-center"
                    >
                      <div class="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600"></div>
                    </div>
                    <div
                      v-else-if="store.productsDetail"
                      class="bg-gray-50 border-t border-b border-gray-200"
                    >
                      <!-- Nutrient totals with gauges -->
                      <NutrientTotalsBar
                        v-if="store.expandedNutrients"
                        layout="horizontal"
                        :totals="store.expandedNutrients"
                        :norms="norms"
                      />
                      <!-- Products list -->
                      <ConsumedProductList
                        :products="store.productsDetail.products"
                        :norms="norms"
                      />
                      <div
                        v-if="store.productsDetail.products.length === 0"
                        class="px-6 py-4 text-center text-sm text-gray-500"
                      >
                        No product details available.
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useHouseholdStore } from '@/store/household'
import { useRecipeDetailStore } from '@/store/recipeDetail'
import NutrientTotalsBar from '../components/NutrientTotalsBar.vue'
import ConsumedProductList from '../components/ConsumedProductList.vue'
import { useNorms } from '@/composables/useNorms'

const route = useRoute()
const householdStore = useHouseholdStore()
const store = useRecipeDetailStore()
const { norms } = useNorms()

watch(() => householdStore.selectedId, (id) => {
  if (id !== null) store.load(route.params.id)
}, { immediate: true })

onUnmounted(() => store.reset())

const formatDate = (dateString: string): string => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('uk-UA', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

const formatDateShort = (dateString: string): string => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('uk-UA', {
    month: 'short',
    day: 'numeric',
  })
}

const formatDateTime = (dateString: string): string => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString('uk-UA', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const formatNumber = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return 'N/A'
  return value.toFixed(1)
}

const formatPrice = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return 'N/A'
  return `${value.toFixed(2)} ₴`
}
</script>
