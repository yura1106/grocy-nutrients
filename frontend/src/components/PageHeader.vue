<template>
  <header>
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-4">
      <div
        v-if="$slots['above-title']"
        class="mb-4"
      >
        <slot name="above-title"></slot>
      </div>

      <div class="md:flex md:items-center md:justify-between">
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-3">
            <component
              :is="metaIcon"
              v-if="metaIcon"
              :size="28"
              :stroke-width="2"
              class="text-gray-900 shrink-0"
            />
            <h1
              v-if="isSkeleton"
              class="text-3xl font-bold leading-tight text-gray-900 bg-gray-200 rounded animate-pulse w-64"
              aria-busy="true"
            >
&nbsp;
            </h1>
            <h1
              v-else
              class="text-3xl font-bold leading-tight text-gray-900"
            >
              {{ effectiveTitle }}
            </h1>
          </div>
          <p
            v-if="subtitle"
            class="mt-2 text-sm text-gray-600"
          >
            {{ subtitle }}
          </p>
        </div>

        <div
          v-if="$slots.actions"
          class="mt-4 md:mt-0 md:ml-4 flex shrink-0"
        >
          <slot name="actions"></slot>
        </div>
      </div>

      <div
        v-if="$slots.meta"
        class="mt-3"
      >
        <slot name="meta"></slot>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps<{
  title?: string | null
  subtitle?: string
}>()

const route = useRoute()

const metaIcon = computed(() => route.meta.icon)

const isSkeleton = computed(() => props.title === null)

const effectiveTitle = computed(() => {
  if (props.title === null) return ''
  if (props.title !== undefined) return props.title
  return route.meta.title ?? ''
})
</script>
