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
// Issue ops#410: zarezerwowany klucz z wylaczonymi (odznaczonymi w oknie
// „Filtr") warunkami i grupami. Serwer wycina go razem z KLUCZ_GRUP
// (`crm.volteo_grupy_filtrow.wydziel_grupy`) i nigdy nie filtruje wg niego.
// Ksztalt: `{ wspolne: {pole: przewod}, grupy: [{wylaczona, warunki:
// {pole: przewod}, wylaczone: [pole]}] }`. `grupy` (pelny zrzut ukladu grup)
// jest obecne tylko, gdy cos w grupach jest wylaczone, i wtedy jest
// zrodlem prawdy dla grup w oknie; filtry wspolne zawsze wracaja z echa
// serwera (pasek szybkich filtrow edytuje je poza oknem), a `wspolne`
// dokleja tylko wylaczone wiersze. Brak klucza = wszystko aktywne.
export const KLUCZ_NIEAKTYWNE = 'volteo_nieaktywne'
export const MAX_GRUP = 10
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
    if (klucz !== KLUCZ_GRUP && klucz !== KLUCZ_NIEAKTYWNE) filtryWspolne[klucz] = wartosc
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
export function dodajGrupe(grupy, grupa) {
  return [...(grupy || []), grupa]
}

/** Usuwa grupę o indeksie `indeksGrupy`. Nie mutuje `grupy`. Indeks poza
 * zakresem zwraca `grupy` bez zmian (kopię) zamiast rzucać wyjątek. */
export function usunGrupe(grupy, indeksGrupy) {
  return (grupy || []).filter((_, i) => i !== indeksGrupy)
}

/** Grupa w stanie okna „Filtr": `{ wylaczona, warunki }` (ops#410). */
export function nowaGrupa(warunki) {
  return { wylaczona: false, warunki }
}

/** Dodaje `warunek` na końcu grupy o indeksie `indeksGrupy`. Nie mutuje
 * `grupy` ani grup składowych. Indeks poza zakresem zwraca `grupy` bez
 * zmian. */
export function dodajWarunekDoGrupy(grupy, indeksGrupy, warunek) {
  const listaGrup = grupy || []
  if (indeksGrupy < 0 || indeksGrupy >= listaGrup.length) return listaGrup
  return listaGrup.map((grupa, i) =>
    i === indeksGrupy ? { ...grupa, warunki: [...grupa.warunki, warunek] } : grupa,
  )
}

/** Usuwa warunek o indeksie `indeksWarunku` z grupy `indeksGrupy`. Jeśli
 * grupa nie ma już żadnego warunku, CAŁA grupa jest usuwana (grupa bez
 * warunków nie ma sensu w UI ani na przewodzie, patrz `polaczGrupy`). Nie
 * mutuje `grupy`. */
export function usunWarunekZGrupy(grupy, indeksGrupy, indeksWarunku) {
  const listaGrup = grupy || []
  if (indeksGrupy < 0 || indeksGrupy >= listaGrup.length) return listaGrup
  const warunki = listaGrup[indeksGrupy].warunki.filter((_, i) => i !== indeksWarunku)
  if (warunki.length === 0) return usunGrupe(listaGrup, indeksGrupy)
  return listaGrup.map((grupa, i) => (i === indeksGrupy ? { ...grupa, warunki } : grupa))
}

/** Podmienia warunek `indeksWarunku` w grupie `indeksGrupy` na
 * `nowyWarunek` (zmiana POLA warunku; zmiana operatora/wartości mutuje
 * wiersz wprost w Filter.vue). Nie mutuje `grupy`. */
export function podmienWarunekWGrupy(grupy, indeksGrupy, indeksWarunku, nowyWarunek) {
  const listaGrup = grupy || []
  if (indeksGrupy < 0 || indeksGrupy >= listaGrup.length) return listaGrup
  return listaGrup.map((grupa, i) =>
    i === indeksGrupy
      ? {
          ...grupa,
          warunki: grupa.warunki.map((w, j) => (j === indeksWarunku ? nowyWarunek : w)),
        }
      : grupa,
  )
}

