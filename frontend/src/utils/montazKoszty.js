// Koszty montażu/realizacji — panel kosztów rzeczywistych (administrator).
// Nazwa pliku odnosi się do DOMENY (koszty montażu), nie do zakładki, w
// której renderuje się korzystający z niego komponent: `MontazKosztyPanel.vue`
// montowany jest na dole zakładki Zestaw (ZestawTab.vue), nie w zakładce
// Montaż — tak zdecydował właściciel po tym, jak wcześniejsza wersja panelu
// przez pomyłkę wylądowała w MontazTab.vue.
//
// WYŁĄCZNIE prezentacyjna arytmetyka, analogicznie do cpMarza.js/pvBreakdown.js:
// serwer (`crm.api.koszty.volteo_koszty_zapisz`) jest jedynym źródłem prawdy
// przy zapisie i przelicza wynik od nowa z tego, co faktycznie wysłano. Ten
// plik istnieje wyłącznie po to, żeby administrator widział marżę/zysk na
// żywo, w trakcie wpisywania rzeczywistych kosztów montażu, zanim jeszcze
// cokolwiek zapisze — bez tego każde naciśnięcie klawisza wymagałoby
// round-tripu do serwera.
//
// Wartości pieniężne trzymamy jako `Number`, nie `Decimal` — świadome
// odstępstwo od ogólnej konwencji projektu ("Use Decimal for money"), z tego
// samego powodu co w cpMarza.js: nic z tych liczb nie jest zapisywane wprost,
// `zbudujPayload` wysyła je do serwera, który je re-waliduje i przelicza
// autorytatywnie. Zaokrąglanie do groszy (`roundPln`, `@/utils/money`)
// dzieje się na wyjściu z każdej funkcji — linie i `razem` sumują się
// dokładnie tak, jak widzi je administrator na ekranie.
//
// Snapshot (`custom_koszty_json`, wersja 1) jest permlevel-2 na `CRM Deal`:
// Frappe po cichu usuwa to pole z odpowiedzi dla ról bez uprawnienia do
// odczytu, więc `parseSnapshot` musi cicho zwracać `null` na każdy
// nieprawidłowy/nieobecny/niesparsowalny wejście — panel wtedy po prostu nie
// renderuje niczego (patrz MontazKosztyPanel.vue), zamiast rzucać błędem w
// konsoli nie-administratora.

import { roundPln } from '@/utils/money'

// Mirrors the server-side cap in `crm/koszty/rdzen.py::_scal_dodatkowe`
// (`len(nazwa) > 140` -> ValueError, which would fail the WHOLE save, not
// just that row). Flagging it here lets the admin see the problem live
// instead of discovering it only after clicking save; `zbudujPayload` below
// drops an over-length row from the payload for the same reason it drops
// any other incomplete row -- see that function's doc comment.
const DLUGOSC_NAZWY_MAX = 140

// Edycja kosztów PLANOWANYCH (ops#335): lustro `crm/koszty/rdzen.py`
// (`KLUCZ_KOREKTY_SUMY`, `LINIE_EDYTOWALNE_PLANU`). Tylko snapshoty OZE.
export const KLUCZ_KOREKTY_SUMY = 'korekta_sumy_plan'
export const LINIE_EDYTOWALNE_PLANU = ['pv', 'oze']

/**
 * Parse a raw cost value typed by the administrator into a finite,
 * non-negative number, or `null` when the input represents "no actual
 * value entered" (empty) or is not a valid non-negative amount (invalid,
 * including negative numbers — a negative actual cost makes no sense and is
 * treated exactly like "not entered").
 *
 * Rules mirror `cpMarza.js`'s `parsujStawke`/`parsujKwote` (trim including
 * non-breaking spaces, comma or dot as decimal separator, space/nbsp as
 * thousands separator) with ONE deliberate difference: `cpMarza.js` maps
 * every invalid/empty input to `0` (a commission rate of "nothing typed" is
 * a legitimate 0-rate default). Here `0` is a legitimate, deliberately
 * entered actual cost and must stay distinguishable from "nothing typed" —
 * so empty/invalid input maps to `null`, not `0`.
 *
 * @param {*} surowa - raw input value (typically a string from an <input>)
 * @returns {number|null} parsed, non-negative, finite amount, or null
 */
