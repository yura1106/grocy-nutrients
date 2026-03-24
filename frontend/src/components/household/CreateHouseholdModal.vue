<template>
  <div
    v-if="visible"
    class="fixed inset-0 z-50 overflow-y-auto"
  >
    <div class="flex items-center justify-center min-h-screen px-4">
      <div
        class="fixed inset-0 bg-gray-500 bg-opacity-75"
        @click="emit('close')"
      ></div>
      <div class="bg-white rounded-lg shadow-xl z-10 w-full max-w-md p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Create Household</h3>
        <form
          @submit.prevent="handleSubmit"
          class="space-y-4"
        >
          <div>
            <label class="block text-sm font-medium text-gray-700">Name *</label>
            <input
              v-model="form.name"
              type="text"
              required
              class="mt-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Grocy URL</label>
            <input
              v-model="form.grocy_url"
              type="url"
              placeholder="http://192.168.1.1:9192"
              class="mt-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Address</label>
            <input
              v-model="form.address"
              type="text"
              class="mt-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
            />
          </div>
          <p
            v-if="error"
            class="text-sm text-red-500"
          >
            {{ error }}
          </p>
          <div class="flex justify-end space-x-3">
            <button
              type="button"
              @click="emit('close')"
              class="py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="loading"
              class="py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
            >
              {{ loading ? 'Creating...' : 'Create' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useHouseholdStore } from '../../store/household'
import { parseApiError } from '../../utils/parseApiError'

defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: [] }>()

const householdStore = useHouseholdStore()
const loading = ref(false)
const error = ref('')
const form = reactive({ name: '', grocy_url: '', address: '' })

const handleSubmit = async () => {
  loading.value = true
  error.value = ''
  try {
    await householdStore.createHousehold({
      name: form.name,
      grocy_url: form.grocy_url || null,
      address: form.address || null,
    })
    form.name = ''
    form.grocy_url = ''
    form.address = ''
    emit('close')
  } catch (err: unknown) {
    error.value = parseApiError(err, 'Failed to create household')
  } finally {
    loading.value = false
  }
}
</script>
