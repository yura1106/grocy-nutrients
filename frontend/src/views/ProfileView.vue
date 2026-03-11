<template>
  <div class="bg-gray-100">
    <div class="py-10">
      <header>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold leading-tight text-gray-900">Profile</h1>
        </div>
      </header>
      <main>
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
          <div class="px-4 py-8 sm:px-0">
            <div class="bg-white shadow overflow-hidden sm:rounded-lg">
              <div class="px-4 py-5 sm:px-6">
                <h3 class="text-lg leading-6 font-medium text-gray-900">Profile Information</h3>
                <p class="mt-1 max-w-2xl text-sm text-gray-500">Update your personal details</p>
              </div>
              <div class="border-t border-gray-200">
                <form @submit.prevent="updateProfile" class="p-6">
                  <div class="space-y-6">
                    <div>
                      <label for="username" class="block text-sm font-medium text-gray-700">Username</label>
                      <div class="mt-1">
                        <input
                          id="username"
                          v-model="form.username"
                          type="text"
                          class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                        />
                      </div>
                    </div>

                    <div>
                      <label for="email" class="block text-sm font-medium text-gray-700">Email</label>
                      <div class="mt-1">
                        <input
                          id="email"
                          v-model="form.email"
                          type="email"
                          class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                        />
                      </div>
                    </div>

                    <div>
                      <label for="password" class="block text-sm font-medium text-gray-700">New Password (leave blank to keep current)</label>
                      <div class="mt-1">
                        <input
                          id="password"
                          v-model="form.password"
                          type="password"
                          class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                        />
                      </div>
                    </div>

                    <div>
                      <label for="grocyUrl" class="block text-sm font-medium text-gray-700">Grocy URL</label>
                      <div class="mt-1">
                        <input
                          id="grocyUrl"
                          v-model="form.grocy_url"
                          type="url"
                          class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                          placeholder="http://192.168.1.1:9192"
                        />
                      </div>
                      <p class="mt-1 text-xs text-gray-500">
                        URL вашого Grocy-сервера (наприклад http://192.168.1.1:9192).
                      </p>
                    </div>

                    <div>
                      <label for="grocyApiKey" class="block text-sm font-medium text-gray-700">Grocy API Key</label>
                      <div class="mt-1">
                        <input
                          id="grocyApiKey"
                          v-model="form.grocy_api_key"
                          type="text"
                          class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                          placeholder="Paste your Grocy API key"
                        />
                      </div>
                      <p class="mt-1 text-xs text-gray-500">
                        Ключ використовується тільки для запитів з цього застосунку до вашого Grocy.
                      </p>
                    </div>

                    <div v-if="error" class="text-red-500 text-sm">
                      {{ error }}
                    </div>

                    <div v-if="success" class="text-green-500 text-sm">
                      {{ success }}
                    </div>

                    <div>
                      <button
                        type="submit"
                        :disabled="loading"
                        class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                      >
                        <svg v-if="loading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Save
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            </div>

            <!-- Grocy Sync Section -->
            <div class="bg-white shadow overflow-hidden sm:rounded-lg mt-6">
              <div class="px-4 py-5 sm:px-6">
                <h3 class="text-lg leading-6 font-medium text-gray-900">Grocy Integration</h3>
                <p class="mt-1 max-w-2xl text-sm text-gray-500">Sync products from your Grocy instance</p>
              </div>
              <div class="border-t border-gray-200 px-4 py-5 sm:px-6">
                <div class="space-y-4">
                  <div v-if="!form.grocy_url || !form.grocy_api_key" class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                    <div class="flex">
                      <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                        </svg>
                      </div>
                      <div class="ml-3">
                        <p class="text-sm text-yellow-700">
                          Please set your Grocy URL and API key above before syncing products.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div v-if="syncError" class="bg-red-50 border-l-4 border-red-400 p-4">
                    <div class="flex">
                      <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                        </svg>
                      </div>
                      <div class="ml-3">
                        <p class="text-sm text-red-700">{{ syncError }}</p>
                      </div>
                    </div>
                  </div>

                  <div v-if="syncSuccess" class="bg-green-50 border-l-4 border-green-400 p-4">
                    <div class="flex">
                      <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                        </svg>
                      </div>
                      <div class="ml-3">
                        <p class="text-sm text-green-700">
                          {{ syncSuccess }}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div>
                    <button
                      @click="syncProducts"
                      :disabled="syncLoading || !form.grocy_api_key || !form.grocy_url"
                      class="inline-flex items-center justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <svg v-if="syncLoading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <svg v-else class="-ml-1 mr-2 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      {{ syncLoading ? syncProgressText : 'Sync Products from Grocy' }}
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
import { onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../store/auth'

const authStore = useAuthStore()
const loading = ref(false)
const error = ref('')
const success = ref('')

// Sync state
const syncLoading = ref(false)
const syncError = ref('')
const syncSuccess = ref('')

const form = reactive({
  username: '',
  email: '',
  password: '',
  grocy_url: '',
  grocy_api_key: ''
})

onMounted(async () => {
  try {
    if (!authStore.user) {
      await authStore.fetchUser()
    }
    
    if (authStore.user) {
      form.username = authStore.user.username
      form.email = authStore.user.email
      // @ts-ignore - fields are added on the backend
      form.grocy_url = (authStore.user as any).grocy_url || ''
      // @ts-ignore
      form.grocy_api_key = (authStore.user as any).grocy_api_key || ''
    }
  } catch (err) {
    error.value = 'Failed to load user data'
  }
})

const updateProfile = async () => {
  loading.value = true
  error.value = ''
  success.value = ''

  try {
    const updateData: Record<string, string> = {}

    if (form.username) updateData.username = form.username
    if (form.email) updateData.email = form.email
    if (form.password) updateData.password = form.password
    if (form.grocy_url !== undefined) updateData.grocy_url = form.grocy_url
    if (form.grocy_api_key !== '') updateData.grocy_api_key = form.grocy_api_key

    const response = await axios.put('/api/users/me', updateData)

    // Update local user data
    if (authStore.user) {
      authStore.user.username = response.data.username
      authStore.user.email = response.data.email
      ;(authStore.user as any).grocy_url = response.data.grocy_url
      ;(authStore.user as any).grocy_api_key = response.data.grocy_api_key
    }

    success.value = 'Profile updated successfully'
    form.password = '' // Clear password field after successful update
  } catch (err: any) {
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'Failed to update profile'
    }
  } finally {
    loading.value = false
  }
}

const syncProgressText = ref('Syncing...')

const syncProducts = async () => {
  syncLoading.value = true
  syncError.value = ''
  syncSuccess.value = ''

  const CHUNK_SIZE = 50
  let offset = 0
  let totalProcessed = 0
  let totalUpdated = 0
  let totalNewRecords = 0
  let total = 0

  try {
    while (true) {
      syncProgressText.value = total > 0
        ? `Syncing... ${Math.min(offset, total)}/${total}`
        : 'Syncing...'

      const response = await axios.post(`/api/sync/grocy-products?offset=${offset}&limit=${CHUNK_SIZE}`)
      const data = response.data

      totalProcessed += data.processed
      totalUpdated += data.updated
      totalNewRecords += data.new_history_records
      total = data.total || 0

      if (!data.has_more) break
      offset += CHUNK_SIZE
    }

    syncSuccess.value = `Successfully synced! Processed: ${totalProcessed}, Updated: ${totalUpdated}, New history records: ${totalNewRecords}`
  } catch (err: any) {
    if (err.response?.data?.detail) {
      syncError.value = err.response.data.detail
    } else {
      syncError.value = 'Failed to sync products. Please check your Grocy API key and try again.'
    }
  } finally {
    syncLoading.value = false
  }
}
</script> 