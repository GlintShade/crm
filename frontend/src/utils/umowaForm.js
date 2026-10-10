// Struktura formularza zakladki Umowa (UmowaTab.vue) zalezna od rodzaju i
// konfiguracji szansy (b69, issue ops#252). Frappe-free, bez Vue, bez __():
// etykiety sa surowym polskim tekstem, a tlumaczy je komponent
// (PULAPKA "Eager chunk a __()": __() na poziomie modulu utils bywa
// wolane przed zaladowaniem katalogu tlumaczen).
//
// Dwie struktury: SEKCJE_DOMYSLNE (PV/PV+ME/ME i kazdy inny rodzaj) oraz
// SEKCJE_WG_RODZAJU (nadpisania per rodzaj). Dodanie sekcji dla Rozbudowy
// PV/ME = jedna zmiana w SEKCJE_WG_RODZAJU nizej.

const TAK_NIE = ['', 'Tak', 'Nie']
const OSD_OPCJE = ['', 'PGE', 'Tauron', 'Enea', 'Energa', 'Stoen (innogy)', 'Inny']
const ZALEZY_OD_ADRESU = { fieldname: 'adres_zam_jak_montaz', value: 'Nie' }

// Wartosci finansowania wysylane i zapisywane BEZ zmian; etykieta tylko w UI.
export const ETYKIETY_FINANSOWANIA = {
  'Kredyt 100%': 'Kredyt 100%',
  'Kredyt + gotówka': 'Kredyt z wkładem własnym',
  'Gotówka 100%': 'Gotówka / przelew',
}

export const OPCJE_FINANSOWANIA = [
  { label: '', value: '' },
  { label: ETYKIETY_FINANSOWANIA['Kredyt 100%'], value: 'Kredyt 100%' },
  { label: ETYKIETY_FINANSOWANIA['Gotówka 100%'], value: 'Gotówka 100%' },
  { label: ETYKIETY_FINANSOWANIA['Kredyt + gotówka'], value: 'Kredyt + gotówka' },
]

const SEKCJA_ADRES = {
  key: 'adres',
  label: 'Adres',
  fields: [
    {
      fieldname: 'adres_zam_jak_montaz',
      label: 'Czy adres montażu jest taki sam jak adres zamieszkania?',
      type: 'select',
      options: TAK_NIE,
      required: true,
    },
    ...[
      ['adres_zam_ulica', 'Ulica (adres zamieszkania)', true],
      ['adres_zam_nr_domu', 'Nr domu (adres zamieszkania)', true],
      ['adres_zam_nr_mieszkania', 'Nr mieszkania (adres zamieszkania)', false],
      ['adres_zam_kod', 'Kod pocztowy (adres zamieszkania)', true],
      ['adres_zam_miasto', 'Miasto (adres zamieszkania)', true],
      ['adres_montaz_ulica', 'Ulica (adres montażu)', true],
      ['adres_montaz_nr_domu', 'Nr domu (adres montażu)', true],
      ['adres_montaz_kod', 'Kod pocztowy (adres montażu)', true],
      ['adres_montaz_miasto', 'Miasto (adres montażu)', true],
    ].map(([fieldname, label, required]) => ({
      fieldname,
      label,
      type: 'text',
      ...(required ? { required: true } : {}),
      depends_on: ZALEZY_OD_ADRESU,
    })),
  ],
}

const SEKCJA_BUDYNEK = {
  key: 'budynek',
  label: 'Budynek',
  fields: [
    {
      fieldname: 'typ_budynku',
      label: 'Typ budynku',
      type: 'select',
      options: ['', 'Jednorodzinny', 'Wielorodzinny'],
      required: true,
    },
    {
      fieldname: 'powierzchnia_prog',
      label: 'Powierzchnia',
      type: 'select',
      options: ['', 'do 300 m²', 'powyżej 300 m²'],
      required: true,
    },
    {
      fieldname: 'powierzchnia_m2',
      label: 'Powierzchnia (m²)',
      type: 'number',
      required: true,
      depends_on: { fieldname: 'powierzchnia_prog', value: 'powyżej 300 m²' },
    },
  ],
}

