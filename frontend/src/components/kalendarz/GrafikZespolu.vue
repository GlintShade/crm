<!--
  Podgląd grafiku całego zespołu (b82, decyzja 2): handlowcy w wierszach, dni
  w kolumnach, w komórce pasek osi 8 do 22 z ciemnymi odcinkami i opis dnia.
  Tylko do oglądania; grafik zmienia się na karcie handlowca ("Grafik").
-->
<template>
  <div
    class="rounded-xl border border-outline-gray-2 bg-surface-base p-3.5 text-xs"
    data-testid="kalendarz-grafik-zespolu"
  >
    <div class="flex items-center gap-2.5">
      <div class="min-w-0 flex-1">
        <div class="text-sm font-semibold text-ink-gray-9">
          {{ __('Grafik zespołu') }}
        </div>
        <div class="text-xs text-ink-gray-5">
          {{ etykieta }}, {{ __('tylko podgląd') }}
        </div>
      </div>
      <Button
        variant="ghost"
        :tooltip="__('Zamknij')"
        @click="$emit('zamknij')"
      >
        <template #icon><FeatherIcon name="x" class="h-4 w-4" /></template>
      </Button>
    </div>
    <div class="mt-2.5 overflow-x-auto">
      <table class="w-full border-separate border-spacing-0">
        <thead>
          <tr>
            <th
              class="border-b border-outline-gray-2 px-1.5 py-1.5 text-left font-medium text-ink-gray-5"
            >
              {{ __('Handlowiec') }}
            </th>
            <th
              v-for="dzien in dni"
              :key="dzien"
              class="whitespace-nowrap border-b border-outline-gray-2 px-1 py-1.5 text-left font-medium"
              :class="
                czyDzis(dzien, teraz)
                  ? 'font-semibold text-ink-blue-8'
                  : 'text-ink-gray-5'
              "
            >
              {{ skrotDnia(dzien) }} {{ numerDnia(dzien) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(h, i) in handlowcy" :key="h.user">
            <td class="border-b border-outline-gray-1 px-1.5 py-1">
              <div class="flex min-w-40 items-center gap-2">
                <span
                  class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold text-white"
                  :class="kolorHandlowca(indeksKoloru(h.user, i)).pelny"
                >
                  {{ inicjaly(h.full_name) }}
                </span>
                <span class="truncate font-semibold text-ink-gray-9">{{
                  h.full_name
                }}</span>
              </div>
            </td>
            <td
              v-for="dzien in dni"
              :key="dzien"
              class="border-b border-outline-gray-1 px-1 py-1"
            >
              <div
                class="min-w-[84px] rounded-lg border border-outline-gray-2 p-1"
              >
                <div
                  class="relative h-2.5 overflow-hidden rounded bg-surface-gray-1"
                >
                  <span
                    v-for="[a, b] in odcinki(h.user, dzien)"
                    :key="a"
                    class="kalendarz-niedostepny absolute bottom-0 top-0 rounded-sm"
                    :style="stylOdcinkaPoziomo(a, b, OS_OD, OS_DO)"
                  ></span>
                </div>
                <span
                  class="mt-0.5 block whitespace-nowrap tabular-nums"
                  :class="
                    okna(h.user, dzien) === null
                      ? 'text-ink-amber-8'
                      : 'text-ink-gray-7'
                  "
                >
                  {{ opisKrotki(okna(h.user, dzien)) }}
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="mozeEdytowac" class="mt-2.5 text-ink-gray-5">
      {{ __('Grafik zmienisz na karcie handlowca, przycisk "Grafik".') }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Button, FeatherIcon } from 'frappe-ui'
import {
  OS_DO,
  OS_OD,
  czyDzis,
  etykietaZakresu,
  inicjaly,
  kolorHandlowca,
  numerDnia,
  odcinkiNiedostepne,
  oknaDnia,
  opisOkien,
  skrotDnia,
  stylOdcinkaPoziomo,
} from '@/utils/kalendarz'

const props = defineProps({
  handlowcy: { type: Array, required: true },
  dostepnosc: { type: Object, default: null },
  dni: { type: Array, required: true },
  teraz: { type: Date, default: () => new Date() },
  mozeEdytowac: { type: Boolean, default: false },
  // Indeks koloru handlowca (ten sam co na kartach tablicy).
  indeksKoloru: { type: Function, default: (_user, i) => i },
})

defineEmits(['zamknij'])

const etykieta = computed(() =>
  props.dni.length
    ? etykietaZakresu(props.dni[0], props.dni[props.dni.length - 1])
    : '',
)

function okna(user, dzien) {
  return oknaDnia(props.dostepnosc?.[user], dzien)
}

function odcinki(user, dzien) {
  return odcinkiNiedostepne(okna(user, dzien), OS_OD, OS_DO)
}

function opisKrotki(o) {
  const tekst = opisOkien(o)
  return tekst.charAt(0).toUpperCase() + tekst.slice(1)
}
</script>