/** ops#410: włącza/wyłącza CAŁĄ grupę. Warunki zachowują własny stan. */
export function przelaczGrupe(grupy, indeksGrupy) {
  return (grupy || []).map((grupa, i) =>
    i === indeksGrupy ? { ...grupa, wylaczona: !grupa.wylaczona } : grupa,
  )
}

/** ops#410: włącza/wyłącza jeden warunek grupy (kopia wiersza z odwróconą
 * flagą `nieaktywny`). */
export function przelaczWarunekWGrupie(grupy, indeksGrupy, indeksWarunku) {
  const listaGrup = grupy || []
  if (indeksGrupy < 0 || indeksGrupy >= listaGrup.length) return listaGrup
  const w = listaGrup[indeksGrupy].warunki[indeksWarunku]
  if (!w) return listaGrup
  return podmienWarunekWGrupy(listaGrup, indeksGrupy, indeksWarunku, { ...w, nieaktywny: !w.nieaktywny })
}

/**
 * Licznik do badge'a „Filtr N": warunki wspólne i warunki grup, ale tylko
 * AKTYWNE (ops#410): bez wierszy z `nieaktywny` i bez warunków grup
 * wyłączonych. `wspolne` to dowolna kolekcja wierszy (Set/tablica).
 */
export function liczbaWarunkowLacznie(wspolne, grupy) {
  const zWspolnych = Array.from(wspolne || []).filter((w) => !w.nieaktywny).length
  const zGrup = (grupy || []).reduce(
    (suma, grupa) =>
      grupa && !grupa.wylaczona ? suma + grupa.warunki.filter((w) => !w.nieaktywny).length : suma,
    0,
  )
  return zWspolnych + zGrup
}

/** Łączna liczba wierszy w oknie, także wyłączonych (do przycisku „wyczyść"). */
export function liczbaWierszyLacznie(wspolne, grupy) {
  return (
    Array.from(wspolne || []).length +
    (grupy || []).reduce((suma, grupa) => suma + (grupa ? grupa.warunki.length : 0), 0)
  )
}

/** Wycina z `filtry` zarezerwowany `KLUCZ_NIEAKTYWNE`: `{ wspolne, grupy }`
 * (`grupy` to tablica albo `null`, gdy brak zrzutu). Kształt niepoprawny =
 * brak (stare/uszkodzone zapisy zachowują się jak „wszystko aktywne"). */
export function wydzielNieaktywne(filtry) {
  const surowe = filtry && typeof filtry === 'object' ? filtry[KLUCZ_NIEAKTYWNE] : null
  const jestObiektem = (x) => x && typeof x === 'object' && !Array.isArray(x)
  if (!jestObiektem(surowe)) return { wspolne: {}, grupy: null }
  return {
    wspolne: jestObiektem(surowe.wspolne) ? surowe.wspolne : {},
    grupy: Array.isArray(surowe.grupy) ? surowe.grupy.filter(jestObiektem) : null,
  }
}

/** Dokleja `KLUCZ_NIEAKTYWNE` do `filtry` (nowy obiekt), ale tylko gdy jest
 * co zapisać: bez wyłączonych wierszy kształt jest identyczny jak sprzed
 * ops#410. */
export function polaczNieaktywne(filtry, { wspolne, grupy }) {
  const wynik = { ...(filtry || {}) }
  const maWspolne = wspolne && Object.keys(wspolne).length > 0
  const maGrupy = Array.isArray(grupy) && grupy.length > 0
  if (maWspolne || maGrupy) {
    wynik[KLUCZ_NIEAKTYWNE] = {
      ...(maWspolne ? { wspolne } : {}),
      ...(maGrupy ? { grupy } : {}),
    }
  }
  return wynik
}

