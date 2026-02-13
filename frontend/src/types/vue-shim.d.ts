declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module 'vue-multiselect' {
  import type { DefineComponent } from 'vue'
  const VueMultiselect: DefineComponent<any, any, any>
  export default VueMultiselect
} 