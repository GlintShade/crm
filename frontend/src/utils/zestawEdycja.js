// Edycja zestawu szansy OZE przez administrację (ops#272, plan sekcje 5 i 6).
//
// Moduł frappe-free i bez matematyki cen: wszystkie kwoty (brutto, dotacja,
// ulga, raty) liczy serwer (`crm.api.zestaw.volteo_zestaw_podglad`), tu tylko
// trzymamy niemutowalny stan formularza, serializujemy go do wywołania API i
// formatujemy różnice do okna potwierdzenia. Cały kod zależny od kształtu
// odpowiedzi API (klucze snake_case) siedzi w tym pliku, żeby ewentualna
// zmiana kontraktu była lokalna.

import { formatPln } from '@/utils/money'
import { PRODUCENT_PV, ZESTAWY } from '@/utils/pvForm'

export const POLA_CENY_WEJSCIE = [
  'netto',
  'vat_pct',
  'dotacja',
  'ulga_pct',
  'okres_lat',
  'wplata_wlasna',
  'dodatki_bez_ulgi_brutto',
  'brutto',
  'podstawa',
]

// Podstawa przeliczenia ceny OZE (ops#334): ostatnio edytowane pole, netto albo brutto.
export const PODSTAWA_NETTO = 'netto'
export const PODSTAWA_BRUTTO = 'brutto'

// Czyste Powietrze (ops#275): jedyne klucze `cena` przyjmowane przez serwer.
export const POLA_CENY_CP = ['dotacja_zrodlo', 'dotacja_co', 'dotacja_termo', 'okres_lat', 'wplata_gotowka']

export const ETYKIETY_POL_CENY_CP = {
  dotacja_zrodlo: 'Źródło ciepła',
  dotacja_co: 'CO i CWU',
  dotacja_termo: 'Termomodernizacja',
  okres_lat: 'Okres rat (lata)',
  wplata_gotowka: 'Wpłata gotówką',
}

// Lustro `POLA_KONFIGURACJI` w crm/api/zestaw.py (kolejność i skład). `custom_zestaw_typ`
// celowo NIE jest polem konfiguracji: serwer wylicza go z producenta.
export const POLA_KONFIGURACJI = [
  'custom_producent',
  'custom_falownik',
  'custom_bateria',
  'custom_pojemnosc_kwh',
  'custom_panel',
  'custom_panele',
  'custom_konstrukcja',
  'custom_kabel_m',
  'custom_licznik_dodatkowy',
  'custom_dod_klima',
  'custom_dod_panele',
  'custom_dod_panele_mikro',
  'custom_ems_breeze',
  'custom_pstryk',
  'custom_ev_ladowarka',
]

export const POLE_PRODUCENT = 'custom_producent'
export const POLE_ZESTAW_TYP = 'custom_zestaw_typ'

// Pola konfiguracji w tabeli "do umowy" (wolny tekst); producent ma osobny select.
export const POLA_KONFIGURACJI_TEKSTOWE = POLA_KONFIGURACJI.filter((p) => p !== POLE_PRODUCENT)

// Pola pokazywane w oknie różnic: producent i wyliczony zestaw na początku.
const POLA_KONFIGURACJI_OKNO = [POLE_PRODUCENT, POLE_ZESTAW_TYP, ...POLA_KONFIGURACJI_TEKSTOWE]

export const MSG_NOTA_PRODUCENTA = 'Zmiana producenta nie przelicza ceny ani kosztów, ustaw netto ręcznie.'

export const RODZAJE_Z_MAGAZYNEM = ['Fotowoltaika + Magazyn', 'Magazyn energii']
export const RODZAJ_PV = 'Fotowoltaika'
const PRODUCENCI_WYBIERALNI = ['FoxESS', 'Sigenergy', 'Hoymiles', 'Solax']

export const ETYKIETY_KONFIGURACJI = {
  custom_producent: 'Producent',
  custom_zestaw_typ: 'Zestaw',
  custom_falownik: 'Falownik',
  custom_bateria: 'Magazyn energii',
  custom_pojemnosc_kwh: 'Pojemność magazynu (kWh)',
  custom_panel: 'Panel',
  custom_panele: 'Liczba paneli',
  custom_konstrukcja: 'Konstrukcja',
  custom_kabel_m: 'Dodatkowy kabel (m)',
  custom_licznik_dodatkowy: 'Dodatkowy licznik',
  custom_dod_klima: 'Klimatyzacja (dodatek)',
  custom_dod_panele: 'Panele PV (dodatek, szt.)',
  custom_dod_panele_mikro: 'Panele PV + mikrofalownik (dodatek, szt.)',
  custom_ems_breeze: 'EMS Zeronest',
  custom_pstryk: 'Licznik Pstryk',
  custom_ev_ladowarka: 'Ładowarka EV',
}

export const ETYKIETY_POL_CENY = {
  netto: 'Cena netto',
  vat_pct: 'VAT %',
  dotacja: 'Dotacja',
  ulga_pct: 'Ulga %',
  okres_lat: 'Okres rat (lata)',
  wplata_wlasna: 'Wpłata własna',
  dodatki_bez_ulgi_brutto: 'Kwota brutto dodatków bez ulgi',
  brutto: 'Cena brutto',
}

