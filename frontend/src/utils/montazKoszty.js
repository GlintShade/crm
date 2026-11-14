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

// Edycja kosztów planowanych i składników marży przeniosła się do wspólnego
// edytora zestawu (ZestawEdycja.vue); tu zostaje klucz linii korekty sumy, bo
// panel nadal ją rozpoznaje przy wyświetlaniu i przy zapisie kosztów rzeczywistych.
export const KLUCZ_KOREKTY_SUMY = 'korekta_sumy_plan'

// Etykiety do wyświetlenia po kluczu linii kosztów i składników marży. Zapisane
// dane nie są zmieniane; nieznany klucz zwraca zapisaną etykietę.
const ETYKIETY_KOSZTOW = {
  k_montaz_pv: 'Montaż PV',
  k_montaz_mag: 'Montaż magazynu',
  kilometrowka: 'Kilometrówka',
  k_spoldzielnia: 'Spółdzielnia energetyczna',
  k_ppoz: 'Uzgodnienia PPOŻ',
  k_ev: 'Dodatek ładowarka EV',
  marza_proenergy: 'Marża ProEnergy',
  marza_sps: 'Marża SPS',
  bonus_liderki: 'Bonus liderski',
  marza_dodatki: 'Marża dodatki',
}

/**
 * Etykieta linii kosztu albo składnika marży do wyświetlenia (mapa po kluczu).
 * @param {string} klucz - klucz linii w snapshocie
 * @param {string} [etykieta] - etykieta zapisana w snapshocie (fallback)
 * @returns {string}
 */
export function etykietaKosztu(klucz, etykieta) {
  return Object.prototype.hasOwnProperty.call(ETYKIETY_KOSZTOW, klucz) ? ETYKIETY_KOSZTOW[klucz] : etykieta || klucz
}


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
    const etykieta = etykietaKosztu(klucz, linia.etykieta)
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
// Arytmetyka w groszach (liczby całkowite), żeby suma na ekranie zgadzała się
// z serwerowym Decimal co do grosza.
// ---------------------------------------------------------------------------

function grosze(wartosc) {
  return Math.round(liczbaLubZero(wartosc) * 100)
}

function zGroszy(g) {
  return g / 100
}

// ---------------------------------------------------------------------------
// Składniki marży planowej (podgląd tylko do odczytu w panelu kosztów; edycja
// odbywa się we wspólnym edytorze zestawu, backend zapisuje autorytatywnie).
// Arytmetyka w groszach (liczby całkowite).
// ---------------------------------------------------------------------------

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
      bledy.push(`Nieprawidłowa kwota składnika marży „${etykietaKosztu(sk.klucz, sk.etykieta)}”.`)
    }
    const nowy = sparsowany === null ? zapisany : Math.round(sparsowany * 100)
    const pierwotnyZapisany = liczbaLubNull(sk.kwota_pierwotna)
    sumaG += nowy
    skladniki.push({
      klucz: sk.klucz,
      etykieta: etykietaKosztu(sk.klucz, sk.etykieta),
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

/**
 * Krótki opis ręcznych zmian snapshotu jako lista linii (pusta, gdy nic nie
 * zmieniano). Pierwsza linia: najnowsza z `edycja_reczna`, `edycja_planu`,
 * `edycja_marzy` (data i osoba), z powodem zmiany zestawu, jeśli jest. Kolejne
 * tylko wtedy, gdy cena netto albo suma kosztów planowanych faktycznie różni
 * się (co do grosza) od wartości pierwotnej. Formatowanie daty i osoby jest
 * wstrzykiwane, żeby funkcja pozostała czysta.
 *
 * @param {object|null} snapshot
 * @param {{formatujDate: Function, nazwaUzytkownika: Function, formatPln: Function}} opcje
 * @returns {string[]}
 */
export function opisEdycjiRecznych(snapshot, { formatujDate, nazwaUzytkownika, formatPln }) {
  if (!snapshot) return []
  const wpisy = ['edycja_reczna', 'edycja_planu', 'edycja_marzy']
    .map((k) => snapshot[k])
    .filter((e) => e && typeof e === 'object')
  if (!wpisy.length) return []

  const czas = (e) => {
    const t = Date.parse(String(e.kiedy ?? '').replace(' ', 'T'))
    return Number.isFinite(t) ? t : -Infinity
  }
  const najnowszy = wpisy.reduce((a, b) => (czas(b) > czas(a) ? b : a))
  const kiedy = formatujDate(najnowszy.kiedy)
  const kto = nazwaUzytkownika(najnowszy.kto)
  const powod = String(snapshot.edycja_reczna?.powod ?? '').trim()
  const linie = [
    `Zestaw, koszty lub marże zmienione ręcznie${kiedy ? ' ' + kiedy : ''}${kto ? ' (' + kto + ')' : ''}.` +
      (powod ? ` Powód: ${powod}.` : ''),
  ]

  const nettoPrzed = liczbaLubNull(snapshot.edycja_reczna?.netto_przed)
  if (nettoPrzed !== null && grosze(nettoPrzed) !== grosze(snapshot.podsumowanie?.netto)) {
    linie.push(`Cena netto przed zmianą: ${formatPln(nettoPrzed)}.`)
  }
  const planPierwotny = liczbaLubNull(snapshot.edycja_planu?.koszt_plan_pierwotny)
  if (planPierwotny !== null && grosze(planPierwotny) !== grosze(snapshot.podsumowanie?.koszt_plan)) {
    linie.push(`Pierwotna suma kosztów planowanych: ${formatPln(planPierwotny)}.`)
  }
  return linie
}

// Zapamiętany w przeglądarce stan zwinięcia panelu "Koszty i marża" (szansa OZE).
// Storage jest argumentem, żeby dało się testować; każdy dostęp w try/catch,
// bo localStorage bywa niedostępny (tryb prywatny, zablokowane dane witryn).
export const KLUCZ_ZWINIECIA_KOSZTOW = 'volteo_koszty_marza_zwiniety'

/** Czy panel ma być zwinięty. Domyślnie false (rozwinięty), też przy błędzie odczytu. */
export function czytajZwiniecieKosztow(storage) {
  try {
    return storage?.getItem(KLUCZ_ZWINIECIA_KOSZTOW) === '1'
  } catch (e) {
    return false
  }
}

/** Zapisuje stan zwinięcia ("1" albo "0"); błąd zapisu jest ignorowany. */
export function zapiszZwiniecieKosztow(storage, zwiniety) {
  try {
    storage?.setItem(KLUCZ_ZWINIECIA_KOSZTOW, zwiniety ? '1' : '0')
  } catch (e) {
    /* storage niedostępny: zostaje domyślny stan */
  }
}
