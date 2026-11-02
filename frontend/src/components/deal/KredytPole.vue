<!--
  Jedno pole formularza kredytowego (KredytTab.vue), ops#321. Wspólne
  renderowanie dla bloku wnioskodawcy, sekcji podstawowych i grup dochodu,
  z trzema poziomami stanu (wymagane / brakuje / błąd):
    - `stan === 'brak'`: niebieska kropka za etykietą i jasnoniebieskie
      obramowanie samego pola (nie etykiety). Pole puste to normalny stan
      wypełniania, nic czerwonego.
    - `stan === 'blad'`: czerwone obramowanie pola i komunikat pod nim (prop
      `error` FormControl).
    - `znacznik`: 'gwiazdka' (szara gwiazdka przy wymaganym polu, prop
      `required` FormControl z przemalowaniem na token szary: czerwień jest
      zarezerwowana dla błędów) albo 'opcjonalne' (dopisek "(opcjonalnie)"
      w etykiecie).
    - `wymagany`: tylko `aria-required` dla dostępności.
  Układ: komórka jest kolumną flex, zawartość (etykieta, input,
  komunikat) jest dosunięta do dołu komórki, więc etykieta wisi tuż nad
  inputem, a inputy w jednym wierszu siatki mają wspólną górną krawędź
  niezależnie od zawinięcia etykiety (najwyższa etykieta wyznacza wiersz).
  Kropka i obramowanie idą przez klasy na wrapperze (warianty `[&_...]`),
  nie przez slot etykiety, bo DatePicker nie przekazuje slotu `label` do
  swojego inputu: tak działają jednakowo dla text, select i date.
  Tokeny kolorów wyłącznie z presetu frappe-ui (tryb ciemny za darmo).
-->
<template>
  <div
    :class="[
      'flex h-full flex-col justify-end rounded',
      bezEtykiety ? KLASY_PARA : KLASY_UKLAD,
      znacznik === 'gwiazdka' ? KLASY_GWIAZDKA : '',
      stan === 'brak' ? KLASY_BRAK + ' kredyt-pole-brak' : '',
      stan === 'blad' ? KLASY_BLAD : '',
    ]"
    :title="tytul"
    @focusout="onFocusOut"
  >
    <FormControl
      :type="f.type"
      :label="bezEtykiety ? undefined : etykieta"
      :options="f.options"
      :inputmode="f.inputmode"
      :placeholder="placeholder"
      :format="f.type === 'date' ? 'DD.MM.YYYY' : undefined"
      :disabled="disabled"
      :required="znacznik === 'gwiazdka'"
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

const etykieta = computed(() =>
  props.znacznik === 'opcjonalne' ? `${props.f.label} ${__('(opcjonalnie)')}` : props.f.label,
)
const placeholder = computed(() => {
  if (props.f.placeholder) return props.f.placeholder
  if (props.f.type === 'date') return 'DD.MM.RRRR'
  if (props.f.type === 'select') return __('Wybierz')
  return undefined
})

// Literały w całości, bez składania z kawałków: Tailwind skanuje źródło
// tekstowo i nie zobaczy klas zbudowanych z interpolacji.
// Kropka to znak (nbsp + ●) w ::after (treść w <style> poniżej), więc
// zawija się razem z ostatnim słowem etykiety i nigdy nie ląduje sama.
const KLASY_UKLAD =
  '[&>div]:flex [&>div]:flex-1 [&>div]:flex-col [&>div]:justify-end [&_[data-slot=label]]:block'
// Para dat "od / do" w jednej komórce (~95 px na pole): bez ikony kalendarza,
// z mniejszym krojem i wcięciem, żeby pełne "DD.MM.RRRR" się mieściło
// (10 znaków w 14 px to ok. 78 px, plus 2 x 4 px wcięcia i ramka).
const KLASY_PARA = '[&_[data-slot=control]]:!px-1 [&_[data-slot=control]]:!text-sm'
// Natywna gwiazdka frappe-ui jest czerwona (text-ink-red-6): w etykiecie
// przemalowana na szary token, czerwień zostaje dla błędów.
const KLASY_GWIAZDKA = '[&_[data-slot=label]_.text-ink-red-6]:text-ink-gray-5'
const KLASY_BRAK =
  '[&_[data-slot=label]]:after:text-[0.6em] [&_[data-slot=label]]:after:align-middle [&_[data-slot=label]]:after:text-ink-blue-6 [&_[data-slot=control]:not(:focus)]:border-outline-blue-3 [&_[data-slot=trigger]:not(:focus)]:border-outline-blue-3'
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

<style scoped>
.kredyt-pole-brak :deep([data-slot='label'])::after {
  /* Przed pseudo-elementem zostaje zwykła spacja z szablonu etykiety, która
     jest miejscem łamania; WORD JOINER (U+2060) zabrania łamania przed
     kropką, więc kropka zawsze zostaje z ostatnim słowem. */
  content: '\2060\25cf';
}
</style>
