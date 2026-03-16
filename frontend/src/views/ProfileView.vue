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
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Save
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            </div>

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
                <div v-if="householdsLoading" class="text-sm text-gray-500">Loading...</div>
                <div v-else-if="householdsError" class="text-sm text-red-500">{{ householdsError }}</div>
                <div v-else-if="households.length === 0" class="text-sm text-gray-500">
                  You don't belong to any household yet.
                </div>
                <div v-else class="space-y-4">
                  <div
                    v-for="h in households"
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
                          @click="openEditModal(h)"
                          class="text-gray-400 hover:text-indigo-600"
                          title="Edit household"
                        >
                          <svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        <button
                          v-if="h.role_name === 'admin'"
                          @click="openDeleteHouseholdModal(h)"
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

                    <!-- Data Migration banner (admin only, shown only when null records exist) -->
                    <div
                      v-if="h.role_name === 'admin' && backfillCounts[h.id] && backfillCounts[h.id].total > 0"
                      class="mt-3 bg-yellow-50 border border-yellow-200 rounded-lg p-4"
                    >
                      <h5 class="text-sm font-medium text-yellow-800 mb-2">Data Migration Required</h5>
                      <p class="text-xs text-yellow-700 mb-3">
                        {{ backfillCounts[h.id].total }} records need to be assigned to this household and user.
                      </p>
                      <ul class="text-xs text-yellow-600 mb-3 space-y-0.5">
                        <li v-if="backfillCounts[h.id].products > 0">Products: {{ backfillCounts[h.id].products }}</li>
                        <li v-if="backfillCounts[h.id].recipes > 0">Recipes: {{ backfillCounts[h.id].recipes }}</li>
                        <li v-if="backfillCounts[h.id].consumed_products > 0">Consumed products: {{ backfillCounts[h.id].consumed_products }}</li>
                        <li v-if="backfillCounts[h.id].recipes_data > 0">Recipe data: {{ backfillCounts[h.id].recipes_data }}</li>
                        <li v-if="backfillCounts[h.id].meal_plan_consumptions > 0">Meal plan consumptions: {{ backfillCounts[h.id].meal_plan_consumptions }}</li>
                        <li v-if="backfillCounts[h.id].note_nutrients > 0">Note nutrients: {{ backfillCounts[h.id].note_nutrients }}</li>
                        <li v-if="backfillCounts[h.id].daily_nutrition > 0">Daily nutrition: {{ backfillCounts[h.id].daily_nutrition }}</li>
                      </ul>
                      <div class="flex items-center gap-3">
                        <button
                          @click="runBackfill(h.id)"
                          :disabled="backfillLoading"
                          class="inline-flex items-center py-1.5 px-3 border border-transparent shadow-sm text-xs font-medium rounded-md text-white bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <svg v-if="backfillLoading && backfillHouseholdId === h.id" class="animate-spin -ml-0.5 mr-1.5 h-3 w-3 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          Assign All to This Household
                        </button>
                      </div>
                      <div v-if="backfillError && backfillHouseholdId === h.id" class="mt-2 text-xs text-red-500">{{ backfillError }}</div>
                      <div v-if="backfillSuccess && backfillHouseholdId === h.id" class="mt-2 text-xs text-green-600">{{ backfillSuccess }}</div>
                    </div>

                    <!-- Grocy Sync panel (admin only) -->
                    <div v-if="expandedSync === h.id && h.role_name === 'admin' && h.grocy_url" class="mt-3 bg-gray-50 rounded-lg p-4">
                      <div v-if="syncError && syncHouseholdId === h.id" class="mb-2 text-xs text-red-500">{{ syncError }}</div>
                      <div v-if="syncSuccess && syncHouseholdId === h.id" class="mb-2 text-xs text-green-600">{{ syncSuccess }}</div>
                      <div class="flex items-center gap-3">
                        <button
                          @click="syncProducts(h.id)"
                          :disabled="syncLoading"
                          class="inline-flex items-center py-1.5 px-3 border border-transparent shadow-sm text-xs font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <svg v-if="syncLoading && syncType === 'products' && syncHouseholdId === h.id" class="animate-spin -ml-0.5 mr-1.5 h-3 w-3 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          {{ syncLoading && syncType === 'products' && syncHouseholdId === h.id ? syncProgressText : 'Sync Products' }}
                        </button>
                        <button
                          @click="syncRecipes(h.id)"
                          :disabled="syncLoading"
                          class="inline-flex items-center py-1.5 px-3 border border-transparent shadow-sm text-xs font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <svg v-if="syncLoading && syncType === 'recipes' && syncHouseholdId === h.id" class="animate-spin -ml-0.5 mr-1.5 h-3 w-3 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          {{ syncLoading && syncType === 'recipes' && syncHouseholdId === h.id ? 'Syncing...' : 'Sync Recipes' }}
                        </button>
                        <span class="text-xs text-gray-400">
                          Last sync: {{ getLastSyncAt(h.id) ? formatSyncDate(getLastSyncAt(h.id)!) : 'never' }}
                        </span>
                      </div>
                    </div>

                    <!-- Members panel -->
                    <div v-if="expandedMembers === h.id && householdDetails[h.id]" class="mt-3">
                      <!-- Members table -->
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
                          <tr v-for="m in householdDetails[h.id].members" :key="m.user_id">
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
                              <!-- Only the user themselves can see/manage their own key -->
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
                                    @click="openSetKeyForm(h.id, m.user_id)"
                                    class="text-indigo-600 hover:text-indigo-800 text-xs underline"
                                  >
                                    {{ m.has_grocy_key ? 'Change' : 'Set' }}
                                  </button>
                                </div>
                                <!-- Inline key input -->
                                <div
                                  v-if="setKeyTarget?.householdId === h.id && setKeyTarget?.userId === m.user_id"
                                  class="mt-2 flex space-x-2"
                                >
                                  <input
                                    v-model="setKeyValue"
                                    type="text"
                                    placeholder="Paste API key..."
                                    class="flex-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block text-xs border-gray-300 rounded-md"
                                  />
                                  <button
                                    @click="saveGrocyKey(h.id, m.user_id)"
                                    :disabled="!setKeyValue || setKeySaving"
                                    class="px-2 py-1 text-xs font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                                  >
                                    {{ setKeySaving ? '...' : 'Save' }}
                                  </button>
                                  <button
                                    @click="setKeyTarget = null"
                                    class="px-2 py-1 text-xs font-medium rounded-md text-gray-700 border border-gray-300 hover:bg-gray-50"
                                  >
                                    Cancel
                                  </button>
                                </div>
                                <p v-if="setKeyTarget?.householdId === h.id && setKeyTarget?.userId === m.user_id && setKeyError" class="mt-1 text-xs text-red-500">{{ setKeyError }}</p>
                              </template>
                              <!-- Other members: no key info shown -->
                              <span v-else class="text-xs text-gray-300">&mdash;</span>
                            </td>
                            <td class="px-4 py-3 text-right">
                              <button
                                v-if="h.role_name === 'admin' && m.user_id !== authStore.user?.id"
                                @click="removeMember(h.id, m.user_id)"
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
                            v-model="userSearchQuery"
                            @input="searchUsers"
                            type="text"
                            placeholder="Search user by name or email..."
                            class="flex-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block sm:text-sm border-gray-300 rounded-md"
                          />
                          <select v-model="addRoleName" class="shadow-sm border-gray-300 rounded-md text-sm">
                            <option value="user">user</option>
                            <option value="admin">admin</option>
                          </select>
                        </div>
                        <ul v-if="userSearchResults.length > 0" class="mt-1 border rounded-md divide-y divide-gray-200 max-h-40 overflow-y-auto">
                          <li
                            v-for="u in userSearchResults"
                            :key="u.id"
                            class="px-3 py-2 flex items-center justify-between text-sm hover:bg-gray-50 cursor-pointer"
                            @click="addMember(h.id, u.id)"
                          >
                            <span>{{ u.username }} <span class="text-gray-400">({{ u.email }})</span></span>
                            <span class="text-indigo-600 text-xs font-medium">+ Add</span>
                          </li>
                        </ul>
                        <p v-if="addMemberError" class="mt-1 text-xs text-red-500">{{ addMemberError }}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Create Household Modal -->
          <div v-if="showCreateModal" class="fixed inset-0 z-50 overflow-y-auto">
            <div class="flex items-center justify-center min-h-screen px-4">
              <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="showCreateModal = false"></div>
              <div class="bg-white rounded-lg shadow-xl z-10 w-full max-w-md p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">Create Household</h3>
                <form @submit.prevent="createHousehold" class="space-y-4">
                  <div>
                    <label class="block text-sm font-medium text-gray-700">Name *</label>
                    <input
                      v-model="newHousehold.name"
                      type="text"
                      required
                      class="mt-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700">Grocy URL</label>
                    <input
                      v-model="newHousehold.grocy_url"
                      type="url"
                      placeholder="http://192.168.1.1:9192"
                      class="mt-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700">Address</label>
                    <input
                      v-model="newHousehold.address"
                      type="text"
                      class="mt-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                    />
                  </div>
                  <p v-if="createError" class="text-sm text-red-500">{{ createError }}</p>
                  <div class="flex justify-end space-x-3">
                    <button
                      type="button"
                      @click="showCreateModal = false"
                      class="py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      :disabled="createLoading"
                      class="py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {{ createLoading ? 'Creating...' : 'Create' }}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>

          <!-- Edit Household Modal -->
          <div v-if="showEditModal" class="fixed inset-0 z-50 overflow-y-auto">
            <div class="flex items-center justify-center min-h-screen px-4">
              <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="showEditModal = false"></div>
              <div class="bg-white rounded-lg shadow-xl z-10 w-full max-w-md p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">Edit Household</h3>
                <form @submit.prevent="updateHousehold" class="space-y-4">
                  <div>
                    <label class="block text-sm font-medium text-gray-700">Name *</label>
                    <input
                      v-model="editHousehold.name"
                      type="text"
                      required
                      class="mt-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700">Grocy URL</label>
                    <input
                      v-model="editHousehold.grocy_url"
                      type="url"
                      placeholder="http://192.168.1.1:9192"
                      class="mt-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700">Address</label>
                    <input
                      v-model="editHousehold.address"
                      type="text"
                      class="mt-1 shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
                    />
                  </div>
                  <p v-if="editError" class="text-sm text-red-500">{{ editError }}</p>
                  <div class="flex justify-end space-x-3">
                    <button
                      type="button"
                      @click="showEditModal = false"
                      class="py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      :disabled="editLoading"
                      class="py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {{ editLoading ? 'Saving...' : 'Save' }}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>

          <!-- Leave/Remove Member Warning Modal -->
          <div v-if="showLeaveModal" class="fixed inset-0 z-50 overflow-y-auto">
            <div class="flex items-center justify-center min-h-screen px-4">
              <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="showLeaveModal = false"></div>
              <div class="bg-white rounded-lg shadow-xl z-10 w-full max-w-md p-6">
                <h3 class="text-lg font-medium text-red-900 mb-4">
                  {{ leaveModalSelf ? 'Leave Household' : 'Remove Member' }}
                </h3>
                <div v-if="leaveDataLoading" class="text-sm text-gray-500">Loading data summary...</div>
                <template v-else>
                  <p class="text-sm text-gray-700 mb-3">
                    {{ leaveModalSelf
                      ? `You are about to leave "${leaveModalName}".`
                      : `You are about to remove this user from "${leaveModalName}".`
                    }}
                  </p>
                  <div v-if="leaveDataSummary && leaveDataSummary.total > 0" class="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
                    <p class="text-sm font-medium text-red-800 mb-2">The following data will be hidden:</p>
                    <ul class="text-xs text-red-700 space-y-0.5">
                      <li v-if="leaveDataSummary.consumed_products > 0">Consumed products: {{ leaveDataSummary.consumed_products }}</li>
                      <li v-if="leaveDataSummary.recipes_data > 0">Recipe records: {{ leaveDataSummary.recipes_data }}</li>
                      <li v-if="leaveDataSummary.meal_plan_consumptions > 0">Meal plan consumptions: {{ leaveDataSummary.meal_plan_consumptions }}</li>
                      <li v-if="leaveDataSummary.note_nutrients > 0">Note nutrients: {{ leaveDataSummary.note_nutrients }}</li>
                      <li v-if="leaveDataSummary.daily_nutrition > 0">Daily nutrition records: {{ leaveDataSummary.daily_nutrition }}</li>
                    </ul>
                  </div>
                  <label class="flex items-center space-x-2 mb-4">
                    <input type="checkbox" v-model="leaveConfirmChecked" class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                    <span class="text-sm text-gray-700">I understand my data will be hidden</span>
                  </label>
                </template>
                <p v-if="leaveError" class="text-sm text-red-500 mb-3">{{ leaveError }}</p>
                <div class="flex justify-end space-x-3">
                  <button
                    type="button"
                    @click="showLeaveModal = false"
                    class="py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    @click="confirmLeave"
                    :disabled="!leaveConfirmChecked || leaveLoading"
                    class="py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {{ leaveLoading ? 'Processing...' : (leaveModalSelf ? 'Leave' : 'Remove') }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Delete Household Modal -->
          <div v-if="showDeleteHouseholdModal" class="fixed inset-0 z-50 overflow-y-auto">
            <div class="flex items-center justify-center min-h-screen px-4">
              <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="showDeleteHouseholdModal = false"></div>
              <div class="bg-white rounded-lg shadow-xl z-10 w-full max-w-md p-6">
                <h3 class="text-lg font-medium text-red-900 mb-2">Delete Household</h3>
                <div class="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                  <p class="text-sm font-medium text-red-800">
                    This will permanently delete ALL data for ALL members of "{{ deleteHouseholdName }}".
                  </p>
                  <p class="text-xs text-red-600 mt-1">This action cannot be undone.</p>
                </div>
                <div class="space-y-3 mb-4">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      Type <code class="bg-gray-100 px-1 rounded text-red-600">DELETE {{ deleteHouseholdName }}</code> to confirm
                    </label>
                    <input
                      v-model="deleteHouseholdConfirmText"
                      type="text"
                      class="shadow-sm focus:ring-red-500 focus:border-red-500 block w-full sm:text-sm border-gray-300 rounded-md"
                      :placeholder="`DELETE ${deleteHouseholdName}`"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Enter your password</label>
                    <input
                      v-model="deleteHouseholdPassword"
                      type="password"
                      class="shadow-sm focus:ring-red-500 focus:border-red-500 block w-full sm:text-sm border-gray-300 rounded-md"
                    />
                  </div>
                </div>
                <label class="flex items-start space-x-2 mb-3">
                  <input type="checkbox" v-model="exportHouseholdData" class="mt-0.5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                  <span class="text-sm text-gray-700">Send a copy of household data to my email before deletion</span>
                </label>
                <p v-if="deleteHouseholdError" class="text-sm text-red-500 mb-3">{{ deleteHouseholdError }}</p>
                <div class="flex justify-end space-x-3">
                  <button
                    type="button"
                    @click="showDeleteHouseholdModal = false; exportHouseholdData = false"
                    class="py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    @click="confirmDeleteHousehold"
                    :disabled="deleteHouseholdConfirmText !== `DELETE ${deleteHouseholdName}` || !deleteHouseholdPassword || deleteHouseholdLoading"
                    class="py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {{ deleteHouseholdLoading ? 'Deleting...' : 'Delete Forever' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

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
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../store/auth'
import { parseApiError } from '../utils/parseApiError'

