<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-red-900">Confirm Account Deletion</h2>
      </div>

      <div
        v-if="!token"
        class="text-center"
      >
        <p class="text-red-500 text-sm">Invalid deletion link.</p>
        <p class="mt-3">
          <router-link
            to="/profile"
            class="font-medium text-indigo-600 hover:text-indigo-500"
          >
            Back to profile
          </router-link>
        </p>
      </div>

      <div
        v-else-if="deleted"
        class="bg-green-50 border-l-4 border-green-400 p-4"
      >
        <p class="text-sm text-green-700">
          Your account has been permanently deleted.
        </p>
        <p class="mt-3 text-center">
          <router-link
            to="/login"
            class="font-medium text-indigo-600 hover:text-indigo-500"
          >
            Go to login
          </router-link>
        </p>
      </div>

      <div
        v-else
        class="space-y-6"
      >
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
          <p class="text-sm font-medium text-red-800">
            You are about to permanently delete your account and all associated data.
          </p>
          <p class="text-xs text-red-600 mt-2">This action cannot be undone.</p>
        </div>

        <div
          v-if="error"
          class="text-red-500 text-sm text-center"
        >
          {{ error }}
        </div>

        <button
          @click="confirmDeletion"
          :disabled="loading"
          class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
        >
          <span
            v-if="loading"
            class="absolute left-0 inset-y-0 flex items-center pl-3"
          >
            <svg
              class="animate-spin h-5 w-5 text-red-300"
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
          </span>
          Delete My Account Forever
        </button>

        <p class="text-center">
          <router-link
            to="/profile"
            class="text-sm font-medium text-gray-600 hover:text-gray-500"
          >
            Cancel and go back
          </router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../store/auth'
import { parseApiError } from '../utils/parseApiError'

const route = useRoute()
const authStore = useAuthStore()

const token = ref('')
const loading = ref(false)
const error = ref('')
const deleted = ref(false)

onMounted(() => {
  token.value = (route.query.token as string) || ''
})

const confirmDeletion = async () => {
  loading.value = true
  error.value = ''

  try {
    await axios.post('/api/users/me/confirm-deletion', {
      token: token.value,
    })
    deleted.value = true
    authStore.logout()
  } catch (err: unknown) {
    error.value = parseApiError(err, 'Failed to delete account. The link may have expired.')
  } finally {
    loading.value = false
  }
}
</script>
