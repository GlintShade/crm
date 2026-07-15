<!-- Faktury tab (Szansa view) — Phase 1 scaffold; Phase 2 = Volteo Faktura doctype (list + upload). -->
<template>
  <div class="flex flex-1 flex-col items-center justify-center gap-3 p-10 text-center">
    <FakturyIcon class="h-10 w-10 text-ink-gray-4" />
    <div class="text-lg font-medium text-ink-gray-7">{{ __('Brak faktur') }}</div>
    <div class="max-w-md text-sm text-ink-gray-5">
      {{ __('Faktury dla tej szansy pojawią się tutaj. Dodawanie i śledzenie faktur — wkrótce.') }}
    </div>
  </div>
</template>

<script setup>
import FakturyIcon from '@/components/Icons/FakturyIcon.vue'

defineProps({
  dealId: { type: String, required: true },
})
</script>
