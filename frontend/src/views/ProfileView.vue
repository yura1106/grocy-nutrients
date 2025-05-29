<template>
  <div class="min-h-screen bg-gray-100">
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

const form = reactive({
  username: '',
  email: '',
  password: ''
})

onMounted(async () => {
  try {
    if (!authStore.user) {
      await authStore.fetchUser()
    }
    
    if (authStore.user) {
      form.username = authStore.user.username
      form.email = authStore.user.email
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
    
    const response = await axios.put('/api/users/me', updateData)
    
    // Update local user data
    if (authStore.user) {
      authStore.user.username = response.data.username
      authStore.user.email = response.data.email
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
</script> 