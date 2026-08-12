// Piaskownica modelowania prowizji dla struktur partnerskich (administrator).
//
// Podział pracy: serwer liczy fakty niezmienne — `netto` i katalogowy
// `koszt` każdej pozycji ofertowej. Ten plik liczy WYŁĄCZNIE podział puli
// między firmę a partnera: `prowizja = stawka × ilość rozliczeniowa` oraz
// wynikający z niej `zysk`. Powód, dla którego ta arytmetyka żyje w
// przeglądarce, a nie na serwerze: właściciel edytuje do jedenastu stawek
// prowizji na żywo, szukając układu atrakcyjnego dla partnera i wciąż
// zyskownego dla firmy — przy odpytywaniu serwera na każde naciśnięcie
// klawisza (350 ms round-trip wg istniejącego debounce w
// KalkulatorCPTab.vue) narzędzie byłoby bezużyteczne. Nic z tych liczb nie
// jest zapisywane, nie zasila żadnego dokumentu i nie jest widoczne dla
// klienta — to czysty podgląd dla administratora budującego cennik do
// umowy partnerskiej.
//
// Obok stawek prowizji, analogicznie nadpisywalny jest też koszt (jednost-
// kowy i — tam, gdzie katalog go przewiduje — stały): gdy dostawca wycenił
// konkretną robotę inaczej niż katalog, administrator wstawia realną
// liczbę i od razu widzi prawdziwą pulę i zysk. To wciąż wyłącznie podgląd
// — serwer pozostaje jedynym źródłem prawdy o `netto`, a katalogowe koszty
// zwrócone w `wewnetrzne.linie` są wartością wyjściową (punktem startowym
// modelowania), a nie wiążącą.
//
// `KalkulatorTab.vue` (kalkulator PV/magazynów) ma w nagłówku regułę
// „ZERO pricing math in this file" — odstępujemy od niej tutaj ŚWIADOMIE
// i w WĄSKIM zakresie ograniczonym do tej piaskownicy. To nie jest
// precedens dla wyceny klienckiej: cena, dotacja i marża nadal liczą się
// wyłącznie na serwerze (crm/czyste_powietrze/), tu tylko rozdzielamy już
// obliczoną pulę.
//
// Wartości pieniężne trzymamy jako `Number`, nie `Decimal`. To świadome
// odstępstwo od ogólnej konwencji projektu ("Use Decimal for money"):
// wynik jest wyłącznie wyświetlany na ekranie administratora, nic z tych
// liczb nie trafia do zapisu ani do dokumentu, więc niedokładność float
// jest tu akceptowalna. Nie przenoś tego wzorca do kodu, który zapisuje
// kwoty.
//
// Kwoty w wynikowych wierszach i w `razem` są zaokrąglane do groszy przez
// `roundPln` (patrz `@/utils/money`) DOPIERO na wyjściu z `przeliczPodzial`,
// żeby to, co widzi administrator, sumowało się dokładnie — procenty
// (`zyskProc`, `marzaProc`) zostają liczone z surowych, niezaokrąglonych
// wartości. To wciąż wyłącznie zaokrąglenie do wyświetlenia; nic z tego nie
// jest zapisywane.

import { roundPln } from '@/utils/money'

/**
 * Parse a commission rate typed by the administrator into a finite,
 * non-negative number. Never returns NaN.
 *
 * Accepts a plain number, a string using either comma or dot as the
 * decimal separator, and plain or non-breaking spaces as thousands
 * separators (e.g. "3 000" or "3 000"). Anything else — including
 * empty input, null/undefined, and garbage — parses to 0. A negative
 * result is clamped to 0: a partner commission rate cannot be negative.
 *
 * @param {*} wartosc - raw rate input from the rate <input>
 * @returns {number} parsed, non-negative, finite rate
 */
export function parsujStawke(wartosc) {
  if (typeof wartosc === 'number') {
    return Number.isFinite(wartosc) && wartosc > 0 ? wartosc : 0
  }

  if (typeof wartosc !== 'string') return 0

  const bezSpacji = wartosc.replace(/[\s ]/g, '')
  if (bezSpacji === '') return 0

  const znormalizowany = bezSpacji.replace(',', '.')
  const parsed = Number(znormalizowany)

  if (!Number.isFinite(parsed) || parsed <= 0) return 0
  return parsed
}