export function parsujKosztRzeczywisty(surowa) {
  if (typeof surowa === 'number') {
    return Number.isFinite(surowa) && surowa >= 0 ? surowa : null
  }

  if (typeof surowa !== 'string') return null

  const bezSpacji = surowa.replace(/[\s ]/g, '')
  if (bezSpacji === '') return null

  const znormalizowana = bezSpacji.replace(',', '.')
  const sparsowana = Number(znormalizowana)

  if (!Number.isFinite(sparsowana) || sparsowana < 0) return null
  return sparsowana
}

/**
 * Safely parse a `custom_koszty_json` string into the snapshot object,
 * never throwing. Returns `null` for anything that is not a well-formed
 * wersja-1 snapshot: unparsable JSON, wrong/missing `wersja`, missing or
 * non-array `linie`, or missing/non-object `podsumowanie`.
 *
 * Also accepts an already-parsed object (defensive: some Frappe field types
 * / test fixtures may hand over a JS object instead of a JSON string) —
 * validated the same way.
 *
 * @param {string|object|null|undefined} jsonLubObiekt - raw field value
 * @returns {object|null} the parsed snapshot, or null when invalid
 */
export function parseSnapshot(jsonLubObiekt) {
  let snapshot = null

  if (typeof jsonLubObiekt === 'string') {
    if (jsonLubObiekt.trim() === '') return null
    try {
      snapshot = JSON.parse(jsonLubObiekt)
    } catch (err) {
      return null
    }
  } else if (jsonLubObiekt && typeof jsonLubObiekt === 'object') {
    snapshot = jsonLubObiekt
  } else {
    return null
  }

  if (!snapshot || typeof snapshot !== 'object' || Array.isArray(snapshot)) return null
  if (snapshot.wersja !== 1) return null
  if (!Array.isArray(snapshot.linie)) return null
  if (!snapshot.podsumowanie || typeof snapshot.podsumowanie !== 'object') return null

  return snapshot
}

// Amount-or-null helper shared by the podsumowanie readers below: a nullable
// snapshot field ("x.xx"|null) becomes either a finite Number or null, never
// NaN — mirrors parsujKosztRzeczywisty's "never NaN" guarantee but for
// values that are already trusted server output (no negative-rejection
// needed, the server never emits a negative planned cost/margin).
function liczbaLubNull(wartosc) {
  if (wartosc === null || wartosc === undefined) return null
  const n = Number(wartosc)
  return Number.isFinite(n) ? n : null
}

function liczbaLubZero(wartosc) {
  return liczbaLubNull(wartosc) ?? 0
}

/**
 * Recompute the live, display-only "rzeczywiste" (actual) breakdown from a
 * snapshot plus the administrator's in-progress edits. Never mutates any
 * argument.
 *
 * @param {object|null} snapshot - parsed snapshot (see parseSnapshot)
 * @param {Object<string, string>} edycje - klucz -> raw typed actual-cost string
 * @param {Array<{id?: string, nazwa: string, kwota: string}>} dodatkowe - extra cost rows (raw, in-progress)
 * @returns {{linie: Array<object>, razem: object, bledy: Array<string>}}
 */
