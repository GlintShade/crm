// Pomocnicze funkcje dla pionowej galezi pol tekstowych w panelu bocznym
// (SidePanelLayout.vue, issue #177). Frappe-free (bez importu `frappe-ui` /
// `@/`), testowalne bezposrednio przez vitest, ten sam wzorzec co
// mapaKolory.js.

// Typy pol, ktore SidePanelLayout.vue renderuje w osobnej, pionowej galezi
// (etykieta u gory na calej szerokosci, textarea pod nia na calej
// szerokosci). `Code` zostaje w dotychczasowej, poziomej galezi -- nie jest
// tu wliczany celowo.
const TYPY_POL_TEKSTOWYCH = ['Small Text', 'Text', 'Long Text']

/**
 * Czy dane pole nalezy renderowac w pionowej galezi pol tekstowych.
 *
 * @param {{fieldtype?: string}} field
 * @returns {boolean}
 */
export function czyPoleTekstowe(field) {
  return TYPY_POL_TEKSTOWYCH.includes(field?.fieldtype)
}

/**
 * Liczy startowa liczbe wierszy dla natywnego <textarea>, zeby cala tresc
 * byla widoczna od razu (zanim auto-grow zmierzy DOM po zamontowaniu) --
 * albo gdy auto-grow z jakiegos powodu nie zadziala (fallback musi wtedy
 * wystarczyc sam). Domyslne 40 znakow/wiersz zmierzone na realnej kolumnie
 * panelu bocznego (~300px, tekst 13px): 48 (pierwotna wartosc) niedoszacowywalo
 * szerokosci i dawalo scrollHeight > clientHeight zaraz po zamontowaniu, zanim
 * auto-grow zdazyl poprawic wysokosc (headless po scaleniu #177).
 * Suma po liniach wejscia (split('\n')), kazda linia liczona jako
 * max(1, ceil(dlugosc / znakowNaWiersz)), suma przycieta do [min, max].
 *
 * @param {*} tekst wartosc pola (string w praktyce, ale wejscie nie jest
 *   zaufane -- patrz kontrakt walidacji na granicy systemu)
 * @param {number} znakowNaWiersz szacunkowa szerokosc jednego wiersza
 * @param {number} min dolny limit liczby wierszy
 * @param {number} max gorny limit liczby wierszy
 * @returns {number}
 */
export function liczWierszeTekstu(tekst, znakowNaWiersz = 40, min = 4, max = 40) {
  if (tekst === null || tekst === undefined) return min

  const napis = typeof tekst === 'string' ? tekst : String(tekst)
  const linie = napis.split('\n')
  const suma = linie.reduce(
    (acc, linia) => acc + Math.max(1, Math.ceil(linia.length / znakowNaWiersz)),
    0,
  )

  return Math.max(min, Math.min(max, suma))
}
