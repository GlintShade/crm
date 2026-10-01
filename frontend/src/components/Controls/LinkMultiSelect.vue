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
// jakiego oczekuje transformIn/parseFilters w Filter.vue dla in/not in,
// żadnej zmiany serializacji filtra).
//
// Issue #214 (2026-10-01): doctype='User' (lead_owner, custom_cc,
// deal_owner, custom_opiekun) dostaje TERAZ ten sam zakres i tę samą opcję
// "@me" co Link.vue (`userScope`) -- wcześniej Filter.vue w ogóle nie
// renderował tego komponentu dla takich pól (patrz historia JSDoc w
// utils/filtrWielokrotny.js::czyWielokrotnyWybor), właśnie żeby nie ominąć
// zawężenia do poddrzewa Sales Hierarchy, które dla pól User nakłada
// Link.vue. Oba komponenty (ten i QuickFilterCheckList.vue) czerpią teraz z
// tego samego, wspólnego, frappe-free modułu, `utils/zakresUzytkownikow.js`
// -- patrz jego JSDoc dla pełnego opisu reguły. Dla każdego innego doctype
// (poza User) ten komponent zachowuje się dokładnie jak dotychczas: bez
// zakresu, bez "@me".
import { scalOpcjeZZaznaczonymi } from '@/utils/filtrWielokrotny'
import { opcjeUzytkownikow } from '@/utils/etykietaUzytkownika'
import { dolozOpcjeMoje, filtrZakresuUzytkownikow } from '@/utils/zakresUzytkownikow'
import { usersStore } from '@/stores/users'
import { MultiSelect, createResource } from 'frappe-ui'
import { computed, onMounted, ref, watch } from 'vue'

const props = defineProps({
  doctype: { type: String, required: true },
  placeholder: { type: String, default: '' },
  // Issue #214: etykieta opcji "@me" (patrz utils/etykietaMoje.js), uwzględniana
  // wyłącznie gdy doctype === 'User'. Wywołujący spoza takich pól (każdy
  // inny Link) nie musi jej podawać -- domyślna wartość nigdy nie trafia do
  // UI, bo gałąź "@me" jest tam w ogóle nieaktywna.
  meLabel: { type: String, default: '@me' },
})

const { getUser } = usersStore()
const jestUser = computed(() => props.doctype === 'User')

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
// wybraną wartość: ten sam wzorzec co przykład "Async Options" w
// dokumentacji frappe-ui MultiSelect.
const znaneEtykiety = ref(new Map())

// Issue #214: zakres widocznych użytkowników (ten sam zasób co Link.vue,
// klucz cache globalny we frappe-ui, więc pobierany raz na stronę) --
// pobierany WYŁĄCZNIE gdy doctype === 'User'.
const widoczniUzytkownicy = createResource({
  url: 'crm.api.volteo_uzytkownicy.widoczni_uzytkownicy',
  cache: ['widoczni_uzytkownicy'],
})

watch(
  jestUser,
  (aktywne) => {
    if (aktywne && !widoczniUzytkownicy.fetched && !widoczniUzytkownicy.loading) {
      widoczniUzytkownicy.fetch()
    }
  },
  { immediate: true },
)

// Filtry faktycznie wysyłane do search_link -- `null` sygnalizuje "jeszcze
// nie gotowe" (dopóki zakres dla doctype='User' nie dotarł z serwera), tak
// jak w Link.vue::effectiveFilters. Dla każdego innego doctype zawsze `{}`.
const effectiveFilters = computed(() => {
  if (!jestUser.value) return {}
  if (!widoczniUzytkownicy.fetched) return null
  return filtrZakresuUzytkownikow({}, widoczniUzytkownicy.data)
})

const zasob = createResource({
  url: 'frappe.desk.search.search_link',
  method: 'POST',
  params: { txt: '', doctype: props.doctype, filters: {} },
  transform: (data) => {
    let wynik = jestUser.value
      ? opcjeUzytkownikow(data, getUser)
      : (data || []).map((option) => ({
          label: option.label || option.value,
          value: option.value,
          description: stripHtml(option.description),
        }))
    if (jestUser.value) {
      // Issue #214: "@me" jako pierwsza pozycja, niezależnie od tekstu
      // wyszukiwania -- ten sam wzorzec co Link.vue (hideMe nie dotyczy
      // tego komponentu, "@me" ma sens wszędzie, gdzie ten komponent jest
      // dziś używany, czyli wyłącznie w filtrach).
      wynik = dolozOpcjeMoje(wynik, props.meLabel)
    }
    for (const opcja of wynik) znaneEtykiety.value.set(opcja.value, opcja)
    return wynik
  },
})

// Lista pokazywana w popoverze: wyniki ostatniego zapytania, plus każda
// aktualnie zaznaczona wartość, której w tych wynikach nie ma, najpierw z
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
  // Issue #214: dopóki doctype==='User' i zakres jeszcze nie dotarł
  // (effectiveFilters === null), nie odpytujemy -- tak jak w
  // Link.vue::reload, żeby pierwszy wynik przez moment nie pokazał
  // wszystkich użytkowników zamiast zawężonych. watch(effectiveFilters)
  // niżej wywoła wyszukiwanie ponownie, gdy zakres dotrze.
  if (jestUser.value && effectiveFilters.value === null) return
  ostatnieZapytanie = txt
  zasob.update({ params: { txt, doctype: props.doctype, filters: effectiveFilters.value } })
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

// Issue #214: gdy effectiveFilters przechodzi z `null` ("jeszcze nie
// gotowe") na gotowy obiekt (zakres dotarł z serwera), uruchom wyszukiwanie
// od razu -- analogicznie do Link.vue::watchDebounced(effectiveFilters).
watch(effectiveFilters, (wartosc, poprzednia) => {
  if (poprzednia === null && wartosc !== null) {
    wyszukaj(ostatnieZapytanie || '')
  }
})

onMounted(() => {
  if (!zasob.data && !zasob.loading) wyszukaj('')
})
</script>
