// Piaskownica modelowania prowizji dla struktur partnerskich (administrator).
//
// Podział pracy: serwer liczy fakty niezmienne — `netto` i `koszt` każdej
// pozycji ofertowej. Ten plik liczy WYŁĄCZNIE podział puli między firmę
// a partnera: `prowizja = stawka × ilość rozliczeniowa` oraz wynikający z
// niej `zysk`. Powód, dla którego ta arytmetyka żyje w przeglądarce, a nie
// na serwerze: właściciel edytuje do jedenastu stawek prowizji na żywo,
// szukając układu atrakcyjnego dla partnera i wciąż zyskownego dla firmy —
// przy odpytywaniu serwera na każde naciśnięcie klawisza (350 ms round-trip
// wg istniejącego debounce w KalkulatorCPTab.vue) narzędzie byłoby
// bezużyteczne. Nic z tych liczb nie jest zapisywane, nie zasila żadnego
// dokumentu i nie jest widoczne dla klienta — to czysty podgląd dla
// administratora budującego cennik do umowy partnerskiej.
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
 * Split the already-computed pool (netto − koszt) of each internal line
 * between the partner commission and the ProEnergy profit, using the
 * administrator's current rates.
 *
 * `zysk` is deliberately allowed to go negative when the administrator
 * hands out too much commission — that is the whole point of the tool: a
 * negative number is the signal that a rate is unsustainable. Never clamp
 * it to zero.
 *
 * `razem` also carries `zyskProc` (zysk ÷ netto) and `marzaProc` (pula ÷
 * netto), both as a percentage of total netto — computed once here so
 * callers never have to re-derive the same ratio from `razem.pula` /
 * `razem.netto` themselves.
 *
 * @param {Array<object>} linieWewnetrzne - `wewnetrzne.linie` from the server
 * @param {Object<string, number>} stawki - current per-code commission rates
 * @returns {{linie: Array<object>, razem: object}} per-line split and totals
 */
export function przeliczPodzial(linieWewnetrzne, stawki) {
  const linie = (linieWewnetrzne || []).map((linia) => {
    const netto = Number(linia.netto) || 0
    const koszt = Number(linia.koszt) || 0
    const iloscRozliczeniowa = Number(linia.ilosc_rozliczeniowa) || 0
    const stawka = parsujStawke(stawki?.[linia.kod])
    const pula = netto - koszt
    const prowizja = stawka * iloscRozliczeniowa
    const zysk = pula - prowizja
    const zyskProc = netto > 0 ? (zysk / netto) * 100 : 0

    return {
      kod: linia.kod,
      iloscRozliczeniowa,
      jednostkaRozliczeniowa: linia.jednostka_rozliczeniowa,
      netto,
      koszt,
      kosztJednostkowy: Number(linia.koszt_jednostkowy) || 0,
      kosztStaly: Number(linia.koszt_staly) || 0,
      stawka,
      prowizja,
      pula,
      zysk,
      zyskProc,
    }
  })

  const razem = linie.reduce(
    (acc, linia) => ({
      netto: acc.netto + linia.netto,
      koszt: acc.koszt + linia.koszt,
      pula: acc.pula + linia.pula,
      prowizja: acc.prowizja + linia.prowizja,
      zysk: acc.zysk + linia.zysk,
    }),
    { netto: 0, koszt: 0, pula: 0, prowizja: 0, zysk: 0 },
  )
  razem.zyskProc = razem.netto > 0 ? (razem.zysk / razem.netto) * 100 : 0
  razem.marzaProc = razem.netto > 0 ? (razem.pula / razem.netto) * 100 : 0

  return { linie, razem }
}