const authStore = useAuthStore()
const loading = ref(false)
const error = ref('')
const success = ref('')

const form = reactive({
  username: '',
  email: '',
  password: '',
})

// --- Household types & state ---
interface HouseholdMember {
  user_id: number
  username: string
  email: string
  role_name: string
  has_grocy_key: boolean
  last_products_sync_at: string | null
}

interface HouseholdWithRole {
  id: number
  name: string
  grocy_url: string | null
  address: string | null
  role_name: string
}

interface HouseholdDetail extends HouseholdWithRole {
  members: HouseholdMember[]
}

interface UserSearchItem {
  id: number
  username: string
  email: string
}

const households = ref<HouseholdWithRole[]>([])
const householdsLoading = ref(false)
const householdsError = ref('')
const householdDetails = ref<Record<number, HouseholdDetail>>({})
const expandedMembers = ref<number | null>(null)
const expandedSync = ref<number | null>(null)

const showCreateModal = ref(false)
const createLoading = ref(false)
const createError = ref('')
const newHousehold = reactive({ name: '', grocy_url: '', address: '' })

const userSearchQuery = ref('')
const userSearchResults = ref<UserSearchItem[]>([])
const addRoleName = ref('user')
const addMemberError = ref('')

const showEditModal = ref(false)
const editLoading = ref(false)
const editError = ref('')
const editHouseholdId = ref<number | null>(null)
const editHousehold = reactive({ name: '', grocy_url: '', address: '' })