const SEKCJA_FINANSOWANIE = {
  key: 'finansowanie',
  label: 'Finansowanie',
  fields: [
    {
      fieldname: 'finansowanie',
      label: 'Sposób finansowania',
      type: 'select',
      options: OPCJE_FINANSOWANIA,
      required: true,
    },
    {
      fieldname: 'wklad_wlasny_pln',
      label: 'Wkład własny (PLN)',
      type: 'number',
      step: '0.01',
      required: true,
      depends_on: { fieldname: 'finansowanie', value: 'Kredyt + gotówka' },
    },
  ],
}

const POLE_OSD = {
  fieldname: 'osd',
  label: 'OSD',
  type: 'select',
  options: OSD_OPCJE,
  required: true,
}

const SEKCJA_WARUNKI = {
  key: 'warunki',
  label: 'Warunki instalacyjne',
  fields: [
    {
      fieldname: 'internet',
      label: 'Internet',
      type: 'select',
      options: ['', 'Wi-Fi', 'Kablowy', 'Brak'],
      required: true,
    },
    {
      fieldname: 'instalacja_odgromowa',
      label: 'Instalacja odgromowa',
      type: 'select',
      options: TAK_NIE,
      required: true,
    },
    {
      fieldname: 'moc_przylaczeniowa_kw',
      label: 'Moc przyłączeniowa (kW)',
      type: 'number',
      step: '0.1',
      required: true,
    },
    {
      fieldname: 'liczba_faz',
      label: 'Liczba faz',
      type: 'select',
      options: ['', '1', '3'],
      required: true,
    },
    POLE_OSD,
    {
      fieldname: 'przekop_gruntowy',
      label: 'Przekop gruntowy',
      type: 'select',
      options: TAK_NIE,
      required: true,
    },
    {
      fieldname: 'przekop_mb',
      label: 'Przekop gruntowy (mb)',
      type: 'number',
      step: '1',
      depends_on: { fieldname: 'przekop_gruntowy', value: 'Tak' },
    },
    {
      fieldname: 'dodatkowy_kabel',
      label: 'Dodatkowy kabel',
      type: 'select',
      options: TAK_NIE,
    },
    {
      fieldname: 'dodatkowy_kabel_m',
      label: 'Dodatkowy kabel (m)',
      type: 'number',
      step: '0.1',
      depends_on: { fieldname: 'dodatkowy_kabel', value: 'Tak' },
    },
  ],
}

const SEKCJA_ISTNIEJACA_PV = {
  key: 'istniejaca_pv',
  label: 'Istniejąca instalacja fotowoltaiczna',
  fields: [
    {
      fieldname: 'istniejaca_pv',
      label: 'Czy klient ma już instalację PV?',
      type: 'select',
      options: TAK_NIE,
      required: true,
    },
    {
      fieldname: 'istniejaca_pv_moc_inwertera_kw',
      label: 'Moc inwertera (kW)',
      type: 'number',
      step: '0.1',
      required: true,
      depends_on: { fieldname: 'istniejaca_pv', value: 'Tak' },
    },
    {
      fieldname: 'istniejaca_pv_moc_kwp',
      label: 'Moc instalacji (kWp)',
      type: 'number',
      step: '0.1',
      required: true,
      depends_on: { fieldname: 'istniejaca_pv', value: 'Tak' },
    },
    {
      fieldname: 'istniejaca_pv_producent_inwertera',
      label: 'Producent inwertera',
      type: 'text',
      required: true,
      depends_on: { fieldname: 'istniejaca_pv', value: 'Tak' },
    },
  ],
}

