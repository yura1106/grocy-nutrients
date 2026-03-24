import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import pluginVue from 'eslint-plugin-vue'

export default [
  // Ignore build output and declaration files
  { ignores: ['dist/**', '**/*.d.ts'] },

  // Base JS recommended rules
  js.configs.recommended,

  // TypeScript recommended
  ...tseslint.configs.recommended,

  // Vue 3 recommended rules
  ...pluginVue.configs['flat/recommended'],

  // Browser + Node globals (Event, HTMLElement, setTimeout, etc.)
  {
    languageOptions: {
      globals: {
        // Browser
        window: 'readonly', document: 'readonly', navigator: 'readonly',
        console: 'readonly', setTimeout: 'readonly', clearTimeout: 'readonly',
        setInterval: 'readonly', clearInterval: 'readonly', localStorage: 'readonly',
        FormData: 'readonly', Event: 'readonly', HTMLElement: 'readonly',
        HTMLSelectElement: 'readonly', HTMLInputElement: 'readonly',
        NodeJS: 'readonly', URL: 'readonly', URLSearchParams: 'readonly',
        fetch: 'readonly', AbortController: 'readonly', Response: 'readonly',
        Headers: 'readonly', Request: 'readonly',
        alert: 'readonly', confirm: 'readonly', FileReader: 'readonly',
        Blob: 'readonly', File: 'readonly',
      },
    },
  },

  // Let the Vue parser handle <script lang="ts"> blocks
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
      },
    },
  },

  // Project-specific overrides
  {
    rules: {
      // Relax Vue template rules that clash with project style
      'vue/multi-word-component-names': 'off',
      // 'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-self-closing': ['warn', {
        html: { void: 'always', normal: 'never', component: 'always' },
      }],
      'vue/attributes-order': 'off',

      // TypeScript
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': ['warn', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
      }],

      // General
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
  },
]