// Grocy API key management for members
const setKeyTarget = ref<{ householdId: number; userId: number } | null>(null)
const setKeyValue = ref('')
const setKeySaving = ref(false)
const setKeyError = ref('')

// Backfill state
interface BackfillCounts {
  products: number
  recipes: number
  consumed_products: number
  recipes_data: number
  meal_plan_consumptions: number
  note_nutrients: number
  daily_nutrition: number
  total: number
}
const backfillCounts = ref<Record<number, BackfillCounts>>({})
const backfillLoading = ref(false)
const backfillHouseholdId = ref<number | null>(null)
const backfillError = ref('')
const backfillSuccess = ref('')

// Leave/Remove member modal state
interface DataSummary {
  consumed_products: number
  recipes_data: number
  meal_plan_consumptions: number
  note_nutrients: number
  daily_nutrition: number
  total: number
}
const showLeaveModal = ref(false)
const leaveModalSelf = ref(false)
const leaveModalName = ref('')
const leaveModalHouseholdId = ref<number | null>(null)
const leaveModalUserId = ref<number | null>(null)
const leaveDataLoading = ref(false)
const leaveDataSummary = ref<DataSummary | null>(null)
const leaveConfirmChecked = ref(false)
const leaveLoading = ref(false)
const leaveError = ref('')

