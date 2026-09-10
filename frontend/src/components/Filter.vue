<template>
  <Popover placement="bottom-end">
    <template #target="{ togglePopover, close }">
      <div class="flex items-center">
        <Button
          :label="__('Filter')"
          :class="liczbaWarunkow ? 'rounded-r-none' : ''"
          :iconLeft="FilterIcon"
          @click="togglePopover"
        >
          <template v-if="liczbaWarunkow" #suffix>
            <div
              class="flex h-5 w-5 items-center justify-center rounded-[5px] bg-surface-base pt-px text-xs-medium text-ink-gray-8 shadow-sm"
            >
              {{ liczbaWarunkow }}
            </div>
          </template>
        </Button>
        <Button
          v-if="liczbaWarunkow"
          :tooltip="__('Clear All Filters')"
          class="rounded-l-none border-l"
          icon="lucide-x"
          @click.stop="clearfilter(close)"
        />
      </div>
    </template>
    <template #body="{ close }">
      <div
        class="my-2 min-w-40 rounded-lg bg-surface-elevation-2 shadow-2xl ring-1 ring-black ring-opacity-5 focus:outline-none"
      >
        <div class="min-w-72 p-2 sm:min-w-[400px]">
          <template v-if="filters?.size">
            <div
              v-for="(f, i) in filters"
              id="filter-list"
              :key="i"
              class="mb-4 sm:mb-3"
            >
              <div v-if="isMobileView" class="flex flex-col gap-2">
                <div class="-mb-2 flex w-full items-center justify-between">
                  <div class="text-base text-ink-gray-5">
                    {{ i == 0 ? __('Where') : __('And') }}
                  </div>
                  <Button
                    class="flex"
                    variant="ghost"
                    icon="lucide-x"
                    @click="removeFilter(i)"
                  />
                </div>
                <div id="fieldname" class="w-full">
                  <Autocomplete
                    :value="f.field.fieldname"
                    :options="filterableFields.data"
                    :placeholder="__('First Name')"
                    @change="(e) => updateFilter(e, i)"
                  />
                </div>
                <div id="operator">
                  <FormControl
                    v-model="f.operator"
                    type="select"
                    :options="
                      getOperators(f.field.fieldtype, f.field.fieldname)
                    "
                    :placeholder="__('Equals')"
                    @update:modelValue="() => updateOperator(f)"
                  />
                </div>
                <div id="value" class="w-full">
                  <div
                    v-if="czyPrzyciskDzis(f) && czyDzis(f)"
                    class="flex h-7 w-full items-center justify-between rounded border border-outline-gray-2 px-2 text-sm text-ink-gray-8"
                  >
                    <span>{{ __('Today') }}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      icon="lucide-x"
                      @click="wyczyscDzis(f)"
                    />
                  </div>
                  <div v-else class="flex items-center gap-1">
                    <component
                      :is="getValueControl(f)"
                      v-model="f.value"
                      :placeholder="placeholder(f)"
                      class="flex-1"
                      @change="(v) => updateValue(v, f)"
                    />
                    <Button
                      v-if="czyPrzyciskDzis(f)"
                      variant="ghost"
                      size="sm"
                      :label="__('Today')"
                      @click="ustawDzis(f)"
                    />
                  </div>
                </div>
              </div>
              <div v-else class="flex items-center justify-between gap-2">
                <div class="flex items-center gap-2">
                  <div class="w-13 pl-2 text-end text-base text-ink-gray-5">
                    {{ i == 0 ? __('Where') : __('And') }}
                  </div>
                  <div id="fieldname" class="!min-w-[140px]">
                    <Autocomplete
                      :value="f.field.fieldname"
                      :options="filterableFields.data"
                      :placeholder="__('First Name')"
                      @change="(e) => updateFilter(e, i)"
                    />
                  </div>
                  <div id="operator">
                    <FormControl
                      v-model="f.operator"
                      type="select"
                      :options="
                        getOperators(f.field.fieldtype, f.field.fieldname)
                      "
                      :placeholder="__('Equals')"
                      @update:modelValue="() => updateOperator(f)"
                    />
                  </div>
                  <div id="value" class="!min-w-[140px]">
                    <div
                      v-if="czyPrzyciskDzis(f) && czyDzis(f)"
                      class="flex h-7 items-center justify-between gap-1 rounded border border-outline-gray-2 px-2 text-sm text-ink-gray-8"
                    >
                      <span>{{ __('Today') }}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        icon="lucide-x"
                        @click="wyczyscDzis(f)"
                      />
                    </div>
                    <div v-else class="flex items-center gap-1">
                      <component
                        :is="getValueControl(f)"
                        v-model="f.value"
                        :placeholder="placeholder(f)"
                        class="flex-1"
                        @change="(v) => updateValue(v, f)"
                      />
                      <Button
                        v-if="czyPrzyciskDzis(f)"
                        variant="ghost"
                        size="sm"
                        :label="__('Today')"
                        @click="ustawDzis(f)"
                      />
                    </div>
                  </div>
                </div>
                <Button
                  class="flex"
                  variant="ghost"
                  icon="lucide-x"
                  @click="removeFilter(i)"
                />
              </div>
            </div>
          </template>
          <div
            v-else-if="!grupy.length"
            class="mb-3 flex h-7 items-center px-3 text-sm text-ink-gray-5"
          >
            {{ __('Empty - Choose a field to filter by') }}
          </div>
          <div class="flex items-center justify-between gap-2">
            <Autocomplete
              value=""
              :options="availableFilters"
              :placeholder="__('First Name')"
              @change="(e) => setfilter(e)"
            >
              <template #target="{ togglePopover }">
                <Button
                  class="!text-ink-gray-5"
                  variant="ghost"
                  :label="__('Add Filter')"
                  iconLeft="plus"
                  @click="togglePopover()"
                />
              </template>
            </Autocomplete>
            <Button
              v-if="liczbaWarunkow"
              class="!text-ink-gray-5"
              variant="ghost"
              :label="__('Clear All Filters')"
              @click="clearfilter(close)"
            />
          </div>
          <!-- Issue #129: grupy filtrów ORAZ/ALBO. Sekcja pod listą
          warunków wspólnych powyżej -- każda grupa to ramka z własną
          listą warunków (ten sam kontrolki co warunki wspólne: pole,
          operator, wartość, przycisk "Dziś" na datach), oddzielona od
          kolejnej etykietą "ALBO". -->
          <div
            v-if="grupy.length"
            class="mt-3 border-t border-outline-gray-2 pt-3"
          >
            <div class="mb-2 px-1 text-sm text-ink-gray-5">
              {{ __('Lead pasuje, gdy spełnia dowolną z grup:') }}
            </div>
            <template v-for="(grupa, gi) in grupy" :key="'volteo-grupa-' + gi">
              <div
                v-if="gi > 0"
                class="my-1 text-center text-xs-medium uppercase text-ink-gray-4"
              >
                {{ __('ALBO') }}
              </div>
              <div class="mb-2 rounded border border-outline-gray-2 p-2">
                <div class="mb-2 flex items-center justify-between">
                  <div class="text-sm-medium text-ink-gray-7">
                    {{ __('Grupa {0}', [gi + 1]) }}
                  </div>
                  <Button
                    variant="ghost"
                    icon="lucide-x"
                    :tooltip="__('Usuń grupę')"
                    @click="removeGroup(gi)"
                  />
                </div>
                <div
                  v-for="(f, fi) in grupa"
                  :key="'volteo-warunek-' + gi + '-' + fi"
                  class="mb-2 flex items-center gap-2"
                >
                  <div id="fieldname" class="!min-w-[120px] flex-1">
                    <Autocomplete
                      :value="f.field.fieldname"
                      :options="availableGroupFilters(gi)"
                      :placeholder="__('First Name')"
                      @change="(e) => updateGroupFilter(e, gi, fi)"
                    />
                  </div>
                  <div id="operator">
                    <FormControl
                      v-model="f.operator"
                      type="select"
                      :options="getOperators(f.field.fieldtype, f.field.fieldname)"
                      :placeholder="__('Equals')"
                      @update:modelValue="() => updateOperator(f)"
                    />
                  </div>
                  <div id="value" class="!min-w-[120px] flex-1">
                    <div
                      v-if="czyPrzyciskDzis(f) && czyDzis(f)"
                      class="flex h-7 items-center justify-between gap-1 rounded border border-outline-gray-2 px-2 text-sm text-ink-gray-8"
                    >
                      <span>{{ __('Today') }}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        icon="lucide-x"
                        @click="wyczyscDzis(f)"
                      />
                    </div>
                    <div v-else class="flex items-center gap-1">
                      <component
                        :is="getValueControl(f)"
                        v-model="f.value"
                        :placeholder="placeholder(f)"
                        class="flex-1"
                        @change="(v) => updateValue(v, f)"
                      />
                      <Button
                        v-if="czyPrzyciskDzis(f)"
                        variant="ghost"
                        size="sm"
                        :label="__('Today')"
                        @click="ustawDzis(f)"
                      />
                    </div>
                  </div>
                  <Button
                    class="flex"
                    variant="ghost"
                    icon="lucide-x"
                    @click="removeGroupFilter(gi, fi)"
                  />
                </div>
                <Autocomplete
                  value=""
                  :options="availableGroupFilters(gi)"
                  :placeholder="__('First Name')"
                  @change="(e) => setGroupFilter(e, gi)"
                >
                  <template #target="{ togglePopover }">
                    <Button
                      class="!text-ink-gray-5"
                      variant="ghost"
                      :label="__('Dodaj warunek')"
                      iconLeft="plus"
                      @click="togglePopover()"
                    />
                  </template>
                </Autocomplete>
              </div>
            </template>
            <Button
              v-if="grupy.length < MAX_GRUP"
              class="!text-ink-gray-5"
              variant="ghost"
              :label="__('Dodaj grupę')"
              iconLeft="plus"
              @click="addGroup"
            />
          </div>
          <Button
            v-else
            class="mt-1 !text-ink-gray-5"
            variant="ghost"
            :label="__('Dodaj grupę')"
            iconLeft="plus"
            @click="addGroup"
          />
        </div>
      </div>
    </template>
  </Popover>
