<!-- Montaż tab (Szansa view) — Phase 1 scaffold; Phase 2 = timestamped install-progress update stream. -->
<template>
  <div class="flex flex-1 flex-col items-center justify-center gap-3 p-10 text-center">
    <MontazIcon class="h-10 w-10 text-ink-gray-4" />
    <div class="text-lg font-medium text-ink-gray-7">{{ __('Montaż') }}</div>
    <div class="max-w-md text-sm text-ink-gray-5">
      {{ __('Aktualizacje montażu od zespołu i przedstawiciela (np. „umówiono termin montażu") pojawią się tutaj — wkrótce.') }}
    </div>
  </div>
</template>

<script setup>
import MontazIcon from '@/components/Icons/MontazIcon.vue'

defineProps({
  dealId: { type: String, required: true },
})
</script>
