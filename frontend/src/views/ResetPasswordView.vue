<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">Set new password</h2>
      </div>

      <div v-if="!token" class="text-center">
        <p class="text-red-500 text-sm">Invalid reset link. Please request a new one.</p>
        <p class="mt-3">
          <router-link to="/forgot-password" class="font-medium text-indigo-600 hover:text-indigo-500">
            Request new reset link
          </router-link>
        </p>
      </div>

      <div v-else-if="success" class="bg-green-50 border-l-4 border-green-400 p-4">
        <p class="text-sm text-green-700">
          Your password has been reset successfully.
        </p>
        <p class="mt-3 text-center">
          <router-link to="/login" class="font-medium text-indigo-600 hover:text-indigo-500">
            Sign in with your new password
          </router-link>
        </p>
      </div>

      <form v-else class="mt-8 space-y-6" @submit.prevent="handleReset">
        <div class="rounded-md shadow-sm -space-y-px">
          <div>
            <label for="password" class="sr-only">New Password</label>
            <input
              id="password"
              v-model="password"
              name="password"
              type="password"
              required
              minlength="8"
              class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
              placeholder="New password"
            />
          </div>
          <div>
            <label for="confirmPassword" class="sr-only">Confirm Password</label>
            <input
              id="confirmPassword"
              v-model="confirmPassword"
              name="confirmPassword"
              type="password"
              required
              minlength="8"
              class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
              placeholder="Confirm new password"
            />
          </div>
        </div>

        <p class="text-xs text-gray-500">
          Min 8 characters, at least one uppercase, lowercase, digit, and special character.
        </p>

        <div v-if="error" class="text-red-500 text-sm text-center">
          {{ error }}
        </div>

        <div>
          <button
            type="submit"
            :disabled="loading"
            class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            <span v-if="loading" class="absolute left-0 inset-y-0 flex items-center pl-3">
              <svg class="animate-spin h-5 w-5 text-indigo-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </span>
            Reset password
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { parseApiError } from '../utils/parseApiError'

const route = useRoute()

const token = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')
const success = ref(false)

onMounted(() => {
  token.value = (route.query.token as string) || ''
})

const handleReset = async () => {
  error.value = ''

  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }

  loading.value = true

  try {
    await axios.post('/api/auth/reset-password', {
      token: token.value,
      new_password: password.value,
    })
    success.value = true
  } catch (err: any) {
    error.value = parseApiError(err, 'Failed to reset password. The link may have expired.')
  } finally {
    loading.value = false
  }
}
</script>
