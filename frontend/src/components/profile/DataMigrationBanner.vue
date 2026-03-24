<template>
  <div
    v-if="counts && counts.total > 0"
    class="mt-3 bg-yellow-50 border border-yellow-200 rounded-lg p-4"
  >
    <h5 class="text-sm font-medium text-yellow-800 mb-2">Data Migration Required</h5>
    <p class="text-xs text-yellow-700 mb-3">
      {{ counts.total }} records need to be assigned to this household and user.
    </p>
    <ul class="text-xs text-yellow-600 mb-3 space-y-0.5">
      <li v-if="counts.products > 0">Products: {{ counts.products }}</li>
      <li v-if="counts.recipes > 0">Recipes: {{ counts.recipes }}</li>
      <li v-if="counts.consumed_products > 0">Consumed products: {{ counts.consumed_products }}</li>
      <li v-if="counts.recipes_data > 0">Recipe data: {{ counts.recipes_data }}</li>
      <li v-if="counts.meal_plan_consumptions > 0">Meal plan consumptions: {{ counts.meal_plan_consumptions }}</li>
      <li v-if="counts.note_nutrients > 0">Note nutrients: {{ counts.note_nutrients }}</li>
      <li v-if="counts.daily_nutrition > 0">Daily nutrition: {{ counts.daily_nutrition }}</li>
    </ul>
    <div class="flex items-center gap-3">
      <button
        @click="handleBackfill"
        :disabled="loading"
        class="inline-flex items-center py-1.5 px-3 border border-transparent shadow-sm text-xs font-medium rounded-md text-white bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <svg
          v-if="loading"
          class="animate-spin -ml-0.5 mr-1.5 h-3 w-3 text-white"
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
        Assign All to This Household
      </button>
    </div>
    <div
      v-if="error"
      class="mt-2 text-xs text-red-500"
    >
      {{ error }}
    </div>
    <div
      v-if="successMessage"
      class="mt-2 text-xs text-green-600"
    >
      {{ successMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useHouseholdStore } from '../../store/household'
import { parseApiError } from '../../utils/parseApiError'

const props = defineProps<{
  householdId: number
}>()

const householdStore = useHouseholdStore()
const loading = ref(false)
const error = ref('')
const successMessage = ref('')

const counts = computed(() => householdStore.backfillCounts[props.householdId])

const handleBackfill = async () => {
  loading.value = true
  error.value = ''
  successMessage.value = ''
  try {
    const res = await householdStore.runBackfill(props.householdId)
    successMessage.value = `Done! Updated ${res.updated_household_id} household and ${res.updated_user_id} user assignments.`
  } catch (err: unknown) {
    error.value = parseApiError(err, 'Failed to run backfill')
  } finally {
    loading.value = false
  }
}
</script>
