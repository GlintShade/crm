<!-- Audyt tab (Szansa view) — Phase 1 scaffold; Phase 2 = Volteo Audyt doctype (technical audit form). -->
<template>
  <div class="flex flex-1 flex-col items-center justify-center gap-3 p-10 text-center">
    <AudytIcon class="h-10 w-10 text-ink-gray-4" />
    <div class="text-lg font-medium text-ink-gray-7">{{ __('Audyt techniczny') }}</div>
    <div class="max-w-md text-sm text-ink-gray-5">
      {{ __('Audyt techniczny (dane podstawowe, dane elektryczne istniejącego budynku, planowana instalacja) — wkrótce.') }}
    </div>
  </div>
</template>

<script setup>
import AudytIcon from '@/components/Icons/AudytIcon.vue'

defineProps({
  dealId: { type: String, required: true },
})
</script>