const SEKCJA_ZGODY = {
  key: 'zgody',
  label: 'Zgody',
  fields: [
    {
      fieldname: 'zgoda_kontakt_telefoniczny',
      label: 'Zgoda na kontakt telefoniczny',
      type: 'checkbox',
    },
    {
      fieldname: 'zgoda_dzialania_promocyjne',
      label: 'Zgoda na działania promocyjne',
      type: 'checkbox',
    },
    {
      fieldname: 'zgoda_realizacja_przed_odstapieniem',
      label: 'Wnoszę o realizację Umowy przed upływem terminu na odstąpienie (Załącznik nr 3)',
      type: 'checkbox',
    },
  ],
}

// Rozbudowa PV/ME: skrocony formularz. Blok "Zakres rozbudowy" jest
// read-only z szansy (patrz zakresRozbudowy), a edytowalna jest tu tylko
// pojemnosc istniejacego magazynu, gdy dokupiono baterie.
const POLE_POJEMNOSC_ME = {
  fieldname: 'istniejacy_me_pojemnosc_kwh',
  label: 'Pojemność istniejącego magazynu (kWh)',
  type: 'number',
  step: '0.1',
  required: true,
}

const SEKCJA_OSD = { key: 'osd', label: 'OSD', fields: [POLE_OSD] }

const SEKCJA_ZAKRES_ROZBUDOWY = {
  key: 'zakres_rozbudowy',
  label: 'Zakres rozbudowy',
  fields: [],
}

export const SEKCJE_DOMYSLNE = [
  SEKCJA_ADRES,
  SEKCJA_BUDYNEK,
  SEKCJA_FINANSOWANIE,
  SEKCJA_WARUNKI,
  SEKCJA_ISTNIEJACA_PV,
  SEKCJA_ZGODY,
]

// Nadpisania per rodzaj. Do uzgodnienia z mapa ROZ (U2k): jesli wzor
// Rozbudowy drukuje warunki instalacyjne PV (internet, odgromowa, przekop,
// kabel, moc przylaczeniowa, fazy), wystarczy tu dopisac SEKCJA_WARUNKI
// (i usunac SEKCJA_OSD, bo OSD jest wtedy w warunkach).
export const SEKCJE_WG_RODZAJU = {
  'Rozbudowa PV/ME': [
    SEKCJA_ADRES,
    SEKCJA_BUDYNEK,
    SEKCJA_FINANSOWANIE,
    SEKCJA_OSD,
    SEKCJA_ZAKRES_ROZBUDOWY,
    SEKCJA_ZGODY,
  ],
}