/**
 * Alias of {@link parsujStawke} for use at call sites that parse a manually
 * entered cost rather than a commission rate. Same parsing rules apply
 * (comma/dot decimal separator, space thousands separator, never NaN,
 * negative clamped to zero) — the underlying arithmetic is identical, only
 * the name at the call site changes to match what is being parsed.
 *
 * `parsujStawke` itself is kept under its original name and behaviour
 * because it is already covered by tests above; do not rename it.
 *
 * @param {*} wartosc - raw cost input from a koszt <input>
 * @returns {number} parsed, non-negative, finite amount
 */
export const parsujKwote = parsujStawke

/**
 * Build the catalogue default rates for a set of internal lines, keyed by
 * line code.
 *
 * @param {Array<object>} linieWewnetrzne - `wewnetrzne.linie` from the server
 * @returns {Object<string, number>} catalogue rate per line code
 */
export function stawkiPoczatkowe(linieWewnetrzne) {
  const stawki = {}
  for (const linia of linieWewnetrzne || []) {
    stawki[linia.kod] = parsujStawke(linia.stawka_prowizji)
  }
  return stawki
}

/**
 * Merge the administrator's manually edited rates with a fresh server
 * response. Rates the administrator already typed for codes that are still
 * present survive; codes that are new get their catalogue default; codes
 * that disappeared from the offer are dropped. This is what lets the tool
 * compare several configurations against the same partner price list
 * without the edited rates resetting on every keystroke in the form above.
 *
 * Does not mutate either argument.
 *
 * @param {Object<string, number>} poprzednieStawki - rates currently held by the component
 * @param {Array<object>} linieWewnetrzne - `wewnetrzne.linie` from the latest server response
 * @returns {Object<string, number>} new merged rates object
 */
export function scalStawki(poprzednieStawki, linieWewnetrzne) {
  const scalone = {}
  for (const linia of linieWewnetrzne || []) {
    const kod = linia.kod
    scalone[kod] = Object.prototype.hasOwnProperty.call(poprzednieStawki || {}, kod)
      ? (poprzednieStawki[kod] ?? 0)
      : parsujStawke(linia.stawka_prowizji)
  }
  return scalone
}

/**
 * Build the catalogue default costs for a set of internal lines, keyed by
 * line code. Mirrors {@link stawkiPoczatkowe}, but each entry carries both
 * the per-unit and the fixed cost, because — unlike the commission rate —
 * a line can have a non-zero fixed cost on top of its per-unit cost (today
 * only `elewacja`, at 3000 zł).
 *
 * @param {Array<object>} linieWewnetrzne - `wewnetrzne.linie` from the server
 * @returns {Object<string, {jednostkowy: number, staly: number}>} catalogue cost per line code
 */
export function kosztyPoczatkowe(linieWewnetrzne) {
  const koszty = {}
  for (const linia of linieWewnetrzne || []) {
    koszty[linia.kod] = {
      jednostkowy: parsujKwote(linia.koszt_jednostkowy),
      staly: parsujKwote(linia.koszt_staly),
    }
  }
  return koszty
}

/**
 * Merge the administrator's manually edited costs with a fresh server
 * response. Mirrors {@link scalStawki} exactly, one level deeper: a manual
 * override for a code that still exists survives unchanged (as a shallow
 * copy, so the returned object never aliases the previous one); a newly
 * appeared code gets its catalogue `{jednostkowy, staly}` pair; a code that
 * disappeared from the offer is dropped.
 *
 * Does not mutate either argument.
 *
 * @param {Object<string, {jednostkowy: number, staly: number}>} poprzednieKoszty - costs currently held by the component
 * @param {Array<object>} linieWewnetrzne - `wewnetrzne.linie` from the latest server response
 * @returns {Object<string, {jednostkowy: number, staly: number}>} new merged costs object
 */