export const ETYKIETY_POL_WIERSZA = {
  typ: 'typ',
  nazwa: 'nazwa',
  ilosc: 'ilość',
  jednostka: 'jednostka',
  netto: 'netto',
  brutto: 'brutto',
}

// Wartość select-a oznaczająca "typ spoza listy" (wolny tekst).
export const TYP_INNY = '__inny__'

const POLA_LICZBOWE_KONFIGURACJI = new Set([
  'custom_pojemnosc_kwh',
  'custom_panele',
  'custom_kabel_m',
  'custom_dod_panele',
  'custom_dod_panele_mikro',
])

let licznikKluczy = 0
function nowyKlucz() {
  licznikKluczy += 1
  return `n${licznikKluczy}`
}

function tekst(v) {
  return v == null ? '' : String(v)
}

function liczba(v) {
  if (typeof v === 'number') return Number.isFinite(v) ? v : 0
  const s = tekst(v).trim().replace(/\s/g, '').replace(',', '.')
  if (s === '') return 0
  const n = Number(s)
  return Number.isFinite(n) ? n : 0
}

function wierszZApi(w) {
  return {
    klucz: w.name || nowyKlucz(),
    name: w.name || null,
    typ: tekst(w.typ),
    nazwa: tekst(w.nazwa),
    ilosc: w.ilosc == null ? '' : tekst(w.ilosc),
    jednostka: tekst(w.jednostka),
    netto: w.netto == null ? '' : tekst(w.netto),
    brutto: w.brutto == null ? '' : tekst(w.brutto),
  }
}

/**
 * Opcje selecta "Producent" dla rodzaju umowy. Sama fotowoltaika: tylko FoxESS;
 * rodzaje z magazynem: FoxESS, Sigenergy, Hoymiles, Solax. Wartość bieżąca spoza
 * listy (np. Deye) jest pokazana jako opcja zdezaktywowana, nie do wyboru; pusta
 * wartość bieżąca daje zdezaktywowaną opcję "(nie ustawiono)". Lustro
 * `producenci_dla_rodzaju` w crm/volteo_zestaw.py.
 *
 * @returns {{value: string, label: string, disabled: boolean}[]}
 */
export function opcjeProducenta(rodzaj, biezacy) {
  const dozwolone = rodzaj === RODZAJ_PV ? [PRODUCENT_PV] : PRODUCENCI_WYBIERALNI
  const obecny = tekst(biezacy).trim()
  const opcje = dozwolone.map((p) => ({ value: p, label: p, disabled: false }))
  if (obecny === '') return [{ value: '', label: '(nie ustawiono)', disabled: true }, ...opcje]
  if (!dozwolone.includes(obecny)) return [{ value: obecny, label: obecny, disabled: true }, ...opcje]
  return opcje
}

/** Zestaw wyprowadzany z producenta (lustro `zestaw_dla_producenta`); '' gdy brak. */
export function zestawDlaProducenta(producent, rodzaj) {
  if (!RODZAJE_Z_MAGAZYNEM.includes(rodzaj)) return ''
  const p = tekst(producent).trim()
  return ZESTAWY.find((z) => z.producent === p)?.kod || ''
}

/**
 * Zestaw do pokazania w podglądzie (lustro `nowy_zestaw_typ`): wyliczany z producenta
 * wyłącznie gdy producent się zmienia, inaczej zestaw zapisany na szansie bez zmian.
 */
export function nowyZestawTyp(producentObecny, producentNowy, zestawObecny, rodzaj) {
  if (tekst(producentNowy).trim() === tekst(producentObecny).trim()) return tekst(zestawObecny).trim()
  return zestawDlaProducenta(producentNowy, rodzaj)
}

export function czyCp(stan) {
  return stan?.linia === 'cp'
}

export function pustyWiersz(typ = '', jednostka = 'szt.') {
  return { klucz: nowyKlucz(), name: null, typ, nazwa: '', ilosc: '1', jednostka, netto: '0', brutto: '0' }
}

function cenaDoStanu(cena, pola = POLA_CENY_WEJSCIE) {
  const c = cena || {}
  const wynik = {}
  for (const pole of pola) {
    wynik[pole] = c[pole] == null ? '' : tekst(c[pole])
  }
  // Podstawę podaje serwer (brutto, gdy zapisana para netto/brutto jest osiągalna tylko z brutto).
  if ('podstawa' in wynik) wynik.podstawa = c.podstawa === PODSTAWA_BRUTTO ? PODSTAWA_BRUTTO : PODSTAWA_NETTO
  return wynik
}

// ---- lustro zaokrąglenia serwera (crm/volteo_zestaw.py: brutto_z_netto, netto_z_brutto) ----
// Arytmetyka na groszach jako liczbach całkowitych, ROUND_HALF_UP. Kwoty tekstowe z pola
// (przecinek lub kropka) są parsowane bez float. Serwer i tak liczy po swojemu i jego
// wartość zastępuje lustro po odpowiedzi podglądu.

