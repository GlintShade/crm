// Cel mapy leadów: "Pokaż na mapie" z widoku leada otwiera trasę Leads w
// widoku mapa z parametrem ?lead=<name>, a MapaLeadow.vue centruje się na tym
// leadzie. Frappe-free i bez importu Vue/Leafleta, żeby decyzje (czy przycisk
// jest aktywny, jak zbudować trasę, jak odczytać i wyczyścić cel) dało się
// przetestować samym vitestem.
export const ZOOM_CELU = 14
export const KLUCZ_CELU = 'lead'

/**
 * Czy lead ma współrzędne, które da się pokazać na mapie. Konwencja projektu:
 * kolumna Float NOT NULL DEFAULT 0, więc 0 znaczy "nie ustawiono". Wartości z
 * serwera mogą przyjść jako string ("52.1"), stąd Number().
 *
 * @param {{custom_lat?: unknown, custom_lng?: unknown} | null | undefined} doc
 * @returns {boolean}
 */
export function czyMoznaPokazacNaMapie(doc) {
  if (!doc) return false
  const lat = czytajLiczbe(doc.custom_lat)
  const lng = czytajLiczbe(doc.custom_lng)
  return Number.isFinite(lat) && Number.isFinite(lng) && lat !== 0
}

function czytajLiczbe(wartosc) {
  if (wartosc === null || wartosc === undefined) return NaN
  if (typeof wartosc === 'string' && wartosc.trim() === '') return NaN
  if (typeof wartosc !== 'number' && typeof wartosc !== 'string') return NaN
  return Number(wartosc)
}

/**
 * Nazwa leada-celu z query trasy albo null. vue-router dopuszcza tablicę przy
 * powtórzonym kluczu, wtedy bierzemy pierwszy niepusty element.
 *
 * @param {Record<string, unknown> | null | undefined} query
 * @returns {string | null}
 */
export function odczytajCelMapy(query) {
  const surowa = query?.[KLUCZ_CELU]
  const kandydaci = Array.isArray(surowa) ? surowa : [surowa]
  for (const k of kandydaci) {
    if (typeof k !== 'string') continue
    const przyciete = k.trim()
    if (przyciete) return przyciete
  }
  return null
}

/**
 * Trasa widoku mapy wycentrowanej na leadzie. Zwraca nowy obiekt, wejściowe
 * query nie jest mutowane.
 *
 * @param {string} name
 * @param {Record<string, unknown>} [query]
 */
export function trasaMapyDlaLeada(name, query = {}) {
  return {
    name: 'Leads',
    params: { viewType: 'mapa' },
    query: { ...query, [KLUCZ_CELU]: name },
  }
}

/**
 * Query bez klucza celu (reszta, np. `view` zapisanego widoku, zostaje).
 *
 * @param {Record<string, unknown> | null | undefined} query
 * @returns {Record<string, unknown>}
 */
export function queryBezCelu(query) {
  if (!query) return {}
  const { [KLUCZ_CELU]: _pominiety, ...reszta } = query
  return reszta
}

/**
 * Wiersz leada o danej nazwie z listy albo null.
 *
 * @param {Array<{name: string}> | null | undefined} leady
 * @param {string | null | undefined} name
 */
export function znajdzCel(leady, name) {
  if (!Array.isArray(leady) || !name) return null
  return leady.find((lead) => lead?.name === name) || null
}

/**
 * Adres (ścieżka, query i hash) bez parametru celu, do `history.replaceState`.
 * Pozostałe parametry query i hash zostają. Zwraca nowy string.
 *
 * @param {string} href pełny URL albo sama ścieżka z query
 * @returns {string}
 */
export function adresBezCelu(href) {
  const url = new URL(href, 'http://lokalnie.invalid')
  url.searchParams.delete(KLUCZ_CELU)
  return `${url.pathname}${url.search}${url.hash}`
}
