// Czysta logika (bez frappe-ui / @) filtrow dat w Filter.vue, CFCondition.vue
// i pasku szybkich filtrow (ops#268, uwaga 66).
//
// Trzy problemy naraz:
//  1. `DateRangePicker` z frappe-ui 1.0.0-beta.19 emituje TABLICE `[od, do]`
//     (albo `[]`), a stary kod robil `value.split(',')`, wiec rzucal
//     TypeError i zakres nigdy nie trafial na serwer.
//  2. Pusty zakres / zakres z jedna granica nie moze isc na serwer: rdzen
//     Frappe (`get_between_date_filter`) podstawia za brakujaca granice
//     DZISIAJ, wiec "Pomiedzy" bez wartosci pokazywalo dzisiejszy dzien.
//  3. Nowy operator "Jest w dniu" (`w dniu`): jeden dzien, tylko data, takze
//     dla pol Datetime. Serwer (`crm.volteo_lista_szans.normalizuj_zakres_dnia`)
//     zamienia go na `["between", [D, D]]`.

export const OPERATOR_W_DNIU = 'w dniu'

/**
 * Rozbija wartosc zakresu dat na `[od, do]`. Przyjmuje tablice (to emituje
 * DateRangePicker) albo string "od,do" (zapisany widok / wpis reczny).
 * Brak wartosci albo tablica pusta daje `[]`; brakujaca granica zostaje jako
 * pusty string, zeby wolajacy mogl odroznic "pol zakresu".
 */
export function czesciZakresuDat(value) {
  if (value === null || value === undefined || value === '') return []
  const czesci = Array.isArray(value) ? value : String(value).split(',')
  const przyciete = czesci.map((c) =>
    c === null || c === undefined ? '' : String(c).trim(),
  )
  if (przyciete.every((c) => c === '')) return []
  return [przyciete[0] ?? '', przyciete[1] ?? '']
}

/**
 * True, gdy warunek daty jest "jeszcze nie wypelniony" i NIE moze trafic do
 * filtrow wysylanych na serwer: `w dniu` bez daty albo `between` bez obu
 * granic. Inne operatory zwracaja false (zachowanie sprzed ops#268).
 */
export function czyPustyWarunekDaty(operator, value) {
  if (operator === OPERATOR_W_DNIU) {
    return value === null || value === undefined || String(value).trim() === ''
  }
  if (operator === 'between') {
    const [od, do_] = czesciZakresuDat(value)
    return !od || !do_
  }
  return false
}

/**
 * Wartosc dla kontrolki daty w pasku szybkich filtrow: `["w dniu", D]` daje
 * `D`, wszystko inne `null` (wolajacy zostaje przy dotychczasowej logice).
 */
export function dzienZFiltraSzybkiegoDaty(raw) {
  if (
    Array.isArray(raw) &&
    typeof raw[0] === 'string' &&
    raw[0].toLowerCase() === OPERATOR_W_DNIU
  ) {
    const dzien = typeof raw[1] === 'string' ? raw[1] : ''
    return dzien === '@dzis' ? '' : dzien.slice(0, 10)
  }
  return null
}

/**
 * Filtr paska szybkiego dla pola Date/Datetime: `["w dniu", D]` (D bez
 * czesci godzinowej), albo `undefined` dla pustej wartosci (klucz usuwany).
 */
export function spakujFiltrSzybkiDaty(wartosc) {
  if (typeof wartosc !== 'string' || wartosc.trim() === '') return undefined
  return [OPERATOR_W_DNIU, wartosc.trim().slice(0, 10)]
}
