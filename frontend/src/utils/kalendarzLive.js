/**
 * Kalendarz spotkań na żywo (ops#331): czyste funkcje bez Vue.
 *
 * Serwer (crm/api/kalendarz_live.py) po commicie zapisu leada albo grafiku
 * wysyła zdarzenie `volteo_kalendarz` z treścią `{ daty: ['RRRR-MM-DD', ...] }`.
 * Pusta lista (albo brak dat) znaczy "nie wiadomo które / wszystkie daty".
 * Zdarzenie nie niesie danych leada; front pobiera je ponownie przez
 * crm.api.kalendarz.spotkania.
 */

export const ZDARZENIE_KALENDARZA = 'volteo_kalendarz'
/** Zbiera serię sygnałów w jedno zapytanie. */
export const ODSTEP_ODSWIEZENIA_MS = 1000
/** Łagodny polling, gdy przez tyle czasu nie było odświeżenia. */
export const ODSTEP_POLLINGU_MS = 60000
/** Jak często sprawdzamy, czy czas na polling. */
export const ODSTEP_SPRAWDZANIA_MS = 15000

/**
 * Czy sygnał dotyczy widocznego zakresu `od`..`do` (RRRR-MM-DD, włącznie).
 * Sygnał bez dat (albo nieczytelny) dotyczy zawsze.
 */
export function dotyczyZakresu(tresc, od, doDaty) {
  const daty = tresc?.daty
  if (!Array.isArray(daty) || !daty.length) return true
  if (!od || !doDaty) return true
  return daty.some((d) => {
    if (typeof d !== 'string' || d.length < 10) return true
    const dzien = d.slice(0, 10)
    return dzien >= od && dzien <= doDaty
  })
}

/** Czy czas na odświeżenie z pollingu: karta widoczna i dawno bez odświeżenia. */
export function czasNaPolling({
  teraz,
  ostatnie,
  widoczna,
  odstep = ODSTEP_POLLINGU_MS,
}) {
  if (!widoczna) return false
  return teraz - (ostatnie || 0) >= odstep
}
