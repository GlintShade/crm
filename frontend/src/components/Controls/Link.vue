<template>
  <div class="space-y-1.5 p-[2px] -m-[2px]">
    <label v-if="attrs.label" class="block" :class="labelClasses">
      {{ __(attrs.label) }}
    </label>
    <Autocomplete
      ref="autocomplete"
      v-model="value"
      :options="options.data"
      :size="attrs.size || 'sm'"
      :variant="attrs.variant"
      :placeholder="attrs.placeholder"
      :disabled="attrs.disabled"
      :placement="attrs.placement"
      :filterable="false"
    >
      <template #target="{ open, togglePopover }">
        <slot name="target" v-bind="{ open, togglePopover }" />
      </template>

      <template #prefix>
        <slot name="prefix" />
      </template>

      <template #item-prefix="{ active, selected, option }">
        <slot name="item-prefix" v-bind="{ active, selected, option }" />
      </template>

      <template #item-label="{ active, selected, option }">
        <slot name="item-label" v-bind="{ active, selected, option }">
          <div v-if="option.description" class="flex flex-col gap-1">
            <div class="flex-1 font-semibold truncate text-ink-gray-7">
              {{ option.label }}
            </div>
            <div class="flex-1 text-sm truncate text-ink-gray-5">
              {{ option.description }}
            </div>
          </div>
          <div v-else class="flex-1 truncate text-ink-gray-7">
            {{ option.label }}
          </div>
        </slot>
      </template>

      <template #footer="{ value: v, close }">
        <div v-if="attrs.onCreate">
          <Button
            variant="ghost"
            class="w-full !justify-start"
            :label="attrs.createLabel || __('Create New')"
            iconLeft="plus"
            @click="() => attrs.onCreate(v, close)"
          />
        </div>
        <div>
          <Button
            variant="ghost"
            class="w-full !justify-start"
            :label="__('Clear')"
            iconLeft="x"
            @click="() => clearValue(close)"
          />
        </div>
      </template>
    </Autocomplete>
  </div>
</template>

<script setup>
import Autocomplete from '@/components/frappe-ui/Autocomplete.vue'
import { isTranslatable } from '@/utils'
import { watchDebounced } from '@vueuse/core'
import { createResource } from 'frappe-ui'
import { useAttrs, computed, ref, watch } from 'vue'