</template>
<script setup>
import FilterIcon from '@/components/Icons/FilterIcon.vue'
import Link from '@/components/Controls/Link.vue'
import LinkMultiSelect from '@/components/Controls/LinkMultiSelect.vue'
import Autocomplete from '@/components/frappe-ui/Autocomplete.vue'
import DurationInput from '@/components/Controls/DurationInput.vue'
import RatingInput from '@/components/Controls/RatingInput.vue'
import { etykietaMoje } from '@/utils/etykietaMoje'
import { opcjeEtapu } from '@/utils/etapFiltr'
import {
  czyWielokrotnyWybor,
  parsujWartoscWielokrotna,
} from '@/utils/filtrWielokrotny'
import {
  MAX_GRUP,
  MAX_WARUNKOW_W_GRUPIE,
  dodajGrupe,
  dodajWarunekDoGrupy,
  liczbaWarunkowLacznie,
  polaczGrupy,
  podmienWarunekWGrupy,
  usunGrupe,
  usunWarunekZGrupy,
  wydzielGrupy,
} from '@/utils/grupyFiltrow'
import {
  FormControl,
  MultiSelect,
  createResource,
  Popover,
  DatePicker,
  DateTimePicker,
  DateRangePicker,
} from 'frappe-ui'
import { h, computed, ref, watch, onMounted } from 'vue'
import { isMobileView } from '@/composables/settings'
import { statusesStore } from '@/stores/statuses'

