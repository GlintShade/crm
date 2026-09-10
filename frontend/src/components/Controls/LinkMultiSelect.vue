<template>
  <MultiSelect
    v-model="wartosc"
    :options="opcje"
    :loading="zasob.loading"
    :placeholder="placeholder || __('Select options')"
    :empty-text="__('No results')"
    class="w-full"
    @update:query="naZmianeZapytania"
    @update:open="naOtwarcie"
  />
</template>

<script setup>
// Kontrolka wielokrotnego wyboru dla operatorów "jest jednym z" / "nie jest
// jednym z" (in / not in) na polach typu Link w rozwijanym filtrze
// (Filter.vue, issue #103). Odpowiednik Link.vue (pojedynczy wybór przez
// frappe.desk.search.search_link + Autocomplete), tylko na frappe-ui
// MultiSelect i z modelValue = tablica stringów (dokładnie ten kształt,
// jakiego oczekuje transformIn/parseFilters w Filter.vue dla in/not in —
// żadnej zmiany serializacji filtra).
//
// Świadomie węższe niż Link.vue: bez obsługi "@me" i bez `userScope`
// (zawężenia do poddrzewa Sales Hierarchy) — issue #103 explicite nie
// wymaga tego dla operatora in/not in. Gdyby to było kiedyś potrzebne,
// przenieść odpowiedni fragment z Link.vue tutaj, a nie odwrotnie
// (LinkMultiSelect ma zostać prostszy z założenia).
import { scalOpcjeZZaznaczonymi } from '@/utils/filtrWielokrotny'
import { MultiSelect, createResource } from 'frappe-ui'
import { computed, onMounted, ref, watch } from 'vue'

const props = defineProps({
  doctype: { type: String, required: true },
  placeholder: { type: String, default: '' },
})

const model = defineModel({ type: Array, default: () => [] })

const wartosc = computed({
  get: () => model.value || [],
  set: (v) => {
    model.value = v || []
  },
})

// Każda etykieta kiedykolwiek zwrócona przez search_link zostaje tutaj, żeby
// zaznaczone "chipy" pozostały czytelne (prawdziwa etykieta, nie goły
// value) nawet gdy kolejne zapytanie zawęzi wyniki i akurat pominie już
// wybraną wartość — ten sam wzorzec co przykład "Async Options" w
// dokumentacji frappe-ui MultiSelect.
const znaneEtykiety = ref(new Map())

const zasob = createResource({
  url: 'frappe.desk.search.search_link',
  method: 'POST',
  params: { txt: '', doctype: props.doctype, filters: {} },
  transform: (data) => {
    const wynik = (data || []).map((option) => ({
      label: option.label || option.value,
      value: option.value,
      description: stripHtml(option.description),
    }))
    for (const opcja of wynik) znaneEtykiety.value.set(opcja.value, opcja)
    return wynik
  },
})

// Lista pokazywana w popoverze: wyniki ostatniego zapytania, plus każda
// aktualnie zaznaczona wartość, której w tych wynikach nie ma — najpierw z
// `znaneEtykiety` (prawdziwa etykieta z wcześniejszego zapytania), a gdy i
// tam jej nie ma (np. wartość z wczytanego zapisanego widoku, sprzed
// jakiegokolwiek zapytania w tej sesji), placeholder `{label: value, value}`
// ze `scalOpcjeZZaznaczonymi`.
const opcje = computed(() => {
  const wyniki = zasob.data || []
  const brakujaceZnane = (wartosc.value || [])
    .filter((v) => !wyniki.some((o) => o.value === v))
    .map((v) => znaneEtykiety.value.get(v))
    .filter(Boolean)
  return scalOpcjeZZaznaczonymi([...wyniki, ...brakujaceZnane], wartosc.value)
})

function stripHtml(html) {
  if (!html) return ''
  return html
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

let ostatnieZapytanie = null

function wyszukaj(txt) {
  zasob.update({ params: { txt, doctype: props.doctype, filters: {} } })
  return zasob.fetch()
}

let debounceTimer = null
function naZmianeZapytania(txt) {
  ostatnieZapytanie = txt || ''
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => wyszukaj(ostatnieZapytanie), 300)
}

function naOtwarcie(otwarty) {
  if (otwarty && !zasob.data && !zasob.loading) wyszukaj('')
}

watch(
  () => props.doctype,
  () => wyszukaj(ostatnieZapytanie || ''),
)

onMounted(() => {
  if (!zasob.data && !zasob.loading) wyszukaj('')
})
</script>
