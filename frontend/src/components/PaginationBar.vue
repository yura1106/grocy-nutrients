<template>
  <div
    v-if="total > limit"
    class="px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6"
  >
    <!-- Mobile -->
    <div class="flex-1 flex justify-between sm:hidden">
      <button
        @click="$emit('prev')"
        :disabled="skip === 0"
        class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
      >
        Previous
      </button>
      <button
        @click="$emit('next')"
        :disabled="skip + limit >= total"
        class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
      >
        Next
      </button>
    </div>
    <!-- Desktop -->
    <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
      <p class="text-sm text-gray-700">
        Showing
        <span class="font-medium">{{ skip + 1 }}</span>
        to
        <span class="font-medium">{{ Math.min(skip + limit, total) }}</span>
        of
        <span class="font-medium">{{ total }}</span>
        results
      </p>
      <nav class="relative z-0 inline-flex rounded-md shadow-xs -space-x-px">
        <button
          @click="$emit('prev')"
          :disabled="skip === 0"
          class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
        >
          <span class="sr-only">Previous</span>
          <svg
            class="h-5 w-5"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
        <button
          @click="$emit('next')"
          :disabled="skip + limit >= total"
          class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
        >
          <span class="sr-only">Next</span>
          <svg
            class="h-5 w-5"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  skip: number
  limit: number
  total: number
}>()

defineEmits<{
  prev: []
  next: []
}>()
</script>
