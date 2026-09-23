<!--
  Renders a phone number as a `tel:` link so tapping/clicking it opens the
  device dialer. Falls back to plain text when the value isn't dialable
  (telHref returns ''), so this can replace any `{{ numer }}` read-only
  rendering without adding an extra empty-state branch at each call site.

  `@click.stop` is required: this is used inside list rows, side-panel
  cards and popups where the row/card itself has its own click handler
  (navigate, apply a filter, open a modal), without it, clicking the
  number would also trigger that outer handler.
-->
<template>
  <a
    v-if="href"
    :href="href"
    :class="['cursor-pointer hover:underline', klasa]"
    rel="nofollow"
    :title="__('Zadzwoń')"
    @click.stop
  >{{ numer }}</a>
  <span v-else :class="klasa">{{ numer }}</span>
</template>

<script setup>
import { computed } from 'vue'
import { telHref } from '@/utils/telefon'

const props = defineProps({
  numer: { type: [String, Number], default: '' },
  klasa: { type: [String, Array, Object], default: '' },
})

const href = computed(() => telHref(props.numer))
</script>
