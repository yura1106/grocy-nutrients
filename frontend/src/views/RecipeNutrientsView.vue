<template>
  <div class="min-h-screen bg-gray-100">
    <div class="py-10">
      <header>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold leading-tight text-gray-900">Recipe Nutrients Calculator</h1>
          <p class="mt-2 text-sm text-gray-600">Calculate nutritional information for recipes</p>
        </div>
      </header>
      <main>
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
          <div class="px-4 py-8 sm:px-0">

            <!-- Step 1: Select Recipe -->
            <div class="bg-white shadow sm:rounded-lg mb-6">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">
                  Step 1: Select Recipe
                </h3>
                <div class="flex gap-4 items-end flex-wrap">
                  <!-- Recipe select with search -->
                  <div class="flex-1 max-w-md">
                    <label class="block text-sm font-medium text-gray-700 mb-2">
                      Search by name
                    </label>
                    <VueMultiselect
                      v-model="selectedRecipe"
                      :options="allRecipes"
                      :searchable="true"
                      :close-on-select="true"
                      :show-labels="false"
                      label="name"
                      track-by="id"
                      placeholder="Start typing recipe name..."
                      :disabled="loading"
                      @select="onRecipeSelect"
                    >
                      <template #option="props">
                        <span>{{ (props as any).option.name }}</span>
                        <span class="text-gray-400 text-xs ml-2">#{{ (props as any).option.id }}</span>
                      </template>
                    </VueMultiselect>
                  </div>
                  <!-- Or recipe ID -->
                  <div class="max-w-[160px]">
                    <label for="recipe-id" class="block text-sm font-medium text-gray-700 mb-2">
                      or Recipe ID
                    </label>
                    <input
                      id="recipe-id"
                      v-model.number="recipeId"
                      type="number"
                      placeholder="e.g. 100"
                      class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                      :disabled="loading"
                      @keyup.enter="calculateNutrients()"
                    />
                  </div>
                  <button
                    @click="calculateNutrients()"
                    :disabled="loading || !recipeId"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg v-if="loading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {{ loading ? 'Calculating...' : 'Calculate Nutrients' }}
                  </button>
                </div>
              </div>
            </div>

            <!-- Error state -->
            <div v-if="error" class="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
              <div class="flex">
                <div class="flex-shrink-0">
                  <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="ml-3">
                  <p class="text-sm text-red-700">{{ error }}</p>
                </div>
              </div>
            </div>

            <!-- Step 2: Product Binding Check & Conversion Factor (if recipe has product) -->
            <div v-if="pendingResult && pendingResult.has_product && !portionConfirmed" class="bg-white shadow sm:rounded-lg mb-6">
              <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">
                  Step 2: Verify Product Conversion
                </h3>
                <p class="text-sm text-gray-600 mb-3">
                  Recipe has an associated product:
                  <a
                    :href="pendingResult.product_url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="font-medium text-indigo-600 hover:text-indigo-500 underline"
                  >
                    Product #{{ pendingResult.product_id }}
                    <svg class="inline h-3 w-3 ml-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                </p>

                <!-- Current conversion factor display -->
                <div v-if="pendingResult.product_conversion_factor !== null && pendingResult.product_conversion_factor !== undefined" class="bg-blue-50 border-l-4 border-blue-400 p-4 mb-4">
                  <p class="text-sm text-blue-800">
                    Current value: <span class="font-bold text-lg">{{ pendingResult.product_conversion_factor }}</span>
                    {{ pendingResult.product_conversion_unit }} per serving
                  </p>
                </div>
                <div v-else class="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
                  <p class="text-sm text-yellow-800">
                    No conversion factor found for this product (stock unit is not grams/ml and no conversion is set).
                  </p>
                </div>

                <!-- Question about changes -->
                <p class="text-sm font-medium text-gray-700 mb-3">
                  Were there changes to this value?
                </p>

                <!-- New value input -->
                <div v-if="showNewConversionInput" class="mb-4">
                  <div class="flex gap-3 items-end">
                    <div class="flex-1 max-w-xs">
                      <label for="new-conversion" class="block text-sm font-medium text-gray-700 mb-1">
                        New value ({{ pendingResult.product_conversion_unit || 'g/ml' }})
                      </label>
                      <input
                        id="new-conversion"
                        v-model.number="newConversionFactor"
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder="Enter new value"
                        class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                        :disabled="conversionSaving"
                      />
                    </div>
                    <button
                      @click="saveNewConversion"
                      :disabled="conversionSaving || !newConversionFactor"
                      class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <svg v-if="conversionSaving" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      {{ conversionSaving ? 'Saving...' : 'Save & Recalculate' }}
                    </button>
                    <button
                      @click="showNewConversionInput = false"
                      :disabled="conversionSaving"
                      class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>

                <!-- Action buttons -->
                <div v-if="!showNewConversionInput" class="flex gap-3">
                  <button
                    @click="showNewConversionInput = true"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-yellow-700 bg-yellow-100 hover:bg-yellow-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500"
                  >
                    Yes, enter new value
                  </button>
                  <button
                    @click="confirmPortionMeasurements(true)"
                    class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                  >
                    No, continue with current value
                  </button>
                </div>
              </div>
            </div>

            <!-- Step 2/3: Recipe Results -->
            <div v-if="result" class="space-y-6">

              <!-- Recipe Info Card -->
              <div class="bg-white shadow overflow-hidden sm:rounded-lg">
                <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                  <h3 class="text-lg font-medium leading-6 text-gray-900">
                    {{ result.recipe_name }}
                  </h3>
                  <p class="mt-1 text-sm text-gray-500">Recipe ID: {{ result.recipe_id }}</p>
                </div>
                <div class="px-4 py-5 sm:p-6">
                  <dl class="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
                    <div>
                      <dt class="text-sm font-medium text-gray-500">Status</dt>
                      <dd class="mt-1 text-sm text-gray-900">
                        <span
                          class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                          :class="result.can_consume ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'"
                        >
                          {{ result.message }}
                        </span>
                      </dd>
                    </div>
                    <div v-if="result.has_product">
                      <dt class="text-sm font-medium text-gray-500">Associated Product</dt>
                      <dd class="mt-1 text-sm">
                        <a
                          :href="result.product_url"
                          target="_blank"
                          class="text-indigo-600 hover:text-indigo-900"
                        >
                          View Product #{{ result.product_id }}
                        </a>
                      </dd>
                    </div>
                    <div v-if="result.desired_servings">
                      <dt class="text-sm font-medium text-gray-500">Servings</dt>
                      <dd class="mt-1 text-sm text-gray-900">{{ result.desired_servings }}</dd>
                    </div>
                  </dl>
                </div>
              </div>

              <!-- Ingredients -->
              <div class="bg-white shadow overflow-hidden sm:rounded-lg">
                <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                  <h3 class="text-lg font-medium leading-6 text-gray-900">Ingredients</h3>
                </div>
                <div class="overflow-x-auto">
                  <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                      </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                      <tr
                        v-for="ingredient in result.ingredients"
                        :key="ingredient.product_id"
                        :class="{ 'bg-yellow-50': ingredient.product_id !== ingredient.product_id_effective }"
                        :title="ingredient.product_id !== ingredient.product_id_effective ? 'Warning: Using substitute product (ID ' + ingredient.product_id_effective + ' instead of ' + ingredient.product_id + ')' : ''"
                      >
                        <td class="px-6 py-4 text-sm font-medium text-gray-900">
                          {{ ingredient.name }}
                          <span v-if="ingredient.product_id !== ingredient.product_id_effective" class="ml-2 text-xs text-yellow-700">
                            ⚠️ Substitute
                          </span>
                        </td>
                        <td class="px-6 py-4 text-sm text-gray-900">{{ formatAmount(ingredient.amount) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Total Nutrients -->
              <div class="bg-white shadow overflow-hidden sm:rounded-lg">
                <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                  <h3 class="text-lg font-medium leading-6 text-gray-900">Total Nutrients</h3>
                </div>
                <div class="px-4 py-5 sm:p-6">
                  <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="bg-gray-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-gray-500">Calories</p>
                      <p class="text-lg font-semibold text-gray-900">{{ formatNutrient(result.total_nutrients.calories) }} kcal</p>
                    </div>
                    <div class="bg-gray-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-gray-500">Proteins</p>
                      <p class="text-lg font-semibold text-gray-900">{{ formatNutrient(result.total_nutrients.proteins) }}g</p>
                    </div>
                    <div class="bg-gray-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-gray-500">Carbohydrates</p>
                      <p class="text-lg font-semibold text-gray-900">{{ formatNutrient(result.total_nutrients.carbohydrates) }}g</p>
                    </div>
                    <div class="bg-gray-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-gray-500">of which Sugars</p>
                      <p class="text-lg font-semibold text-gray-900">{{ formatNutrient(result.total_nutrients.carbohydrates_of_sugars) }}g</p>
                    </div>
                    <div class="bg-gray-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-gray-500">Fats</p>
                      <p class="text-lg font-semibold text-gray-900">{{ formatNutrient(result.total_nutrients.fats) }}g</p>
                    </div>
                    <div class="bg-gray-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-gray-500">of which Saturated</p>
                      <p class="text-lg font-semibold text-gray-900">{{ formatNutrient(result.total_nutrients.fats_saturated) }}g</p>
                    </div>
                    <div class="bg-gray-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-gray-500">Salt</p>
                      <p class="text-lg font-semibold text-gray-900">{{ formatNutrient(result.total_nutrients.salt) }}g</p>
                    </div>
                    <div class="bg-gray-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-gray-500">Fiber</p>
                      <p class="text-lg font-semibold text-gray-900">{{ formatNutrient(result.total_nutrients.fibers) }}g</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Per Serving Nutrients (if available) -->
              <div v-if="result.per_serving_nutrients" class="bg-white shadow overflow-hidden sm:rounded-lg">
                <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                  <h3 class="text-lg font-medium leading-6 text-gray-900">Per Serving Nutrients</h3>
                  <p class="mt-1 text-sm text-gray-500">Based on {{ result.desired_servings }} servings</p>
                </div>
                <div class="px-4 py-5 sm:p-6">
                  <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="bg-indigo-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-indigo-600">Calories</p>
                      <p class="text-lg font-semibold text-indigo-900">{{ formatNutrient(result.per_serving_nutrients.calories) }} kcal</p>
                    </div>
                    <div class="bg-indigo-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-indigo-600">Proteins</p>
                      <p class="text-lg font-semibold text-indigo-900">{{ formatNutrient(result.per_serving_nutrients.proteins) }}g</p>
                    </div>
                    <div class="bg-indigo-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-indigo-600">Carbohydrates</p>
                      <p class="text-lg font-semibold text-indigo-900">{{ formatNutrient(result.per_serving_nutrients.carbohydrates) }}g</p>
                    </div>
                    <div class="bg-indigo-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-indigo-600">of which Sugars</p>
                      <p class="text-lg font-semibold text-indigo-900">{{ formatNutrient(result.per_serving_nutrients.carbohydrates_of_sugars) }}g</p>
                    </div>
                    <div class="bg-indigo-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-indigo-600">Fats</p>
                      <p class="text-lg font-semibold text-indigo-900">{{ formatNutrient(result.per_serving_nutrients.fats) }}g</p>
                    </div>
                    <div class="bg-indigo-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-indigo-600">of which Saturated</p>
                      <p class="text-lg font-semibold text-indigo-900">{{ formatNutrient(result.per_serving_nutrients.fats_saturated) }}g</p>
                    </div>
                    <div class="bg-indigo-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-indigo-600">Salt</p>
                      <p class="text-lg font-semibold text-indigo-900">{{ formatNutrient(result.per_serving_nutrients.salt) }}g</p>
                    </div>
                    <div class="bg-indigo-50 px-4 py-3 rounded-md">
                      <p class="text-xs text-indigo-600">Fiber</p>
                      <p class="text-lg font-semibold text-indigo-900">{{ formatNutrient(result.per_serving_nutrients.fibers) }}g</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Fulfillment Status -->
              <div class="bg-white shadow overflow-hidden sm:rounded-lg">
                <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                  <h3 class="text-lg font-medium leading-6 text-gray-900">Recipe Fulfillment</h3>
                </div>
                <div class="px-4 py-5 sm:p-6">
                  <dl class="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-3">
                    <div>
                      <dt class="text-sm font-medium text-gray-500">Missing Products</dt>
                      <dd class="mt-1 text-sm">
                        <span
                          class="text-lg font-semibold"
                          :class="result.fulfillment.missing_products_count === 0 ? 'text-green-600' : 'text-red-600'"
                        >
                          {{ result.fulfillment.missing_products_count }}
                        </span>
                      </dd>
                    </div>
                    <div>
                      <dt class="text-sm font-medium text-gray-500">Total Cost</dt>
                      <dd class="mt-1 text-sm text-gray-900 text-lg font-semibold">
                        {{ result.fulfillment.costs.toFixed(2) }}
                      </dd>
                    </div>
                    <div v-if="result.fulfillment.costs_per_serving">
                      <dt class="text-sm font-medium text-gray-500">Cost per Serving</dt>
                      <dd class="mt-1 text-sm text-gray-900 text-lg font-semibold">
                        {{ result.fulfillment.costs_per_serving.toFixed(2) }}
                      </dd>
                    </div>
                  </dl>

                  <div class="mt-4">
                    <dt class="text-sm font-medium text-gray-500 mb-2">Products</dt>
                    <dd class="text-sm text-gray-900">{{ result.fulfillment.product_names_comma_separated }}</dd>
                  </div>
                </div>
              </div>

              <!-- Missing Nutrients Data -->
              <div v-if="result.missing_nutrients && hasMissingNutrients" class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                <div class="flex">
                  <div class="flex-shrink-0">
                    <svg class="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                  </div>
                  <div class="ml-3 flex-1">
                    <h3 class="text-sm font-medium text-yellow-800">Some Products Missing Nutrient Data</h3>
                    <div class="mt-2 text-sm text-yellow-700">
                      <details class="cursor-pointer">
                        <summary class="font-medium">View details</summary>
                        <div class="mt-2 space-y-2">
                          <div v-if="result.missing_nutrients.calories.length > 0">
                            <p class="font-medium">Calories:</p>
                            <ul class="list-disc list-inside ml-2">
                              <li v-for="product in result.missing_nutrients.calories" :key="product">{{ product }}</li>
                            </ul>
                          </div>
                          <div v-if="result.missing_nutrients.proteins.length > 0">
                            <p class="font-medium">Proteins:</p>
                            <ul class="list-disc list-inside ml-2">
                              <li v-for="product in result.missing_nutrients.proteins" :key="product">{{ product }}</li>
                            </ul>
                          </div>
                          <div v-if="result.missing_nutrients.carbohydrates.length > 0">
                            <p class="font-medium">Carbohydrates:</p>
                            <ul class="list-disc list-inside ml-2">
                              <li v-for="product in result.missing_nutrients.carbohydrates" :key="product">{{ product }}</li>
                            </ul>
                          </div>
                          <div v-if="result.missing_nutrients.fats.length > 0">
                            <p class="font-medium">Fats:</p>
                            <ul class="list-disc list-inside ml-2">
                              <li v-for="product in result.missing_nutrients.fats" :key="product">{{ product }}</li>
                            </ul>
                          </div>
                        </div>
                      </details>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Step 3: Consume Recipe (only if can consume) -->
              <div v-if="result.can_consume && !consumed" class="bg-white shadow sm:rounded-lg">
                <div class="px-4 py-5 sm:p-6">
                  <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">
                    Step 2: Consume Recipe
                  </h3>
                  <div class="bg-green-50 border-l-4 border-green-400 p-4 mb-4">
                    <p class="text-sm text-green-700">All products are available! You can consume this recipe.</p>
                  </div>
                  <div class="flex gap-4">
                    <button
                      @click="showConsumeConfirmation = true"
                      :disabled="consumeLoading"
                      class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                    >
                      {{ consumeLoading ? 'Consuming...' : 'Consume Recipe' }}
                    </button>
                    <button
                      @click="reset"
                      class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                    >
                      Calculate Another Recipe
                    </button>
                  </div>
                </div>
              </div>

              <!-- Consume Confirmation Modal -->
              <div v-if="showConsumeConfirmation" class="fixed z-10 inset-0 overflow-y-auto">
                <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                  <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="showConsumeConfirmation = false"></div>
                  <div class="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
                    <div>
                      <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
                        <svg class="h-6 w-6 text-green-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <div class="mt-3 text-center sm:mt-5">
                        <h3 class="text-lg leading-6 font-medium text-gray-900">Confirm Recipe Consumption</h3>
                        <div class="mt-2">
                          <p class="text-sm text-gray-500">
                            Are you sure you want to consume recipe "{{ result.recipe_name }}"? This will update the stock levels in Grocy.
                          </p>
                        </div>
                      </div>
                    </div>
                    <div class="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
                      <button
                        @click="consumeRecipe"
                        :disabled="consumeLoading"
                        class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-green-600 text-base font-medium text-white hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 sm:col-start-2 sm:text-sm disabled:opacity-50"
                      >
                        {{ consumeLoading ? 'Consuming...' : 'Yes, Consume' }}
                      </button>
                      <button
                        @click="showConsumeConfirmation = false"
                        :disabled="consumeLoading"
                        class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:col-start-1 sm:text-sm"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Success Message -->
              <div v-if="consumed" class="bg-green-50 border-l-4 border-green-400 p-4">
                <div class="flex">
                  <div class="flex-shrink-0">
                    <svg class="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                  </div>
                  <div class="ml-3">
                    <h3 class="text-sm font-medium text-green-800">Recipe Consumed!</h3>
                    <p class="mt-2 text-sm text-green-700">{{ consumeMessage }}</p>
                    <button
                      @click="reset"
                      class="mt-3 inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-green-700 bg-green-100 hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                    >
                      Calculate Another Recipe
                    </button>
                  </div>
                </div>
              </div>

            </div>

          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import VueMultiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'

interface RecipeNutrients {
  calories: number
  proteins: number
  carbohydrates: number
  carbohydrates_of_sugars: number
  fats: number
  fats_saturated: number
  salt: number
  fibers: number
}

interface RecipeIngredient {
  product_id: number
  product_id_effective: number
  name: string
  amount: number
  unit?: string
}

interface RecipeFulfillment {
  id: number
  recipe_id: number
  need_fulfilled: number
  need_fulfilled_with_shopping_list: number
  missing_products_count: number
  costs: number
  costs_per_serving?: number
  calories?: number
  due_score: number
  product_names_comma_separated: string
  prices_incomplete: number
}

interface MissingNutrients {
  calories: string[]
  proteins: string[]
  carbohydrates: string[]
  carbohydrates_of_sugars: string[]
  fats: string[]
  fats_saturated: string[]
  salt: string[]
  fibers: string[]
}

interface RecipeResult {
  status: string
  recipe_id: number
  recipe_name: string
  has_product: boolean
  product_id?: number
  product_url?: string
  desired_servings?: number
  product_conversion_factor?: number | null
  product_conversion_unit?: string | null
  product_qu_id_stock?: number | null
  product_conversion_target_qu_id?: number | null
  ingredients: RecipeIngredient[]
  total_nutrients: RecipeNutrients
  per_serving_nutrients?: RecipeNutrients
  fulfillment: RecipeFulfillment
  missing_nutrients?: MissingNutrients
  can_consume: boolean
  message: string
}

interface RecipeListItem {
  id: number
  name: string
}

const recipeId = ref<number | null>(null)
const loading = ref(false)
const consumeLoading = ref(false)
const error = ref('')
const result = ref<RecipeResult | null>(null)
const pendingResult = ref<RecipeResult | null>(null)
const portionConfirmed = ref(false)
const consumed = ref(false)
const consumeMessage = ref('')
const showConsumeConfirmation = ref(false)
const showNewConversionInput = ref(false)
const newConversionFactor = ref<number | null>(null)
const conversionSaving = ref(false)

// Recipe search/select — all recipes loaded once, filtered client-side by vue-multiselect
const selectedRecipe = ref<RecipeListItem | null>(null)
const allRecipes = ref<RecipeListItem[]>([])

const loadAllRecipes = async () => {
  try {
    const response = await axios.get('/api/recipes/grocy-list')
    allRecipes.value = response.data
  } catch {
    allRecipes.value = []
  }
}

const onRecipeSelect = (recipe: RecipeListItem) => {
  recipeId.value = recipe.id
  calculateNutrients()
}

const hasMissingNutrients = computed(() => {
  if (!result.value?.missing_nutrients) return false

  const mn = result.value.missing_nutrients
  return (
    mn.calories.length > 0 ||
    mn.proteins.length > 0 ||
    mn.carbohydrates.length > 0 ||
    mn.carbohydrates_of_sugars.length > 0 ||
    mn.fats.length > 0 ||
    mn.fats_saturated.length > 0 ||
    mn.salt.length > 0 ||
    mn.fibers.length > 0
  )
})

const calculateNutrients = async (skipConfirmation = false) => {
  if (!recipeId.value) return

  loading.value = true
  error.value = ''
  result.value = null
  pendingResult.value = null
  portionConfirmed.value = false
  consumed.value = false

  try {
    const response = await axios.post<RecipeResult>('/api/recipes/calculate', {
      recipe_id: recipeId.value,
    })

    // If recipe has associated product and not skipping confirmation, ask first
    if (response.data.has_product && !skipConfirmation) {
      pendingResult.value = response.data
    } else {
      // No product or skipping confirmation - show results directly
      result.value = response.data
      portionConfirmed.value = true
    }
  } catch (err: any) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'Failed to calculate recipe nutrients. Please try again.'
    }
  } finally {
    loading.value = false
  }
}

