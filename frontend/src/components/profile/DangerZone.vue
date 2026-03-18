<template>
  <!-- Delete Account Section -->
  <div class="bg-white shadow overflow-hidden sm:rounded-lg mt-6">
    <div class="px-4 py-5 sm:px-6">
      <h3 class="text-lg leading-6 font-medium text-red-900">Danger Zone</h3>
      <p class="mt-1 max-w-2xl text-sm text-gray-500">Permanently delete your account</p>
    </div>
    <div class="border-t border-gray-200 px-4 py-5 sm:px-6">
      <p class="text-sm text-gray-700 mb-4">
        Once you delete your account, all your data will be permanently removed. This includes all consumed products, recipes, meal plans, and household memberships.
      </p>
      <div v-if="deleteAccountMessage" class="text-sm text-green-600 mb-3">{{ deleteAccountMessage }}</div>
      <div v-if="deleteAccountError" class="text-sm text-red-500 mb-3">{{ deleteAccountError }}</div>
      <button
        @click="showDeleteAccountModal = true"
        class="inline-flex items-center py-2 px-4 border border-red-300 shadow-sm text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
      >
        Delete My Account
      </button>
    </div>
  </div>

  <!-- Delete Account Modal -->
  <div v-if="showDeleteAccountModal" class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex items-center justify-center min-h-screen px-4">
      <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="showDeleteAccountModal = false"></div>
      <div class="bg-white rounded-lg shadow-xl z-10 w-full max-w-md p-6">
        <h3 class="text-lg font-medium text-red-900 mb-4">Delete Account</h3>
        <div class="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          <p class="text-sm text-red-800 font-medium">This action is irreversible.</p>
          <p class="text-xs text-red-600 mt-1">All your data will be permanently deleted, including consumed products, recipes, meal plans, and household memberships.</p>
        </div>
        <label class="flex items-start space-x-2 mb-3">
          <input type="checkbox" v-model="exportAccountData" class="mt-0.5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
          <span class="text-sm text-gray-700">Send a copy of my data to my email before deletion</span>
        </label>
        <label class="flex items-start space-x-2 mb-4">
          <input type="checkbox" v-model="deleteAccountConfirmed" class="mt-0.5 rounded border-gray-300 text-red-600 focus:ring-red-500" />
          <span class="text-sm text-gray-700">I understand and want to proceed</span>
        </label>
        <div class="flex justify-end space-x-3">
          <button
            type="button"
            @click="showDeleteAccountModal = false; deleteAccountConfirmed = false; exportAccountData = false"
            class="py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            @click="requestAccountDeletion"
            :disabled="!deleteAccountConfirmed || deleteAccountLoading"
            class="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
          >
            <svg v-if="deleteAccountLoading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Send Deletion Confirmation Email
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../../store/auth'
import { parseApiError } from '../../utils/parseApiError'

const authStore = useAuthStore()

const showDeleteAccountModal = ref(false)
const deleteAccountLoading = ref(false)
const deleteAccountMessage = ref('')
const deleteAccountError = ref('')
const deleteAccountConfirmed = ref(false)
const exportAccountData = ref(false)

const requestAccountDeletion = async () => {
  deleteAccountLoading.value = true
  deleteAccountError.value = ''
  deleteAccountMessage.value = ''
  try {
    const res = await authStore.requestAccountDeletion(exportAccountData.value)
    deleteAccountMessage.value = res.message
    showDeleteAccountModal.value = false
    deleteAccountConfirmed.value = false
    exportAccountData.value = false
  } catch (err: any) {
    deleteAccountError.value = parseApiError(err, 'Failed to request account deletion')
  } finally {
    deleteAccountLoading.value = false
  }
}
</script>
