// Czyste funkcje wariantu "karty" panelu bocznego szansy i leada (ops#326):
// podsumowania sekcji widoczne po zwinieciu, formaty kwot/dat/telefonu,
// rozbicie pola Uwagi na linie "Klucz: wartosc" i pamiec otwartych sekcji.
// Frappe-free (bez importow `frappe-ui` / `@/`), testowalne przez vitest.

import { formatujGgMm } from './czasKontaktu'

const NBSP = ' '

// --- Formaty -----------------------------------------------------------------

function grupujTysiace(cyfry) {
  return cyfry.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

/**
 * Liczba w polskim zapisie: spacja jako separator tysiecy, przecinek
 * dziesietny. `miejsca` = stala liczba miejsc; `maks` = maksymalna liczba
 * miejsc (zbedne zera obcinane).
 * @returns {string} pusty string dla wartosci nieliczbowej
 */
export function formatLiczba(wartosc, { miejsca = null, maks = 2 } = {}) {
  if (wartosc === null || wartosc === undefined || wartosc === '') return ''
  const n = Number(wartosc)
  if (!Number.isFinite(n)) return ''
  const m = miejsca === null ? maks : miejsca
  let tekst = Math.abs(n).toFixed(m)
  if (miejsca === null && tekst.includes('.')) {
    tekst = tekst.replace(/0+$/, '').replace(/\.$/, '')
  }
  const [calosc, ulamek] = tekst.split('.')
  const wynik = grupujTysiace(calosc) + (ulamek ? ',' + ulamek : '')
  return (n < 0 ? '-' : '') + wynik
}

/** "63 093,60 zł" (jednostka=false daje samo "63 093,60"). */
export function formatKwota(wartosc, { jednostka = true } = {}) {
  const liczba = formatLiczba(wartosc, { miejsca: 2 })
  if (!liczba) return ''
  return jednostka ? `${liczba}${NBSP}zł` : liczba
}

const RE_DATA_PELNA = /^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?)?$/
const RE_DATA = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?/

/** "2026-11-03" -> "03.11.2026" (pusty string dla niepoprawnej wartosci). */
export function formatData(wartosc) {
  const m = RE_DATA.exec(String(wartosc ?? ''))
  return m ? `${m[3]}.${m[2]}.${m[1]}` : ''
}

/** "2026-11-03 14:30:00" -> "03.11.2026, 14:30" (bez godziny: sama data). */
export function formatDataCzas(wartosc) {
  const m = RE_DATA.exec(String(wartosc ?? ''))
  if (!m) return ''
  const data = `${m[3]}.${m[2]}.${m[1]}`
  return m[4] !== undefined ? `${data}, ${m[4]}:${m[5]}` : data
}

/**
 * Wyswietlany numer telefonu: wylacznie grupowanie, nigdy zmiana danych.
 * "+48600123456" -> "+48 600 123 456", "600123456" -> "600 123 456".
 * Inne ksztalty wracaja bez zmian.
 */
export function formatTelefon(wartosc) {
  if (wartosc === null || wartosc === undefined) return ''
  const tekst = String(wartosc).trim()
  if (!tekst) return ''
  const plus = tekst.startsWith('+')
  const cyfry = tekst.replace(/\D/g, '')
  const grupuj = (s) => s.replace(/(\d{3})(?=\d)/g, '$1 ')
  if (plus && cyfry.length === 11 && cyfry.startsWith('48')) {
    return `+48 ${grupuj(cyfry.slice(2))}`
  }
  if (!plus && cyfry.length === 9 && /^[\d\s-]+$/.test(tekst)) {
    return grupuj(cyfry)
  }
  return tekst
}

// --- Uwagi -------------------------------------------------------------------

const SEPARATOR_UWAG = ' | '

function bezOgonkow(s) {
  return s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/ł/g, 'l')
    .replace(/Ł/g, 'L')
    .toLowerCase()
    .trim()
}