export function przeliczRzeczywiste(snapshot, edycje, dodatkowe) {
  const bledy = []
  const edycjeBezpieczne = edycje || {}
  const dodatkoweBezpieczne = Array.isArray(dodatkowe) ? dodatkowe : []
  const linieZrodlowe = Array.isArray(snapshot?.linie) ? snapshot.linie : []

  const linie = linieZrodlowe.map((linia) => {
    const klucz = linia.klucz
    const etykieta = linia.etykieta || klucz
    const netto = liczbaLubNull(linia.netto)
    const prowizjaPlan = liczbaLubNull(linia.prowizja_plan)
    const kosztPlan = liczbaLubZero(linia.koszt_plan)

    const surowyWpis = edycjeBezpieczne[klucz]
    const kosztRzeczywistySurowy = parsujKosztRzeczywisty(surowyWpis)
    // A non-empty typed value that failed to parse (garbage, or a rejected
    // negative amount) is surfaced as an error, even though it is treated
    // as "no actual" for the live math below — the admin should not save
    // over a value they only think they entered.
    if (kosztRzeczywistySurowy === null && typeof surowyWpis === 'string' && surowyWpis.trim() !== '') {
      bledy.push(`Nieprawidłowa wartość kosztu rzeczywistego dla pozycji „${etykieta}”.`)
    }

    const wgPlanu = kosztRzeczywistySurowy === null
    const kosztUzytySurowy = wgPlanu ? kosztPlan : kosztRzeczywistySurowy
    const deltaSurowa = kosztUzytySurowy - kosztPlan
    const marzaLiniiSurowa = netto !== null ? netto - kosztUzytySurowy : null

    return {
      klucz,
      etykieta,
      ilosc: linia.ilosc ?? null,
      jednostka: linia.jednostka ?? null,
      netto: netto !== null ? roundPln(netto) : null,
      prowizjaPlan: prowizjaPlan !== null ? roundPln(prowizjaPlan) : null,
      kosztPlan: roundPln(kosztPlan),
      kosztPlanPierwotny: liczbaLubNull(linia.koszt_plan_pierwotny),
      czyKorekta: klucz === KLUCZ_KOREKTY_SUMY,
      kosztRzeczywisty: kosztRzeczywistySurowy !== null ? roundPln(kosztRzeczywistySurowy) : null,
      kosztUzyty: roundPln(kosztUzytySurowy),
      wgPlanu,
      delta: roundPln(deltaSurowa),
      marzaLinii: marzaLiniiSurowa !== null ? roundPln(marzaLiniiSurowa) : null,
    }
  })

  // Dodatkowe pozycje: pusty wiersz (bez nazwy i bez kwoty) jest normalnym
  // stanem "jeszcze nie wypełniony" i nie jest błędem. Wiersz z nazwą, ale
  // bez poprawnej kwoty (lub odwrotnie) JEST błędem — wliczamy go do sumy
  // jako 0, żeby suma na ekranie pozostała przewidywalna, ale ostrzegamy,
  // żeby administrator nie zapisał niekompletnego wiersza po cichu.
  let sumaDodatkowych = 0
  const dodatkoweRozliczone = dodatkoweBezpieczne.map((wiersz, indeks) => {
    const nazwa = String(wiersz?.nazwa ?? '').trim()
    const surowaKwota = wiersz?.kwota
    const kwotaSparsowana = parsujKosztRzeczywisty(surowaKwota)
    const kwotaPusta = surowaKwota === undefined || surowaKwota === null || String(surowaKwota).trim() === ''

    if (!nazwa && kwotaPusta) {
      // Całkowicie pusty wiersz roboczy — brak błędu, brak wkładu do sumy.
      return { ...wiersz, kwota: 0 }
    }

    if (kwotaSparsowana === null) {
      bledy.push(`Nieprawidłowa kwota dodatkowej pozycji „${nazwa || `#${indeks + 1}`}”.`)
      return { ...wiersz, kwota: 0 }
    }
    if (!nazwa) {
      bledy.push(`Brakuje nazwy dla dodatkowej pozycji z kwotą ${roundPln(kwotaSparsowana)}.`)
    } else if (nazwa.length > DLUGOSC_NAZWY_MAX) {
      bledy.push(`Nazwa dodatkowej pozycji „${nazwa.slice(0, 20)}…” jest za długa (maks. ${DLUGOSC_NAZWY_MAX} znaków).`)
    }

    const kwotaZaokraglona = roundPln(kwotaSparsowana)
    sumaDodatkowych += kwotaZaokraglona
    return { ...wiersz, kwota: kwotaZaokraglona }
  })
  sumaDodatkowych = roundPln(sumaDodatkowych)

  const nettoRazem = liczbaLubZero(snapshot?.podsumowanie?.netto)
  const kosztPlanRazem = liczbaLubZero(snapshot?.podsumowanie?.koszt_plan)
  const marzaPlanRazem = liczbaLubZero(snapshot?.podsumowanie?.marza_plan)
  const prowizjaPlanRazem = liczbaLubNull(snapshot?.podsumowanie?.prowizja_plan)
  const zyskPlanRazem = liczbaLubZero(snapshot?.podsumowanie?.zysk_plan)

  const sumaKosztowUzytych = linie.reduce((suma, linia) => suma + linia.kosztUzyty, 0)
  const kosztRzeczywistyRazem = roundPln(sumaKosztowUzytych + sumaDodatkowych)
  const marzaRzeczywistaRazem = roundPln(nettoRazem - kosztRzeczywistyRazem)
  const zyskRzeczywistyRazem = roundPln(marzaRzeczywistaRazem - (prowizjaPlanRazem || 0))
  const pozycjeWgPlanu = linie.filter((linia) => linia.wgPlanu).length

  const razem = {
    netto: roundPln(nettoRazem),
    kosztPlan: roundPln(kosztPlanRazem),
    kosztRzeczywisty: kosztRzeczywistyRazem,
    marzaPlan: roundPln(marzaPlanRazem),
    marzaRzeczywista: marzaRzeczywistaRazem,
    prowizjaPlan: prowizjaPlanRazem !== null ? roundPln(prowizjaPlanRazem) : null,
    zyskPlan: roundPln(zyskPlanRazem),
    zyskRzeczywisty: zyskRzeczywistyRazem,
    pozycjeWgPlanu,
  }

  return { linie, razem, bledy }
}

/**
 * Build the save payload for `crm.api.koszty.volteo_koszty_zapisz` from the
 * current snapshot and in-progress edits. Never mutates any argument.
 *
 * `koszty_rzeczywiste` carries an explicit entry (number or null) for EVERY
 * line in the snapshot, per the API contract — a line the administrator
 * cleared must send `null`, not be omitted, so the server knows to clear it
 * too rather than leaving the previously saved actual untouched.
 *
 * `dodatkowe` is a full replacement array: rows that are entirely empty
 * (no name AND no parseable amount) are dropped, as are rows missing either
 * a name or a valid non-negative amount (see `przeliczRzeczywiste` above,
 * which surfaces those as `bledy` so the admin sees the problem before
 * saving instead of it being silently dropped without explanation). `id` is
 * kept only when present, so the server can tell a pre-existing row
 * (preserve autor/utworzono) from a brand new one.
 *
 * @param {object|null} snapshot - parsed snapshot (see parseSnapshot)
 * @param {Object<string, string>} edycje - klucz -> raw typed actual-cost string
 * @param {Array<{id?: string, nazwa: string, kwota: string}>} dodatkowe - extra cost rows (raw, in-progress)
 * @returns {{koszty_rzeczywiste: Object<string, number|null>, dodatkowe: Array<{id?: string, nazwa: string, kwota: number}>}}
 */
export function zbudujPayload(snapshot, edycje, dodatkowe) {
  const edycjeBezpieczne = edycje || {}
  const dodatkoweBezpieczne = Array.isArray(dodatkowe) ? dodatkowe : []
  const linieZrodlowe = Array.isArray(snapshot?.linie) ? snapshot.linie : []

  const koszty_rzeczywiste = {}
  for (const linia of linieZrodlowe) {
    // Linia korekty sumy planu nie ma kosztu rzeczywistego (serwer odrzuca wartość).
    if (linia.klucz === KLUCZ_KOREKTY_SUMY) continue
    const sparsowana = parsujKosztRzeczywisty(edycjeBezpieczne[linia.klucz])
    koszty_rzeczywiste[linia.klucz] = sparsowana !== null ? roundPln(sparsowana) : null
  }

  const dodatkowePayload = []
  for (const wiersz of dodatkoweBezpieczne) {
    const nazwa = String(wiersz?.nazwa ?? '').trim()
    const kwotaSparsowana = parsujKosztRzeczywisty(wiersz?.kwota)
    // Skip incomplete/invalid rows entirely (missing name, name over the
    // server's 140-char cap, or missing/invalid amount) — see the function
    // doc comment above for why these are dropped rather than sent as-is.
    if (!nazwa || nazwa.length > DLUGOSC_NAZWY_MAX || kwotaSparsowana === null) continue

    const wpis = { nazwa, kwota: roundPln(kwotaSparsowana) }
    if (wiersz?.id) wpis.id = wiersz.id
    dodatkowePayload.push(wpis)
  }

  return { koszty_rzeczywiste, dodatkowe: dodatkowePayload }
}

// ---------------------------------------------------------------------------
// Edycja kosztów PLANOWANYCH (ops#335). Tylko podgląd na żywo; serwer
// (`crm.api.koszty.volteo_koszty_plan_zapisz`) przelicza autorytatywnie.
// Arytmetyka w groszach (liczby całkowite), żeby suma na ekranie zgadzała
// się z serwerowym Decimal co do grosza.
// ---------------------------------------------------------------------------

function grosze(wartosc) {
  return Math.round(liczbaLubZero(wartosc) * 100)
}

function zGroszy(g) {
  return g / 100
}

/** Czy snapshot jest edytowalny w trybie planu (tylko OZE: pv, oze). */
export function czyEdytowalnyPlan(snapshot) {
  return !!snapshot && LINIE_EDYTOWALNE_PLANU.includes(snapshot.linia_produktowa)
}

/** Wartości wejściowe pól planu na starcie edycji: klucz -> zapisany koszt planowany. */
export function edycjePlanuStart(snapshot) {
  const wynik = {}
  for (const linia of snapshot?.linie || []) {
    if (linia.klucz === KLUCZ_KOREKTY_SUMY) continue
    wynik[linia.klucz] = linia.koszt_plan != null ? String(linia.koszt_plan) : ''
  }
  return wynik
}

/**
 * Podgląd na żywo edycji kosztów planowanych. Nie mutuje argumentów.
 *
 * @param {object|null} snapshot - sparsowany snapshot
 * @param {Object<string,string>} edycjePlanu - klucz -> wpisany koszt planowany
 * @param {string|null} sumaWpisana - wpisana suma kosztów planowanych albo null (nie ruszana)
 * @param {boolean} usunKorekte - czy usunąć linię korekty sumy
 */
export function przeliczPlan(snapshot, edycjePlanu, sumaWpisana, usunKorekte = false) {
  const bledy = []
  const edycje = edycjePlanu || {}
  const linieZrodlowe = Array.isArray(snapshot?.linie) ? snapshot.linie : []
  const sumaPrzed = grosze(snapshot?.podsumowanie?.koszt_plan)

  let delta = 0
  let korektaStara = 0
  const linie = []
  for (const linia of linieZrodlowe) {
    const klucz = linia.klucz
    const etykieta = linia.etykieta || klucz
    const zapisany = grosze(linia.koszt_plan)
    if (klucz === KLUCZ_KOREKTY_SUMY) {
      korektaStara = zapisany
      continue
    }
    const surowy = edycje[klucz]
    const sparsowany = parsujKosztRzeczywisty(surowy)
    if (sparsowany === null && typeof surowy === 'string' && surowy.trim() !== '') {
      bledy.push(`Nieprawidłowa wartość kosztu planowanego dla pozycji „${etykieta}”.`)
    }
    // Pusty albo błędny wpis = bez zmiany (zostaje zapisana wartość).
    const nowy = sparsowany === null ? zapisany : Math.round(sparsowany * 100)
    const pierwotnyZapisany = liczbaLubNull(linia.koszt_plan_pierwotny)
    const zmieniona = nowy !== zapisany
    delta += nowy - zapisany
    linie.push({
      klucz,
      etykieta,
      kosztZapisany: zGroszy(zapisany),
      kosztNowy: zGroszy(nowy),
      // Wartość, do której wraca przycisk przywrócenia: zapisana pierwotna albo (przy
      // niezapisanej zmianie) obecnie zapisany koszt.
      pierwotny: pierwotnyZapisany !== null ? roundPln(pierwotnyZapisany) : zmieniona ? zGroszy(zapisany) : null,
      zmieniona,
    })
  }

  let korekta = korektaStara
  if (usunKorekte && korektaStara !== 0) {
    delta -= korektaStara
    korekta = 0
  }
  const sumaPoLiniach = sumaPrzed + delta

  const sumaSparsowana = parsujKosztRzeczywisty(sumaWpisana)
  if (sumaSparsowana === null && typeof sumaWpisana === 'string' && sumaWpisana.trim() !== '') {
    bledy.push('Nieprawidłowa wartość sumy kosztów planowanych.')
  }
  let sumaNowa = sumaPoLiniach
  let roznica = 0
  if (sumaSparsowana !== null) {
    sumaNowa = Math.round(sumaSparsowana * 100)
    roznica = sumaNowa - sumaPoLiniach
    korekta += roznica
  }

  const netto = grosze(snapshot?.podsumowanie?.netto)
  const prowizjaPlan = liczbaLubNull(snapshot?.podsumowanie?.prowizja_plan)
  const marza = netto - sumaNowa
  const zysk = marza - (prowizjaPlan !== null ? grosze(prowizjaPlan) : 0)

  return {
    linie,
    razem: {
      netto: zGroszy(netto),
      kosztPlan: zGroszy(sumaNowa),
      sumaPoLiniach: zGroszy(sumaPoLiniach),
      marzaPlan: zGroszy(marza),
      zyskPlan: zGroszy(zysk),
      prowizjaPlan: prowizjaPlan !== null ? roundPln(prowizjaPlan) : null,
    },
    // `roznica` != 0 oznacza, że różnica między wpisaną sumą a sumą linii trafi do korekty.
    roznicaSumy: zGroszy(roznica),
    korekta: zGroszy(korekta),
    korektaIstnieje: korektaStara !== 0,
    bledy,
  }
}

/**
 * Payload dla `crm.api.koszty.volteo_koszty_plan_zapisz`. Do `koszty_plan` trafiają
 * tylko linie, których wpisana wartość różni się od zapisanej (wartość równa
 * pierwotnej serwer traktuje jak przywrócenie). `suma_plan` (string) tylko gdy
 * wpisana i poprawna; wygrywa nad zmianami linii. Nie mutuje argumentów.
 */
export function zbudujPayloadPlanu(snapshot, edycjePlanu, sumaWpisana, usunKorekte = false) {
  const edycje = edycjePlanu || {}
  const koszty_plan = {}
  for (const linia of Array.isArray(snapshot?.linie) ? snapshot.linie : []) {
    if (linia.klucz === KLUCZ_KOREKTY_SUMY) continue
    const sparsowany = parsujKosztRzeczywisty(edycje[linia.klucz])
    if (sparsowany === null) continue
    const nowy = Math.round(sparsowany * 100)
    if (nowy !== grosze(linia.koszt_plan)) koszty_plan[linia.klucz] = zGroszy(nowy).toFixed(2)
  }
  if (usunKorekte) koszty_plan[KLUCZ_KOREKTY_SUMY] = null

  const sumaSparsowana = parsujKosztRzeczywisty(sumaWpisana)
  const suma_plan = sumaSparsowana !== null ? zGroszy(Math.round(sumaSparsowana * 100)).toFixed(2) : null
  return { koszty_plan, suma_plan }
}

/** Czy payload planu niesie jakąkolwiek zmianę (do wyłączania przycisku Zapisz). */
export function czyPayloadPlanuMaZmiany(payload) {
  return Object.keys(payload?.koszty_plan || {}).length > 0 || payload?.suma_plan != null
}

/**
 * Czy administrator ma niezapisane zmiany kosztów RZECZYWISTYCH (edycje linii albo
 * dodatkowe pozycje względem snapshotu). Tryb edycji planu startuje dopiero bez nich:
 * jeden zapis na raz, nic nie ginie po cichu.
 */
export function czyZmienioneRzeczywiste(snapshot, edycje, dodatkowe) {
  const bazaEdycji = {}
  for (const linia of snapshot?.linie || []) {
    bazaEdycji[linia.klucz] = linia.koszt_rzeczywisty != null ? String(linia.koszt_rzeczywisty) : ''
  }
  const bazaDodatkowe = (snapshot?.dodatkowe || []).map((d) => ({
    id: d.id,
    nazwa: d.nazwa || '',
    kwota: d.kwota != null ? String(d.kwota) : '',
  }))
  // Surowe dodatkowe (z niepełnymi wierszami) też liczą się jako zmiana.
  const surowe = (Array.isArray(dodatkowe) ? dodatkowe : []).map((d) => ({
    id: d?.id,
    nazwa: String(d?.nazwa ?? ''),
    kwota: String(d?.kwota ?? ''),
  }))
  const a = zbudujPayload(snapshot, edycje, dodatkowe)
  const b = zbudujPayload(snapshot, bazaEdycji, bazaDodatkowe)
  return JSON.stringify(a) !== JSON.stringify(b) || JSON.stringify(surowe) !== JSON.stringify(bazaDodatkowe)
}

// ---------------------------------------------------------------------------
// Edycja składników marży planowej (ops#339). Tylko podgląd na żywo; serwer
// (`crm.api.koszty.volteo_koszty_marze_zapisz`) jest autorytatywny. Cena i
// podsumowanie nie zmieniają się: składniki to wewnętrzny podział marży.
// Arytmetyka w groszach (liczby całkowite).
// ---------------------------------------------------------------------------

/** Wartości wejściowe pól składników na starcie edycji: klucz -> zapisana kwota. */
export function skladnikiMarzyStart(snapshot) {
  const wynik = {}
  for (const sk of snapshot?.skladniki_marzy || []) {
    wynik[sk.klucz] = sk.kwota != null ? String(sk.kwota) : ''
  }
  return wynik
}

/**
 * Podgląd na żywo składników marży. Nie mutuje argumentów. Pusty albo błędny wpis
 * oznacza brak zmiany (zostaje zapisana kwota).
 *
 * @param {object|null} snapshot - sparsowany snapshot
 * @param {Object<string,string>} edycjeMarz - klucz -> wpisana kwota składnika
 * @returns {{skladniki: object[], suma: number, marzaPlan: number, nierozdzielona: number, bledy: string[]}}
 */
export function przeliczSkladnikiMarzy(snapshot, edycjeMarz) {
  const bledy = []
  const edycje = edycjeMarz || {}
  let sumaG = 0
  const skladniki = []
  for (const sk of snapshot?.skladniki_marzy || []) {
    const zapisany = grosze(sk.kwota)
    const surowy = edycje[sk.klucz]
    const sparsowany = parsujKosztRzeczywisty(surowy)
    if (sparsowany === null && typeof surowy === 'string' && surowy.trim() !== '') {
      bledy.push(`Nieprawidłowa kwota składnika marży „${sk.etykieta || sk.klucz}”.`)
    }
    const nowy = sparsowany === null ? zapisany : Math.round(sparsowany * 100)
    const pierwotnyZapisany = liczbaLubNull(sk.kwota_pierwotna)
    sumaG += nowy
    skladniki.push({
      klucz: sk.klucz,
      etykieta: sk.etykieta || sk.klucz,
      kwotaZapisana: zGroszy(zapisany),
      kwotaNowa: zGroszy(nowy),
      // Wartość, do której wraca przywrócenie: zapisana pierwotna albo (przy niezapisanej
      // zmianie) obecnie zapisana kwota.
      pierwotny:
        pierwotnyZapisany !== null ? roundPln(pierwotnyZapisany) : nowy !== zapisany ? zGroszy(zapisany) : null,
      zmieniony: nowy !== zapisany,
    })
  }
  const marzaG = grosze(snapshot?.podsumowanie?.marza_plan)
  return {
    skladniki,
    suma: zGroszy(sumaG),
    marzaPlan: zGroszy(marzaG),
    nierozdzielona: zGroszy(marzaG - sumaG),
    bledy,
  }
}

/** Payload do API: tylko składniki zmienione względem zapisanych; kwota jako wpisany napis. */
export function zbudujPayloadMarz(snapshot, edycjeMarz) {
  const podglad = przeliczSkladnikiMarzy(snapshot, edycjeMarz)
  const skladniki = {}
  for (const sk of podglad.skladniki) {
    if (sk.zmieniony) skladniki[sk.klucz] = sk.kwotaNowa.toFixed(2)
  }
  return { skladniki }
}

/** Czy payload marż niesie jakąkolwiek zmianę (do wyłączania przycisku Zapisz). */
export function czyPayloadMarzMaZmiany(payload) {
  return Object.keys(payload?.skladniki || {}).length > 0
}