/** Tekst kwoty -> grosze (całkowite, half-up po 3. miejscu) albo null, gdy to nie liczba >= 0. */
function naGrosze(v) {
  const t = tekst(v).trim().replace(/\s/g, '').replace(',', '.')
  if (!/^\d*\.?\d*$/.test(t) || t === '' || t === '.') return null
  const [calosci, ulamek = ''] = t.split('.')
  const u = `${ulamek}000`
  return Number(calosci || '0') * 100 + Number(u.slice(0, 2)) + (Number(u[2]) >= 5 ? 1 : 0)
}

/** Stawka VAT (procent) -> setne procenta jako liczba całkowita albo null. */
function naSetneProcenta(v) {
  const g = naGrosze(v)
  return g === null || g > 10000 ? null : g
}

function dzielenieHalfUp(licznik, mianownik) {
  const q = Math.floor(licznik / mianownik)
  return 2 * (licznik - q * mianownik) >= mianownik ? q + 1 : q
}

function naTekstKwoty(grosze) {
  return `${Math.floor(grosze / 100)}.${String(grosze % 100).padStart(2, '0')}`
}

/** Brutto z netto: netto + zaokrąglenie(netto * VAT / 100). '' gdy dane nie są liczbami. */
export function bruttoZNetto(netto, vatPct) {
  const n = naGrosze(netto)
  const v = naSetneProcenta(vatPct)
  if (n === null || v === null) return ''
  return naTekstKwoty(n + dzielenieHalfUp(n * v, 10000))
}

/** Netto z brutto: zaokrąglenie(brutto / (1 + VAT / 100)). '' gdy dane nie są liczbami. */
export function nettoZBrutto(brutto, vatPct) {
  const b = naGrosze(brutto)
  const v = naSetneProcenta(vatPct)
  if (b === null || v === null) return ''
  return naTekstKwoty(dzielenieHalfUp(b * 10000, 10000 + v))
}

/** Pole przeliczane (nie będące podstawą) dla danej podstawy: lustro lokalne. */
function zLustrem(cena) {
  if (cena.podstawa === PODSTAWA_BRUTTO) return { ...cena, netto: nettoZBrutto(cena.brutto, cena.vat_pct) }
  return { ...cena, brutto: bruttoZNetto(cena.netto, cena.vat_pct) }
}

function konfiguracjaDoStanu(konfiguracja) {
  const k = konfiguracja || {}
  const wynik = {}
  for (const pole of POLA_KONFIGURACJI) {
    wynik[pole] = k[pole] == null ? '' : k[pole]
  }
  return wynik
}

/**
 * Stan formularza z odpowiedzi `volteo_zestaw_get`. `reczne` to zbiór pól
 * konfiguracji nadpisanych ręcznie przez admina (propozycja z podglądu ich
 * nie rusza).
 */
export function stanZOdpowiedzi(odp) {
  const o = odp || {}
  const cp = o.linia === 'cp'
  const wiersze = (o.wiersze || []).map(wierszZApi)
  return {
    linia: cp ? 'cp' : 'oze',
    wiersze,
    cena: cp ? cenaDoStanu(o.cena_cp, POLA_CENY_CP) : cenaDoStanu(o.cena),
    konfiguracja: konfiguracjaDoStanu(o.konfiguracja),
    // Koszty i marże (ops#341): tylko OZE ze snapshotem; null = zachowanie jak dotąd.
    koszty: cp ? null : kosztyZApi(o.koszty, wiersze),
    reczne: [],
    powod: '',
  }
}

export function dodajWiersz(stan, wiersz = pustyWiersz()) {
  return { ...stan, wiersze: [...stan.wiersze, wiersz] }
}

export function usunWiersz(stan, indeks) {
  if (indeks < 0 || indeks >= stan.wiersze.length) return stan
  const usuniety = stan.wiersze[indeks]
  const wynik = { ...stan, wiersze: stan.wiersze.filter((_, i) => i !== indeks) }
  // Linia kosztu usuwanej pozycji znika z ładunku (serwer linię katalogową i tak zostawi z zerem).
  if (stan.koszty) {
    wynik.koszty = { ...stan.koszty, linie: stan.koszty.linie.filter((l) => l.wierszKlucz !== usuniety.klucz) }
  }
  return wynik
}

/** kierunek: -1 w górę, +1 w dół. Poza zakresem: stan bez zmian. */
export function przesunWiersz(stan, indeks, kierunek) {
  const cel = indeks + kierunek
  if (indeks < 0 || indeks >= stan.wiersze.length) return stan
  if (cel < 0 || cel >= stan.wiersze.length) return stan
  const kopia = [...stan.wiersze]
  const [wyjety] = kopia.splice(indeks, 1)
  kopia.splice(cel, 0, wyjety)
  return { ...stan, wiersze: kopia }
}

