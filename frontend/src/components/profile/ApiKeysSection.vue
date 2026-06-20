<template>
  <!-- API Keys Section — global list + revoke. Creation lives in the Households
       panel (each key binds to a household). -->
  <div class="bg-white shadow-sm overflow-hidden sm:rounded-lg mt-6">
    <div class="px-4 py-5 sm:px-6">
      <h3 class="text-lg leading-6 font-medium text-gray-900">API Keys</h3>
      <p class="mt-1 max-w-2xl text-sm text-gray-500">
        Long-lived keys for the MCP server (query your nutrition data from Claude Code).
        Create a key from a household's <span class="font-medium">Members</span> panel above.
      </p>
    </div>
    <div class="border-t border-gray-200 px-4 py-5 sm:px-6">
      <div
        v-if="loading"
        class="text-sm text-gray-500"
      >
        Loading...
      </div>
      <div
        v-else-if="keys.length === 0"
        class="text-sm text-gray-500"
      >
        No API keys yet.
      </div>
      <table
        v-else
        class="min-w-full divide-y divide-gray-200 border rounded-md overflow-hidden"
      >
        <thead class="bg-gray-50">
          <tr>
            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Prefix</th>
            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Household</th>
            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Last used</th>
            <th class="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="k in keys"
            :key="k.id"
          >
            <td class="px-4 py-3 text-sm font-medium text-gray-900">{{ k.name }}</td>
            <td class="px-4 py-3 text-xs text-gray-500 font-mono">gnk_{{ k.key_prefix }}…</td>
            <td class="px-4 py-3 text-xs">
              <span
                v-if="k.household_id !== null"
                class="text-gray-600"
              >{{ householdName(k.household_id) }}</span>
              <span
                v-else
                class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800"
              >recreate</span>
            </td>
            <td class="px-4 py-3 text-xs text-gray-400">
              {{ k.last_used_at ? formatDate(k.last_used_at) : 'never' }}
            </td>
            <td class="px-4 py-3 text-right">
              <button
                @click="revoke(k.id)"
                class="text-red-500 hover:text-red-700 text-xs font-medium"
              >
                Revoke
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p
        v-if="error"
        class="mt-2 text-xs text-red-500"
      >
        {{ error }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import axios, { isAxiosError } from 'axios'
import { useHouseholdStore } from '../../store/household'

interface ApiKey {
  id: number
  name: string
  key_prefix: string
  household_id: number | null
  created_at: string | null
  last_used_at: string | null
  expires_at: string | null
}

const householdStore = useHouseholdStore()

const keys = ref<ApiKey[]>([])
const loading = ref(true)
const error = ref('')

const formatDate = (iso: string) => new Date(iso).toLocaleString()

const householdsById = computed(() =>
  Object.fromEntries(householdStore.households.map((h) => [h.id, h.name])),
)
const householdName = (id: number) => householdsById.value[id] ?? `#${id}`

const fetchKeys = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await axios.get<ApiKey[]>('/api/users/me/api-keys')
    keys.value = res.data
  } catch (err: unknown) {
    error.value = (isAxiosError(err) && err.response?.data?.detail) || 'Failed to load API keys'
  } finally {
    loading.value = false
  }
}

const revoke = async (id: number) => {
  if (!confirm('Revoke this API key? Clients using it will stop working.')) return
  error.value = ''
  try {
    await axios.delete(`/api/users/me/api-keys/${id}`)
    await fetchKeys()
  } catch (err: unknown) {
    error.value = (isAxiosError(err) && err.response?.data?.detail) || 'Failed to revoke API key'
  }
}

onMounted(() => {
  fetchKeys()
  if (householdStore.households.length === 0) householdStore.fetchHouseholds()
})
</script>