// Znane klucze webhooka Facebooka zapisywane bez polskich liter.
const ETYKIETY_UWAG = {
  zrodlo: 'Źródło',
  'system rozliczen': 'System rozliczeń',
  'zasady rozliczen': 'Zasady rozliczeń',
  'posiada pv': 'Posiada PV',
  produkt: 'Produkt',
  formularz: 'Formularz',
  kampania: 'Kampania',
  odpowiedzi: 'Odpowiedzi',
  miasto: 'Miasto',
  'kod pocztowy': 'Kod pocztowy',
}

/**
 * Rozbija tekst Uwag na pary {klucz, wartosc}. Segmenty rozdziela " | ",
 * klucz od wartosci pierwszy ": ". Segment bez dwukropka ma pusty klucz.
 * Nigdy nie zmienia zapisanego tekstu, tylko go prezentuje.
 */
export function rozbijUwagi(tekst) {
  if (tekst === null || tekst === undefined) return []
  return String(tekst)
    .split(SEPARATOR_UWAG)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((segment) => {
      const i = segment.indexOf(': ')
      if (i <= 0) return { klucz: '', wartosc: segment }
      const surowy = segment.slice(0, i).trim()
      const klucz = ETYKIETY_UWAG[bezOgonkow(surowy)] ?? surowy
      return { klucz, wartosc: segment.slice(i + 2).trim() }
    })
}

// --- Pamiec otwartych sekcji --------------------------------------------------

export function kluczSekcji(doctype, nazwaSekcji) {
  return `volteo.panel.sekcja.${doctype}.${nazwaSekcji}`
}

/** @returns {boolean|null} null, gdy brak zapisu (lub localStorage niedostepny) */
export function wczytajOtwartaSekcje(doctype, nazwaSekcji) {
  try {
    const v = localStorage.getItem(kluczSekcji(doctype, nazwaSekcji))
    return v === '1' ? true : v === '0' ? false : null
  } catch (e) {
    return null
  }
}

export function zapiszOtwartaSekcje(doctype, nazwaSekcji, otwarta) {
  try {
    localStorage.setItem(kluczSekcji(doctype, nazwaSekcji), otwarta ? '1' : '0')
  } catch (e) {
    /* tryb prywatny: stan po prostu nie przetrwa przeladowania */
  }
}

// --- Podsumowania sekcji ------------------------------------------------------

// Wartosci, ktore w podsumowaniu nic nie mowia (przelacznik na "Nie", zero).
const WARTOSCI_NIEZNACZACE = new Set(['nie', '0', 'false', 'no'])

const BRAK_DANYCH = 'Brak danych'

function pustaWartosc(v) {
  return v === null || v === undefined || String(v).trim() === ''
}

function odmianaKontaktow(n) {
  if (n === 1) return 'kontakt'
  const d = n % 100
  const j = n % 10
  if (j >= 2 && j <= 4 && !(d >= 12 && d <= 14)) return 'kontakty'
  return 'kontaktów'
}

function polaSekcji(sekcja) {
  const kolumny = sekcja?.columns || []
  return kolumny.flatMap((k) => k.fields || [])
}

/**
 * Wartosc pola do pokazania w podsumowaniu. `opcje.rozwiaz(pole, wartosc)`
 * moze zwrocic czytelny tytul (imie uzytkownika, tytul linku); zwrocone
 * undefined/null oznacza "uzyj surowej wartosci".
 */
