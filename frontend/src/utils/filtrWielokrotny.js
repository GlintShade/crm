// Logika czysta (bez importu frappe-ui / @) dla operatora "jest jednym z"
// (in / not in) w Filter.vue, przy polach typu Select i Link, obsługiwanych
// kontrolką wielokrotnego wyboru (frappe-ui MultiSelect) zamiast pola
// tekstowego z wartościami po przecinku (issue #103).
//
// Serializacja filtra do backendu i zapisanych widoków NIE zmienia się:
// wartość operatora in/not in to tablica stringów, dokładnie jak dotychczas
// po splicie po przecinku w Filter.vue::transformIn. Ten moduł tylko
// normalizuje wartość używaną jako `modelValue` kontrolki wielokrotnego
// wyboru (bez względu na to, czy przyszła jako tablica z zapisanego widoku,
// czy jako string sprzed tej zmiany) i scala listę opcji z aktualnie
// zaznaczonymi wartościami, żeby zaznaczenie było widoczne nawet zanim/gdy
// wyszukiwanie (Link) zawęzi listę wyników i akurat pominie już wybraną
// wartość.
//
// Frappe-free (żadnego `__()` na poziomie modułu — patrz PUŁAPKA w
// etapFiltr.js / etykietaMoje.js: eager chunk wywołuje moduł przed
// zainicjowaniem i18n), testowalne bezpośrednio przez vitest.

/**
 * Normalizuje wartość filtra in/not in do tablicy niepustych stringów.
 * Przyjmuje zarówno tablicę (kształt zapisany przez transformIn / wczytany
 * z zapisanego widoku, np. `["in", ["Nowy", "Próba kontaktu"]]`), jak i
 * string sprzed tej zmiany (wartości rozdzielone przecinkiem, z polem
 * tekstowym) — dla kompatybilności wstecz z dowolnym stanem `f.value`
 * napotkanym w locie. Wartości są przycinane (`trim`), puste odrzucane.
 */
export function parsujWartoscWielokrotna(value) {
  if (Array.isArray(value)) {
    return value
      .map((v) => String(v ?? '').trim())
      .filter((v) => v.length > 0)
  }
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((v) => v.trim())
      .filter((v) => v.length > 0)
  }
  return []
}

/**
 * Scala listę opcji (katalog Select albo wyniki wyszukiwania Link) z
 * aktualnie zaznaczonymi wartościami: każda zaznaczona wartość, która nie
 * jest (już/jeszcze) w `opcje`, dostaje opcję zastępczą `{ label: wartość,
 * value: wartość }`, dołączaną na końcu listy. Zachowuje kolejność `opcje`
 * i nie duplikuje wartości już tam obecnych.
 */
export function scalOpcjeZZaznaczonymi(opcje, zaznaczoneWartosci) {
  const listaOpcji = Array.isArray(opcje) ? opcje : []
  const listaZaznaczonych = parsujWartoscWielokrotna(zaznaczoneWartosci)
  const znaneWartosci = new Set(listaOpcji.map((opcja) => opcja.value))
  const brakujace = listaZaznaczonych
    .filter((wartosc) => !znaneWartosci.has(wartosc))
    .map((wartosc) => ({ label: wartosc, value: wartosc }))
  return [...listaOpcji, ...brakujace]
}
