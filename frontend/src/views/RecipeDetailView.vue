<template>
  <div class="container mx-auto px-4 py-8">
    <!-- Header -->
    <div class="mb-6">
      <router-link to="/recipes" class="text-blue-600 hover:text-blue-800 mb-4 inline-block">
        ← Back to Recipes
      </router-link>
      <h1 class="text-3xl font-bold text-gray-900">{{ recipe?.name || 'Loading...' }}</h1>
      <div v-if="recipe" class="mt-2 text-gray-600">
        <span>Grocy ID: {{ recipe.grocy_id }}</span>
        <span class="ml-4">Created: {{ formatDate(recipe.created_at) }}</span>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <p class="mt-2 text-gray-600">Loading recipe details...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
      <p class="text-red-800">{{ error }}</p>
    </div>

    <!-- Recipe Details -->
    <div v-else-if="recipe">
      <!-- Statistics Cards -->
      <div v-if="recipe.history.length > 0" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-blue-50 rounded-lg p-4">
          <div class="text-blue-600 text-sm font-medium">Total Preparations</div>
          <div class="text-2xl font-bold text-blue-900">{{ recipe.total_history }}</div>
        </div>
        <div class="bg-green-50 rounded-lg p-4">
          <div class="text-green-600 text-sm font-medium">Avg Calories/Serving</div>
          <div class="text-2xl font-bold text-green-900">{{ formatNumber(averageCalories) }}</div>
        </div>
        <div class="bg-purple-50 rounded-lg p-4">
          <div class="text-purple-600 text-sm font-medium">Avg Price/Serving</div>
          <div class="text-2xl font-bold text-purple-900">{{ formatPrice(averagePrice) }}</div>
        </div>
        <div class="bg-orange-50 rounded-lg p-4">
          <div class="text-orange-600 text-sm font-medium">Last Prepared</div>
          <div class="text-2xl font-bold text-orange-900">{{ formatDateShort(recipe.history[0]?.consumed_date || recipe.history[0]?.consumed_at) }}</div>
        </div>
      </div>

      <!-- Actions -->
      <div class="mb-6 flex gap-4">
        <router-link
          :to="`/recipe-nutrients?id=${recipe.grocy_id}`"
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

        <div v-if="recipe.history.length === 0" class="px-6 py-8 text-center text-gray-500">
          <p>No consumption history yet.</p>
          <p class="mt-2 text-sm">Use "Calculate & Consume" to add your first entry.</p>
        </div>

        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
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
              <tr v-for="item in recipe.history" :key="item.id" class="hover:bg-gray-50">
                <td class="px-3 py-4 whitespace-nowrap text-sm text-gray-900">
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
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

interface RecipeHistoryItem {
  id: number
  servings: number
  weight_per_serving: number | null
  price_per_serving: number | null
  calories: number | null
  proteins: number | null
  carbohydrates: number | null
  carbohydrates_of_sugars: number | null
  fats: number | null
  fats_saturated: number | null
  salt: number | null
  fibers: number | null
  consumed_at: string
  consumed_date: string | null
}

interface RecipeDetail {
  id: number
  grocy_id: number
  name: string
  created_at: string
  history: RecipeHistoryItem[]
  total_history: number
}

const route = useRoute()
const recipe = ref<RecipeDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const averageCalories = computed(() => {
  if (!recipe.value || recipe.value.history.length === 0) return 0
  const total = recipe.value.history.reduce((sum, item) => sum + (item.calories || 0), 0)
  return total / recipe.value.history.length
})

const averagePrice = computed(() => {
  if (!recipe.value || recipe.value.history.length === 0) return 0
  const items = recipe.value.history.filter(item => item.price_per_serving !== null)
  if (items.length === 0) return 0
  const total = items.reduce((sum, item) => sum + (item.price_per_serving || 0), 0)
  return total / items.length
})

const loadRecipeDetail = async () => {
  loading.value = true
  error.value = null

  try {
    const recipeId = route.params.id
    const response = await axios.get(`/api/recipes/${recipeId}`)
    recipe.value = response.data
  } catch (err: any) {
    console.error('Failed to load recipe details:', err)
    error.value = err.response?.data?.detail || 'Failed to load recipe details'
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString: string): string => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('uk-UA', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const formatDateShort = (dateString: string): string => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('uk-UA', {
    month: 'short',
    day: 'numeric'
  })
}

const formatDateTime = (dateString: string): string => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleString('uk-UA', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
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

onMounted(() => {
  loadRecipeDetail()
})
</script>