function liczba(v) {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

function niepusty(v) {
  return v !== undefined && v !== null && String(v).trim() !== ''
}

/**
 * Czy pokazac pole pojemnosci istniejacego magazynu (Rozbudowa z bateria).
 * @param {object} prefill
 * @returns {boolean}
 */
export function pokazPojemnoscMe(prefill) {
  return liczba(prefill?.custom_oze_rozbudowa_bateria) > 0
}

/**
 * Sekcje formularza dla rodzaju. Dla Rozbudowy sekcja "Zakres rozbudowy"
 * dostaje pole pojemnosci magazynu tylko gdy bateria > 0. Zwraca nowe
 * obiekty (bez mutacji definicji).
 *
 * @param {string|null|undefined} rodzaj
 * @param {object} [prefill]
 * @returns {Array<{key: string, label: string, fields: object[]}>}
 */
export function sekcjeFormularza(rodzaj, prefill = {}) {
  const baza = SEKCJE_WG_RODZAJU[rodzaj] || SEKCJE_DOMYSLNE
  return baza.map((sek) =>
    sek.key === 'zakres_rozbudowy'
      ? { ...sek, fields: pokazPojemnoscMe(prefill) ? [POLE_POJEMNOSC_ME] : [] }
      : sek,
  )
}

/** Wszystkie pola mozliwe do wyslania (suma wszystkich wariantow), bez duplikatow. */
export function wszystkiePola() {
  const wszystkie = [
    ...SEKCJE_DOMYSLNE,
    ...Object.values(SEKCJE_WG_RODZAJU).flat(),
  ].flatMap((s) => s.fields)
  return [...wszystkie, POLE_POJEMNOSC_ME].filter(
    (f, i, arr) => arr.findIndex((x) => x.fieldname === f.fieldname) === i,
  )
}

/**
 * Etykieta finansowania wylacznie do wyswietlania (wartosc zapisu bez zmian).
 * @param {string|null|undefined} wartosc
 * @returns {string}
 */
export function etykietaFinansowania(wartosc) {
  if (!niepusty(wartosc)) return ''
  return ETYKIETY_FINANSOWANIA[wartosc] || String(wartosc)
}

/**
 * Opis wzoru (`wzor` z odpowiedzi API) do badge/baneru nad formularzem.
 * @param {{nazwa?: string, dostepny?: boolean, powod?: string}|null|undefined} wzor
 * @returns {{tekst: string, dostepny: boolean, powod: string}|null}
 */
export function opisWzoru(wzor) {
  if (!wzor || typeof wzor !== 'object') return null
  if (wzor.dostepny) {
    return { tekst: `Wzór: ${wzor.nazwa || ''}`.trim(), dostepny: true, powod: '' }
  }
  const powod = wzor.powod || ''
  return { tekst: powod, dostepny: false, powod }
}

/**
 * Wiersze bloku "Dodatki z kalkulatora (drukowane w umowie)". Pusta lista,
 * gdy nic nie ma. EMS Breeze i Pstryk to tylko informacja (nie drukowane).
 *
 * @param {object} prefill
 * @returns {Array<{key: string, label: string, value: string, info: boolean}>}
 */
export function dodatkiDoPokazania(prefill) {
  const p = prefill || {}
  const wiersze = []
  if (niepusty(p.custom_dod_klima)) {
    wiersze.push({ key: 'klima', label: 'Klimatyzacja', value: String(p.custom_dod_klima), info: false })
  }
  if (niepusty(p.custom_ev_ladowarka)) {
    wiersze.push({ key: 'ev', label: 'Ładowarka EV', value: String(p.custom_ev_ladowarka), info: false })
  }
  if (liczba(p.custom_dod_panele) > 0) {
    wiersze.push({ key: 'panele', label: 'Panele PV dodatkowe', value: `${liczba(p.custom_dod_panele)} szt.`, info: false })
  }
  if (liczba(p.custom_dod_panele_mikro) > 0) {
    wiersze.push({
      key: 'panele_mikro',
      label: 'Panele PV z mikrofalownikiem',
      value: `${liczba(p.custom_dod_panele_mikro)} szt.`,
      info: false,
    })
  }
  if (p.custom_ems_breeze === 'Tak') {
    wiersze.push({ key: 'ems', label: 'EMS Breeze', value: 'Tak (nie drukowane w umowie, w cenie)', info: true })
  }
  if (p.custom_pstryk === 'Tak') {
    wiersze.push({ key: 'pstryk', label: 'Licznik Pstryk', value: 'Tak (nie drukowane w umowie, w cenie)', info: true })
  }
  return wiersze
}

/**
 * Wiersze read-only bloku "Zakres rozbudowy" (Rozbudowa PV/ME), z szansy.
 * @param {object} prefill
 * @returns {Array<{key: string, label: string, value: string}>}
 */
export function zakresRozbudowy(prefill) {
  const p = prefill || {}
  const fmt = (v, jednostka) => (liczba(v) > 0 ? `${liczba(v)} ${jednostka}` : '-')
  return [
    { key: 'panele', label: 'Panele PV', value: fmt(p.custom_oze_rozbudowa_panele, 'szt.') },
    {
      key: 'panele_mikro',
      label: 'Panele PV z mikrofalownikiem',
      value: fmt(p.custom_oze_rozbudowa_panele_mikro, 'szt.'),
    },
    { key: 'bateria', label: 'Moduły baterii', value: fmt(p.custom_oze_rozbudowa_bateria, 'szt.') },
    { key: 'istniejaca_pv', label: 'Istniejąca PV', value: fmt(p.custom_istniejaca_pv_moc_kwp, 'kWp') },
  ]
}