export function wartoscDoWyswietlenia(pole, wartosc, opcje = {}) {
  if (pustaWartosc(wartosc)) return ''
  const typ = pole?.fieldtype
  const nazwa = pole?.fieldname || ''
  if (typ === 'Check') return Number(wartosc) ? pole.label || '' : ''
  if (!typ && RE_DATA_PELNA.test(String(wartosc))) return formatDataCzas(wartosc)
  if (typ === 'Duration' || nazwa === 'custom_czas_do_kontaktu') {
    return formatujGgMm(wartosc)
  }
  if (['Select', 'Check', 'Data'].includes(typ) && WARTOSCI_NIEZNACZACE.has(String(wartosc).trim().toLowerCase())) {
    return ''
  }
  if (typ === 'Date') return formatData(wartosc)
  if (typ === 'Datetime') return formatDataCzas(wartosc)
  if (typ === 'Currency') return Number(wartosc) === 0 ? '' : formatKwota(wartosc)
  if (['Int', 'Float', 'Percent'].includes(typ)) {
    return Number(wartosc) === 0 ? '' : formatLiczba(wartosc)
  }
  if (nazwa === 'mobile_no' || nazwa === 'phone') return formatTelefon(wartosc)
  if (typ === 'User' || typ === 'Link' || typ === 'Dynamic Link') {
    const r = opcje.rozwiaz?.(pole, wartosc)
    return pustaWartosc(r) ? String(wartosc) : String(r)
  }
  if (nazwa === 'custom_uwagi_import') {
    return rozbijUwagi(wartosc)[0]?.wartosc || ''
  }
  return String(wartosc).replace(/\s+/g, ' ').trim()
}

function wartosc(sekcja, doc, nazwa, opcje) {
  const pole = polaSekcji(sekcja).find((p) => p.fieldname === nazwa)
  const surowa = doc?.[nazwa]
  if (pustaWartosc(surowa)) return ''
  return wartoscDoWyswietlenia(pole || { fieldname: nazwa }, surowa, opcje)
}

// Pola, z ktorych sekcja nie buduje ogolnego podsumowania.
const TYPY_BEZ_PODSUMOWANIA = [
  'Button',
  'HTML',
  'Table',
  'Attach',
  'Attach Image',
  'Text Editor',
  'Geolocation',
  'Password',
  'Code',
]

/**
 * Jednolinijkowe podsumowanie sekcji, widoczne takze po zwinieciu.
 *
 * @param sekcja  {label, name, columns:[{fields}]} (po parsedField: z `visible`)
 * @param doc     dokument (szansa/lead)
 * @param opcje   {rozwiaz(pole, wartosc), liczbaKontaktow, t(tekst)}
 */
export function podsumowanieSekcji(sekcja, doc, opcje = {}) {
  const t = opcje.t || ((s) => s)
  const etykieta = String(sekcja?.label || '').trim().toLowerCase()
  const w = (nazwa) => wartosc(sekcja, doc, nazwa, opcje)
  const sklej = (czesci, sep = ' · ') => czesci.filter(Boolean).join(sep)

  if (sekcja?.name === 'contacts_section' || etykieta === 'klient') {
    const n = opcje.liczbaKontaktow
    if (Number.isInteger(n)) {
      return n > 0 ? `${n} ${t(odmianaKontaktow(n))}` : t('Brak kontaktów')
    }
    return t(BRAK_DANYCH)
  }

  if (etykieta === 'dane klienta') return t('Imię, nazwisko, telefon')

  if (etykieta === 'dane instalacji') {
    const moc = formatLiczba(doc?.custom_pv_power_kwp, { maks: 2 })
    const kwota = formatKwota(doc?.deal_value, { jednostka: false })
    const tekst = sklej([
      moc && Number(doc.custom_pv_power_kwp) !== 0 ? `${moc} kWp` : '',
      kwota && Number(doc.deal_value) !== 0 ? `${kwota} zł brutto` : '',
    ])
    if (tekst) return tekst
  }

  if (etykieta === 'nieruchomość' || etykieta === 'adres') {
    const ulica = sklej([w('custom_install_address'), w('custom_nr_domu')], ' ')
    const miasto = sklej(
      [w('custom_install_postal_code'), w('custom_install_city')],
      ' ',
    )
    const tekst = sklej([ulica, miasto], ', ')
    if (tekst) return tekst
  }

  if (etykieta === 'spotkanie') {
    const tekst = sklej([w('custom_termin_spotkania'), w('lead_owner')])
    if (tekst) return tekst
  }

  if (etykieta === 'źródło') {
    const tekst = sklej([w('custom_import_source'), w('custom_import_date')])
    if (tekst) return tekst
  }

  const wartosci = []
  for (const pole of polaSekcji(sekcja)) {
    if (wartosci.length >= 3) break
    if (pole.visible === false) continue
    if (TYPY_BEZ_PODSUMOWANIA.includes(pole.fieldtype)) continue
    const tekst = w(pole.fieldname)
    if (tekst) wartosci.push(tekst)
  }
  return wartosci.length ? wartosci.join(' · ') : t(BRAK_DANYCH)
}

