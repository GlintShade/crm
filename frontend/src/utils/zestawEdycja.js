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
]

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

export function czyCp(stan) {
  return stan?.linia === 'cp'
}

export function pustyWiersz(typ = '') {
  return { klucz: nowyKlucz(), name: null, typ, nazwa: '', ilosc: '1', jednostka: 'szt.', netto: '0', brutto: '0' }
}

function cenaDoStanu(cena, pola = POLA_CENY_WEJSCIE) {
  const c = cena || {}
  const wynik = {}
  for (const pole of pola) {
    wynik[pole] = c[pole] == null ? '' : tekst(c[pole])
  }
  return wynik
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
  return {
    linia: cp ? 'cp' : 'oze',
    wiersze: (o.wiersze || []).map(wierszZApi),
    cena: cp ? cenaDoStanu(o.cena_cp, POLA_CENY_CP) : cenaDoStanu(o.cena),
    konfiguracja: konfiguracjaDoStanu(o.konfiguracja),
    reczne: [],
    powod: '',
  }
}

export function dodajWiersz(stan, wiersz = pustyWiersz()) {
  return { ...stan, wiersze: [...stan.wiersze, wiersz] }
}

export function usunWiersz(stan, indeks) {
  if (indeks < 0 || indeks >= stan.wiersze.length) return stan
  return { ...stan, wiersze: stan.wiersze.filter((_, i) => i !== indeks) }
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
  return { ...stan, cena: { ...stan.cena, [pole]: wartosc } }
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

/** Argumenty wspólne podglądu i zapisu (wiersze + cena). */
export function doWywolania(stan) {
  return { wiersze: wierszeDoWywolania(stan), cena: cenaDoWywolania(stan) }
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
  return JSON.stringify(doZapisu(stanPoczatkowy)) !== JSON.stringify(doZapisu(stan))
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
