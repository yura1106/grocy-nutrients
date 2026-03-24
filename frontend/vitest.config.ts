import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  test: {
    // Use jsdom to simulate a browser environment
    environment: 'jsdom',

    // Global vitest functions (describe, it, expect, vi) without imports
    globals: true,

    // Setup file runs before each test file
    setupFiles: ['./src/tests/setup.ts'],

    // Code coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: ['src/**/*.{ts,vue}'],
      exclude: [
        'src/tests/**',
        'src/main.ts',
        'src/types/**',
      ],
      thresholds: {
        lines: 10,
        functions: 10,
        branches: 10,
      },
    },

    // Clear mocks between tests
    clearMocks: true,
    restoreMocks: true,
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