// Delete household modal state
const showDeleteHouseholdModal = ref(false)
const deleteHouseholdId = ref<number | null>(null)
const deleteHouseholdName = ref('')
const deleteHouseholdConfirmText = ref('')
const deleteHouseholdPassword = ref('')
const deleteHouseholdLoading = ref(false)
const deleteHouseholdError = ref('')
const exportHouseholdData = ref(false)

// Delete account state
const showDeleteAccountModal = ref(false)
const deleteAccountLoading = ref(false)
const deleteAccountMessage = ref('')
const deleteAccountError = ref('')
const deleteAccountConfirmed = ref(false)
const exportAccountData = ref(false)

// Grocy sync state
const syncLoading = ref(false)
const syncType = ref<'products' | 'recipes'>('products')
const syncHouseholdId = ref<number | null>(null)
const syncError = ref('')
const syncSuccess = ref('')
const syncProgressText = ref('Syncing...')

let searchTimeout: ReturnType<typeof setTimeout> | null = null

const fetchHouseholds = async () => {
  householdsLoading.value = true
  householdsError.value = ''
  try {
    const res = await axios.get('/api/households')
    households.value = res.data
  } catch {
    householdsError.value = 'Failed to load households'
  } finally {
    householdsLoading.value = false
  }
}

const toggleMembers = async (id: number) => {
  if (expandedMembers.value === id) {
    expandedMembers.value = null
    return
  }
  expandedMembers.value = id
  userSearchQuery.value = ''
  userSearchResults.value = []
  addMemberError.value = ''
  try {
    const res = await axios.get(`/api/households/${id}`)
    householdDetails.value[id] = res.data
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
  syncError.value = ''
  syncSuccess.value = ''
  if (!householdDetails.value[id]) {
    try {
      const res = await axios.get(`/api/households/${id}`)
      householdDetails.value[id] = res.data
    } catch {
      // ignore
    }
  }
}

const getLastSyncAt = (householdId: number): string | null => {
  const detail = householdDetails.value[householdId]
  if (!detail) return null
  const me = detail.members.find(m => m.user_id === authStore.user?.id)
  return me?.last_products_sync_at ?? null
}

const formatSyncDate = (iso: string): string => {
  const d = new Date(iso)
  return d.toLocaleString()
}

const createHousehold = async () => {
  createLoading.value = true
  createError.value = ''
  try {
    await axios.post('/api/households', {
      name: newHousehold.name,
      grocy_url: newHousehold.grocy_url || null,
      address: newHousehold.address || null,
    })
    showCreateModal.value = false
    newHousehold.name = ''
    newHousehold.grocy_url = ''
    newHousehold.address = ''
    await fetchHouseholds()
  } catch (err: any) {
    createError.value = err.response?.data?.detail || 'Failed to create household'
  } finally {
    createLoading.value = false
  }
}

const openEditModal = (h: HouseholdWithRole) => {
  editHouseholdId.value = h.id
  editHousehold.name = h.name
  editHousehold.grocy_url = h.grocy_url || ''
  editHousehold.address = h.address || ''
  editError.value = ''
  showEditModal.value = true
}

const updateHousehold = async () => {
  if (!editHouseholdId.value) return
  editLoading.value = true
  editError.value = ''
  try {
    await axios.patch(`/api/households/${editHouseholdId.value}`, {
      name: editHousehold.name,
      grocy_url: editHousehold.grocy_url || null,
      address: editHousehold.address || null,
    })
    showEditModal.value = false
    await fetchHouseholds()
  } catch (err: any) {
    editError.value = parseApiError(err, 'Failed to update household')
  } finally {
    editLoading.value = false
  }
}

const searchUsers = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  if (userSearchQuery.value.length < 2) {
    userSearchResults.value = []
    return
  }
  searchTimeout = setTimeout(async () => {
    try {
      const res = await axios.get(`/api/households/search-users?q=${encodeURIComponent(userSearchQuery.value)}`)
      userSearchResults.value = res.data
    } catch {
      userSearchResults.value = []
    }
  }, 300)
}

