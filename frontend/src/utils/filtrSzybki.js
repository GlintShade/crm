// Logika czysta (bez importu frappe-ui / @) dla wielokrotnego wyboru w
// pasku szybkich filtrów (QuickFilterField.vue / ViewControls.vue, issue
// #127), dla pól Select i Link (poza polami User i datami, patrz
// czyWielokrotnyWybor w filtrWielokrotny.js, którego ten pasek też używa).
//
// Serializacja do backendu i do zapisanych widoków, w obu kierunkach:
//   0 wartości  -> klucz filtra usunięty (undefined tutaj, wywołujący
//                  kasuje klucz z obiektu filters)
//   1 wartość   -> dotychczasowy skalarny kształt (`filters[pole] = wartość`),
//                  bez zmian względem stanu sprzed tej zmiany
//   N wartości  -> `["in", [w1, w2, ...]]`, ten sam format co operator
//                  "jest jednym z" w rozwijanym Filter.vue (issue #103)
//
// Odczyt idzie tą samą drogą w drugą stronę: rozpakujWartoscFiltraSzybkiego
// rozpoznaje wyłącznie skalar i `["in", [...]]`, każdy inny kształt
// tablicowy (np. `["like", "%x%"]` z rozwijanego filtra) zostaje pusty,
// dokładnie tak jak zachowywał się pasek szybkich filtrów przed tą zmianą
// dla pól Select/Link/Date/Datetime (patrz quickFilterList w
// ViewControls.vue: każdy nierozpoznany kształt tablicowy zostawiał
// wartość domyślną).
//
// Frappe-free (żadnego `__()` na poziomie modułu, patrz PUŁAPKA w
// etapFiltr.js/etykietaMoje.js: eager chunk woła moduł przed i18n),
// testowalne bezpośrednio przez vitest.

import { czyWielokrotnyWybor, parsujWartoscWielokrotna } from './filtrWielokrotny'

/**
 * Rozpakowuje surową wartość filtra (`list.params.filters[fieldname]`,
 * kształt jakiego oczekuje backend) do tablicy zaznaczonych stringów, do
 * użytku jako stan checkboxów. Rozpoznaje skalar (pojedyncza wartość) i
 * `["in", [...]]` (wiele wartości, wielkość liter operatora bez znaczenia).
 * Każdy inny kształt tablicowy (np. `["like", "%x%"]`) zwraca pustą tablicę
 * nie ma z czego bezpiecznie odtworzyć zaznaczeń checkboxów.
 */
export function rozpakujWartoscFiltraSzybkiego(rawValue) {
  if (rawValue === undefined || rawValue === null || rawValue === '') return []
  if (Array.isArray(rawValue)) {
    const operator = String(rawValue[0] ?? '').toLowerCase()
    if (operator === 'in') {
      return parsujWartoscWielokrotna(rawValue[1])
    }
    return []
  }
  return parsujWartoscWielokrotna(rawValue)
}

/**
 * Pakuje tablicę zaznaczonych stringów z powrotem do kształtu filtra
 * backendu: 0 wartości -> undefined (wywołujący usuwa klucz), 1 wartość ->
 * sam string (dotychczasowy kształt), N wartości -> `["in", [...]]`.
 */
export function spakujWartoscFiltraSzybkiego(wybrane) {
  const lista = parsujWartoscWielokrotna(wybrane)
  if (lista.length === 0) return undefined
  if (lista.length === 1) return lista[0]
  return ['in', lista]
}

/**
 * Buduje tekst chipa szybkiego filtra z etykiety pola i etykiet aktualnie
 * zaznaczonych wartości (nie ze stringów wartości: etykieta pochodzi z
 * katalogu opcji, np. dla pola Link etykieta może różnić się od wartości):
 * brak zaznaczeń -> sama etykieta pola (jak dziś dla pustego filtra), jedna
 * wartość -> `Etykieta: Wartość`, wiele -> `Etykieta: Pierwsza +N` (N =
 * liczba pozostałych, nie licząc pierwszej).
 */
export function etykietaChipaFiltraSzybkiego(etykietaPola, wybraneEtykiety) {
  const lista = (Array.isArray(wybraneEtykiety) ? wybraneEtykiety : [])
    .map((w) => (w == null ? '' : String(w)))
    .filter((w) => w.length > 0)
  if (lista.length === 0) return etykietaPola
  if (lista.length === 1) return `${etykietaPola}: ${lista[0]}`
  return `${etykietaPola}: ${lista[0]} +${lista.length - 1}`
}

/**
 * Rozstrzyga, czy dane pole na pasku szybkich filtrów dostaje wielokrotny
 * wybór (issue #127): Select lub Link poza User (patrz czyWielokrotnyWybor)
 * z jednym dodatkowym wyłączeniem specyficznym dla paska szybkiego, nie
 * dla rozwijanego Filter.vue: pole „Etap" (`status`) na `CRM Deal` ma
 * własną, zawężoną do aktywnego procesu listę opcji (utils/etapFiltr.js,
 * `opcjeEtapu`) i zostaje na dotychczasowym pojedynczym Autocomplete,
 * ten sam wyjątek musi być zastosowany identycznie w QuickFilterField.vue
 * (kolejność gałęzi v-else-if) i w ViewControls.vue (`quickFilterList`,
 * inicjalizacja `filter.value`), inaczej dla Etapu przyszłaby tablica tam,
 * gdzie komponent oczekuje pojedynczej wartości.
 */
export function czyWielokrotnyFiltrSzybki(doctype, filter) {
  if (doctype === 'CRM Deal' && filter?.fieldname === 'status') return false
  return czyWielokrotnyWybor(filter, 'in')
}

/**
 * Przełącza pojedynczą wartość w tablicy zaznaczonych (dodaje, gdy jej nie
 * ma, usuwa, gdy jest), immutable, zwraca nową tablicę.
 */
export function przelaczWartoscWielokrotna(wybrane, wartosc) {
  const lista = parsujWartoscWielokrotna(wybrane)
  return lista.includes(wartosc)
    ? lista.filter((w) => w !== wartosc)
    : [...lista, wartosc]
}