const confirmPortionMeasurements = (confirmed: boolean) => {
  if (confirmed) {
    result.value = pendingResult.value
    portionConfirmed.value = true
    pendingResult.value = null
  }
}

const saveNewConversion = async () => {
  if (!pendingResult.value || !newConversionFactor.value) return

  const pr = pendingResult.value
  if (!pr.product_id || !pr.product_qu_id_stock) return

  // Determine target unit: use existing or default to GRAM (82)
  const targetQuId = pr.product_conversion_target_qu_id || 82

  conversionSaving.value = true
  error.value = ''

  try {
    await axios.post('/api/recipes/update-conversion', {
      product_id: pr.product_id,
      from_qu_id: pr.product_qu_id_stock,
      to_qu_id: targetQuId,
      factor: newConversionFactor.value,
    })

    // Recalculate after saving, skip confirmation step
    showNewConversionInput.value = false
    newConversionFactor.value = null
    pendingResult.value = null
    portionConfirmed.value = false
    await calculateNutrients(true)
  } catch (err: any) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'Failed to save conversion factor. Please try again.'
    }
  } finally {
    conversionSaving.value = false
  }
}

const consumeRecipe = async () => {
  if (!result.value) return

  consumeLoading.value = true
  error.value = ''

  try {
    // Prepare data to send
    const consumeData: any = {
      recipe_id: result.value.recipe_id,
      confirmed: true,
    }

    // Add optional data for saving if available
    if (result.value.per_serving_nutrients && result.value.desired_servings) {
      consumeData.servings = result.value.desired_servings
      consumeData.price_per_serving = result.value.fulfillment.costs_per_serving || null
      consumeData.per_serving_nutrients = result.value.per_serving_nutrients
    }

    const response = await axios.post('/api/recipes/consume', consumeData)

    consumed.value = true
    consumeMessage.value = response.data.message
    showConsumeConfirmation.value = false
  } catch (err: any) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'Failed to consume recipe. Please try again.'
    }
    showConsumeConfirmation.value = false
  } finally {
    consumeLoading.value = false
  }
}

const reset = () => {
  recipeId.value = null
  selectedRecipe.value = null
  result.value = null
  pendingResult.value = null
  portionConfirmed.value = false
  consumed.value = false
  consumeMessage.value = ''
  error.value = ''
  showConsumeConfirmation.value = false
  showNewConversionInput.value = false
  newConversionFactor.value = null
  conversionSaving.value = false
}

const formatNutrient = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return '-'
  return value.toFixed(2)
}

const formatAmount = (value: number): string => {
  return value.toFixed(2)
}

// Initialize from query parameters and load recipes list
const route = useRoute()
onMounted(async () => {
  loadAllRecipes()
  const queryId = route.query.id
  if (queryId) {
    recipeId.value = parseInt(queryId as string)
    if (!isNaN(recipeId.value)) {
      calculateNutrients()
    }
  }
})
</script>
