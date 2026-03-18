import { reactive, toRefs } from 'vue'
import { useHouseholdStore } from '../store/household'
import type { UserSearchItem } from '../types/household'

export function useMemberSearch() {
  const householdStore = useHouseholdStore()

  const state = reactive({
    query: '',
    results: [] as UserSearchItem[],
    roleName: 'user',
    error: '',
  })

  let searchTimeout: ReturnType<typeof setTimeout> | null = null

  const search = () => {
    if (searchTimeout) clearTimeout(searchTimeout)
    if (state.query.length < 2) {
      state.results = []
      return
    }
    searchTimeout = setTimeout(async () => {
      try {
        state.results = await householdStore.searchUsers(state.query)
      } catch {
        state.results = []
      }
    }, 300)
  }

  const addMember = async (householdId: number, userId: number) => {
    state.error = ''
    try {
      await householdStore.addMember(householdId, userId, state.roleName)
      state.query = ''
      state.results = []
    } catch (err: any) {
      state.error = err.response?.data?.detail || 'Failed to add user'
    }
  }

  const reset = () => {
    state.query = ''
    state.results = []
    state.error = ''
  }

  return {
    ...toRefs(state),
    search,
    addMember,
    reset,
  }
}