const typeCheck = ['Check']
const typeLink = ['Link', 'Dynamic Link']
const typeNumber = ['Float', 'Int', 'Currency', 'Percent']
const typeSelect = ['Select']
const typeString = ['Data', 'Long Text', 'Small Text', 'Text Editor', 'Text']
const typeDate = ['Date', 'Datetime']
// Issue #128: operatory jednowartościowe pola daty, dla których przycisk
// "Dziś" ma sens -- `between` (DateRangePicker, dwie wartości) i `timespan`/
// `is`/`is not` (własne kontrolki, patrz getValueControl) są celowo
// wykluczone, backend (`crm.volteo_lista_szans.podstaw_dzis`) i tak rozumie
// literał "@dzis" tylko w kształcie skalar/[operator, wartość].
const OPERATORY_JEDNOWARTOSCIOWE_DZIS = ['equals', 'not equals', '>', '<', '>=', '<=']
const typeDuration = ['Duration']
const typeRating = ['Rating']

const props = defineProps({
  doctype: { type: String, required: true },
  default_filters: { type: Object, default: () => {} },
})

const emit = defineEmits(['update'])

const list = defineModel({ type: Object, default: () => ({}) })

const filterableFields = createResource({
  url: 'crm.api.doc.get_filterable_fields',
  cache: ['filterableFields', props.doctype],
  params: { doctype: props.doctype },
})

// Filtr „Etap" (status) zawężony do procesu wybranej linii produktowej —
// patrz `utils/etapFiltr.js`. Ten sam współdzielony fetch (cache klucz jak
// w Deal.vue/DealModal.vue dla `volteo_pipeline_get`/`volteo_pipeline_grupy`)
// — config nie zależy od konkretnej szansy. Tylko dla `props.doctype ===
// 'CRM Deal'`, ale wołanie zasobu jest nieszkodliwe i tanie (cache'owane)
// nawet gdy ten Filter stoi na innej liście — utrzymuje kod prostszym niż
// warunkowe tworzenie zasobu.
const { dealStatuses } = statusesStore()
const grupyStatusow = createResource({
  url: 'crm.api.pipeline.volteo_pipeline_grupy',
  cache: ['volteo-pipeline-grupy'],
  auto: true,
})

function isKnownStatus(name) {
  return Boolean(dealStatuses.data?.some((s) => s.name === name))
}

onMounted(() => {
  if (filterableFields.data?.length) return
  filterableFields.fetch()
})

const filters = computed(() => {
  if (!list.value?.data) return new Set()
  let allFilters =
    list.value?.params?.filters || list.value.data?.params?.filters
  if (
    !allFilters ||
    Object.keys(allFilters).length === 0 ||
    !filterableFields.data
  )
    return new Set()
  // remove default filters
  if (props.default_filters) {
    allFilters = removeCommonFilters(props.default_filters, allFilters)
  }
  return convertFilters(filterableFields.data, allFilters)
})

const availableFilters = computed(() => {
  if (!filterableFields.data) return []

  const selectedFieldNames = new Set()
  for (const filter of filters.value) {
    selectedFieldNames.add(filter.fieldname)
  }

  return filterableFields.data.filter(
    (field) => !selectedFieldNames.has(field.fieldname),
  )
})

