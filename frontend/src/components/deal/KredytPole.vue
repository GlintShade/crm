<!--
  Jedno pole formularza kredytowego (KredytTab.vue), ops#321. Wspólne
  renderowanie dla bloku wnioskodawcy, sekcji podstawowych i grup dochodu,
  z trzema poziomami stanu (wymagane / brakuje / błąd):
    - `stan === 'brak'`: niebieska kropka za etykietą i jasnoniebieskie
      obramowanie samego pola (nie etykiety). Pole puste to normalny stan
      wypełniania, nic czerwonego.
    - `stan === 'blad'`: czerwone obramowanie pola i komunikat pod nim (prop
      `error` FormControl).
    - `wymagane`: gwiazdka przy etykiecie (prop `required` FormControl).
  Kropka i obramowanie idą przez klasy na wrapperze (warianty `[&_...]`),
  nie przez slot etykiety, bo DatePicker nie przekazuje slotu `label` do
  swojego inputu: tak działają jednakowo dla text, select i date.
  Tokeny kolorów wyłącznie z presetu frappe-ui (tryb ciemny za darmo).
-->
<template>
  <div
    :class="['rounded', stan === 'brak' ? KLASY_BRAK : '', stan === 'blad' ? KLASY_BLAD : '']"
    :title="tytul"
    @focusout="onFocusOut"
  >
    <FormControl
      :type="f.type"
      :label="bezEtykiety ? undefined : f.label"
      :options="f.options"
      :inputmode="f.inputmode"
      :placeholder="f.placeholder || (f.type === 'date' ? 'DD.MM.RRRR' : undefined)"
      :format="f.type === 'date' ? 'DD.MM.YYYY' : undefined"
      :disabled="disabled"
      :required="wymagane"
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
    </FormControl>
  </div>
</template>

<script setup>
import { computed } from 'vue'
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
  wymagane: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  tytul: { type: String, default: '' },
  // Pole telefonu: mała ikona "Zadzwoń" w sufiksie, gdy wartość to numer.
  telefon: { type: Boolean, default: false },
  // Pomija etykietę (wspólna etykieta pary "od / do" jest w rodzicu).
  bezEtykiety: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'input', 'blur'])

// Literały w całości, bez składania z kawałków: Tailwind skanuje źródło
// tekstowo i nie zobaczy klas zbudowanych z interpolacji. Kropka za
// etykietą ma ten sam kształt co KROPKA_BRAK_KLASY w KredytTab.vue
// (bg-current + text-ink-blue-6).
const KLASY_BRAK =
  '[&_[data-slot=label]]:after:ml-1.5 [&_[data-slot=label]]:after:inline-block [&_[data-slot=label]]:after:size-1.5 [&_[data-slot=label]]:after:rounded-full [&_[data-slot=label]]:after:bg-current [&_[data-slot=label]]:after:align-middle [&_[data-slot=label]]:after:text-ink-blue-6 [&_[data-slot=control]:not(:focus)]:border-outline-blue-3 [&_[data-slot=trigger]:not(:focus)]:border-outline-blue-3'
const KLASY_BLAD = '[&_[aria-invalid=true]]:border-outline-red-3'

const przyciskTelefonu = computed(
  () => props.telefon && czyTelefon(String(props.modelValue ?? '')),
)
const maSufiks = computed(
  () => przyciskTelefonu.value || props.f.type === 'date' || props.f.inputmode === 'decimal',
)

// Błąd formatu i "dotknięte" liczymy po wyjściu z pola. focusout bąbelkuje
// z dowolnego kontrolera (input, trigger selecta, input daty), a ruch
// fokusu wewnątrz tego samego pola nie liczy się jako wyjście.
function onFocusOut(e) {
  if (e.currentTarget.contains(e.relatedTarget)) return
  emit('blur')
}
</script>