/**
 * Buduje słownik filtrów do wysłania (`list.params.filters`) ze stanu okna.
 * Do zapytań trafiają WYŁĄCZNIE aktywne warunki aktywnych grup; wiersze
 * wyłączone idą osobno pod `KLUCZ_NIEAKTYWNE`. `doPrzewodu(wiersze)` zamienia
 * tablicę wierszy na słownik przewodowy (Filter.vue: `parseFilters` na
 * kopiach), `pomin(wiersz)` wyklucza wiersze, których nie wysyłamy wcale
 * (np. pusty wielokrotny wybór).
 */
export function zbudujPrzewod(wspolne, grupy, doPrzewodu, pomin = () => false) {
  const brane = (w) => !pomin(w)
  const lista = Array.from(wspolne || []).filter(brane)
  const listaGrup = grupy || []
  const aktywneGrupy = listaGrup
    .filter((g) => !g.wylaczona)
    .map((g) => doPrzewodu(g.warunki.filter((w) => brane(w) && !w.nieaktywny)))
  const trzebaZrzut = listaGrup.some((g) => g.wylaczona || g.warunki.some((w) => w.nieaktywny))
  const zrzut = trzebaZrzut
    ? listaGrup
        .map((g) => {
          const warunki = g.warunki.filter(brane)
          return {
            wylaczona: !!g.wylaczona,
            warunki: doPrzewodu(warunki),
            wylaczone: warunki.filter((w) => w.nieaktywny).map((w) => w.fieldname),
          }
        })
        .filter((g) => Object.keys(g.warunki).length > 0)
    : null
  return polaczNieaktywne(
    polaczGrupy(doPrzewodu(lista.filter((w) => !w.nieaktywny)), aktywneGrupy),
    { wspolne: doPrzewodu(lista.filter((w) => w.nieaktywny)), grupy: zrzut },
  )
}

/** Grupy okna z echa serwera: z zrzutu `KLUCZ_NIEAKTYWNE`, gdy jest (to on
 * niesie grupy wyłączone i flagi warunków), inaczej z `volteo_grupy`
 * (stare widoki: wszystko aktywne). `doWierszy(słownik)` -> tablica wierszy. */
export function odtworzGrupy(filtry, doWierszy) {
  const { grupy: zrzut } = wydzielNieaktywne(filtry)
  if (zrzut) {
    return zrzut.map((g) => {
      const wylaczone = new Set(Array.isArray(g.wylaczone) ? g.wylaczone : [])
      return {
        wylaczona: !!g.wylaczona,
        warunki: doWierszy(g.warunki || {}).map((w) =>
          wylaczone.has(w.fieldname) ? { ...w, nieaktywny: true } : w,
        ),
      }
    })
  }
  return wydzielGrupy(filtry).grupy.map((g) => nowaGrupa(doWierszy(g)))
}

/** Wiersze wspólne: aktywne z echa plus wyłączone z `KLUCZ_NIEAKTYWNE`
 * (pole aktywne w echu wygrywa, np. po ustawieniu go z paska szybkich). */
export function odtworzWspolne(aktywne, filtry, doWierszy) {
  const lista = Array.from(aktywne || [])
  const zajete = new Set(lista.map((w) => w.fieldname))
  const wylaczone = doWierszy(wydzielNieaktywne(filtry).wspolne)
    .filter((w) => !zajete.has(w.fieldname))
    .map((w) => ({ ...w, nieaktywny: true }))
  return [...lista, ...wylaczone]
}

/** Układa `nowe` w kolejności wierszy z `stare` (po `fieldname`), nieznane
 * na końcu: wyłączenie warunku nie przerzuca go na dół listy. */
export function uporzadkujWgPoprzednich(nowe, stare) {
  const indeks = new Map(Array.from(stare || []).map((w, i) => [w.fieldname, i]))
  const poz = (w) => (indeks.has(w.fieldname) ? indeks.get(w.fieldname) : Infinity)
  return Array.from(nowe || []).sort((a, b) => (poz(a) === poz(b) ? 0 : poz(a) < poz(b) ? -1 : 1))
}
