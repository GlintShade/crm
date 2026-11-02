<!--
  Jedno pole formularza kredytowego (KredytTab.vue), ops#321. Wspólne
  renderowanie dla bloku wnioskodawcy, sekcji podstawowych i grup dochodu,
  z trzema poziomami stanu (wymagane / brakuje / błąd):
    - `stan === 'brak'`: niebieska kropka za etykietą i jasnoniebieskie
      obramowanie samego pola (nie etykiety). Pole puste to normalny stan
      wypełniania, nic czerwonego.
    - `stan === 'blad'`: czerwone obramowanie pola i komunikat pod nim (prop
      `error` FormControl).
    - `znacznik`: 'gwiazdka' (szara gwiazdka przy wymaganym polu, czerwień
      jest zarezerwowana dla błędów) albo 'opcjonalne' (szary dopisek
      "(opcjonalnie)").
    - `wymagany`: tylko `aria-required` dla dostępności.
  Etykieta jest własna (`<label for>` z klasami jak InputLabel frappe-ui),
  nie etykieta FormControl: ostatnie słowo, dopisek, gwiazdka i kropka są
  w jednym span `whitespace-nowrap`, więc kropka nigdy nie zawija się sama.
  Kontrolka dostaje stabilne `id` (Vue useId), etykieta wskazuje je przez `for`.
  Układ: komórka jest kolumną flex dosuniętą do dołu, więc etykieta wisi tuż
  nad inputem (6 px), a inputy w wierszu siatki mają wspólną górną krawędź
  (najwyższa etykieta wyznacza wiersz).
  Tokeny kolorów wyłącznie z presetu frappe-ui (tryb ciemny za darmo).
-->
<template>
  <div
    :class="[
      'flex h-full flex-col justify-end rounded',
      bezEtykiety ? KLASY_PARA : '',
      stan === 'brak' ? KLASY_BRAK : '',
      stan === 'blad' ? KLASY_BLAD : '',
    ]"
    :title="tytul"
    @focusout="onFocusOut"
  >
    <!-- Własna etykieta zamiast etykiety frappe-ui: ostatnie słowo, dopisek,
         gwiazdka i kropka są w jednym nowrap, więc kropka nigdy nie zostaje
         sama w nowej linii. Klasy jak w frappe-ui InputLabel.vue. -->
    <label
      v-if="!bezEtykiety"
      :for="inputId"
      data-slot="label"
      class="mb-1.5 block text-base text-ink-gray-5"
    >
      {{ etykietaPoczatek }}
      <span class="whitespace-nowrap">{{ etykietaKoniec }}<span
          v-if="znacznik === 'opcjonalne'"
          class="text-ink-gray-5"
        >&nbsp;{{ __('(opcjonalnie)') }}</span><span
          v-if="znacznik === 'gwiazdka'"
          class="select-none text-ink-gray-5"
          aria-hidden="true"
        >&nbsp;*</span><span
          v-if="stan === 'brak'"
          data-testid="kropka-brak"
          class="select-none align-middle text-[0.6em] text-ink-blue-6"
          aria-hidden="true"
        >&nbsp;●</span></span>
    </label>
    <FormControl
      :id="inputId"
      :type="f.type"
      :options="f.options"
      :inputmode="f.inputmode"
      :placeholder="placeholder"
      :format="f.type === 'date' ? 'DD.MM.YYYY' : undefined"
      :disabled="disabled"
      :aria-required="wymagany ? 'true' : undefined"
      :error="stan === 'blad' ? komunikat : undefined"
      :model-value="modelValue"
      @update:model-value="emit('update:modelValue', $event)"
      @input="emit('input', $event)"
    >
      <template v-if="maSufiks" #suffix="slotProps">
        <Button
          v-if="przyciskTelefonu"
          variant="ghost"
          icon="lucide-phone"
          class="!size-5"
          :tooltip="__('Zadzwoń')"
          :link="telHref(modelValue)"
        />
        <LucideCalendar
          v-else-if="f.type === 'date'"
          class="h-4 w-4 cursor-pointer"
          @mousedown.prevent="slotProps?.togglePopover?.()"
        />
        <span v-else class="select-none text-sm text-ink-gray-5">zł</span>
      </template>
      <!-- Para dat: pusty sufiks wyłącza domyślną strzałkę frappe-ui (picker
           nadal otwiera się kliknięciem w input). -->
      <template v-else-if="bezEtykiety && f.type === 'date'" #suffix>
        <span />
      </template>
    </FormControl>
  </div>