const addMember = async (householdId: number, userId: number) => {
  addMemberError.value = ''
  try {
    await axios.post(`/api/households/${householdId}/users`, {
      user_id: userId,
      role_name: addRoleName.value,
    })
    userSearchQuery.value = ''
    userSearchResults.value = []
    // Refresh detail
    const res = await axios.get(`/api/households/${householdId}`)
    householdDetails.value[householdId] = res.data
  } catch (err: any) {
    addMemberError.value = err.response?.data?.detail || 'Failed to add user'
  }
}

const removeMember = async (householdId: number, userId: number) => {
  const h = households.value.find(hh => hh.id === householdId)
  openLeaveModal(householdId, h?.name || '', userId, false)
}

const syncProducts = async (householdId: number) => {
  syncLoading.value = true
  syncType.value = 'products'
  syncHouseholdId.value = householdId
  syncError.value = ''
  syncSuccess.value = ''

  const CHUNK_SIZE = 50
  let offset = 0
  let totalProcessed = 0
  let totalUpdated = 0
  let total = 0

  try {
    while (true) {
      syncProgressText.value = total > 0
        ? `Syncing... ${Math.min(offset, total)}/${total}`
        : 'Syncing...'

      const response = await axios.post(
        `/api/sync/grocy-products?offset=${offset}&limit=${CHUNK_SIZE}&household_id=${householdId}`,
      )
      const data = response.data
      totalProcessed += data.processed
      totalUpdated += data.updated
      total = data.total || 0

      if (!data.has_more) break
      offset += CHUNK_SIZE
    }
    syncSuccess.value = `Products synced! Processed: ${totalProcessed}, Updated: ${totalUpdated}`
    // Update last sync timestamp locally
    const detail = householdDetails.value[householdId]
    if (detail) {
      const me = detail.members.find(m => m.user_id === authStore.user?.id)
      if (me) me.last_products_sync_at = new Date().toISOString()
    }
  } catch (err: any) {
    syncError.value = err.response?.data?.detail || 'Failed to sync products'
  } finally {
    syncLoading.value = false
  }
}