const STATUSY_ZAKONCZONE = ['Done', 'Canceled']

/** Polska odmiana: forma dla 1, dla 2-4 (poza 12-14) i dla reszty. */
function odmien(n, jeden, kilka, wiele) {
  const d = n % 100
  const j = n % 10
  if (n === 1) return jeden
  return j >= 2 && j <= 4 && !(d >= 12 && d <= 14) ? kilka : wiele
}

/** "1 otwarte" / "2 otwarte" / "5 otwartych". */
export function liczbaOtwartych(n) {
  return `${n} ${odmien(n, 'otwarte', 'otwarte', 'otwartych')}`
}

/** "1 zakończone" / "2 zakończone" / "5 zakończonych". */
export function liczbaZakonczonych(n) {
  return `${n} ${odmien(n, 'zakończone', 'zakończone', 'zakończonych')}`
}

/**
 * Podsumowanie karty Zadania: "3 otwarte · 3 zakończone", "2 otwarte",
 * "Wszystko zrobione · 6 zakończonych", "Brak zadań".
 */
export function podsumowanieZadan(otwarte, zakonczone = 0) {
  if (!otwarte && !zakonczone) return 'Brak zadań'
  if (!otwarte) return `Wszystko zrobione · ${liczbaZakonczonych(zakonczone)}`
  if (!zakonczone) return liczbaOtwartych(otwarte)
  return `${liczbaOtwartych(otwarte)} · ${liczbaZakonczonych(zakonczone)}`
}

function dzienKalendarzowy(v) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(v ?? ''))
  return m ? Date.UTC(+m[1], +m[2] - 1, +m[3]) : null
}

/**
 * Dzieli zadania na otwarte (Backlog/Todo/In Progress) i zakonczone
 * (Done/Canceled). Otwarte: przeterminowane pierwsze, potem najblizszy
 * termin rosnaco, bez terminu na koncu, remisy po `modified` malejaco.
 * Zakonczone: najnowsze (`modified`) pierwsze. `zostajaOtwarte` to zbior
 * nazw zadan, ktore maja zostac na liscie otwartych mimo statusu zakonczonego
 * (przejsciowy stan "Cofnij").
 */
export function podzielZadania(lista, teraz = new Date(), zostajaOtwarte = null) {
  const dzis = Date.UTC(teraz.getFullYear(), teraz.getMonth(), teraz.getDate())
  const otwarte = []
  const zakonczone = []
  for (const t of lista || []) {
    const koniec = STATUSY_ZAKONCZONE.includes(t.status)
    if (koniec && !zostajaOtwarte?.has(String(t.name))) zakonczone.push(t)
    else otwarte.push(t)
  }
  const modMalejaco = (a, b) =>
    String(b.modified || '').localeCompare(String(a.modified || ''))
  otwarte.sort((a, b) => {
    const da = dzienKalendarzowy(a.due_date)
    const db = dzienKalendarzowy(b.due_date)
    if (da === null && db === null) return modMalejaco(a, b)
    if (da === null) return 1
    if (db === null) return -1
    const pa = da < dzis
    const pb = db < dzis
    if (pa !== pb) return pa ? -1 : 1
    if (da !== db) return da - db
    return modMalejaco(a, b)
  })
  zakonczone.sort(modMalejaco)
  return { otwarte, zakonczone }
}

/**
 * Czy placeholder jest wygenerowany przez serwer ("Dodaj {etykieta}...",
 * "Add {label}...", "Wybierz {etykieta}...") zamiast ustawiony jawnie.
 */
export function czyWygenerowanyPlaceholder(tekst) {
  return /^(Dodaj|Add|Wybierz|Select)\s/i.test(String(tekst ?? '').trim())
}