export function scalKoszty(poprzednieKoszty, linieWewnetrzne) {
  const scalone = {}
  for (const linia of linieWewnetrzne || []) {
    const kod = linia.kod
    scalone[kod] = Object.prototype.hasOwnProperty.call(poprzednieKoszty || {}, kod)
      ? { ...(poprzednieKoszty[kod] || {}) }
      : {
          jednostkowy: parsujKwote(linia.koszt_jednostkowy),
          staly: parsujKwote(linia.koszt_staly),
        }
  }
  return scalone
}

/**
 * Split the already-computed pool (netto − koszt) of each internal line
 * between the partner commission and the ProEnergy profit, using the
 * administrator's current rates and — optionally — the administrator's
 * manually overridden costs.
 *
 * `zysk` is deliberately allowed to go negative when the administrator
 * hands out too much commission — that is the whole point of the tool: a
 * negative number is the signal that a rate is unsustainable. Never clamp
 * it to zero.
 *
 * `koszty` is optional and, for any line code missing from it (including
 * when the argument is omitted entirely), the catalogue values from
 * `linieWewnetrzne` are used — this is what keeps every pre-existing call
 * site (and every pre-existing test) behaving exactly as before. When a
 * code has an entry, its `jednostkowy`/`staly` fields override the
 * catalogue independently: overriding only the unit cost still adds the
 * catalogue's fixed cost, and vice versa.
 *
 * `koszt` per line is always recomputed as `kosztJednostkowy ×
 * iloscRozliczeniowa + kosztStaly` — never read directly off the server's
 * `linia.koszt` — so an override is reflected consistently; this matches
 * the server's own invariant (verified by the fixture data in the tests
 * below), so it changes no existing result.
 *
 * `razem` also carries `zyskProc` (zysk ÷ netto) and `marzaProc` (pula ÷
 * netto), both as a percentage of total netto — computed once here so
 * callers never have to re-derive the same ratio from `razem.pula` /
 * `razem.netto` themselves.
 *
 * @param {Array<object>} linieWewnetrzne - `wewnetrzne.linie` from the server
 * @param {Object<string, number>} stawki - current per-code commission rates
 * @param {Object<string, {jednostkowy: number, staly: number}>} [koszty] - current per-code cost overrides
 * @returns {{linie: Array<object>, razem: object}} per-line split and totals
 */
