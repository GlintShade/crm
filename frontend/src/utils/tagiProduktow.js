// Logika czysta (frappe-free/Vue-free) dla modelu "produkty leada jako
// tagi" (issue ops#150, decyzja właściciela 2026-09-16, model A+): pole
// Data (`custom_posiadane_produkty`/`custom_produkt_procesu` na `CRM
// Lead`) zostaje nośnikiem -- string tokenów ze słownika w kanonicznej
// kolejności, złączonych "+", bez wolnego tekstu -- a prezentacja, edycja
// i filtrowanie działają jak na zbiorze tagów.
//
// Kanoniczny słownik (KOLEJNOSC_PRODUKTOW / KOLEJNOSC_PRODUKTOW_PROCESU,
// `crm/volteo_leady_import.py`) NIE jest tu duplikowany: backend dokłada
// go jako `field.options` (string złączony "\n", dokładnie jak dla pola
// Select) i `field.volteo_tagi: 1` do wyników
// `crm.api.doc.get_quick_filters`/`get_filterable_fields` (ops#150 pkt 3)
// -- ten moduł tylko rozpoznaje/rozbija/składa na podstawie tego, co
// przyszło z serwera w `field`.
//
// `NAZWY_POL_TAGOW` poniżej jest jedynym dopuszczalnym wyjątkiem od "bez
// duplikowania słownika w JS": to lista dwóch NAZW PÓL (nie tokenów).
// Powód: `SidePanelLayout.vue` renderuje pole na podstawie definicji
// layoutu (`CRM Fields Layout`), która NIE przechodzi przez
// `get_filterable_fields`/`get_quick_filters` i więc nie niesie
// `field.volteo_tagi` -- bez tego fallbacku panel boczny nie rozpoznałby
// tych dwóch pól jako tagowych wcale. `opcjeTagow` mimo to NIGDY nie
// zgaduje tokenów z tej listy -- zawsze czyta je z `field.options`,
// dostarczonego przez wywołującego (patrz `TagiProduktowInput.vue`, która
// dociąga `options` osobnym zapytaniem do `get_filterable_fields`).
//
// Frappe-free (żadnego `__()` na poziomie modułu, patrz PUŁAPKA w
// etapFiltr.js/filtrSzybki.js: eager chunk woła moduł przed i18n),
// testowalne bezpośrednio przez vitest.

const NAZWY_POL_TAGOW = new Set([
  'custom_posiadane_produkty',
  'custom_produkt_procesu',
])

/**
 * Rozstrzyga, czy `field` jest polem "produktów leada" (tagów): prawda,
 * gdy backend dołożył `field.volteo_tagi` (List/Filter/QuickFilter --
 * `get_filterable_fields`/`get_quick_filters`, ops#150 pkt 3), ALBO gdy
 * `field.fieldname` jest jedną z dwóch znanych nazw (fallback dla
 * kontekstów, które nie przechodzą przez te dwie funkcje, np. panel
 * boczny -- patrz komentarz modułu wyżej).
 */
export function czyPoleTagow(field) {
  if (!field) return false
  return Boolean(field.volteo_tagi) || NAZWY_POL_TAGOW.has(field.fieldname)
}

/**
 * Rozbija string `+`-łączony (`"PV+PC+AUDYT"`) na tablicę tokenów, w
 * kolejności występowania w stringu (NIE kanonicznej -- patrz `zlaczTagi`
 * dla ustawienia w kanonicznej kolejności). Puste segmenty (string pusty,
 * podwójny `+`, białe znaki) odrzucone. Wartość nie będąca stringiem
 * (`null`/`undefined`/inne) -> pusta tablica.
 */
export function rozbijTagi(str) {
  if (typeof str !== 'string') return []
  return str
    .split('+')
    .map((token) => token.trim())
    .filter((token) => token.length > 0)
}

/**
 * Składa listę tokenów z powrotem do stringu `+`-łączonego, w KANONICZNEJ
 * kolejności (`kolejnosc`, np. `opcjeTagow(field)`) -- nie w kolejności
 * `list`. Duplikaty w `list` scalane (Set). Token spoza `kolejnosc` jest
 * pominięty (model A+ zakłada wyłącznie wartości ze słownika, bez
 * wolnego tekstu -- patrz brief ops#150), więc `zlaczTagi` jest też
 * naturalnym filtrem odrzucającym nieznane tokeny, gdyby jakieś dotarły.
 */
export function zlaczTagi(list, kolejnosc) {
  const zbior = new Set(Array.isArray(list) ? list : [])
  const porzadek = Array.isArray(kolejnosc) ? kolejnosc : []
  return porzadek.filter((token) => zbior.has(token)).join('+')
}

/**
 * Zwraca kanoniczną listę tokenów dla `field` (kolejność prezentacji w
 * UI: checkboxy paska szybkich filtrów, opcje MultiSelect w Filter.vue,
 * opcje dodawania w TagiProduktowInput.vue), czytając `field.options`
 * (string złączony "\n", tak jak dla pola Select -- patrz
 * `Filter.vue::getSelectOptions`). Brak `field` albo `options` nie będące
 * stringiem -> pusta tablica (żaden token do zaoferowania).
 */
export function opcjeTagow(field) {
  if (!field || typeof field.options !== 'string' || !field.options) return []
  return field.options
    .split('\n')
    .map((token) => token.trim())
    .filter((token) => token.length > 0)
}
