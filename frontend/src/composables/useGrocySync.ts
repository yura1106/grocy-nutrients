import { reactive, toRefs } from 'vue'
import { isAxiosError } from 'axios'
import { useAuthStore } from '../store/auth'
import { useHouseholdStore } from '../store/household'

export function useGrocySync() {
  const authStore = useAuthStore()
  const householdStore = useHouseholdStore()

  const state = reactive({
    loading: false,
    type: 'products' as 'products' | 'recipes',
    householdId: null as number | null,
    error: '',
    success: '',
    progressText: 'Syncing...',
  })

  const syncProducts = async (householdId: number) => {
    state.loading = true
    state.type = 'products'
    state.householdId = householdId
    state.error = ''
    state.success = ''

    try {
      const result = await householdStore.syncProducts(householdId, (text) => {
        state.progressText = text
      })
      state.success = `Products synced! Processed: ${result.processed}, Updated: ${result.updated}`
      const detail = householdStore.householdDetails[householdId]
      if (detail) {
        const me = detail.members.find(m => m.user_id === authStore.user?.id)
        if (me) me.last_products_sync_at = new Date().toISOString()
      }
    } catch (err: unknown) {
      state.error = isAxiosError(err) && err.response?.data?.detail || 'Failed to sync products'
    } finally {
      state.loading = false
    }
  }

  const syncRecipes = async (householdId: number) => {
    state.loading = true
    state.type = 'recipes'
    state.householdId = householdId
    state.error = ''
    state.success = ''

    try {
      const data = await householdStore.syncRecipes(householdId)
      state.success = `Recipes synced! Processed: ${data.processed}, Synced: ${data.synced}`
    } catch (err: unknown) {
      state.error = isAxiosError(err) && err.response?.data?.detail || 'Failed to sync recipes'
    } finally {
      state.loading = false
    }
  }

  const getLastSyncAt = (householdId: number): string | null => {
    const detail = householdStore.householdDetails[householdId]
    if (!detail) return null
    const me = detail.members.find(m => m.user_id === authStore.user?.id)
    return me?.last_products_sync_at ?? null
  }

  const formatSyncDate = (iso: string): string => {
    return new Date(iso).toLocaleString()
  }

  return {
    ...toRefs(state),
    syncProducts,
    syncRecipes,
    getLastSyncAt,
    formatSyncDate,
  }
}