export function zmienPoleWiersza(stan, indeks, pole, wartosc) {
  if (indeks < 0 || indeks >= stan.wiersze.length) return stan
  return {
    ...stan,
    wiersze: stan.wiersze.map((w, i) => (i === indeks ? { ...w, [pole]: wartosc } : w)),
  }
}

export function zmienPoleCeny(stan, pole, wartosc) {
  const cena = { ...stan.cena, [pole]: wartosc }
  if (czyCp(stan) || !('podstawa' in stan.cena)) return { ...stan, cena }
  // OZE: ostatnio edytowane pole netto/brutto jest podstawą, drugie jest lustrem.
  if (pole === 'netto') return { ...stan, cena: zLustrem({ ...cena, podstawa: PODSTAWA_NETTO }) }
  if (pole === 'brutto') return { ...stan, cena: zLustrem({ ...cena, podstawa: PODSTAWA_BRUTTO }) }
  if (pole === 'vat_pct') return { ...stan, cena: zLustrem(cena) }
  return { ...stan, cena }
}

/**
 * Wartość z podglądu serwera dla pola, które NIE jest podstawą (brutto przy podstawie
 * netto, netto przy podstawie brutto). Pole podstawy nie jest ruszane, więc użytkownik
 * pisze bez nadpisywania. Czyste Powietrze i brak wartości: stan bez zmian.
 */
export function zastosujCeneZSerwera(stan, cenaSerwera) {
  if (czyCp(stan) || !cenaSerwera || !('podstawa' in stan.cena)) return stan
  const pole = stan.cena.podstawa === PODSTAWA_BRUTTO ? 'netto' : 'brutto'
  const v = cenaSerwera[pole]
  if (v == null || tekst(stan.cena[pole]) === tekst(v)) return stan
  return { ...stan, cena: { ...stan.cena, [pole]: tekst(v) } }
}

/** Ręczne nadpisanie pola konfiguracji: zapamiętujemy je jako ręczne. */
export function zmienPoleKonfiguracji(stan, pole, wartosc) {
  const reczne = stan.reczne.includes(pole) ? stan.reczne : [...stan.reczne, pole]
  return { ...stan, konfiguracja: { ...stan.konfiguracja, [pole]: wartosc }, reczne }
}

/**
 * Wchodzi propozycja konfiguracji z podglądu: nadpisuje wszystkie pola, które
 * admin nie ruszył ręcznie. `_ostrzezenia` nie jest polem konfiguracji.
 */
export function zastosujPropozycje(stan, propozycja) {
  if (!propozycja) return stan
  const konfiguracja = { ...stan.konfiguracja }
  for (const pole of POLA_KONFIGURACJI) {
    if (stan.reczne.includes(pole)) continue
    if (propozycja[pole] !== undefined) konfiguracja[pole] = propozycja[pole] == null ? '' : propozycja[pole]
  }
  return { ...stan, konfiguracja }
}

function wierszDoWywolania(w, cp) {
  const baza = { typ: tekst(w.typ).trim(), nazwa: tekst(w.nazwa).trim(), ilosc: liczba(w.ilosc), jednostka: tekst(w.jednostka).trim() }
  const wynik = cp ? { ...baza, netto: liczba(w.netto), brutto: liczba(w.brutto) } : baza
  return w.name ? { name: w.name, ...wynik } : wynik
}

export function wierszeDoWywolania(stan) {
  const cp = czyCp(stan)
  return stan.wiersze.map((w) => wierszDoWywolania(w, cp))
}

/**
 * Błędy formularza CP po stronie klienta (serwer waliduje i tak): jednostka
 * wymagana, 0 <= netto <= brutto. Pusta tablica = bez uwag; dla OZE zawsze [].
 */
export function bledyWierszyCp(stan) {
  if (!czyCp(stan)) return []
  const bledy = []
  stan.wiersze.forEach((w, i) => {
    if (tekst(w.jednostka).trim() === '') bledy.push({ indeks: i, pole: 'jednostka' })
    const netto = liczba(w.netto)
    const brutto = liczba(w.brutto)
    if (netto < 0 || brutto < netto) bledy.push({ indeks: i, pole: 'brutto' })
  })
  return bledy
}

/** Data (DD.MM.RRRR) z "YYYY-MM-DD[ HH:mm:ss]" dla banera prowizji CP; '' gdy brak. */
export function dataBaneruProwizji(edycja) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(tekst(edycja?.kiedy))
  return m ? `${m[3]}.${m[2]}.${m[1]}` : ''
}

export function cenaDoWywolania(stan) {
  const wynik = {}
  if (czyCp(stan)) {
    // Serwer CP przyjmuje wyłącznie te klucze; okres w latach jest całkowity.
    for (const pole of POLA_CENY_CP) {
      const v = liczba(stan.cena[pole])
      wynik[pole] = pole === 'okres_lat' ? Math.max(0, Math.trunc(v)) : v
    }
    return wynik
  }
  for (const pole of POLA_CENY_WEJSCIE) {
    const v = stan.cena[pole]
    if (pole === 'podstawa') {
      wynik[pole] = v === PODSTAWA_BRUTTO ? PODSTAWA_BRUTTO : PODSTAWA_NETTO
      continue
    }
    // ulga_pct to w bazie pole Data (tekst), reszta to liczby.
    wynik[pole] = pole === 'ulga_pct' ? tekst(v).trim().replace(',', '.') || '0' : liczba(v)
  }
  return wynik
}

