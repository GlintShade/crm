<!--
  Podsumowanie liczbowe paska górnego zakładki "Notatki" (issue ops#206,
  wariant C): "17 notatek | 6 załączników | ostatnia dziś 15:25 | autorzy: 2"
  - liczby pogrubione, segmenty rozdzielone pionową kreską. Wyodrębnione z
  `NotatkiTab.vue` do osobnego pliku, bo ta sama treść renderuje się DWA
  razy w tym samym rodzicu (wiersz desktopowy w pasku górnym i drugi wiersz
  mobilny pod polem szukania, `md:hidden`/`hidden md:flex`) - jeden
  komponent zamiast duplikować pięć linijek znacznika i kluczy tłumaczeń w
  dwóch miejscach tego samego pliku.

  Bezstanowy: dostaje gotowe `{ notatki, zalaczniki, ostatnia, autorzy }` z
  `podsumowanieFeedu()` (`utils/notatki.js`) jako prop i tylko je formatuje.
  `ostatnia` (string ISO albo `null`) jest tu formatowane do postaci "dziś
  15:25" - `etykietaDnia()` zwraca "Dziś"/"Wczoraj" z wielkiej litery (nagłówki
  grup dni), ale w zdaniu "ostatnia ..." chcemy małej litery, stąd
  `pierwszaMala()`; dla dat starszych niż wczoraj `etykietaDnia()` i tak
  zwraca już małą literę (skrót dnia tygodnia, np. "pt., 25 wrz 2026"), więc
  `pierwszaMala()` jest tam bez efektu - jedna funkcja obsługuje oba
  przypadki bez rozgałęzienia.
-->
<template>
  <div class="flex flex-wrap items-center gap-2 text-sm text-ink-gray-6">
    <span>
      <span class="font-semibold text-ink-gray-9">{{ podsumowanie.notatki }}</span>
      {{ __('notatek') }}
    </span>
    <span class="h-3 w-px shrink-0 bg-outline-gray-2" aria-hidden="true" />
    <span>
      <span class="font-semibold text-ink-gray-9">{{ podsumowanie.zalaczniki }}</span>
      {{ __('załączników') }}
    </span>
    <template v-if="ostatniaTekst">
      <span class="h-3 w-px shrink-0 bg-outline-gray-2" aria-hidden="true" />
      <span>{{ __('ostatnia') }} {{ ostatniaTekst }}</span>
    </template>
    <span class="h-3 w-px shrink-0 bg-outline-gray-2" aria-hidden="true" />
    <span>
      {{ __('autorzy') }}: <span class="font-semibold text-ink-gray-9">{{ podsumowanie.autorzy }}</span>
    </span>
  </div>
</template>

<script setup>
import { etykietaDnia, godzinaZTekstu } from '@/utils/notatki'
import { computed } from 'vue'

const props = defineProps({
  // { notatki, zalaczniki, ostatnia (ISO albo null), autorzy } - kształt
  // zwracany przez `podsumowanieFeedu()`.
  podsumowanie: { type: Object, required: true },
})

function pierwszaMala(tekst) {
  return tekst ? tekst.charAt(0).toLowerCase() + tekst.slice(1) : ''
}

const ostatniaTekst = computed(() => {
  if (!props.podsumowanie.ostatnia) return ''
  const dzien = pierwszaMala(etykietaDnia(props.podsumowanie.ostatnia))
  const godzina = godzinaZTekstu(props.podsumowanie.ostatnia)
  return [dzien, godzina].filter(Boolean).join(' ')
})
</script>