</template>

<script setup>
import { computed, useId } from 'vue'
import { Button, FormControl } from 'frappe-ui'
import LucideCalendar from '~icons/lucide/calendar'
import { telHref, czyTelefon } from '@/utils/telefon'

const props = defineProps({
  // { fieldname, label, type, options?, inputmode?, placeholder? }
  f: { type: Object, required: true },
  modelValue: { type: [String, Number], default: '' },
  // '' | 'brak' | 'blad' (kredytForm.js stanPola)
  stan: { type: String, default: '' },
  komunikat: { type: String, default: '' },
  // '' | 'gwiazdka' | 'opcjonalne' (kredytForm.js znacznikPola)
  znacznik: { type: String, default: '' },
  // Pole wymagane (aria-required), niezależnie od widocznego znacznika.
  wymagany: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  tytul: { type: String, default: '' },
  // Pole telefonu: mała ikona "Zadzwoń" w sufiksie, gdy wartość to numer.
  telefon: { type: Boolean, default: false },
  // Pomija etykietę (wspólna etykieta pary "od / do" jest w rodzicu).
  bezEtykiety: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'input', 'blur'])

// Stabilne id kontrolki (label for=, czytniki ekranu). Vue 3.5 useId.
const inputId = `kredyt-${useId()}`
const slowa = computed(() => String(props.f.label || '').trim().split(/\s+/))
const etykietaPoczatek = computed(() => slowa.value.slice(0, -1).join(' '))
const etykietaKoniec = computed(() => slowa.value[slowa.value.length - 1] || '')
const placeholder = computed(() => {
  if (props.f.placeholder) return props.f.placeholder
  if (props.f.type === 'date') return 'DD.MM.RRRR'
  if (props.f.type === 'select') return __('Wybierz')
  return undefined
})

// Literały w całości, bez składania z kawałków: Tailwind skanuje źródło
// tekstowo i nie zobaczy klas zbudowanych z interpolacji.
// Para dat "od / do" w jednej komórce (~95 px na pole): bez ikony kalendarza,
// z mniejszym krojem i wcięciem, żeby pełne "DD.MM.RRRR" się mieściło
// (10 znaków w 14 px to ok. 78 px, plus 2 x 4 px wcięcia i ramka).
const KLASY_PARA = '[&_[data-slot=control]]:!px-1 [&_[data-slot=control]]:!text-sm'
const KLASY_BRAK =
  '[&_[data-slot=control]:not(:focus)]:border-outline-blue-3 [&_[data-slot=trigger]:not(:focus)]:border-outline-blue-3'
const KLASY_BLAD = '[&_[aria-invalid=true]]:border-outline-red-3'

const przyciskTelefonu = computed(
  () => props.telefon && czyTelefon(String(props.modelValue ?? '')),
)
const maSufiks = computed(
  () =>
    przyciskTelefonu.value ||
    (props.f.type === 'date' && !props.bezEtykiety) ||
    props.f.inputmode === 'decimal',
)

// Błąd formatu i "dotknięte" liczymy po wyjściu z pola. focusout bąbelkuje
// z dowolnego kontrolera (input, trigger selecta, input daty), a ruch
// fokusu wewnątrz tego samego pola nie liczy się jako wyjście.
function onFocusOut(e) {
  if (e.currentTarget.contains(e.relatedTarget)) return
  emit('blur')
}
</script>
