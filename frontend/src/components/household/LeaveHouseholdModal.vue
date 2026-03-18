<template>
  <div v-if="visible" class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex items-center justify-center min-h-screen px-4">
      <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="emit('close')"></div>
      <div class="bg-white rounded-lg shadow-xl z-10 w-full max-w-md p-6">
        <h3 class="text-lg font-medium text-red-900 mb-4">
          {{ isSelf ? 'Leave Household' : 'Remove Member' }}
        </h3>
        <div v-if="dataLoading" class="text-sm text-gray-500">Loading data summary...</div>
        <template v-else>
          <p class="text-sm text-gray-700 mb-3">
            {{ isSelf
              ? `You are about to leave "${householdName}".`
              : `You are about to remove this user from "${householdName}".`
            }}
          </p>
          <div v-if="dataSummary && dataSummary.total > 0" class="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
            <p class="text-sm font-medium text-red-800 mb-2">The following data will be hidden:</p>
            <ul class="text-xs text-red-700 space-y-0.5">
              <li v-if="dataSummary.consumed_products > 0">Consumed products: {{ dataSummary.consumed_products }}</li>
              <li v-if="dataSummary.recipes_data > 0">Recipe records: {{ dataSummary.recipes_data }}</li>
              <li v-if="dataSummary.meal_plan_consumptions > 0">Meal plan consumptions: {{ dataSummary.meal_plan_consumptions }}</li>
              <li v-if="dataSummary.note_nutrients > 0">Note nutrients: {{ dataSummary.note_nutrients }}</li>
              <li v-if="dataSummary.daily_nutrition > 0">Daily nutrition records: {{ dataSummary.daily_nutrition }}</li>
            </ul>
          </div>
          <label class="flex items-center space-x-2 mb-4">
            <input type="checkbox" v-model="confirmChecked" class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
            <span class="text-sm text-gray-700">I understand my data will be hidden</span>
          </label>
        </template>
        <p v-if="error" class="text-sm text-red-500 mb-3">{{ error }}</p>
        <div class="flex justify-end space-x-3">
          <button
            type="button"
            @click="emit('close')"
            class="py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            @click="handleConfirm"
            :disabled="!confirmChecked || loading"
            class="py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ loading ? 'Processing...' : (isSelf ? 'Leave' : 'Remove') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useHouseholdStore } from '../../store/household'
import { parseApiError } from '../../utils/parseApiError'
import type { DataSummary } from '../../types/household'

const props = defineProps<{
  visible: boolean
  householdId: number | null
  userId: number | null
  householdName: string
  isSelf: boolean
}>()

const emit = defineEmits<{ close: []; done: [] }>()

const householdStore = useHouseholdStore()
const dataLoading = ref(false)
const dataSummary = ref<DataSummary | null>(null)
const confirmChecked = ref(false)
const loading = ref(false)
const error = ref('')

watch(() => props.visible, async (open) => {
  if (open && props.householdId && props.userId) {
    confirmChecked.value = false
    error.value = ''
    dataSummary.value = null
    dataLoading.value = true
    dataSummary.value = await householdStore.getUserDataSummary(props.householdId, props.userId)
    dataLoading.value = false
  }
})

const handleConfirm = async () => {
  if (!props.householdId || !props.userId) return
  loading.value = true
  error.value = ''
  try {
    await householdStore.removeMember(props.householdId, props.userId)
    emit('done')
  } catch (err: any) {
    error.value = parseApiError(err, 'Failed to remove user')
  } finally {
    loading.value = false
  }
}
</script>