export function przeliczPodzial(linieWewnetrzne, stawki, koszty) {
  // Dwie „widoki" na każdy wiersz: `publiczna` to kształt zwracany do
  // komponentu (kwoty zaokrąglone do groszy), `surowa` niesie te same kwoty
  // przed zaokrągleniem — potrzebne wyłącznie do policzenia procentów
  // (zyskProc/marzaProc) tak, żeby te nie dziedziczyły błędu zaokrąglenia.
  const obliczone = (linieWewnetrzne || []).map((linia) => {
    const netto = Number(linia.netto) || 0
    const iloscRozliczeniowa = Number(linia.ilosc_rozliczeniowa) || 0
    const stawkaKatalogowa = parsujStawke(linia.stawka_prowizji)
    const stawka = parsujStawke(stawki?.[linia.kod])

    const kosztJednostkowyKatalogowy = Number(linia.koszt_jednostkowy) || 0
    const kosztStalyKatalogowy = Number(linia.koszt_staly) || 0
    const nadpisanieKosztu = koszty?.[linia.kod]
    const kosztJednostkowy = nadpisanieKosztu?.jednostkowy !== undefined
      ? parsujKwote(nadpisanieKosztu.jednostkowy)
      : kosztJednostkowyKatalogowy
    const kosztStaly = nadpisanieKosztu?.staly !== undefined
      ? parsujKwote(nadpisanieKosztu.staly)
      : kosztStalyKatalogowy

    // Surowe (niezaokrąglone) wartości — patrz komentarz wyżej.
    const kosztSurowy = kosztJednostkowy * iloscRozliczeniowa + kosztStaly
    const pulaSurowa = netto - kosztSurowy
    const prowizjaSurowa = stawka * iloscRozliczeniowa
    const zyskSurowy = pulaSurowa - prowizjaSurowa

    // Kwoty pieniężne zaokrąglamy do groszy DOPIERO na wyjściu, po
    // wyliczeniu z pełnej precyzji — to jedyny sposób, żeby wiersz
    // wyświetlony administratorowi (grosze) sumował się dokładnie do
    // wyświetlanego wiersza „razem" poniżej (patrz `razem` niżej). Sam
    // podział nadal jest czystym podglądem: nic z tego nie jest zapisywane.
    // `netto` jest tu na równi z resztą: choć przychodzi z serwera (a nie
    // jest liczony w tym pliku), to wyświetla się w tym samym wierszu co
    // koszt/pula/prowizja/zysk, więc podlega tej samej regule — inaczej
    // kolumna netto mogłaby nie sumować się do wiersza „razem".
    const nettoZaokraglone = roundPln(netto)
    const koszt = roundPln(kosztSurowy)
    const pula = roundPln(pulaSurowa)
    const prowizja = roundPln(prowizjaSurowa)
    const zysk = roundPln(zyskSurowy)
    // Procenty NIE są kwotami — liczymy je z surowych (niezaokrąglonych)
    // wartości i nie zaokrąglamy tutaj w ogóle; komponent renderuje je z
    // dokładnością do 1 miejsca po przecinku.
    const zyskProc = netto > 0 ? (zyskSurowy / netto) * 100 : 0

    return {
      publiczna: {
        kod: linia.kod,
        iloscRozliczeniowa,
        jednostkaRozliczeniowa: linia.jednostka_rozliczeniowa,
        netto: nettoZaokraglone,
        koszt,
        kosztJednostkowy,
        kosztStaly,
        kosztJednostkowyKatalogowy,
        kosztStalyKatalogowy,
        stawka,
        stawkaKatalogowa,
        prowizja,
        pula,
        zysk,
        zyskProc,
      },
      // Surowe wartości (przed zaokrągleniem) — wyłącznie do policzenia
      // procentów niżej, żeby te nie dziedziczyły błędu zaokrąglenia kwoty.
      surowa: { netto, pula: pulaSurowa, prowizja: prowizjaSurowa, zysk: zyskSurowy },
    }
  })

  const linie = obliczone.map((x) => x.publiczna)

  // Sumujemy już zaokrąglone wartości wierszy (netto/koszt/pula/prowizja/
  // zysk), nie surowe — inaczej kolumna widoczna na ekranie (grosze) nie
  // zgadzałaby się z wierszem „razem" o reszty float rzędu pojedynczych
  // groszy. Każdy krok sumowania jest ponownie przepuszczony przez
  // roundPln, bo suma wielu wartości już-po-groszu wciąż może zostawić
  // binarną resztę w reprezentacji double (np. 10.13 + 10.13 w IEEE-754).
  // `netto` jest w tym zbiorze na równi z resztą pól — jest wyświetlane w
  // tym samym wierszu, więc `razem.netto` musi się sumować z tego, co
  // administrator faktycznie widzi w kolumnie, a nie z surowej wartości
  // serwera.
  const razem = linie.reduce(
    (acc, linia) => ({
      netto: roundPln(acc.netto + linia.netto),
      koszt: roundPln(acc.koszt + linia.koszt),
      pula: roundPln(acc.pula + linia.pula),
      prowizja: roundPln(acc.prowizja + linia.prowizja),
      zysk: roundPln(acc.zysk + linia.zysk),
    }),
    { netto: 0, koszt: 0, pula: 0, prowizja: 0, zysk: 0 },
  )

  // Podobnie jak zyskProc na poziomie wiersza: procenty sumaryczne liczymy
  // z surowych, niezaokrąglonych sum, nie z już zaokrąglonych
  // `razem.zysk`/`razem.pula` powyżej.
  const surowaSumaNetto = obliczone.reduce((suma, x) => suma + x.surowa.netto, 0)
  const surowaSumaPuli = obliczone.reduce((suma, x) => suma + x.surowa.pula, 0)
  const surowaSumaZysku = obliczone.reduce((suma, x) => suma + x.surowa.zysk, 0)
  razem.zyskProc = surowaSumaNetto > 0 ? (surowaSumaZysku / surowaSumaNetto) * 100 : 0
  razem.marzaProc = surowaSumaNetto > 0 ? (surowaSumaPuli / surowaSumaNetto) * 100 : 0

  return { linie, razem }
}
