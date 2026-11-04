<template>
  <div>
    <slot name="header" v-bind="{ opened, hide, open, close, toggle }">
      <div
        v-if="!hide"
        class="section-header flex items-center justify-between"
        :class="headerClass"
      >
        <div
          class="flex text-ink-gray-9 max-w-fit cursor-pointer items-center gap-2 text-base"
          :class="labelClass"
          @click="collapsible && toggle()"
        >
          <span
            v-if="collapsible && collapseIconPosition === 'left'"
            class="lucide-chevron-right h-4 transition-all duration-300 ease-in-out"
            :class="{ 'rotate-90': opened }"
            aria-hidden="true"
          />
          <span>
            {{ __(label) || __('Untitled') }}
          </span>
          <Badge
            v-if="count"
            :label="count"
            :variant="countVariant"
            :theme="countTheme"
          />
          <span
            v-if="collapsible && collapseIconPosition === 'right'"
            class="lucide-chevron-right h-4 transition-all duration-300 ease-in-out"
            :class="{ 'rotate-90': opened }"
            aria-hidden="true"
          />
        </div>
        <slot name="actions"></slot>
      </div>
    </slot>
    <transition
      enter-active-class="duration-300 ease-in"
      leave-active-class="duration-300 ease-[cubic-bezier(0, 1, 0.5, 1)]"
      enter-to-class="max-h-[200px] overflow-hidden"
      leave-from-class="max-h-[200px] overflow-hidden"
      enter-from-class="max-h-0 overflow-hidden"
      leave-to-class="max-h-0 overflow-hidden"
    >
      <div v-show="opened" class="columns" v-bind="$attrs">
        <slot v-bind="{ opened, open, close, toggle }" />
      </div>
    </transition>
  </div>
</template>
<script setup>
import { Badge } from 'frappe-ui'
import { ref, watch } from 'vue'

const props = defineProps({
  label: { type: String, default: '' },
  count: { type: [String, Number], default: '' },
  countVariant: { type: String, default: 'subtle' },
  countTheme: { type: String, default: 'gray' },
  hideLabel: { type: Boolean, default: false },
  opened: { type: Boolean, default: true },
  collapsible: { type: Boolean, default: true },
  collapseIconPosition: { type: String, default: 'left' },
  labelClass: { type: [String, Object, Array], default: '' },
  headerClass: { type: [String, Object, Array], default: '' },
})

const emit = defineEmits(['update:opened'])

const hide = ref(props.hideLabel)
const opened = ref(props.opened)

// VOLTEO ops#330: rodzic moze trzymac stan (pamiec sekcji panelu bocznego),
// wiec zmiana propsa nadpisuje stan lokalny, a kazde przelaczenie jest
// zglaszane przez update:opened. Bez nasluchu dziala jak dotad.
watch(
  () => props.opened,
  (v) => (opened.value = v),
)

function ustaw(v) {
  opened.value = v
  emit('update:opened', v)
}

function toggle() {
  ustaw(!opened.value)
}

function open() {
  ustaw(true)
}

function close() {
  ustaw(false)
}
</script>
<script>
export default {
  inheritAttrs: false,
}
</script>
