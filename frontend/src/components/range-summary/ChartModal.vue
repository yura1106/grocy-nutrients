<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
        @click.self="onClose"
      >
        <Transition
          enter-active-class="transition duration-150 ease-out"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition duration-100 ease-in"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
          appear
        >
          <div
            ref="dialogRef"
            class="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden"
            role="dialog"
            aria-modal="true"
            aria-labelledby="chart-modal-title"
            tabindex="-1"
            @keydown.tab="onTabKey"
          >
            <header class="px-5 pt-4 pb-3 border-b border-gray-100 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <BarChart2
                  :size="16"
                  class="text-blue-500"
                />
                <h3
                  id="chart-modal-title"
                  class="text-sm font-semibold text-gray-900"
                >
                  Тренди нутрієнтів
                </h3>
                <span class="text-xs text-gray-400 ml-1">{{ days.length }} {{ daysWord(days.length) }}</span>
              </div>
              <button
                ref="closeButtonRef"
                class="text-gray-400 hover:text-gray-600 text-lg leading-none"
                aria-label="Закрити"
                @click="onClose"
              >
                ✕
              </button>
            </header>

            <nav class="flex items-center gap-0.5 px-5 pt-3 pb-0 border-b border-gray-100 overflow-x-auto">
              <button
                v-for="tab in TABS"
                :key="tab.key"
                type="button"
                class="px-3 py-1.5 text-xs rounded-t transition-colors border-b-2 -mb-px shrink-0"
                :class="activeTab === tab.key
                  ? 'text-blue-600 border-blue-500 bg-blue-50/60'
                  : 'text-gray-500 border-transparent hover:text-gray-800 hover:bg-gray-50'"
                @click="activeTab = tab.key"
              >
                <component
                  v-if="tab.key === 'overview'"
                  :is="TrendingUp"
                  :size="11"
                  class="inline mr-1 align-middle"
                />
                <span
                  v-else
                  class="inline-block w-1.5 h-1.5 rounded-full mr-1.5 align-middle"
                  :style="{ background: NUTRIENT_COLORS[tab.key as NutrientKey] }"
                ></span>
                {{ tab.label }}
              </button>
            </nav>

            <div class="px-5 pt-4 pb-5 overflow-y-auto">
              <OverviewChart
                v-if="activeTab === 'overview'"
                :days="days"
                :effective-limits-by-date="effectiveLimitsByDate"
              />
              <NutrientBarChart
                v-else
                :nutrient-key="activeTab as NutrientKey"
                :days="days"
                :effective-limits-by-date="effectiveLimitsByDate"
              />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { BarChart2, TrendingUp } from 'lucide-vue-next'
import OverviewChart from './charts/OverviewChart.vue'
import NutrientBarChart from './charts/NutrientBarChart.vue'
import {
  type DailyStatsRow,
  type NutrientKey,
  NUTRIENT_KEYS,
  NUTRIENT_META,
  NUTRIENT_COLORS,
} from '@/composables/useRangeAverages'
import type { NormValues } from '@/composables/useNorms'

type TabKey = 'overview' | NutrientKey

const TABS: { key: TabKey; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  ...NUTRIENT_KEYS.map(k => ({ key: k as TabKey, label: NUTRIENT_META[k].label })),
]

const props = defineProps<{
  open: boolean
  days: DailyStatsRow[]
  effectiveLimitsByDate: Map<string, NormValues | null>
}>()

const emit = defineEmits<{ close: [] }>()

const activeTab = ref<TabKey>('overview')
const dialogRef = ref<HTMLElement | null>(null)
const closeButtonRef = ref<HTMLElement | null>(null)
let openerEl: HTMLElement | null = null

function onClose(): void {
  emit('close')
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape' && props.open) {
    e.preventDefault()
    onClose()
  }
}

function getFocusable(root: HTMLElement): HTMLElement[] {
  const sel = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  return Array.from(root.querySelectorAll<HTMLElement>(sel))
    .filter(el => !el.hasAttribute('disabled') && el.offsetParent !== null)
}

function onTabKey(e: KeyboardEvent): void {
  if (e.key !== 'Tab' || !dialogRef.value) return
  const focusables = getFocusable(dialogRef.value)
  if (focusables.length === 0) return
  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  const active = document.activeElement as HTMLElement | null
  if (e.shiftKey && active === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && active === last) {
    e.preventDefault()
    first.focus()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})

watch(
  () => props.open,
  async (v) => {
    if (v) {
      // Capture opener immediately (synchronously) so that re-focusing on close
      // works on the very first open — when ChartModal is async-loaded and
      // mounted with `open=true`, this watcher fires via `immediate: true`
      // before the user could move focus elsewhere.
      openerEl = document.activeElement as HTMLElement | null
      activeTab.value = 'overview'
      await nextTick()
      closeButtonRef.value?.focus()
    } else if (openerEl && typeof openerEl.focus === 'function') {
      openerEl.focus()
      openerEl = null
    }
  },
  { immediate: true },
)

function daysWord(n: number): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'день'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'дні'
  return 'днів'
}
</script>
