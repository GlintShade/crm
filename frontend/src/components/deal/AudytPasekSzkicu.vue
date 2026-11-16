<!--
  Dolny pasek Szkicu audytu OZE: postep (pola i zdjecia), stan zapisu i
  przycisk "Prześlij do weryfikacji". Wyglad jak AudytPasekDecyzji (Weryfikacja).
  Prezentacyjny: emituje `wyslij`, nie wola API. Przycisk jest zawsze aktywny
  (przy brakach rodzic pokazuje czerwony baner zamiast przesylac); admin i
  back office w Szkicu widza pasek bez przycisku (`pokazPrzycisk` = false).
-->
<template>
  <div
    data-testid="audyt-pasek-szkicu"
    class="sticky -bottom-5 z-20 -mx-5 -mb-5 mt-auto border-t border-outline-gray-2 bg-surface-base px-5 py-3"
  >
    <div class="mx-auto flex w-full max-w-3xl flex-wrap items-center gap-x-4 gap-y-2">
      <div class="hidden h-1.5 w-24 shrink-0 overflow-hidden rounded-full bg-surface-gray-3 sm:block">
        <div class="h-full rounded-full bg-surface-green-3" :style="{ width: procent + '%' }" />
      </div>

      <div class="min-w-0 flex-1 text-xs text-ink-gray-6 sm:text-sm">
        <strong class="font-semibold text-ink-gray-8">
          {{ __('{0} z {1} pól', [polaGotowe, polaRazem]) }}
        </strong>
        · {{ __('{0} z {1} zdjęć', [zdjeciaGotowe, zdjeciaRazem]) }}
      </div>

      <span v-if="saveState === 'saving'" class="text-xs text-ink-gray-4">{{ __('Zapisywanie…') }}</span>
      <span v-else-if="saveState === 'saved'" class="text-xs text-ink-green-6">{{ __('Zapisano') }} ✓</span>
      <span v-else-if="saveState === 'error'" class="text-xs text-ink-red-6">{{ __('Błąd zapisu') }}</span>

      <Button
        v-if="pokazPrzycisk"
        data-testid="audyt-wyslij"
        class="w-full sm:w-auto"
        variant="solid"
        :theme="kompletny ? 'green' : 'gray'"
        :label="__('Prześlij do weryfikacji')"
        :loading="loading"
        @click="$emit('wyslij')"
      />
    </div>
  </div>
</template>

<script setup>
import { Button } from 'frappe-ui'
import { computed } from 'vue'
import { procentPostepu } from '@/utils/audytSzkic'

const props = defineProps({
  polaGotowe: { type: Number, default: 0 },
  polaRazem: { type: Number, default: 0 },
  zdjeciaGotowe: { type: Number, default: 0 },
  zdjeciaRazem: { type: Number, default: 0 },
  kompletny: { type: Boolean, default: false },
  pokazPrzycisk: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  // idle | saving | saved | error (puste, gdy zapis nie dotyczy tego widoku)
  saveState: { type: String, default: 'idle' },
})

defineEmits(['wyslij'])

const procent = computed(() =>
  procentPostepu(props.polaGotowe, props.polaRazem, props.zdjeciaGotowe, props.zdjeciaRazem),
)
</script>
