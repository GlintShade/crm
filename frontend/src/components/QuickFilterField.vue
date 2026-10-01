<template>
  <FormControl
    v-if="filter.fieldtype == 'Check'"
    v-model="filter.value"
    :label="filter.label"
    type="checkbox"
    @change.stop="updateFilter(filter, $event.target.checked)"
  />
  <QuickFilterCheckList
    v-else-if="jestWielokrotny"
    :label="filter.label"
    :fieldtype="typCheckList"
    :options="opcjeCheckList"
    :meLabel="etykietaMoje(doctype)"
    :modelValue="parsujWartoscWielokrotna(filter.value)"
    @update:modelValue="(wartosci) => updateFilter(filter, wartosci)"
  />
  <Link
    v-else-if="filter.fieldtype === 'Link'"
    :value="filter.value"
    :doctype="filter.options"
    :placeholder="filter.label"
    :meLabel="etykietaMoje(doctype)"
    :userScope="true"
    @change="(data) => updateFilter(filter, data)"
  />
  <component
    :is="filter.fieldtype === 'Date' ? DatePicker : DateTimePicker"
    v-else-if="['Date', 'Datetime'].includes(filter.fieldtype)"
    class="border-none"
    :value="filter.value"
    :placeholder="filter.label"
    @change="(v) => updateFilter(filter, v)"
  />
  <FormControl
    v-else
    v-model="filter.value"
    type="text"
    :placeholder="filter.label"
    @input.stop="debouncedFn(filter, $event.target.value)"
  />
</template>
<script setup>
import Link from '@/components/Controls/Link.vue'
import QuickFilterCheckList from '@/components/Controls/QuickFilterCheckList.vue'
import { FormControl, DatePicker, DateTimePicker, createResource } from 'frappe-ui'
import { useDebounceFn } from '@vueuse/core'
import { etykietaMoje } from '@/utils/etykietaMoje'
import { opcjeEtapu } from '@/utils/etapFiltr'
import { parsujWartoscWielokrotna } from '@/utils/filtrWielokrotny'
import { czyWielokrotnyFiltrSzybki } from '@/utils/filtrSzybki'
import { czyPoleTagow, opcjeTagow } from '@/utils/tagiProduktow'
import { statusesStore } from '@/stores/statuses'
import { computed, reactive, watch } from 'vue'

const props = defineProps({
  filter: { type: Object, required: true },
  // Doctype strony (Szanse/Klienci/Leady/...), NIE doctype pola filtra —
  // ten komponent sam nie wie, na jakiej liście stoi (patrz ViewControls.vue,
  // które ma props.doctype); potrzebny tylko do wyboru etykiety "@me".
  doctype: { type: String, default: '' },
  // Aktywne filtry listy (`list.params?.filters`, patrz ViewControls.vue) —
  // potrzebne wyłącznie dla filtra „Etap" (status), żeby zawęzić opcje do
  // procesu aktywnego filtra „Rodzaj umowy" (`custom_rodzaj_umowy`), patrz
  // utils/etapFiltr.js. Ten komponent stoi obok Filtra rozwijanego, więc
  // musi widzieć TE SAME filtry, żeby oba paski zawężały się identycznie.
  activeFilters: { type: Object, default: () => ({}) },
})

const filter = reactive(props.filter)

// Ten sam współdzielony fetch (cache klucz jak w Deal.vue/Filter.vue dla
// `volteo_pipeline_grupy`) — config nie zależy od konkretnej szansy.
const { dealStatuses } = statusesStore()
const grupyStatusow = createResource({
  url: 'crm.api.pipeline.volteo_pipeline_grupy',
  cache: ['volteo-pipeline-grupy'],
  auto: true,
})

function isKnownStatus(name) {
  return Boolean(dealStatuses.data?.some((s) => s.name === name))
}

const opcjeEtapuFiltra = computed(() =>
  opcjeEtapu(
    grupyStatusow.data,
    props.activeFilters?.custom_rodzaj_umowy,
    isKnownStatus,
    dealStatuses.data?.map((s) => s.name),
  ),
)

// Issue #127: Select i Link (poza User, patrz JSDoc czyWielokrotnyFiltrSzybki)
// dostają checkboxową listę wielokrotnego wyboru zamiast pojedynczego pola.
// Issue ops#150: pole "produktów leada" (tagów) dostaje ją też, mimo
// fieldtype === 'Data'. Owner remark #37 (2026-09-28): Etap (status) na
// CRM Deal też -- nie jest już wyjątkiem, patrz jestEtapSzansy niżej.
const jestWielokrotny = computed(() =>
  czyWielokrotnyFiltrSzybki(props.doctype, filter),
)

// Owner remark #37 (2026-09-28): pole „Etap" (status) na CRM Deal dostaje
// wielokrotny wybór przez checkboxy jak każdy inny Link, ale zostaje przy
// WŁASNEJ, zawężonej do aktywnego procesu liście opcji (opcjeEtapuFiltra,
// płaskiej albo pogrupowanej OZE/Czyste Powietrze/Inne) zamiast przy
// pełnym katalogu `CRM Deal Status` przez search_link.
const jestEtapSzansy = computed(
  () => props.doctype === 'CRM Deal' && filter.fieldname === 'status',
)

// Issue ops#150: QuickFilterCheckList w trybie "Select" (fieldtype !==
// 'Link') oczekuje `options` jako tablicy {label, value} (albo, dla Etapu,
// jako listy pogrupowanej {group, items} -- patrz
// grupyOpcjiFiltraSzybkiego w utils/filtrSzybki.js) -- dokładnie to, co
// `crm.api.doc.get_quick_filters` już zwraca dla prawdziwego Select. Dla
// Etapu na CRM Deal to opcjeEtapuFiltra (zawężona do procesu). Dla pola
// tagów `filter.options` to string złączony "\n" (ten sam format co dla
// Select w DB, dołożony przez `_dolacz_tagi_lead`), więc tutaj rozbijamy
// go przez `opcjeTagow` i mapujemy do tego samego kształtu -- bez
// duplikowania słownika w JS (opcje nadal pochodzą z serwera). Każde inne
// pole (Select prawdziwy, Link) dostaje `filter.options` bez zmian, jak
// dotychczas.
const opcjeCheckList = computed(() =>
  jestEtapSzansy.value
    ? opcjeEtapuFiltra.value
    : czyPoleTagow(filter)
      ? opcjeTagow(filter).map((token) => ({ label: token, value: token }))
      : filter.options,
)

// QuickFilterCheckList wybiera tryb Select/Link po `fieldtype`: Select
// zostaje w statycznej liście opcji (`options` przekazane wprost), Link
// pyta `frappe.desk.search.search_link` z `doctype` = wartość `options`.
// Etap na CRM Deal MA fieldtype 'Link' (options: 'CRM Deal Status'), ale
// tu wymuszamy 'Select', żeby zostać na statycznej, zawężonej do procesu
// liście -- tryb Link zignorowałby opcjeEtapuFiltra i przeszukałby cały
// katalog CRM Deal Status, gubiąc zawężenie do aktywnego procesu i jego
// kolejność.
const typCheckList = computed(() =>
  jestEtapSzansy.value ? 'Select' : filter.fieldtype,
)

const emit = defineEmits(['applyQuickFilter'])

watch(
  () => props.filter,
  (newFilter) => Object.assign(filter, newFilter),
  { deep: true },
)

const debouncedFn = useDebounceFn((f, value) => {
  emit('applyQuickFilter', f, value)
}, 500)

function updateFilter(f, value) {
  emit('applyQuickFilter', f, value)
}
</script>
