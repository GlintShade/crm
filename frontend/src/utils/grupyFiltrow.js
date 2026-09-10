// Logika czysta (bez importu frappe-ui / @, bez __()) dla grup filtrów
// ORAZ / ALBO w oknie „Filtr" listy leadów (issue #129, sekcja „Grupy
// ALBO" w Filter.vue). Ten sam kontrakt danych co backend
// (`crm.volteo_grupy_filtrow`, fork): zarezerwowany klucz `volteo_grupy`
// w słowniku filtrów, wartość = lista słowników, każdy słownik to JEDNA
// grupa warunków ORAZ w tym samym kształcie co zwykłe filtry
// (`{pole: wartość}` / `{pole: [operator, wartość]}`). Semantyka:
// `(grupa1 ALBO grupa2 ALBO ...) ORAZ (pozostałe klucze słownika)`. Pusta
// lista grup (albo brak klucza) = brak wpływu - stare zapisane widoki bez
// klucza wracają bez zmian z `wydzielGrupy`/`polaczGrupy`.
//
// Limity (`MAX_GRUP`, `MAX_WARUNKOW_W_GRUPIE`) są tu WYŁĄCZNIE podpowiedzią
// UI (wyłączenie przycisku „Dodaj grupę"/„Dodaj warunek" po przekroczeniu)
// - jedynym autorytatywnym źródłem jest backend (`crm.volteo_grupy_filtrow`,
// te same wartości), który waliduje niezależnie od tego, co wysłał
// frontend.
//
// Rozróżnienie dwóch reprezentacji grupy w tym module:
//   - "wiersz warunku" (Filter.vue): obiekt `{ field, fieldname, operator,
//     value }`, ten sam kształt co wiersz filtrów wspólnych - funkcje
//     strukturalne (dodaj/usuń/podmień) w tym pliku operują na TABLICACH
//     takich wierszy (Filter.vue trzyma `grupy` jako tablicę tablic
//     wierszy) i są celowo generyczne względem kształtu elementu (nie
//     zaglądają do środka wiersza), więc testują się na dowolnych
//     wartościach niżej;
//   - "słownik przewodowy" (`{pole: wartość}`): kształt wysyłany do
//     backendu pod kluczem `volteo_grupy` - `wydzielGrupy`/`polaczGrupy`
//     operują na TEJ reprezentacji (to jest to, co faktycznie leci przez
//     sieć i co jest zapisywane w `CRM View Settings.filters`).
// Filter.vue samo konwertuje między obiema reprezentacjami (przez
// `parseFilters`/`convertFilters`, niezmienione przez ten issue) przy
// każdym `apply()`.
//
// Frappe-free (żadnego `__()` na poziomie modułu, patrz PUŁAPKA w
// etapFiltr.js/etykietaMoje.js: eager chunk woła moduł przed i18n),
// testowalne bezpośrednio przez vitest.

export const KLUCZ_GRUP = 'volteo_grupy'
export const MAX_GRUP = 5
export const MAX_WARUNKOW_W_GRUPIE = 10

/**
 * Wydziela klucz `KLUCZ_GRUP` ze słownika filtrów (kształt przewodowy,
 * np. `list.params.filters`). Zwraca `{ filtryWspolne, grupy }`:
 * `filtryWspolne` to NOWY obiekt (immutability, coding-style.md) bez
 * klucza grup; `grupy` to wartość spod tego klucza, jeśli jest tablicą,
 * inaczej pusta tablica (brak klucza, `null`, kształt niepoprawny - ta
 * funkcja nie waliduje, tylko wydziela; walidacja kształtu jest wyłącznie
 * po stronie backendu, patrz nagłówek modułu).
 */
export function wydzielGrupy(filtry) {
  if (!filtry || typeof filtry !== 'object') return { filtryWspolne: {}, grupy: [] }

  const filtryWspolne = {}
  for (const [klucz, wartosc] of Object.entries(filtry)) {
    if (klucz !== KLUCZ_GRUP) filtryWspolne[klucz] = wartosc
  }

  const surowe = filtry[KLUCZ_GRUP]
  const grupy = Array.isArray(surowe) ? surowe : []
  return { filtryWspolne, grupy }
}

/**
 * Odwrotność `wydzielGrupy`: scala `filtryWspolne` (słownik przewodowy) z
 * `grupy` (tablica słowników przewodowych, jeden na grupę) w JEDEN nowy
 * słownik filtrów, gotowy do wysłania jako `list.params.filters`. Grupy
 * bez ŻADNEGO warunku (`Object.keys(grupa).length === 0`) są POMIJANE -
 * "Pusta grupa nie serializuje się" (kontrakt issue #129): grupa pusta w
 * zapytaniu `frappe.get_list` dopasowałaby WSZYSTKIE wiersze, co
 * zepsułoby semantykę ALBO (jedna pusta grupa = "pokaż wszystko"), więc
 * nie ma prawa opuścić tej funkcji. Jeśli po odsianiu pustych grup nic
 * nie zostało, klucz `KLUCZ_GRUP` jest CAŁKOWICIE pomijany w wyniku (nie
 * `[]`) - dokładnie taki sam kształt, jaki wysyłał kod sprzed tego issue,
 * więc stare zapisane widoki i zwykłe filtrowanie bez grup nie zauważają
 * różnicy. Nie mutuje `filtryWspolne` ani `grupy`.
 */
