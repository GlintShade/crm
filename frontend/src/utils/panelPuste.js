// Logika ukrywania pustych pol w panelach bocznych (lead, szansa, klient,
// zakladka Szczegoly leada, szybki podglad na mapie), issue #178.
//
// Frappe-free (bez importu `frappe-ui` / `@/`), testowalne bezposrednio przez
// vitest, ten sam wzorzec co mapaKolory.js. Zapis/odczyt z `localStorage`
// tez zyje tu, zeby SidePanelLayout.vue tylko wolal gotowe funkcje.

/**
 * Czy dana wartosc liczy sie jako "pusta" dla danego typu pola.
 *
 * `isNull` w utils/index.js zwraca false dla liczbowego zera (`cstr(0) ===
 * '0'`, niepusty string), wiec Currency/Int/Float/Percent rowne 0 i
 * odznaczony Check licza sie tam jako wypelnione -- ta funkcja celowo
 * odwraca to dla potrzeb przelacznika "Ukryj puste pola": zero na tych
 * typach ma znaczyc pusto.
 *
 * @param {*} wartosc
 * @param {string} fieldtype
 * @returns {boolean}
 */
export function czyPustaWartosc(wartosc, fieldtype) {
  if (wartosc === null || wartosc === undefined) return true

  if (fieldtype === 'Check') return !Number(wartosc)

  if (['Int', 'Float', 'Currency', 'Percent'].includes(fieldtype)) {
    return Number(wartosc) === 0
  }

  return String(wartosc).trim() === ''
}

/**
 * Czy dane pole nalezy ukryc, gdy przelacznik "Ukryj puste pola" jest
 * wlaczony. Pola wymagane (`reqd`) i przyciski (`Button`) nigdy nie sa
 * ukrywane, niezaleznie od wartosci.
 *
 * @param {{reqd?: boolean, fieldtype?: string, fieldname?: string}} pole
 * @param {*} wartosc
 * @param {boolean} ukryj czy przelacznik jest wlaczony (i nie jest to preview)
 * @returns {boolean}
 */
export function czyUkrycPole(pole, wartosc, ukryj) {
  if (!ukryj) return false
  if (pole?.reqd) return false
  if (pole?.fieldtype === 'Button') return false

  return czyPustaWartosc(wartosc, pole?.fieldtype)
}

// --- Trwalosc ustawienia (localStorage) -------------------------------------

export const KLUCZ = 'volteo.panel.ukryjPuste'

/**
 * @returns {boolean}
 */
export function wczytajUkryjPuste() {
  try {
    return localStorage.getItem(KLUCZ) === '1'
  } catch (e) {
    /* localStorage niedostepny (tryb prywatny itp.) -- domyslnie wylaczone */
    return false
  }
}

export function zapiszUkryjPuste(wartosc) {
  try {
    localStorage.setItem(KLUCZ, wartosc ? '1' : '0')
  } catch (e) {
    /* brak localStorage -- ustawienie po prostu nie przetrwa przeladowania */
  }
}
