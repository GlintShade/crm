<!--
  Dymek spotkania (kalendarz, ops#318): trzy linie (czas i data, klient i
  miasto, status i telefon) nad paskiem albo blokiem. Opakowuje element
  wyzwalający (as-child), pokazuje się po 100 ms.
-->
<template>
  <Tooltip placement="top" :hover-delay="0.1">
    <slot />
    <template #body>
      <div
        class="rounded bg-surface-gray-10 px-2.5 py-1.5 text-xs leading-snug text-ink-base shadow-xl"
        data-testid="kalendarz-dymek"
      >
        <div class="font-semibold">{{ opis.linia1 }}</div>
        <div>{{ opis.linia2 }}</div>
        <div class="opacity-80">{{ opis.linia3 }}</div>
      </div>
    </template>
  </Tooltip>
</template>

<script setup>
import { computed } from 'vue'
import { Tooltip } from 'frappe-ui'
import { opisDymka } from '@/utils/kalendarz'

const props = defineProps({
  spotkanie: { type: Object, required: true },
})

const opis = computed(() => opisDymka(props.spotkanie))
</script>