// Issue #129: grupy filtrów ORAZ/ALBO ("Grupy ALBO" w sekcji poniżej
// listy warunków wspólnych). `grupy` trzyma tablicę tablic wierszy
// warunków -- ten sam kształt wiersza co `filters` wyżej ({ field,
// fieldname, operator, value }), więc getValueControl/getOperators/
// updateValue/updateOperator/czyPrzyciskDzis i inne funkcje niżej
// (parametryzowane wyłącznie samym wierszem `f`, nie tym, skąd pochodzi)
// działają na warunkach wewnątrz grupy BEZ ŻADNEJ zmiany -- tylko
// operacje STRUKTURALNE (dodaj/usuń warunek, dodaj/usuń grupę) mają
// swoje własne funkcje niżej, delegujące do czystych helperów w
// grupyFiltrow.js (immutability, coding-style.md).
//
// W odróżnieniu od `filters` (computed, mutowany w miejscu przez
// `.add()`/`.delete()` na Set-ie i odczytywany na nowo z `list.value`
// dopiero po `apply()`, wzorzec sprzed tego issue) `grupy` jest zwykłym
// `ref` synchronizowanym `watch`-em: `apply()` NIGDY nie wysyła grupy o
// zerowej liczbie warunków (patrz `polaczGrupy` -- pusta grupa
// dopasowałaby WSZYSTKIE wiersze w zapytaniu backendu, zepsułoby to
// semantykę ALBO), więc gdyby `grupy` była computed jak `filters`,
// dodanie grupy bez żadnego warunku zniknęłoby natychmiast z widoku przy
// najbliższym odczycie (nic nie zostało wysłane, więc "z powrotem" nie
// ma czego odtworzyć). Dlatego `dodajGrupa()` niżej zawsze wstawia
// pierwszy warunek OD RAZU (domyślne pole), więc grupa nigdy nie jest
// faktycznie pusta w stanie UI -- ten sam efekt uboczny (nigdy nie wysyłać
// pustej grupy) jest więc osiągnięty bez potrzeby utrzymywania osobnego,
// niewysyłanego stanu "placeholder pustej grupy".
function grupaZDict(dict) {
  if (!filterableFields.data) return []
  return Array.from(convertFilters(filterableFields.data, dict))
}

function wyliczGrupy() {
  if (!list.value?.data || !filterableFields.data) return []
  let allFilters = list.value?.params?.filters || list.value.data?.params?.filters
  if (!allFilters) return []
  const { grupy: surowe } = wydzielGrupy(allFilters)
  return surowe.map(grupaZDict)
}

// `computed`, nie ręcznie wyliczone źródła `watch`: Vue śledzi WSZYSTKIE
// reaktywne odczyty wewnątrz `wyliczGrupy` (list.value?.data,
// list.value?.params?.filters, filterableFields.data) automatycznie, bez
// ręcznego wymieniania każdego z osobna -- odporniejsze niż lista
// źródeł, którą łatwo przypadkiem zostawić niekompletną. `wyliczGrupy`
// buduje za każdym razem NOWĄ tablicę, więc `grupyPochodne` zmienia
// tożsamość (i budzi poniższy `watch`) przy KAŻDYM przeliczeniu, także
// echo własnego `apply()` -- nieszkodliwe: `addGroup()` zawsze wstawia
// pierwszy warunek od razu (patrz komentarz przy `grupy` niżej), więc
// nigdy nie ma lokalnego stanu "pusta grupa-placeholder", którego
// odtworzenie z powrotem z `list.value.params.filters` mogłoby zgubić.
const grupyPochodne = computed(wyliczGrupy)
const grupy = ref(grupyPochodne.value)
watch(grupyPochodne, (nowe) => {
  grupy.value = nowe
})

function removeCommonFilters(commonFilters, allFilters) {
  for (const key in commonFilters) {
    if (Object.hasOwn(commonFilters, key) && Object.hasOwn(allFilters, key)) {
      if (commonFilters[key] === allFilters[key]) {
        delete allFilters[key]
      }
    }
  }
  return allFilters
}

function convertFilters(data, allFilters) {
  let f = []
  for (let [key, value] of Object.entries(allFilters)) {
    let field = data.find((f) => f.fieldname === key)
    if (typeof value !== 'object' || !value) {
      value = ['=', value]
      if (field?.fieldtype === 'Check') {
        value = ['equals', value[1] ? 'Yes' : 'No']
      }
    }

    if (field) {
      f.push({
        field,
        fieldname: key,
        operator: oppositeOperatorMap[value[0]],
        value: value[1],
      })
    }
  }
  return new Set(f)
}

