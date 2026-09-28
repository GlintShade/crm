<!--
  Pasek narzędzi feedu "Notatki" (issue ops#201, uwaga 40): lista
  wielokrotnego wyboru źródeł (z licznikami) plus dropdown sortowania, w
  jednym komponencie - kontrakt issue daje obu kontrolkom wspólne props/
  emity (`modelValue`/`update:modelValue` dla zaznaczonych źródeł,
  `kierunek`/`update:kierunek` dla sortu).

  Wzorowane stylistycznie na `Controls/QuickFilterCheckList.vue` (Popover +
  Checkbox, przycisk-chip z chevronem), ale NIE reużywa go wprost: ten
  komponent nie ma opcji ani grupowanych, ani z zapytania (Link) - stały,
  krótki zestaw źródeł z licznikami wystarcza na zwykłą listę checkboxów
  bez wyszukiwarki. Reużycie QuickFilterCheckList wymagałoby udawania pola
  Select z opcjami `{label, value}` tylko po to, żeby dostać z powrotem to
  samo UI - prościej i czytelniej zbudować własny, mniejszy komponent.

  "Wszystkie" zaznacza WSZYSTKIE źródła z `zrodla` (nie tylko te z liczbą >
  0) - lista ma pokazywać wszystkie możliwe źródła niezależnie od tego, czy
  akurat mają jakieś wpisy (patrz `crm.volteo_notatki.zbuduj_zrodla`).
  "Wyczyść" zaznacza pustą listę - `filtrujFeed([], [])` w utils/notatki.js
  wtedy świadomie zwraca pusty wynik, nie "pokaż wszystko".
-->
<template>
  <div class="flex flex-wrap items-center gap-2">
    <Popover placement="bottom-start">
      <template #target="{ togglePopover }">
        <button
          type="button"
          class="relative flex h-7 items-center gap-1 rounded border border-outline-gray-2 bg-surface-gray-2 px-2 py-1 text-base text-ink-gray-7 transition-colors hover:border-outline-elevation-2 hover:bg-surface-gray-3"
          @click="togglePopover()"
        >
          <span>{{ etykietaPrzycisku }}</span>
          <FeatherIcon name="chevron-down" class="h-4 w-4 text-ink-gray-5" />
        </button>
      </template>
      <template #body>
        <div
          class="my-1 w-64 rounded-lg bg-surface-elevation-2 p-1 shadow-2xl ring-1 ring-black ring-opacity-5 focus:outline-none"
        >
          <div class="max-h-72 overflow-y-auto">
            <div
              v-for="zrodlo in zrodla"
              :key="zrodlo.klucz"
              class="flex items-center justify-between gap-2 rounded px-2 py-1 hover:bg-surface-gray-2"
            >
              <Checkbox
                :modelValue="zaznaczoneSet.has(zrodlo.klucz)"
                :label="zrodlo.etykieta"
                @update:modelValue="(zaznaczona) => przelacz(zrodlo.klucz, zaznaczona)"
              />
              <span class="shrink-0 text-xs text-ink-gray-4">{{ zrodlo.liczba }}</span>
            </div>
            <div v-if="!zrodla.length" class="px-2 py-1.5 text-sm text-ink-gray-4">
              {{ __('Brak źródeł.') }}
            </div>
          </div>
          <div class="mt-1 flex gap-1 border-t pt-1">
            <Button
              variant="ghost"
              class="w-1/2 justify-center"
              :label="__('Wszystkie')"
              @click="zaznaczWszystkie"
            />
            <Button
              variant="ghost"
              class="w-1/2 justify-center"
              :label="__('Wyczyść')"
              @click="wyczysc"
            />
          </div>
        </div>
      </template>
    </Popover>

    <Dropdown :options="opcjeSortu" placement="bottom-end">
      <template #default="{ open }">
        <Button
          variant="ghost"
          :label="etykietaSortu"
          :iconRight="open ? 'chevron-up' : 'chevron-down'"
        />
      </template>
    </Dropdown>
  </div>
</template>

<script setup>
import { KIERUNKI_SORTU } from '@/utils/notatki'
import { Button, Checkbox, Dropdown, FeatherIcon, Popover } from 'frappe-ui'
import { computed } from 'vue'

const props = defineProps({
  // [{ klucz, etykieta, liczba }] - kształt `crm.api.notatki.feed().zrodla`.
  zrodla: { type: Array, default: () => [] },
  // Lista zaznaczonych kluczy źródeł (podzbiór `zrodla.map(z => z.klucz)`).
  modelValue: { type: Array, default: () => [] },
  kierunek: { type: String, default: KIERUNKI_SORTU.NAJNOWSZE },
})

const emit = defineEmits(['update:modelValue', 'update:kierunek'])

const zaznaczoneSet = computed(() => new Set(props.modelValue))

const etykietaPrzycisku = computed(() =>
  __('Źródła ({0}/{1})', [zaznaczoneSet.value.size, props.zrodla.length]),
)

function przelacz(klucz, zaznaczona) {
  const nastepny = new Set(zaznaczoneSet.value)
  if (zaznaczona) {
    nastepny.add(klucz)
  } else {
    nastepny.delete(klucz)
  }
  // Kolejność zaznaczonych kluczy zawsze zgodna z kolejnością `zrodla`
  // (czyli `ZRODLA_FEEDU` z backendu), niezależnie od kolejności kliknięć.
  emit(
    'update:modelValue',
    props.zrodla.map((z) => z.klucz).filter((klucz) => nastepny.has(klucz)),
  )
}

function zaznaczWszystkie() {
  emit('update:modelValue', props.zrodla.map((z) => z.klucz))
}

function wyczysc() {
  emit('update:modelValue', [])
}

const opcjeSortu = computed(() => [
  {
    label: __('Od najnowszych'),
    onClick: () => emit('update:kierunek', KIERUNKI_SORTU.NAJNOWSZE),
  },
  {
    label: __('Od najstarszych'),
    onClick: () => emit('update:kierunek', KIERUNKI_SORTU.NAJSTARSZE),
  },
])

const etykietaSortu = computed(() =>
  props.kierunek === KIERUNKI_SORTU.NAJSTARSZE ? __('Od najstarszych') : __('Od najnowszych'),
)
</script>
