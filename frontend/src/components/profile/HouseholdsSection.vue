<template>
  <!-- Households Section -->
  <div class="bg-white shadow overflow-hidden sm:rounded-lg mt-6">
    <div class="px-4 py-5 sm:px-6 flex items-center justify-between">
      <div>
        <h3 class="text-lg leading-6 font-medium text-gray-900">Households</h3>
        <p class="mt-1 max-w-2xl text-sm text-gray-500">Manage your households</p>
      </div>
      <button
        @click="showCreateModal = true"
        class="inline-flex items-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
      >
        + Create
      </button>
    </div>
    <div class="border-t border-gray-200 px-4 py-5 sm:px-6">
      <div v-if="!householdStore.loaded" class="text-sm text-gray-500">Loading...</div>
      <div v-else-if="householdStore.households.length === 0" class="text-sm text-gray-500">
        You don't belong to any household yet.
      </div>
      <div v-else class="space-y-4">
        <div
          v-for="h in householdStore.households"
          :key="h.id"
          class="border rounded-lg p-4"
        >
          <div class="flex items-center justify-between">
            <div>
              <h4 class="font-medium text-gray-900">{{ h.name }}</h4>
              <p v-if="h.grocy_url" class="text-sm text-gray-500">{{ h.grocy_url }}</p>
              <p v-if="h.address" class="text-sm text-gray-400">{{ h.address }}</p>
            </div>
            <div class="flex items-center space-x-2">
              <button
                v-if="h.role_name === 'admin'"
                @click="editTarget = h"
                class="text-gray-400 hover:text-indigo-600"
                title="Edit household"
              >
                <svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </button>
              <button
                v-if="h.role_name === 'admin'"
                @click="openDeleteModal(h)"
                class="text-gray-400 hover:text-red-600"
                title="Delete household"
              >
                <svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
              <button
                v-if="h.role_name !== 'admin'"
                @click="openLeaveModal(h.id, h.name)"
                class="text-gray-400 hover:text-red-600"
                title="Leave household"
              >
                <svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
              <span
                :class="h.role_name === 'admin' ? 'bg-indigo-100 text-indigo-800' : 'bg-gray-100 text-gray-800'"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
              >
                {{ h.role_name }}
              </span>
            </div>
          </div>

          <!-- Action buttons -->
          <div class="mt-3 flex items-center gap-3">
            <button
              @click="toggleMembers(h.id)"
              class="text-sm text-indigo-600 hover:text-indigo-800"
            >
              {{ expandedMembers === h.id ? 'Hide members' : 'Show members' }}
            </button>
            <button
              v-if="h.role_name === 'admin' && h.grocy_url"
              @click="toggleSync(h.id)"
              class="text-sm text-green-600 hover:text-green-800"
            >
              {{ expandedSync === h.id ? 'Hide sync' : 'Grocy sync' }}
            </button>
          </div>

          <!-- Data Migration banner (admin only) -->
          <DataMigrationBanner
            v-if="h.role_name === 'admin'"
            :household-id="h.id"
          />

          <!-- Grocy Sync panel (admin only) -->
          <div v-if="expandedSync === h.id && h.role_name === 'admin' && h.grocy_url" class="mt-3 bg-gray-50 rounded-lg p-4">
            <div v-if="sync.error.value && sync.householdId.value === h.id" class="mb-2 text-xs text-red-500">{{ sync.error.value }}</div>
            <div v-if="sync.success.value && sync.householdId.value === h.id" class="mb-2 text-xs text-green-600">{{ sync.success.value }}</div>
            <div class="flex items-center gap-3">
              <button
                @click="sync.syncProducts(h.id)"
                :disabled="sync.loading.value"
                class="inline-flex items-center py-1.5 px-3 border border-transparent shadow-sm text-xs font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg v-if="sync.loading.value && sync.type.value === 'products' && sync.householdId.value === h.id" class="animate-spin -ml-0.5 mr-1.5 h-3 w-3 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {{ sync.loading.value && sync.type.value === 'products' && sync.householdId.value === h.id ? sync.progressText.value : 'Sync Products' }}
              </button>
              <button
                @click="sync.syncRecipes(h.id)"
                :disabled="sync.loading.value"
                class="inline-flex items-center py-1.5 px-3 border border-transparent shadow-sm text-xs font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg v-if="sync.loading.value && sync.type.value === 'recipes' && sync.householdId.value === h.id" class="animate-spin -ml-0.5 mr-1.5 h-3 w-3 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {{ sync.loading.value && sync.type.value === 'recipes' && sync.householdId.value === h.id ? 'Syncing...' : 'Sync Recipes' }}
              </button>
              <span class="text-xs text-gray-400">
                Last sync: {{ sync.getLastSyncAt(h.id) ? sync.formatSyncDate(sync.getLastSyncAt(h.id)!) : 'never' }}
              </span>
            </div>
          </div>

          <!-- Members panel -->
          <div v-if="expandedMembers === h.id && householdStore.householdDetails[h.id]" class="mt-3">
            <table class="min-w-full divide-y divide-gray-200 border rounded-md overflow-hidden">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">API Key</th>
                  <th class="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr v-for="m in householdStore.householdDetails[h.id].members" :key="m.user_id">
                  <td class="px-4 py-3">
                    <div class="text-sm font-medium text-gray-900">{{ m.username }}</div>
                    <div class="text-xs text-gray-400">{{ m.email }}</div>
                  </td>
                  <td class="px-4 py-3">
                    <span
                      :class="m.role_name === 'admin' ? 'bg-indigo-100 text-indigo-800' : 'bg-gray-100 text-gray-800'"
                      class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                    >
                      {{ m.role_name }}
                    </span>
                  </td>
                  <td class="px-4 py-3">
                    <template v-if="m.user_id === authStore.user?.id">
                      <div class="flex items-center space-x-2">
                        <span v-if="m.has_grocy_key" class="inline-flex items-center text-xs text-green-700">
                          <svg class="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" /></svg>
                          Set
                        </span>
                        <span v-else class="inline-flex items-center text-xs text-gray-400">
                          <svg class="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" /></svg>
                          Not set
                        </span>
                        <button
                          @click="grocyKey.open(h.id, m.user_id)"
                          class="text-indigo-600 hover:text-indigo-800 text-xs underline"
                        >
                          {{ m.has_grocy_key ? 'Change' : 'Set' }}
                        </button>
                      </div>
                      <div
                        v-if="grocyKey.target.value?.householdId === h.id && grocyKey.target.value?.userId === m.user_id"
                        class="mt-2 flex space-x-2"
                      >
                        <input
                          v-model="grocyKey.value.value"
                          type="text"
                          placeholder="Paste API key..."
                          class="flex-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block text-xs border-gray-300 rounded-md"
                        />
                        <button
                          @click="grocyKey.save(h.id)"
                          :disabled="!grocyKey.value.value || grocyKey.saving.value"
                          class="px-2 py-1 text-xs font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                        >
                          {{ grocyKey.saving.value ? '...' : 'Save' }}
                        </button>
                        <button
                          @click="grocyKey.close()"
                          class="px-2 py-1 text-xs font-medium rounded-md text-gray-700 border border-gray-300 hover:bg-gray-50"
                        >
                          Cancel
                        </button>
                      </div>
                      <p v-if="grocyKey.target.value?.householdId === h.id && grocyKey.target.value?.userId === m.user_id && grocyKey.error.value" class="mt-1 text-xs text-red-500">{{ grocyKey.error.value }}</p>
                    </template>
                    <span v-else class="text-xs text-gray-300">&mdash;</span>
                  </td>
                  <td class="px-4 py-3 text-right">
                    <button
                      v-if="h.role_name === 'admin' && m.user_id !== authStore.user?.id"
                      @click="openLeaveModal(h.id, h.name, m.user_id, false)"
                      class="text-red-500 hover:text-red-700 text-xs font-medium"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>

            <!-- Add user form (admin only) -->
            <div v-if="h.role_name === 'admin'" class="mt-4">
              <label class="block text-xs font-medium text-gray-500 uppercase mb-1">Add member</label>
              <div class="flex space-x-2">
                <input
                  v-model="memberSearch.query.value"
                  @input="memberSearch.search()"
                  type="text"
                  placeholder="Search user by name or email..."
                  class="flex-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block sm:text-sm border-gray-300 rounded-md"
                />
                <select v-model="memberSearch.roleName.value" class="shadow-sm border-gray-300 rounded-md text-sm">
                  <option value="user">user</option>
                  <option value="admin">admin</option>
                </select>
              </div>
              <ul v-if="memberSearch.results.value.length > 0" class="mt-1 border rounded-md divide-y divide-gray-200 max-h-40 overflow-y-auto">
                <li
                  v-for="u in memberSearch.results.value"
                  :key="u.id"
                  class="px-3 py-2 flex items-center justify-between text-sm hover:bg-gray-50 cursor-pointer"
                  @click="memberSearch.addMember(h.id, u.id)"
                >
                  <span>{{ u.username }} <span class="text-gray-400">({{ u.email }})</span></span>
                  <span class="text-indigo-600 text-xs font-medium">+ Add</span>
                </li>
              </ul>
              <p v-if="memberSearch.error.value" class="mt-1 text-xs text-red-500">{{ memberSearch.error.value }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Modals -->
  <CreateHouseholdModal
    :visible="showCreateModal"
    @close="showCreateModal = false"
  />
  <EditHouseholdModal
    :household="editTarget"
    @close="editTarget = null"
  />
  <LeaveHouseholdModal
    :visible="showLeaveModal"
    :household-id="leaveHouseholdId"
    :user-id="leaveUserId"
    :household-name="leaveHouseholdName"
    :is-self="leaveIsSelf"
    @close="showLeaveModal = false"
    @done="handleLeaveDone"
  />
  <DeleteHouseholdModal
    :visible="showDeleteModal"
    :household-id="deleteHouseholdId"
    :household-name="deleteHouseholdName"
    @close="showDeleteModal = false"
  />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../../store/auth'
import { useHouseholdStore } from '../../store/household'
import { useGrocySync } from '../../composables/useGrocySync'
import { useMemberSearch } from '../../composables/useMemberSearch'
import { useGrocyKey } from '../../composables/useGrocyKey'
import type { HouseholdWithRole } from '../../types/household'
import DataMigrationBanner from './DataMigrationBanner.vue'
import CreateHouseholdModal from '../household/CreateHouseholdModal.vue'
import EditHouseholdModal from '../household/EditHouseholdModal.vue'
import LeaveHouseholdModal from '../household/LeaveHouseholdModal.vue'
import DeleteHouseholdModal from '../household/DeleteHouseholdModal.vue'

const authStore = useAuthStore()
const householdStore = useHouseholdStore()

// Composables
const sync = useGrocySync()
const memberSearch = useMemberSearch()
const grocyKey = useGrocyKey()

// UI panels
const expandedMembers = ref<number | null>(null)
const expandedSync = ref<number | null>(null)

// Modal state
const showCreateModal = ref(false)
const editTarget = ref<HouseholdWithRole | null>(null)

const showLeaveModal = ref(false)
const leaveHouseholdId = ref<number | null>(null)
const leaveUserId = ref<number | null>(null)
const leaveHouseholdName = ref('')
const leaveIsSelf = ref(true)

const showDeleteModal = ref(false)
const deleteHouseholdId = ref<number | null>(null)
const deleteHouseholdName = ref('')

// --- Actions ---

const toggleMembers = async (id: number) => {
  if (expandedMembers.value === id) {
    expandedMembers.value = null
    return
  }
  expandedMembers.value = id
  memberSearch.reset()
  try {
    await householdStore.fetchHouseholdDetail(id)
  } catch {
    // ignore
  }
}

const toggleSync = async (id: number) => {
  if (expandedSync.value === id) {
    expandedSync.value = null
    return
  }
  expandedSync.value = id
  sync.error.value = ''
  sync.success.value = ''
  if (!householdStore.householdDetails[id]) {
    try {
      await householdStore.fetchHouseholdDetail(id)
    } catch {
      // ignore
    }
  }
}

const openLeaveModal = (householdId: number, name: string, userId?: number, isSelf: boolean = true) => {
  leaveHouseholdId.value = householdId
  leaveUserId.value = userId ?? authStore.user?.id ?? null
  leaveHouseholdName.value = name
  leaveIsSelf.value = isSelf
  showLeaveModal.value = true
}

const handleLeaveDone = async () => {
  showLeaveModal.value = false
  if (leaveIsSelf.value) {
    await householdStore.fetchHouseholds()
  } else if (leaveHouseholdId.value) {
    await householdStore.fetchHouseholdDetail(leaveHouseholdId.value)
  }
}

const openDeleteModal = (h: HouseholdWithRole) => {
  deleteHouseholdId.value = h.id
  deleteHouseholdName.value = h.name
  showDeleteModal.value = true
}

onMounted(async () => {
  await householdStore.fetchHouseholds()
  await householdStore.fetchBackfillStatusForAdmins()
})
</script>