function getOperators(fieldtype, fieldname) {
  let options = []
  if (typeString.includes(fieldtype)) {
    options.push(
      ...[
        { label: __('Equals'), value: 'equals' },
        { label: __('Not equals'), value: 'not equals' },
        { label: __('Like'), value: 'like' },
        { label: __('Not like'), value: 'not like' },
        { label: __('In'), value: 'in' },
        { label: __('Not in'), value: 'not in' },
        { label: __('Is'), value: 'is' },
      ],
    )
  }
  if (fieldname === '_assign') {
    // TODO: make equals and not equals work
    options = [
      { label: __('Like'), value: 'like' },
      { label: __('Not like'), value: 'not like' },
      { label: __('Is'), value: 'is' },
    ]
  }
  if (typeNumber.includes(fieldtype)) {
    options.push(
      ...[
        { label: __('Equals'), value: 'equals' },
        { label: __('Not equals'), value: 'not equals' },
        { label: __('Like'), value: 'like' },
        { label: __('Not like'), value: 'not like' },
        { label: __('In'), value: 'in' },
        { label: __('Not in'), value: 'not in' },
        { label: __('Is'), value: 'is' },
        { label: __('<'), value: '<' },
        { label: __('>'), value: '>' },
        { label: __('<='), value: '<=' },
        { label: __('>='), value: '>=' },
      ],
    )
  }
  if (typeSelect.includes(fieldtype)) {
    options.push(
      ...[
        { label: __('Equals'), value: 'equals' },
        { label: __('Not equals'), value: 'not equals' },
        { label: __('In'), value: 'in' },
        { label: __('Not in'), value: 'not in' },
        { label: __('Is'), value: 'is' },
      ],
    )
  }
  if (typeLink.includes(fieldtype)) {
    options.push(
      ...[
        { label: __('Equals'), value: 'equals' },
        { label: __('Not equals'), value: 'not equals' },
        { label: __('Like'), value: 'like' },
        { label: __('Not like'), value: 'not like' },
        { label: __('In'), value: 'in' },
        { label: __('Not in'), value: 'not in' },
        { label: __('Is'), value: 'is' },
      ],
    )
  }
  if (typeCheck.includes(fieldtype)) {
    options.push(...[{ label: __('Equals'), value: 'equals' }])
  }
  if (typeDuration.includes(fieldtype)) {
    options.push(
      ...[
        { label: __('Like'), value: 'like' },
        { label: __('Not like'), value: 'not like' },
        { label: __('In'), value: 'in' },
        { label: __('Not in'), value: 'not in' },
        { label: __('Is'), value: 'is' },
      ],
    )
  }
  if (typeDate.includes(fieldtype)) {
    options.push(
      ...[
        { label: __('Equals'), value: 'equals' },
        { label: __('Not equals'), value: 'not equals' },
        { label: __('Is'), value: 'is' },
        { label: __('>'), value: '>' },
        { label: __('<'), value: '<' },
        { label: __('>='), value: '>=' },
        { label: __('<='), value: '<=' },
        { label: __('Between'), value: 'between' },
        { label: __('Timespan'), value: 'timespan' },
      ],
    )
  }
  if (typeRating.includes(fieldtype)) {
    options.push(
      ...[
        { label: __('Equals'), value: 'equals' },
        { label: __('Not equals'), value: 'not equals' },
        { label: __('Greater than'), value: '>' },
        { label: __('Less than'), value: '<' },
        { label: __('Greater than or equal to'), value: '>=' },
        { label: __('Less than or equal to'), value: '<=' },
        { label: __('Is'), value: 'is' },
      ],
    )
  }
  return options
}

