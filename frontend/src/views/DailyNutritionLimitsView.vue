<!-- frontend/src/views/DailyNutritionLimitsView.vue -->
<template>
  <div class="bg-gray-100 min-h-screen">
    <PageHeader subtitle="Set per-day nutrient targets based on TDEE and body weight" />
    <main>
      <div class="max-w-7xl mx-auto sm:px-6 lg:px-8 space-y-6 px-4">
        <NewLimitForm @created="onCreated" />
        <DailyLimitsTable @edit="openEdit" />
      </div>
    </main>

    <EditLimitModal
      v-if="editing"
      :item="editing"
      @close="editing = null"
      @saved="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import NewLimitForm from '../components/nutrition-limits/NewLimitForm.vue'
import DailyLimitsTable from '../components/nutrition-limits/DailyLimitsTable.vue'
import EditLimitModal from '../components/nutrition-limits/EditLimitModal.vue'
import PageHeader from '../components/PageHeader.vue'
import type { NutritionLimit } from '../types/nutritionLimit'
import { useNutritionLimitsStore } from '../store/nutritionLimits'

const store = useNutritionLimitsStore()
const editing = ref<NutritionLimit | null>(null)

function openEdit(item: NutritionLimit) {
  editing.value = item
}

function onCreated() {
  store.fetchTodayLimit()
}

function onSaved() {
  store.fetchTodayLimit()
}
</script>