const syncRecipes = async (householdId: number) => {
  syncLoading.value = true
  syncType.value = 'recipes'
  syncHouseholdId.value = householdId
  syncError.value = ''
  syncSuccess.value = ''

  try {
    const response = await axios.post(
      `/api/recipes/sync-all?household_id=${householdId}`,
    )
    const data = response.data
    syncSuccess.value = `Recipes synced! Processed: ${data.processed}, Synced: ${data.synced}`
  } catch (err: any) {
    syncError.value = err.response?.data?.detail || 'Failed to sync recipes'
  } finally {
    syncLoading.value = false
  }
}

const openLeaveModal = async (householdId: number, name: string, userId?: number, isSelf: boolean = true) => {
  const targetUserId = userId ?? authStore.user?.id
  if (!targetUserId) return
  leaveModalHouseholdId.value = householdId
  leaveModalUserId.value = targetUserId
  leaveModalName.value = name
  leaveModalSelf.value = isSelf
  leaveConfirmChecked.value = false
  leaveError.value = ''
  leaveDataSummary.value = null
  showLeaveModal.value = true

  // Fetch data summary
  leaveDataLoading.value = true
  try {
    const res = await axios.get(`/api/households/${householdId}/users/${targetUserId}/data-summary`)
    leaveDataSummary.value = res.data
  } catch {
    leaveDataSummary.value = { consumed_products: 0, recipes_data: 0, meal_plan_consumptions: 0, note_nutrients: 0, daily_nutrition: 0, total: 0 }
  } finally {
    leaveDataLoading.value = false
  }
}