function getValueControl(f) {
  const { field, operator } = f
  const { fieldtype, options } = field
  if (operator == 'is') {
    return h(FormControl, {
      type: 'select',
      options: [
        {
          label: __('Set'),
          value: 'set',
        },
        {
          label: __('Not Set'),
          value: 'not set',
        },
      ],
      modelValue: f.value,
      'onUpdate:modelValue': (v) => updateValue(v, f),
    })
  } else if (operator == 'timespan') {
    return h(FormControl, {
      type: 'select',
      options: timespanOptions,
      modelValue: f.value,
      'onUpdate:modelValue': (v) => updateValue(v, f),
    })
  } else if (czyWielokrotnyWybor(f.field, operator) && typeSelect.includes(fieldtype)) {
    // Issue #103: "jest jednym z" / "nie jest jednym z" na polu Select:
    // wielokrotny wybór z opcji pola (tych samych, co przy operatorze
    // równości), zamiast pola tekstowego z wartościami po przecinku.
    // Serializacja bez zmian: modelValue MultiSelect to tablica stringów,
    // dokładnie ten kształt, jakiego oczekuje transformIn/parseFilters.
    return h(MultiSelect, {
      options: getSelectOptions(options).map((o) => ({ label: o, value: o })),
      modelValue: parsujWartoscWielokrotna(f.value),
      'onUpdate:modelValue': (v) => updateValue(v, f),
    })
  } else if (czyWielokrotnyWybor(f.field, operator) && typeLink.includes(fieldtype)) {
    // Issue #103: to samo dla pól Link, poza dwoma wyłączeniami już
    // zakodowanymi w czyWielokrotnyWybor (Dynamic Link: doctype docelowy
    // zmienia się per wiersz, nie ma jednego stałego katalogu do
    // przeszukania; Link z options === 'User': zostaje na polu tekstowym
    // niżej, żeby nie ominąć zakresów Link.vue, patrz JSDoc w
    // filtrWielokrotny.js). Wyszukiwanie przez
    // frappe.desk.search.search_link, jak dziś przy operatorze równości
    // (Link.vue), tylko z wielokrotnym wyborem (LinkMultiSelect.vue).
    return h(LinkMultiSelect, {
      doctype: options,
      modelValue: parsujWartoscWielokrotna(f.value),
      'onUpdate:modelValue': (v) => updateValue(v, f),
    })
  } else if (['like', 'not like', 'in', 'not in'].includes(operator)) {
    return h(FormControl, { type: 'text' })
  } else if (typeSelect.includes(fieldtype) || typeCheck.includes(fieldtype)) {
    const _options =
      fieldtype == 'Check' ? ['Yes', 'No'] : getSelectOptions(options)
    return h(FormControl, {
      type: 'select',
      options: _options.map((o) => ({
        label: o,
        value: o,
      })),
      modelValue: f.value,
      'onUpdate:modelValue': (v) => updateValue(v, f),
    })
  } else if (
    props.doctype === 'CRM Deal' &&
    field.fieldname === 'status' &&
    ['equals', 'not equals'].includes(operator)
  ) {
    // Etap zawężony do procesu aktywnego filtra „Rodzaj umowy" — patrz
    // utils/etapFiltr.js. Operatory `in`/`not in` NIE trafiają tutaj (już
    // przechwycone wyżej przez gałąź `['like', 'not like', 'in', 'not
    // in'].includes(operator)`, niezmieniona).
    return h(Autocomplete, {
      value: f.value,
      options: opcjeEtapu(
        grupyStatusow.data,
        list.value?.params?.filters?.custom_rodzaj_umowy,
        isKnownStatus,
        dealStatuses.data?.map((s) => s.name),
      ),
      onChange: (o) => updateValue(o?.value ?? '', f),
    })
  } else if (typeLink.includes(fieldtype)) {
    if (fieldtype == 'Dynamic Link') {
      return h(FormControl, { type: 'text' })
    }
    return h(Link, {
      class: 'form-control',
      doctype: options,
      value: f.value,
      meLabel: etykietaMoje(props.doctype),
      userScope: true,
    })
  } else if (typeNumber.includes(fieldtype)) {
    return h(FormControl, { type: 'number' })
  } else if (typeDate.includes(fieldtype) && operator == 'between') {
    return h(DateRangePicker, { value: f.value, iconLeft: '' })
  } else if (typeDuration.includes(fieldtype)) {
    return h(DurationInput, { value: f.value })
  } else if (typeRating.includes(fieldtype)) {
    return h(RatingInput, {
      value: f.value,
      max: options || 5,
      class: '!flex',
    })
  } else if (typeDate.includes(fieldtype)) {
    return h(fieldtype == 'Date' ? DatePicker : DateTimePicker, {
      value: f.value,
      iconLeft: '',
    })
  } else {
    return h(FormControl, { type: 'text' })
  }
}

function getDefaultValue(field) {
  if (typeSelect.includes(field.fieldtype)) {
    return getSelectOptions(field.options)[0]
  }
  if (typeCheck.includes(field.fieldtype)) {
    return 'Yes'
  }
  if (typeDate.includes(field.fieldtype)) {
    return null
  }
  return ''
}

function getDefaultOperator(fieldtype) {
  if (typeSelect.includes(fieldtype)) {
    return 'equals'
  }
  if (typeCheck.includes(fieldtype) || typeNumber.includes(fieldtype)) {
    return 'equals'
  }
  if (typeDate.includes(fieldtype)) {
    return 'between'
  }
  return 'like'
}

function getSelectOptions(options) {
  return options.split('\n')
}

function setfilter(data) {
  if (!data) return
  filters.value.add({
    field: {
      label: data.label,
      fieldname: data.fieldname,
      fieldtype: data.fieldtype,
      options: data.options,
    },
    fieldname: data.fieldname,
    operator: getDefaultOperator(data.fieldtype),
    value: getDefaultValue(data),
  })
  apply()
}

function updateFilter(data, index) {
  if (!data.fieldname) return

  filters.value.delete(Array.from(filters.value)[index])
  filters.value.add({
    fieldname: data.fieldname,
    operator: getDefaultOperator(data.fieldtype),
    value: getDefaultValue(data),
    field: {
      label: data.label,
      fieldname: data.fieldname,
      fieldtype: data.fieldtype,
      options: data.options,
    },
  })
  apply()
}

function removeFilter(index) {
  filters.value.delete(Array.from(filters.value)[index])
  apply()
}

// Issue #129: operacje strukturalne na grupy -- dodanie/usunięcie CAŁEJ
// grupy albo pojedynczego warunku wewnątrz grupy. Wszystkie delegują do
// czystych, testowanych osobno helperów w grupyFiltrow.js (immutability)
// i kończą wywołaniem `apply()`, tak jak odpowiedniki dla filtrów
// wspólnych wyżej.
function zbudujWarunek(data) {
  return {
    field: {
      label: data.label,
      fieldname: data.fieldname,
      fieldtype: data.fieldtype,
      options: data.options,
    },
    fieldname: data.fieldname,
    operator: getDefaultOperator(data.fieldtype),
    value: getDefaultValue(data),
  }
}

