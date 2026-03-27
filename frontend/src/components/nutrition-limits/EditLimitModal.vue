<!-- frontend/src/components/nutrition-limits/EditLimitModal.vue -->
<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
    @click.self="emit('close')"
  >
    <div class="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <h3 class="text-base font-semibold text-gray-900">Edit Limit — {{ item.date }}</h3>
        <button
          @click="emit('close')"
          class="text-gray-400 hover:text-gray-600 text-lg leading-none"
        >
          ✕
        </button>
      </div>

      <div class="px-6 py-4 space-y-4">
        <!-- Activity metadata -->
        <div class="bg-gray-50 rounded-lg p-3 grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">Calories Burned</label>
            <input
              v-model.number="form.calories_burned"
              type="number"
              step="1"
              class="block w-full py-1.5 px-2.5 text-sm bg-white border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">Body Weight (kg)</label>
            <input
              v-model.number="form.body_weight"
              type="number"
              step="0.1"
              class="block w-full py-1.5 px-2.5 text-sm bg-white border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div class="col-span-2">
            <label class="block text-xs font-medium text-gray-500 mb-1">Activity Level</label>
            <VueMultiselect
              v-model="selectedActivityLevel"
              :options="activityLevelOptions"
              :searchable="false"
              :close-on-select="true"
              :show-labels="false"
              label="label"
              track-by="value"
              placeholder="Select activity level"
            />
          </div>
        </div>

        <!-- Nutrient limits -->
        <div>
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Nutrient Limits</p>
          <div class="grid grid-cols-2 gap-x-4 gap-y-3">
            <div
              v-for="field in nutrientFields"
              :key="field.key"
            >
              <label class="block text-xs font-medium text-gray-500 mb-1">{{ field.label }}</label>
              <input
                v-model.number="form[field.key]"
                type="number"
                :step="field.step"
                class="block w-full py-1.5 px-2.5 text-sm bg-gray-50 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:bg-white"
              />
            </div>
          </div>
        </div>
      </div>

      <div
        v-if="store.error"
        class="mx-6 mb-3 text-red-500 text-sm"
      >
        {{ store.error }}
      </div>

      <div class="flex justify-between gap-3 px-6 py-4 border-t border-gray-200">
        <button
          @click="del"
          :disabled="store.loading"
          class="inline-flex items-center px-3 py-2 border border-red-200 text-sm font-medium rounded-md text-red-600 bg-white hover:bg-red-50 disabled:opacity-50"
        >
          Delete
        </button>
        <div class="flex gap-3">
          <button
            @click="emit('close')"
            class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            @click="save"
            :disabled="store.loading"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
          >
            {{ store.loading ? 'Saving...' : 'Save' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import VueMultiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'
import { useNutritionLimitsStore } from '../../store/nutritionLimits'
import type { NutritionLimit } from '../../types/nutritionLimit'
import type { ActivityLevel } from '../../types/health'
import { ACTIVITY_LEVEL_LABELS } from '../../types/health'

const props = defineProps<{ item: NutritionLimit }>()
const emit = defineEmits<{ close: []; saved: [] }>()

const store = useNutritionLimitsStore()

interface SelectOption<T> { value: T; label: string }

const activityLevelOptions: SelectOption<ActivityLevel>[] = Object.entries(ACTIVITY_LEVEL_LABELS).map(
  ([value, label]) => ({ value: value as ActivityLevel, label }),
)

const selectedActivityLevel = ref<SelectOption<ActivityLevel> | null>(
  props.item.activity_level
    ? activityLevelOptions.find((o) => o.value === props.item.activity_level) ?? null
    : null,
)

type NutrientKey = 'calories' | 'proteins' | 'carbohydrates' | 'carbohydrates_of_sugars' |
                   'fats' | 'fats_saturated' | 'salt' | 'fibers'

const nutrientFields: { key: NutrientKey; label: string; step: number }[] = [
  { key: 'calories', label: 'Kcal Limit', step: 1 },
  { key: 'proteins', label: 'Proteins (g)', step: 1 },
  { key: 'carbohydrates', label: 'Carbs (g)', step: 1 },
  { key: 'carbohydrates_of_sugars', label: 'Sugars (g)', step: 1 },
  { key: 'fats', label: 'Fats (g)', step: 1 },
  { key: 'fats_saturated', label: 'Sat. Fats (g)', step: 1 },
  { key: 'salt', label: 'Salt (g)', step: 0.1 },
  { key: 'fibers', label: 'Fiber (g)', step: 1 },
]

const r2 = (v: number | null) => v !== null ? Math.round(v * 100) / 100 : null

const form = reactive<Record<NutrientKey | 'calories_burned' | 'body_weight', number | null> & { activity_level: string | null }>({
  calories_burned: r2(props.item.calories_burned),
  body_weight: r2(props.item.body_weight),
  activity_level: props.item.activity_level ?? null,
  calories: r2(props.item.calories),
  proteins: r2(props.item.proteins),
  carbohydrates: r2(props.item.carbohydrates),
  carbohydrates_of_sugars: r2(props.item.carbohydrates_of_sugars),
  fats: r2(props.item.fats),
  fats_saturated: r2(props.item.fats_saturated),
  salt: r2(props.item.salt),
  fibers: r2(props.item.fibers),
})

watch(selectedActivityLevel, (opt) => { form.activity_level = opt?.value ?? null })

async function save() {
  await store.updateLimit(props.item.id, { ...form })
  emit('saved')
  emit('close')
}

async function del() {
  await store.deleteLimit(props.item.id)
  emit('saved')
  emit('close')
}
</script>