const confirmLeave = async () => {
  if (!leaveModalHouseholdId.value || !leaveModalUserId.value) return
  leaveLoading.value = true
  leaveError.value = ''
  try {
    await axios.delete(`/api/households/${leaveModalHouseholdId.value}/users/${leaveModalUserId.value}?confirm=true`)
    showLeaveModal.value = false
    if (leaveModalSelf.value) {
      await fetchHouseholds()
    } else {
      const res = await axios.get(`/api/households/${leaveModalHouseholdId.value}`)
      householdDetails.value[leaveModalHouseholdId.value] = res.data
    }
  } catch (err: any) {
    leaveError.value = parseApiError(err, 'Failed to remove user')
  } finally {
    leaveLoading.value = false
  }
}

const openDeleteHouseholdModal = (h: HouseholdWithRole) => {
  deleteHouseholdId.value = h.id
  deleteHouseholdName.value = h.name
  deleteHouseholdConfirmText.value = ''
  deleteHouseholdPassword.value = ''
  deleteHouseholdError.value = ''
  showDeleteHouseholdModal.value = true
}

const confirmDeleteHousehold = async () => {
  if (!deleteHouseholdId.value) return
  deleteHouseholdLoading.value = true
  deleteHouseholdError.value = ''
  try {
    await axios.delete(`/api/households/${deleteHouseholdId.value}`, {
      data: {
        password: deleteHouseholdPassword.value,
        confirmation_text: deleteHouseholdConfirmText.value,
        export_data: exportHouseholdData.value,
      },
    })
    exportHouseholdData.value = false
    showDeleteHouseholdModal.value = false
    await fetchHouseholds()
  } catch (err: any) {
    deleteHouseholdError.value = parseApiError(err, 'Failed to delete household')
  } finally {
    deleteHouseholdLoading.value = false
  }
}

const requestAccountDeletion = async () => {
  deleteAccountLoading.value = true
  deleteAccountError.value = ''
  deleteAccountMessage.value = ''
  try {
    const params = exportAccountData.value ? '?export_data=true' : ''
    const res = await axios.post(`/api/users/me/request-deletion${params}`)
    deleteAccountMessage.value = res.data.message
    showDeleteAccountModal.value = false
    deleteAccountConfirmed.value = false
    exportAccountData.value = false
  } catch (err: any) {
    deleteAccountError.value = parseApiError(err, 'Failed to request account deletion')
  } finally {
    deleteAccountLoading.value = false
  }
}

const fetchBackfillStatus = async (householdId: number) => {
  try {
    const res = await axios.get(`/api/households/${householdId}/backfill-status`)
    backfillCounts.value[householdId] = res.data
  } catch {
    // If 403 or error, section won't render
  }
}

const runBackfill = async (householdId: number) => {
  backfillLoading.value = true
  backfillHouseholdId.value = householdId
  backfillError.value = ''
  backfillSuccess.value = ''
  try {
    const res = await axios.post(`/api/households/${householdId}/backfill`)
    backfillSuccess.value = `Done! Updated ${res.data.updated_household_id} household and ${res.data.updated_user_id} user assignments.`
    await fetchBackfillStatus(householdId)
  } catch (err: any) {
    backfillError.value = parseApiError(err, 'Failed to run backfill')
  } finally {
    backfillLoading.value = false
  }
}

const openSetKeyForm = (householdId: number, userId: number) => {
  setKeyTarget.value = { householdId, userId }
  setKeyValue.value = ''
  setKeyError.value = ''
}

const saveGrocyKey = async (householdId: number, _userId: number) => {
  setKeySaving.value = true
  setKeyError.value = ''
  try {
    await axios.put(`/api/households/${householdId}/grocy-key`, { grocy_api_key: setKeyValue.value })
    setKeyTarget.value = null
    // Refresh member list
    const res = await axios.get(`/api/households/${householdId}`)
    householdDetails.value[householdId] = res.data
  } catch (err: any) {
    setKeyError.value = err.response?.data?.detail || 'Failed to save API key'
  } finally {
    setKeySaving.value = false
  }
}

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

  await fetchHouseholds()

  // Fetch backfill status for admin households
  const adminHouseholds = households.value.filter(h => h.role_name === 'admin')
  await Promise.all(adminHouseholds.map(h => fetchBackfillStatus(h.id)))
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
    error.value = parseApiError(err, 'Failed to update profile')
  } finally {
    loading.value = false
  }
}

</script>