function availableGroupFilters(groupIndex) {
  if (!filterableFields.data) return []
  const uzyte = new Set((grupy.value[groupIndex] || []).map((f) => f.fieldname))
  return filterableFields.data.filter((field) => !uzyte.has(field.fieldname))
}

function addGroup() {
  if (grupy.value.length >= MAX_GRUP) return
  const pierwszePole = filterableFields.data?.[0]
  if (!pierwszePole) return
  grupy.value = dodajGrupe(grupy.value, [zbudujWarunek(pierwszePole)])
  apply()
}

function removeGroup(groupIndex) {
  grupy.value = usunGrupe(grupy.value, groupIndex)
  apply()
}

function setGroupFilter(data, groupIndex) {
  if (!data) return
  if ((grupy.value[groupIndex]?.length ?? 0) >= MAX_WARUNKOW_W_GRUPIE) return
  grupy.value = dodajWarunekDoGrupy(grupy.value, groupIndex, zbudujWarunek(data))
  apply()
}

function updateGroupFilter(data, groupIndex, condIndex) {
  if (!data.fieldname) return
  grupy.value = podmienWarunekWGrupy(grupy.value, groupIndex, condIndex, zbudujWarunek(data))
  apply()
}

function removeGroupFilter(groupIndex, condIndex) {
  grupy.value = usunWarunekZGrupy(grupy.value, groupIndex, condIndex)
  apply()
}

function clearfilter(close) {
  filters.value.clear()
  grupy.value = []
  apply()
  close()
}

// Issue #128: placeholder daty "@dzis" (analogiczny do "@me" dla
// użytkownika, patrz `crm.api.doc._podstaw_me`/`_podstaw_dzis`). Widoczny
// wyłącznie dla pól Date/Datetime z operatorem jednowartościowym -- `between`
// ma własną kontrolkę (DateRangePicker) i jest tu celowo pominięty (patrz
// brief issue #128: "operator between z @dzis: dopuszczalne pominąć").
function czyPrzyciskDzis(f) {
  return (
    typeDate.includes(f.field.fieldtype) &&
    OPERATORY_JEDNOWARTOSCIOWE_DZIS.includes(f.operator)
  )
}

function czyDzis(f) {
  return f.value === '@dzis'
}

function ustawDzis(f) {
  updateValue('@dzis', f)
}

function wyczyscDzis(f) {
  updateValue(getDefaultValue(f.field), f)
}

function updateValue(value, filter) {
  value = value.target ? value.target.value : value
  if (filter.operator === 'between') {
    filter.value = [value.split(',')[0], value.split(',')[1]]
  } else {
    filter.value = value
  }
  apply()
}

function updateOperator(filter) {
  if (czyWielokrotnyWybor(filter.field, filter.operator)) {
    // Issue #103: dokładnie tam, gdzie getValueControl renderuje
    // MultiSelect/LinkMultiSelect (Select albo Link poza Dynamic Link i
    // poza User, patrz JSDoc czyWielokrotnyWybor w filtrWielokrotny.js),
    // in/not in startuje z tablicą pustą zamiast skalarnego domyślnego
    // (np. pierwszą opcją Select): te kontrolki oczekują modelValue jako
    // tablicy. Pozostałe typy (Data, Int i inne, które nadal mają pole
    // tekstowe z wartościami po przecinku, tak jak pola Link do User)
    // zostają przy dotychczasowym skalarnym default poniżej, bo
    // transformIn dla nich oczekuje stringa, nie tablicy.
    filter.value = []
  } else if (filter.operator === 'is' || filter.operator === 'is not') {
    filter.value = 'set'
  } else {
    filter.value = getDefaultValue(filter.field)
  }
  apply()
}

function apply() {
  let _filters = []
  filters.value.forEach((f) => {
    _filters.push({
      fieldname: f.fieldname,
      operator: f.operator,
      value: f.value,
    })
  })
  const filtryWspolne = parseFilters(_filters)

  // Issue #129: każda grupa serializowana tą samą `parseFilters` co
  // filtry wspólne wyżej (ten sam kształt wiersza, ten sam operatorMap/
  // transformIn), a `polaczGrupy` doklada wynik pod `volteo_grupy` --
  // pomijając grupy o zerowej liczbie warunków (patrz jej JSDoc), czego
  // w praktyce i tak nie ma, bo `addGroup()` zawsze wstawia pierwszy
  // warunek od razu (patrz komentarz przy deklaracji `grupy` wyżej).
  // Tak jak `_filters` wyżej: kopie zwykłych obiektów, NIE same wiersze
  // z `grupy.value` -- `transformIn` w `parseFilters` mutuje `.value` (np.
  // dokleja "%...%"), a wiersze w `grupy.value` muszą zostać nietknięte,
  // żeby edycja w popupie nadal pokazywała wartość wpisaną przez
  // użytkownika, nie jej opakowaną, "przewodową" postać.
  const grupyWire = grupy.value.map((warunki) =>
    parseFilters(
      warunki.map((f) => ({ fieldname: f.fieldname, operator: f.operator, value: f.value })),
    ),
  )

  emit('update', polaczGrupy(filtryWspolne, grupyWire))
}