export function polaczGrupy(filtryWspolne, grupy) {
  const wynik = { ...(filtryWspolne || {}) }
  const niepuste = (grupy || []).filter(
    (grupa) => grupa && Object.keys(grupa).length > 0,
  )
  if (niepuste.length > 0) wynik[KLUCZ_GRUP] = niepuste
  return wynik
}

/** Dodaje nową grupę (tablica wierszy warunków) na końcu `grupy`. Nie
 * mutuje `grupy` - zwraca nowa tablicę. Nie sprawdza `MAX_GRUP`, to
 * odpowiedzialność wywołującego (Filter.vue, przed wywołaniem tej
 * funkcji) - backend i tak jest autorytatywnym źródłem limitu. */
export function dodajGrupe(grupy, nowaGrupa) {
  return [...(grupy || []), nowaGrupa]
}

/** Usuwa grupę o indeksie `indeksGrupy`. Nie mutuje `grupy`. Indeks poza
 * zakresem zwraca `grupy` bez zmian (kopię) zamiast rzucać wyjątek. */
export function usunGrupe(grupy, indeksGrupy) {
  return (grupy || []).filter((_, i) => i !== indeksGrupy)
}

/** Dodaje `warunek` na końcu grupy o indeksie `indeksGrupy`. Nie mutuje
 * `grupy` ani żadnej z jej grup składowych - kopiuje zarówno tablicę
 * grup, jak i tablicę warunków tej JEDNEJ grupy, którą zmienia. Indeks
 * poza zakresem zwraca `grupy` bez zmian. */
export function dodajWarunekDoGrupy(grupy, indeksGrupy, warunek) {
  const listaGrup = grupy || []
  if (indeksGrupy < 0 || indeksGrupy >= listaGrup.length) return listaGrup
  return listaGrup.map((grupa, i) =>
    i === indeksGrupy ? [...grupa, warunek] : grupa,
  )
}

/** Usuwa warunek o indeksie `indeksWarunku` z grupy o indeksie
 * `indeksGrupy`. Jeśli po usunięciu grupa nie ma już ŻADNEGO warunku, CAŁA
 * grupa jest usuwana (auto-sprzątanie: grupa bez warunków nie ma sensu w
 * UI ani na przewodzie, patrz `polaczGrupy` - to samo zachowanie, tylko
 * zastosowane wcześniej, po stronie stanu UI). Nie mutuje `grupy`. */
export function usunWarunekZGrupy(grupy, indeksGrupy, indeksWarunku) {
  const listaGrup = grupy || []
  if (indeksGrupy < 0 || indeksGrupy >= listaGrup.length) return listaGrup
  const nowaGrupa = listaGrup[indeksGrupy].filter((_, i) => i !== indeksWarunku)
  if (nowaGrupa.length === 0) return usunGrupe(listaGrup, indeksGrupy)
  return listaGrup.map((grupa, i) => (i === indeksGrupy ? nowaGrupa : grupa))
}

/** Podmienia warunek o indeksie `indeksWarunku` w grupie o indeksie
 * `indeksGrupy` na `nowyWarunek` (zmiana POLA warunku - zmiana
 * operatora/wartości bez zmiany pola mutuje wiersz wprost w Filter.vue,
 * tak jak dla filtrów wspólnych, patrz JSDoc modułu). Nie mutuje `grupy`. */
export function podmienWarunekWGrupy(grupy, indeksGrupy, indeksWarunku, nowyWarunek) {
  const listaGrup = grupy || []
  if (indeksGrupy < 0 || indeksGrupy >= listaGrup.length) return listaGrup
  return listaGrup.map((grupa, i) =>
    i === indeksGrupy
      ? grupa.map((warunek, j) => (j === indeksWarunku ? nowyWarunek : warunek))
      : grupa,
  )
}

/**
 * Liczba warunków łącznie: warunki wspólne (`iloscWspolnych`, rozmiar
 * `Set`/tablicy filtrów wspólnych Filter.vue) plus suma warunków we
 * WSZYSTKICH grupach - do badge'a „Filtr N" na przycisku otwierającym
 * popup.
 */
export function liczbaWarunkowLacznie(iloscWspolnych, grupy) {
  const zWspolnych = iloscWspolnych || 0
  const zGrup = (grupy || []).reduce((suma, grupa) => suma + (grupa ? grupa.length : 0), 0)
  return zWspolnych + zGrup
}