export function konfiguracjaDoWywolania(stan) {
  const wynik = {}
  for (const pole of POLA_KONFIGURACJI) {
    const v = stan.konfiguracja[pole]
    wynik[pole] = POLA_LICZBOWE_KONFIGURACJI.has(pole) ? liczba(v) : tekst(v)
  }
  return wynik
}

/** Argumenty wspólne podglądu i zapisu (wiersze + cena + opcjonalnie koszty). */
export function doWywolania(stan) {
  const wynik = { wiersze: wierszeDoWywolania(stan), cena: cenaDoWywolania(stan) }
  const koszty = kosztyDoWywolania(stan)
  return koszty ? { ...wynik, koszty } : wynik
}

/** Argumenty `volteo_zestaw_podglad` (bez `deal`): wiersze, cena i (OZE) wybrany producent. */
export function doPodgladu(stan) {
  if (czyCp(stan)) return doWywolania(stan)
  return { ...doWywolania(stan), producent: tekst(stan.konfiguracja[POLE_PRODUCENT]).trim() }
}

/** Argumenty `volteo_zestaw_zapisz` (bez `deal` i `modified`). */
export function doZapisu(stan, powod = '') {
  return {
    ...doWywolania(stan),
    konfiguracja: czyCp(stan) ? {} : konfiguracjaDoWywolania(stan),
    powod: tekst(powod).trim().slice(0, 500),
  }
}

/** Czy formularz różni się od stanu początkowego (z `stanZOdpowiedzi`). */
export function czyZmieniony(stanPoczatkowy, stan) {
  // `podstawa` sama (przy tych samych kwotach) nie jest zmianą: liczą się kwoty.
  const bezPodstawy = (s) => {
    const z = doZapisu(s)
    if ('podstawa' in z.cena) {
      const { podstawa: _p, ...cena } = z.cena
      return { ...z, cena }
    }
    return z
  }
  return JSON.stringify(bezPodstawy(stanPoczatkowy)) !== JSON.stringify(bezPodstawy(stan))
}

export function etykietaTypu(typ) {
  const t = tekst(typ).trim()
  return t === '' ? '-' : t
}

/** Czy typ wiersza jest spoza podpowiadanej listy (UI odsłania wolny tekst). */
export function czyTypInny(typ, typy) {
  const t = tekst(typ)
  return t !== '' && !(typy || []).includes(t)
}

function opisWiersza(w) {
  const ilosc = w.ilosc == null || w.ilosc === '' ? '' : ` x ${w.ilosc}${w.jednostka ? ` ${w.jednostka}` : ''}`
  const nazwa = tekst(w.nazwa).trim()
  return `${etykietaTypu(w.typ)}${nazwa ? ` "${nazwa}"` : ''}${ilosc}`
}

function wartoscPola(pole, w) {
  const v = w[pole]
  return v == null || v === '' ? '-' : String(v)
}

/**
 * Wiersze tekstowe do okna potwierdzenia. Zwraca
 * `{ dodane: [str], usuniete: [str], zmienione: [str], cena: [{etykieta, przed, po}], konfiguracja: [{etykieta, przed, po}] }`.
 * Puste sekcje to puste tablice. Kwoty przez `formatPln`.
 */
export function roznicaDoOkna(roznice, cenaPrzed, cenaPo, konfiguracjaPrzed, konfiguracjaPo, cpPrzed, cpPo) {
  const r = roznice || {}
  const dodane = (r.dodane || []).map(opisWiersza)
  const usuniete = (r.usuniete || []).map(opisWiersza)
  const zmienione = (r.zmienione || []).map((z) => {
    const zmiany = (z.pola || [])
      .map((p) => `${ETYKIETY_POL_WIERSZA[p] || p} ${wartoscPola(p, z.stary || {})} -> ${wartoscPola(p, z.nowy || {})}`)
      .join(', ')
    const nowy = z.nowy || {}
    const stary = z.stary || {}
    return `${etykietaTypu(nowy.typ || stary.typ)}: ${zmiany}`
  })

  const cena = []
  const przed = cenaPrzed || {}
  const po = cenaPo || {}
  const kwoty = [
    ['netto', 'Netto'],
    ['brutto', 'Brutto'],
    ['dotacja', 'Dotacja'],
    ['cena_po_dotacji', 'Cena po dotacji'],
    ['cena_po_uldze', 'Cena po uldze'],
  ]
  for (const [pole, etykieta] of kwoty) {
    if (przed[pole] == null && po[pole] == null) continue
    if (liczba(przed[pole]) === liczba(po[pole])) continue
    cena.push({ etykieta, przed: formatPln(przed[pole]), po: formatPln(po[pole]) })
  }

  // Czyste Powietrze: wartość szansy, dotacja łączna i wkład własny (kwoty ze stringów serwera).
  if (cpPrzed || cpPo) {
    const a = cpPrzed || {}
    const b = cpPo || {}
    for (const [pole, etykieta] of [
      ['deal_value', 'Wartość szansy'],
      ['dotacja_laczna', 'Dotacja łączna'],
      ['wklad_wlasny', 'Wkład własny'],
    ]) {
      if (a[pole] == null && b[pole] == null) continue
      if (liczba(a[pole]) === liczba(b[pole])) continue
      cena.push({ etykieta, przed: formatPln(a[pole]), po: formatPln(b[pole]) })
    }
  }

  const konfiguracja = []
  const kp = konfiguracjaPrzed || {}
  const kn = konfiguracjaPo || {}
  for (const pole of POLA_KONFIGURACJI_OKNO) {
    const a = kp[pole] == null ? '' : String(kp[pole])
    const b = kn[pole] == null ? '' : String(kn[pole])
    if (a === b) continue
    konfiguracja.push({ etykieta: ETYKIETY_KONFIGURACJI[pole], przed: a === '' ? '-' : a, po: b === '' ? '-' : b })
  }

  return { dodane, usuniete, zmienione, cena, konfiguracja }
}