const liczbaWarunkow = computed(() => liczbaWarunkowLacznie(filters.value.size, grupy.value))

function parseFilters(filters) {
  const filtersArray = Array.from(filters)
  const obj = filtersArray.map(transformIn).reduce((p, c) => {
    if (['equals', '='].includes(c.operator)) {
      p[c.fieldname] =
        c.value == 'Yes' ? true : c.value == 'No' ? false : c.value
    } else {
      p[c.fieldname] = [operatorMap[c.operator.toLowerCase()], c.value]
    }
    return p
  }, {})
  const merged = { ...obj }
  return merged
}

function transformIn(f) {
  if (f.operator.includes('like') && !f.value.includes('%')) {
    f.value = `%${f.value}%`
  }
  if (['in', 'not in'].includes(f.operator) && typeof f.value === 'string') {
    f.value = f.value.split(',').map((v) => v.trim())
  }
  return f
}

function placeholder(f) {
  if (f.operator === 'between') {
    return __('01/01/2022 to 01/31/2022')
  } else if (f.operator === 'in' || f.operator === 'not in') {
    // Issue #103: pola z kontrolką wielokrotnego wyboru (MultiSelect dla
    // Select, LinkMultiSelect dla Link poza Dynamic Link i poza User,
    // patrz czyWielokrotnyWybor w filtrWielokrotny.js) dostają ten
    // placeholder jako etykietę pustego stanu tej kontrolki, nie jako
    // treść wpisywaną przez przecinek. Pozostałe pola (w tym Link do
    // User, np. lead_owner/custom_cc/deal_owner/custom_opiekun) zostają
    // na dotychczasowym polu tekstowym niżej.
    if (czyWielokrotnyWybor(f.field, f.operator)) {
      return __('Select options')
    }
    if (typeNumber.includes(f.field.fieldtype)) {
      return __('100, 200, 300')
    }
    return __('John, Jane, Doe')
  } else if (f.operator === 'like' || f.operator === 'not like') {
    if (typeNumber.includes(f.field.fieldtype)) {
      return __('%100%')
    }
    return __('%John%')
  } else if (f.operator === 'is' || f.operator === 'is not') {
    return __('Set')
  } else if (f.operator === 'timespan') {
    return __('Last Week')
  } else if (typeNumber.includes(f.field.fieldtype)) {
    return __('1000')
  } else if (typeDate.includes(f.field.fieldtype)) {
    return __('01/01/2022')
  } else if (typeCheck.includes(f.field.fieldtype)) {
    return __('Yes')
  } else if (typeLink.includes(f.field.fieldtype)) {
    return __('Select a Value')
  } else if (typeSelect.includes(f.field.fieldtype)) {
    return __('Select an Option')
  } else if (typeString.includes(f.field.fieldtype)) {
    return __('John Doe')
  }
  return __('Enter Value')
}

const operatorMap = {
  is: 'is',
  'is not': 'is not',
  in: 'in',
  'not in': 'not in',
  equals: '=',
  'not equals': '!=',
  yes: true,
  no: false,
  like: 'LIKE',
  'not like': 'NOT LIKE',
  '>': '>',
  '<': '<',
  '>=': '>=',
  '<=': '<=',
  between: 'between',
  timespan: 'timespan',
}

const oppositeOperatorMap = {
  is: 'is',
  '=': 'equals',
  '!=': 'not equals',
  equals: 'equals',
  'is not': 'is not',
  true: 'yes',
  false: 'no',
  LIKE: 'like',
  'NOT LIKE': 'not like',
  in: 'in',
  'not in': 'not in',
  '>': '>',
  '<': '<',
  '>=': '>=',
  '<=': '<=',
  between: 'between',
  timespan: 'timespan',
}

const timespanOptions = [
  {
    label: __('Last Week'),
    value: 'last week',
  },
  {
    label: __('Last Month'),
    value: 'last month',
  },
  {
    label: __('Last Quarter'),
    value: 'last quarter',
  },
  {
    label: __('Last 6 Months'),
    value: 'last 6 months',
  },
  {
    label: __('Last Year'),
    value: 'last year',
  },
  {
    label: __('Yesterday'),
    value: 'yesterday',
  },
  {
    label: __('Today'),
    value: 'today',
  },
  {
    label: __('Tomorrow'),
    value: 'tomorrow',
  },
  {
    label: __('This Week'),
    value: 'this week',
  },
  {
    label: __('This Month'),
    value: 'this month',
  },
  {
    label: __('This Quarter'),
    value: 'this quarter',
  },
  {
    label: __('This Year'),
    value: 'this year',
  },
  {
    label: __('Next Week'),
    value: 'next week',
  },
  {
    label: __('Next Month'),
    value: 'next month',
  },
  {
    label: __('Next Quarter'),
    value: 'next quarter',
  },
  {
    label: __('Next 6 Months'),
    value: 'next 6 months',
  },
  {
    label: __('Next Year'),
    value: 'next year',
  },
]
</script>
