<template>
  <div class="bg-gray-100">
    <div class="py-10">
      <header>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div class="md:flex md:items-center md:justify-between">
            <div class="flex-1 min-w-0">
              <h1 class="text-3xl font-bold leading-tight text-gray-900">Recipes</h1>
              <p class="mt-2 text-sm text-gray-600">Manage and sync your Grocy recipes</p>
            </div>
            <div class="mt-4 flex md:mt-0 md:ml-4 gap-3">
              <button
                @click="store.syncAll()"
                :disabled="store.syncingAll"
                class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-xs text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                <svg
                  v-if="store.syncingAll"
                  class="animate-spin -ml-1 mr-2 h-4 w-4"
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
                {{ store.syncingAll ? 'Syncing...' : 'Sync All Recipes' }}
              </button>
              <button
                @click="store.load()"
                :disabled="store.loading"
                class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-xs text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                <svg
                  class="h-4 w-4 mr-2"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      <main>
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
          <div class="px-4 py-8 sm:px-0">
            <!-- Success/Error Messages -->
            <div
              v-if="store.successMessage"
              class="mb-6 bg-green-50 border-l-4 border-green-400 p-4"
            >
              <div class="flex">
                <div class="shrink-0">
                  <svg
                    class="h-5 w-5 text-green-400"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clip-rule="evenodd"
                    />
                  </svg>
                </div>
                <div class="ml-3">
                  <p class="text-sm text-green-700">{{ store.successMessage }}</p>
                </div>
                <div class="ml-auto pl-3">
                  <button
                    @click="store.successMessage = ''"
                    class="inline-flex text-green-400 hover:text-green-600"
                  >
                    <svg
                      class="h-5 w-5"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            <div
              v-if="store.error"
              class="mb-6 bg-red-50 border-l-4 border-red-400 p-4"
            >
              <div class="flex">
                <div class="shrink-0">
                  <svg
                    class="h-5 w-5 text-red-400"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clip-rule="evenodd"
                    />
                  </svg>
                </div>
                <div class="ml-3">
                  <p class="text-sm text-red-700">{{ store.error }}</p>
                </div>
                <div class="ml-auto pl-3">
                  <button
                    @click="store.error = ''"
                    class="inline-flex text-red-400 hover:text-red-600"
                  >
                    <svg
                      class="h-5 w-5"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            <!-- Search Bar -->
            <div class="mb-6 bg-white shadow-sm sm:rounded-lg p-4">
              <div class="flex gap-3">
                <div class="flex-1">
                  <label
                    for="search"
                    class="sr-only"
                  >Search recipes</label>
                  <input
                    v-model="searchQuery"
                    @keyup.enter="store.search()"
                    type="text"
                    id="search"
                    placeholder="Search by Grocy ID or recipe name..."
                    class="shadow-xs focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                  />
                </div>
                <button
                  @click="store.search()"
                  class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-xs text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  <svg
                    class="h-4 w-4 mr-2"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                  </svg>
                  Search
                </button>
                <button
                  v-if="searchQuery"
                  @click="store.clearSearch()"
                  class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-xs text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  <svg
                    class="h-4 w-4 mr-2"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                  Clear
                </button>
              </div>
            </div>

            <!-- Recipes Table -->
            <div class="bg-white shadow-sm overflow-hidden sm:rounded-lg">
              <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                <h3 class="text-lg font-medium leading-6 text-gray-900">
                  All Recipes ({{ store.total }})
                </h3>
              </div>

              <div
                v-if="store.loading"
                class="px-4 py-12 text-center"
              >
                <svg
                  class="animate-spin h-8 w-8 mx-auto text-indigo-600"
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
                <p class="mt-2 text-sm text-gray-500">Loading recipes...</p>
              </div>

              <div
                v-else-if="store.recipes.length === 0"
                class="px-4 py-12 text-center"
              >
                <svg
                  class="mx-auto h-12 w-12 text-gray-400"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <h3 class="mt-2 text-sm font-medium text-gray-900">No recipes</h3>
                <p class="mt-1 text-sm text-gray-500">Get started by syncing recipes from Grocy.</p>
                <div class="mt-6">
                  <button
                    @click="store.syncAll()"
                    class="inline-flex items-center px-4 py-2 border border-transparent shadow-xs text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Sync All Recipes
                  </button>
                </div>
              </div>

              <div
                v-else
                class="overflow-x-auto"
              >
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Recipe</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Latest Data</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nutrients (per serving)</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Consumed</th>
                      <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    <tr
                      v-for="recipe in store.recipes"
                      :key="recipe.id"
                      class="hover:bg-gray-50"
                    >
                      <td class="px-6 py-4">
                        <router-link
                          :to="`/recipes/${recipe.id}`"
                          class="text-sm font-medium text-blue-600 hover:text-blue-900"
                        >
                          {{ recipe.name }}
                        </router-link>
                        <div class="text-sm text-gray-500">Grocy ID: {{ recipe.grocy_id }}</div>
                      </td>
                      <td class="px-6 py-4">
                        <div
                          v-if="recipe.latest_servings"
                          class="text-sm text-gray-900"
                        >
                          {{ recipe.latest_servings }} servings
                          <span
                            v-if="recipe.latest_price_per_serving"
                            class="text-gray-500"
                          >
                            ({{ recipe.latest_price_per_serving.toFixed(2) }}/serving)
                          </span>
                        </div>
                        <div
                          v-else
                          class="text-sm text-gray-500"
                        >
                          No data yet
                        </div>
                      </td>
                      <td class="px-6 py-4">
                        <div
                          v-if="recipe.latest_calories !== null"
                          class="text-sm"
                        >
                          <div class="text-gray-900">{{ recipe.latest_calories.toFixed(0) }} kcal</div>
                          <div class="text-gray-500 text-xs">
                            P: {{ recipe.latest_proteins?.toFixed(1) }}g |
                            C: {{ recipe.latest_carbohydrates?.toFixed(1) }}g |
                            F: {{ recipe.latest_fats?.toFixed(1) }}g
                          </div>
                        </div>
                        <div
                          v-else
                          class="text-sm text-gray-500"
                        >
                          -
                        </div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {{ recipe.latest_consumed_at ? formatDate(recipe.latest_consumed_at) : '-' }}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          @click="store.syncSingle(recipe.grocy_id)"
                          :disabled="store.syncingRecipes.has(recipe.grocy_id)"
                          class="text-indigo-600 hover:text-indigo-900 mr-4 disabled:opacity-50"
                        >
                          {{ store.syncingRecipes.has(recipe.grocy_id) ? 'Syncing...' : 'Sync' }}
                        </button>
                        <router-link
                          :to="`/recipes/${recipe.id}`"
                          class="text-blue-600 hover:text-blue-900 mr-4"
                        >
                          History
                        </router-link>
                        <router-link
                          :to="`/recipe-nutrients?id=${recipe.grocy_id}`"
                          class="text-green-600 hover:text-green-900"
                        >
                          Calculate
                        </router-link>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <PaginationBar
                :skip="store.skip"
                :limit="store.limit"
                :total="store.total"
                @prev="store.previousPage()"
                @next="store.nextPage()"
              />
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useHouseholdStore } from '@/store/household'
import { useRecipesStore } from '@/store/recipes'
import PaginationBar from '@/components/PaginationBar.vue'

const householdStore = useHouseholdStore()
const store = useRecipesStore()
const { searchQuery } = storeToRefs(store)

watch(() => householdStore.selectedId, (id) => {
  if (id !== null) store.load()
}, { immediate: true })

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>
