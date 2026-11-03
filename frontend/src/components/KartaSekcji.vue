<!--
  Karta sekcji panelu bocznego (wariant "karty", ops#326): obramowanie,
  klikalny naglowek (chevron, tytul, jednolinijkowe podsumowanie widoczne
  takze po zwinieciu, akcje po prawej) i cialo. Stan otwarcia trzyma
  rodzic (SidePanelLayout), tu tylko prezentacja.
-->
<template>
  <div
    class="karta-sekcji min-w-0 rounded-lg border border-outline-gray-1 bg-surface-white"
    :data-testid="'karta-' + (nazwa || label)"
  >
    <div
      class="flex min-w-0 cursor-pointer items-center gap-2 py-2 pl-3 pr-2"
      @click="$emit('toggle')"
    >
      <span
        :class="[
          opened ? 'lucide-chevron-down' : 'lucide-chevron-right',
          'size-4 shrink-0 text-ink-gray-5',
        ]"
        aria-hidden="true"
      />
      <div class="flex min-w-0 flex-1 flex-col gap-px">
        <div class="truncate text-[13px] font-semibold text-ink-gray-9">
          {{ __(label) || __('Untitled') }}
        </div>
        <div
          v-if="summary"
          class="truncate text-[11.5px] text-ink-gray-5"
          :title="summary"
        >
          {{ summary }}
        </div>
      </div>
      <div class="shrink-0" @click.stop>
        <slot name="actions" />
      </div>
    </div>
    <div v-show="opened" class="border-t border-outline-gray-1 px-3 pb-3 pt-2.5">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, default: '' },
  nazwa: { type: String, default: '' },
  summary: { type: String, default: '' },
  opened: { type: Boolean, default: true },
})
defineEmits(['toggle'])
</script>
