<template>
  <div v-if="visible" class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex items-center justify-center min-h-screen px-4">
      <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="emit('close')"></div>
      <div class="bg-white rounded-lg shadow-xl z-10 w-full max-w-md p-6">
        <h3 class="text-lg font-medium text-red-900 mb-2">Delete Household</h3>
        <div class="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          <p class="text-sm font-medium text-red-800">
            This will permanently delete ALL data for ALL members of "{{ householdName }}".
          </p>
          <p class="text-xs text-red-600 mt-1">This action cannot be undone.</p>
        </div>
        <div class="space-y-3 mb-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Type <code class="bg-gray-100 px-1 rounded text-red-600">DELETE {{ householdName }}</code> to confirm
            </label>
            <input
              v-model="confirmText"
              type="text"
              class="shadow-sm focus:ring-red-500 focus:border-red-500 block w-full sm:text-sm border-gray-300 rounded-md"
              :placeholder="`DELETE ${householdName}`"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Enter your password</label>
            <input
              v-model="password"
              type="password"
              class="shadow-sm focus:ring-red-500 focus:border-red-500 block w-full sm:text-sm border-gray-300 rounded-md"
            />
          </div>
        </div>
        <label class="flex items-start space-x-2 mb-3">
          <input type="checkbox" v-model="exportData" class="mt-0.5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
          <span class="text-sm text-gray-700">Send a copy of household data to my email before deletion</span>
        </label>
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
            @click="handleDelete"
            :disabled="confirmText !== `DELETE ${householdName}` || !password || loading"
            class="py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ loading ? 'Deleting...' : 'Delete Forever' }}
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

const props = defineProps<{
  visible: boolean
  householdId: number | null
  householdName: string
}>()

const emit = defineEmits<{ close: [] }>()

const householdStore = useHouseholdStore()
const confirmText = ref('')
const password = ref('')
const exportData = ref(false)
const loading = ref(false)
const error = ref('')

watch(() => props.visible, (open) => {
  if (open) {
    confirmText.value = ''
    password.value = ''
    exportData.value = false
    error.value = ''
  }
})

const handleDelete = async () => {
  if (!props.householdId) return
  loading.value = true
  error.value = ''
  try {
    await householdStore.deleteHousehold(props.householdId, {
      password: password.value,
      confirmation_text: confirmText.value,
      export_data: exportData.value,
    })
    emit('close')
  } catch (err: any) {
    error.value = parseApiError(err, 'Failed to delete household')
  } finally {
    loading.value = false
  }
}
</script>
