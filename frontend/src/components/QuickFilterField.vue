<template>
  <FormControl
    v-if="filter.fieldtype == 'Check'"
    v-model="filter.value"
    :label="filter.label"
    type="checkbox"
    @change.stop="updateFilter(filter, $event.target.checked)"
  />
  <FormControl
    v-else-if="filter.fieldtype === 'Select'"
    v-model="filter.value"
    class="form-control cursor-pointer [&_select]:cursor-pointer"
    type="select"
    :options="filter.options"
    :placeholder="filter.label"
    @update:modelValue="updateFilter(filter, $event)"
  />
  <Autocomplete
    v-else-if="doctype === 'CRM Deal' && filter.fieldname === 'status'"
    :value="filter.value"
    :options="opcjeEtapuFiltra"
    :placeholder="filter.label"
    @change="(o) => updateFilter(filter, o?.value ?? '')"
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
import Autocomplete from '@/components/frappe-ui/Autocomplete.vue'
import { FormControl, DatePicker, DateTimePicker, createResource } from 'frappe-ui'
import { useDebounceFn } from '@vueuse/core'
import { etykietaMoje } from '@/utils/etykietaMoje'
import { opcjeEtapu } from '@/utils/etapFiltr'
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