const props = defineProps({
  doctype: { type: String, required: true },
  filters: { type: [Array, Object, String], default: () => [] },
  modelValue: { type: String, default: '' },
  hideMe: { type: Boolean, default: false },
  // Etykieta dla opcji "@me" (wartość zostaje '@me', tylko podpis się
  // zmienia) — patrz etykietaMoje() w @/utils/index.js. Domyślnie surowe
  // '@me', jak dotychczas, dla wywołań spoza kontekstów filtrowania.
  meLabel: { type: String, default: '@me' },
  // Ops#72: gdy true i doctype === 'User', dropdown pokazuje tylko
  // użytkowników z poddrzewa Sales Hierarchy bieżącej sesji (patrz
  // crm.api.volteo_uzytkownicy.widoczni_uzytkownicy) zamiast wszystkich
  // aktywnych kont. Domyślnie false — formularze/przydziały (hideMe=true)
  // zostają bez zmian, jak dotychczas.
  userScope: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change'])

const attrs = useAttrs()

const valuePropPassed = computed(() => 'value' in attrs)

const value = computed({
  get: () => {
    let v = valuePropPassed.value ? attrs.value : props.modelValue

    if (isTranslatable(props.doctype)) return __(v)
    return v
  },
  set: (val) => {
    return (
      val?.value &&
      emit(valuePropPassed.value ? 'change' : 'update:modelValue', val?.value)
    )
  },
})

const autocomplete = ref(null)
const text = ref('')

// Ops#72: userScope tylko dla doctype='User' — na inne Linki (np. Company,
// Contact) nie ma wpływu, nawet jeśli ktoś przekaże userScope=true przez
// pomyłkę na komponencie, którego doctype akurat nie jest 'User'.
const userScopeActive = computed(
  () => props.userScope && props.doctype === 'User',
)

// Zasób dzielony między WSZYSTKIMI instancjami Link.vue na stronie (klucz
// cache jest globalny w frappe-ui) — lista pobierana jest raz, nie per
// dropdown.
const widoczniUzytkownicy = createResource({
  url: 'crm.api.volteo_uzytkownicy.widoczni_uzytkownicy',
  cache: ['widoczni_uzytkownicy'],
})

watch(
  userScopeActive,
  (aktywne) => {
    if (aktywne && !widoczniUzytkownicy.fetched && !widoczniUzytkownicy.loading) {
      widoczniUzytkownicy.fetch()
    }
  },
  { immediate: true },
)

// Filtry faktycznie wysyłane do search_link. Gdy userScope jest aktywny,
// dokładamy ograniczenie do poddrzewa hierarchii; dopóki lista nie dotrze
// z serwera, zwracamy `null` jako sygnał "jeszcze nie gotowe" — reload()
// niżej wtedy nic nie wysyła, żeby pierwszy dropdown nie pokazał przez
// moment wszystkich użytkowników zanim ograniczenie dojedzie. Rozróżniamy
// `fetched` (zakończone pobieranie) od `data === null` (odpowiedź serwera:
// "bez ograniczenia", bo Administrator/BYPASS_ROLES/Sales Manager spoza
// drzewa) — to dwie różne rzeczy, mylenie ich zwróciłoby "jeszcze nie
// gotowe" na zawsze dla użytkowników bez ograniczenia.
const effectiveFilters = computed(() => {
  if (!userScopeActive.value) return props.filters
  if (!widoczniUzytkownicy.fetched) return null

  const lista = widoczniUzytkownicy.data
  if (lista === null) return props.filters

  // W kontekstach filtrowania (jedyne dziś użycie userScope) filters nie
  // jest przekazywane (domyślne [] traktujemy jak {}); gdyby kiedyś ktoś
  // przekazał tablicę/string razem z userScope, i tak nie umiemy scalić
  // formatu tablicowego filtrów Frappe z dict-em wymaganym przez
  // search_link, więc bezpiecznie zaczynamy od pustego obiektu.
  const baza =
    props.filters && typeof props.filters === 'object' && !Array.isArray(props.filters)
      ? { ...props.filters }
      : {}
  baza.name = lista.length ? ['in', lista] : ['in', ['']]
  return baza
})

watchDebounced(
  () => autocomplete.value?.query,
  (val) => {
    val = val || ''
    if (text.value === val) return
    text.value = val
    reload(val)
  },
  { debounce: 300, immediate: true },
)

watchDebounced(
  () => props.doctype,
  () => reload(''),
  { debounce: 300, immediate: true },
)

watchDebounced(
  effectiveFilters,
  () => {
    reload('', true)
  },
  { debounce: 300, immediate: true },
)

const options = createResource({
  url: 'frappe.desk.search.search_link',
  // meLabel i userScope muszą być w kluczu cache: bez tego dwa Linki dla
  // doctype='User' z różnymi meLabel (np. "Moi klienci" na liście Klienci
  // vs "Moje szanse" na liście Szanse) dzieliłyby jeden zasób frappe-ui i
  // drugi z nich pokazałby cudzą etykietę — transform() nakłada etykietę
  // PRZED zapisaniem do cache, cache trzyma dane PO transformie. Ten sam
  // powód dla userScope: bez niego Link z userScope=true i Link bez niego,
  // dla tego samego doctype/tekstu/hideMe/filters, dzieliłyby wynik —
  // jeden pokazałby ograniczoną listę tam, gdzie druga instancja jej nie
  // chce (albo odwrotnie).
  cache: [
    props.doctype,
    text.value,
    props.hideMe,
    props.filters,
    props.meLabel,
    props.userScope,
  ],
  method: 'POST',
  params: {
    txt: text.value,
    doctype: props.doctype,
    filters: effectiveFilters.value,
  },
  transform: (data) => {
    let allData = data.map((option) => {
      return {
        label: option.label || option.value,
        value: option.value,
        description: stripHtml(option.description),
      }
    })
    if (!props.hideMe && props.doctype == 'User') {
      allData.unshift({
        label: props.meLabel,
        value: '@me',
      })
    }
    return allData
  },
})

function stripHtml(html) {
  if (!html) return ''
  return html
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function reload(val, force = false) {
  if (!props.doctype) return
  // Ops#72: dopóki userScope jest aktywny a lista poddrzewa jeszcze nie
  // dotarła, effectiveFilters zwraca null — nie odpalamy wyszukiwania, żeby
  // pierwszy dropdown przez moment nie pokazał wszystkich użytkowników.
  // Gdy lista dotrze, watchDebounced na effectiveFilters (wyżej) wywoła
  // reload ponownie.
  if (userScopeActive.value && effectiveFilters.value === null) return
  if (
    !force &&
    options.data?.length &&
    val === options.params?.txt &&
    props.doctype === options.params?.doctype
  )
    return

  options.update({
    params: {
      txt: val,
      doctype: props.doctype,
      filters: effectiveFilters.value,
    },
  })
  options.reload()
}

function clearValue(close) {
  emit(valuePropPassed.value ? 'change' : 'update:modelValue', '')
  close()
}

const labelClasses = computed(() => {
  return [
    {
      sm: 'text-xs',
      md: 'text-base',
    }[attrs.size || 'sm'],
    'text-ink-gray-5',
  ]
})

defineExpose({ reload })
</script>