/** Czy komunikat błędu dotyczy konfliktu wersji (`modified`). */
export function czyBladWersji(komunikat) {
  const t = tekst(komunikat).toLowerCase()
  return t.includes('modified') || t.includes('zmodyfikowan') || t.includes('zmieniony przez') || t.includes('zmieniona przez')
}

/** Komunikat z błędu `call()`: `err.messages[0]` albo `err.message`. */
export function komunikatBledu(err, domyslny) {
  if (err?.messages?.length && err.messages[0]) return String(err.messages[0])
  if (err?.message) return String(err.message)
  return domyslny
}

/**
 * Rozbija komunikat(y) walidacji na osobne wiersze: dzieli po nowej linii, przycina,
 * odrzuca puste. Wiersz "Pozycja <Typ> "nazwa" ..." dostaje `typ` (np. "Falownik",
 * "Magazyn energii") i `tresc` bez słów "Pozycja <Typ>"; pozostałe mają `typ` pusty.
 * Akceptuje string albo tablicę stringów.
 */
export function wierszeKomunikatow(komunikaty) {
  const lista = Array.isArray(komunikaty) ? komunikaty : [komunikaty]
  const wiersze = []
  for (const element of lista) {
    for (const linia of tekst(element).split(/\r?\n/)) {
      const t = linia.trim()
      if (!t) continue
      const m = t.match(/^Pozycja (.+?) ("[^"]*" .*)$/)
      wiersze.push(m ? { typ: m[1], tresc: m[2] } : { typ: '', tresc: t })
    }
  }
  return wiersze
}

/** "Ostatnia edycja ręczna: DD.MM.RRRR HH:MM, Kto, powód: ..." (powód pomijany, gdy pusty). */
export function opisOstatniejEdycji(edycja) {
  if (!edycja) return ''
  const d = new Date(tekst(edycja.kiedy).replace(' ', 'T'))
  let kiedy = tekst(edycja.kiedy)
  if (!Number.isNaN(d.getTime())) {
    const p = (n) => String(n).padStart(2, '0')
    kiedy = `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`
  }
  const czesci = [kiedy, tekst(edycja.kto)].filter(Boolean)
  const powod = tekst(edycja.powod).trim()
  if (powod) czesci.push(`powód: ${powod}`)
  return czesci.join(', ')
}


// ---- koszty planowane i marże (ops#341, wariant A) ----
// Wszystko w groszach (liczby całkowite). Linia kosztu jest związana z pozycją przez
// stabilny `klucz` wiersza (`wierszKlucz`); indeksy `wiersz` powstają dopiero przy budowie
// ładunku, więc dodawanie, usuwanie i przesuwanie pozycji ich nie psuje.

export const KLUCZ_SKLADNIKA_NARZUT = 'narzut'
export const MSG_PROWIZJA_NALICZONA = 'Prowizja handlowca jest już naliczona. Po zapisie nalicz ją ponownie w zakładce Rozliczenia.'

function kosztyZApi(k, wiersze) {
  if (!k || typeof k !== 'object') return null
  const linie = (k.linie || []).map((l) => ({
      lid: l.klucz ? `l:${l.klucz}` : nowyKlucz(),
      klucz: l.klucz ?? null,
      etykieta: tekst(l.etykieta),
      koszt: l.koszt_plan == null ? '' : tekst(l.koszt_plan),
      wierszKlucz: l.wiersz != null && wiersze[l.wiersz] ? wiersze[l.wiersz].klucz : null,
      reczna: Boolean(l.reczna),
      korekta: Boolean(l.korekta),
      nowa: false,
    }))
  // Zapisana suma bywa różna od sumy linii (stare snapshoty, delty): trzymamy obie bazy.
  const sumaLiniiBazowa = linie.reduce((s, l) => s + groszeZPola(l.koszt), 0)
  const zapisana = k.podsumowanie?.koszt_plan
  const sumaBazowa = zapisana == null || naGrosze(zapisana) === null ? sumaLiniiBazowa : naGrosze(zapisana)
  return {
    linie,
    sumaBazowa,
    sumaLiniiBazowa,
    marze: (k.skladniki_marzy || []).map((m) => ({
      klucz: m.klucz,
      etykieta: tekst(m.etykieta),
      kwota: m.kwota == null ? '' : tekst(m.kwota),
      bazowa: m.kwota == null ? '' : tekst(m.kwota),
      pierwotna: m.kwota_pierwotna == null ? null : tekst(m.kwota_pierwotna),
    })),
    pokazPuste: false,
  }
}

/** Grosze z pola tekstowego; puste albo błędne = 0. */
export function groszeZPola(v) {
  return naGrosze(v) ?? 0
}

/** Grosze -> "1234.50" (do ładunku API). */
export function groszeNaTekst(grosze) {
  return naTekstKwoty(grosze)
}

/** Kwota w groszach do pokazania ("3 251,00 zł"). */
export function pokazGrosze(grosze) {
  return formatPln(naTekstKwoty(grosze))
}

export function linieZPozycja(stan) {
  return stan.koszty ? stan.koszty.linie.filter((l) => l.wierszKlucz != null) : []
}

export function linieBezPozycji(stan) {
  return stan.koszty ? stan.koszty.linie.filter((l) => l.wierszKlucz == null) : []
}

/** Linia bez pozycji z kosztem 0,00 (poza świeżo dodaną) jest schowana pod odnośnikiem. */
export function czyLiniaPusta(l) {
  return l.wierszKlucz == null && !l.nowa && groszeZPola(l.koszt) === 0
}

export function liczbaPustychKosztow(stan) {
  return linieBezPozycji(stan).filter(czyLiniaPusta).length
}

/** Linie bez pozycji do pokazania: wszystkie, gdy `pokazPuste`, inaczej bez pustych. */
export function linieBezPozycjiWidoczne(stan) {
  const wszystkie = linieBezPozycji(stan)
  return stan.koszty?.pokazPuste ? wszystkie : wszystkie.filter((l) => !czyLiniaPusta(l))
}

export function przelaczPusteKoszty(stan) {
  if (!stan.koszty) return stan
  return { ...stan, koszty: { ...stan.koszty, pokazPuste: !stan.koszty.pokazPuste } }
}

/** Wartość pola kosztu pozycji (puste, gdy pozycja nie ma linii kosztu). */
export function kosztPozycji(stan, wierszKlucz) {
  const l = linieZPozycja(stan).find((x) => x.wierszKlucz === wierszKlucz)
  return l ? l.koszt : ''
}

/** Zmiana kosztu pozycji; puste pole usuwa linię, nowa wartość bez linii ją tworzy. */
export function zmienKosztPozycji(stan, wierszKlucz, wartosc) {
  if (!stan.koszty) return stan
  const w = stan.wiersze.find((x) => x.klucz === wierszKlucz)
  if (!w) return stan
  const istnieje = stan.koszty.linie.some((l) => l.wierszKlucz === wierszKlucz)
  let linie
  if (tekst(wartosc).trim() === '') {
    linie = stan.koszty.linie.filter((l) => l.wierszKlucz !== wierszKlucz)
  } else if (istnieje) {
    linie = stan.koszty.linie.map((l) => (l.wierszKlucz === wierszKlucz ? { ...l, koszt: wartosc } : l))
  } else {
    const etykieta = tekst(w.nazwa).trim() || tekst(w.typ).trim()
    linie = [
      ...stan.koszty.linie,
      { lid: nowyKlucz(), klucz: null, etykieta, koszt: wartosc, wierszKlucz, reczna: false, korekta: false, nowa: false },
    ]
  }
  return { ...stan, koszty: { ...stan.koszty, linie } }
}

/** Nowa linia kosztu bez pozycji (klucz null, ręczna). */
export function dodajSamKoszt(stan) {
  if (!stan.koszty) return stan
  const linia = { lid: nowyKlucz(), klucz: null, etykieta: '', koszt: '', wierszKlucz: null, reczna: true, korekta: false, nowa: true }
  return { ...stan, koszty: { ...stan.koszty, linie: [...stan.koszty.linie, linia] } }
}

export function zmienLinieKosztu(stan, lid, pole, wartosc) {
  if (!stan.koszty) return stan
  return {
    ...stan,
    koszty: { ...stan.koszty, linie: stan.koszty.linie.map((l) => (l.lid === lid ? { ...l, [pole]: wartosc } : l)) },
  }
}

export function usunLinieKosztu(stan, lid) {
  if (!stan.koszty) return stan
  return { ...stan, koszty: { ...stan.koszty, linie: stan.koszty.linie.filter((l) => l.lid !== lid) } }
}

export function zmienMarze(stan, klucz, wartosc) {
  if (!stan.koszty) return stan
  return {
    ...stan,
    koszty: { ...stan.koszty, marze: stan.koszty.marze.map((m) => (m.klucz === klucz ? { ...m, kwota: wartosc } : m)) },
  }
}

/** Składnik zmieniony względem wartości z ładowania (porównanie w groszach). */
export function marzaZmieniona(m) {
  return groszeZPola(m.kwota) !== groszeZPola(m.bazowa)
}

/** Wartość "było" do pokazania przy zmienionym składniku: pierwotna z serwera albo z ładowania; '' gdy bez zmiany. */
export function marzaBylo(m) {
  const baza = m.pierwotna ?? m.bazowa
  return groszeZPola(m.kwota) === groszeZPola(baza) ? '' : baza
}

/** Suma linii w groszach (bez korekty o bazę). */
export function sumaLiniiGrosze(stan) {
  return stan.koszty ? stan.koszty.linie.reduce((s, l) => s + groszeZPola(l.koszt), 0) : 0
}

/** Zapisana suma plus delta zmian linii (zgodnie z backendem). */
export function sumaKosztowGrosze(stan) {
  if (!stan.koszty) return 0
  return stan.koszty.sumaBazowa + (sumaLiniiGrosze(stan) - stan.koszty.sumaLiniiBazowa)
}

export function sumaMarzyGrosze(stan) {
  return stan.koszty ? stan.koszty.marze.reduce((s, m) => s + groszeZPola(m.kwota), 0) : 0
}

/**
 * Bilans na żywo: netto = koszty planowane + marże. Przy podstawie brutto netto bierzemy
 * z ostatniego podglądu serwera (`nettoPodgladu`), inaczej z pola. `status`: zgadza,
 * do_pokrycia (koszty + marże > netto) albo nadwyzka. null bez kosztów.
 */
export function bilans(stan, nettoPodgladu) {
  if (!stan.koszty || czyCp(stan)) return null
  const zPola = naGrosze(stan.cena.netto)
  const zPodgladu = naGrosze(nettoPodgladu)
  const netto = stan.cena.podstawa === PODSTAWA_BRUTTO ? (zPodgladu ?? zPola ?? 0) : (zPola ?? 0)
  const koszty = sumaKosztowGrosze(stan)
  const marze = sumaMarzyGrosze(stan)
  const roznica = netto - koszty - marze
  const status = roznica === 0 ? 'zgadza' : roznica < 0 ? 'do_pokrycia' : 'nadwyzka'
  return { netto, koszty, marze, roznica, status }
}

/** Linie z pustą nazwą (ręczne bez nazwy) blokują zapis. */
export function bledyKoszty(stan) {
  if (!stan.koszty) return []
  return stan.koszty.linie.filter((l) => l.reczna && tekst(l.etykieta).trim() === '').map((l) => l.lid)
}

/** Parametr `koszty` podglądu i zapisu; null (brak parametru) gdy edytor nie ma kosztów. */
export function kosztyDoWywolania(stan) {
  if (!stan.koszty || czyCp(stan)) return null
  const indeks = (klucz) => (klucz == null ? -1 : stan.wiersze.findIndex((w) => w.klucz === klucz))
  const linie = stan.koszty.linie.map((l) => {
    const i = indeks(l.wierszKlucz)
    let etykieta = tekst(l.etykieta).trim()
    if (l.klucz == null && i >= 0) {
      const w = stan.wiersze[i]
      etykieta = tekst(w.nazwa).trim() || tekst(w.typ).trim() || etykieta
    }
    return {
      klucz: l.klucz,
      etykieta,
      koszt_plan: naTekstKwoty(groszeZPola(l.koszt)),
      wiersz: i >= 0 ? i : null,
    }
  })
  const marze = {}
  for (const m of stan.koszty.marze) {
    if (marzaZmieniona(m)) marze[m.klucz] = naTekstKwoty(groszeZPola(m.kwota))
  }
  return { linie, marze }
}

/**
 * Sekcja "Koszty i marże" okna potwierdzenia. `sumaZapisanaGrosze` to suma kosztów z
 * ładowania. `prowizjaNaliczona`: `koszty.rozliczenie_handlowca.naliczone`.
 * @returns {{koszty: {przed: string, po: string}|null, marze: {etykieta, przed, po}[], ostrzezenie: string}|null}
 */
export function roznicaKosztowDoOkna(stan, sumaZapisanaGrosze, prowizjaNaliczona) {
  if (!stan.koszty) return null
  const po = sumaKosztowGrosze(stan)
  const koszty = po === sumaZapisanaGrosze ? null : { przed: pokazGrosze(sumaZapisanaGrosze), po: pokazGrosze(po) }
  const zmienione = stan.koszty.marze.filter(marzaZmieniona)
  const marze = zmienione.map((m) => ({
    etykieta: m.etykieta,
    przed: pokazGrosze(groszeZPola(m.bazowa)),
    po: pokazGrosze(groszeZPola(m.kwota)),
  }))
  const narzut = zmienione.some((m) => m.klucz === KLUCZ_SKLADNIKA_NARZUT)
  return { koszty, marze, ostrzezenie: prowizjaNaliczona && narzut ? MSG_PROWIZJA_NALICZONA : '' }
}
