// Zakres widocznych uzytkownikow (ops#72) + opcja "@me" -- logika wspolna
// dla trzech kontrolek, ktore pytaja frappe.desk.search.search_link dla
// doctype='User': Controls/Link.vue (wybor pojedynczy), Controls/
// QuickFilterCheckList.vue (pasek szybkich filtrow, wielokrotny wybor,
// issue #214) i Controls/LinkMultiSelect.vue (popover "Filtr", wielokrotny
// wybor, issue #214). Przed issue #214 tylko Link.vue mial dostep do tej
// logiki (pola User byly wylaczone z wielokrotnego wyboru dokladnie
// dlatego, zeby QuickFilterCheckList/LinkMultiSelect nie ominely zawezenia
// do poddrzewa hierarchii -- patrz historia JSDoc w filtrWielokrotny.js).
// Wydzielone stad, zeby ta sama regula (i ta sama kolejnosc/etykieta opcji
// "@me") nie zyla w trzech kopiach.
//
// Frappe-free (zadnego importu frappe-ui/@, zero __() na poziomie modulu,
// patrz PULAPKA eager chunk w etapFiltr.js/etykietaMoje.js) -- testowalne
// bezposrednio przez vitest.

/**
 * Buduje filtry faktycznie wysylane do frappe.desk.search.search_link dla
 * doctype='User', dokladajac ograniczenie do poddrzewa hierarchii na
 * podstawie wyniku `crm.api.volteo_uzytkownicy.widoczni_uzytkownicy()`.
 *
 * `lista`:
 *   - `null`/`undefined` -- dwa ZLANE znaczenia, nierozroznialne tutaj:
 *     "jeszcze nie pobrane" ALBO odpowiedz serwera "bez ograniczenia" (dla
 *     Administratora/BYPASS_ROLES/Sales Managera spoza drzewa). Rozroznienie
 *     miedzy nimi (czy zapytanie juz wrocilo) zostaje po stronie kazdego
 *     wywolujacego komponentu (flaga `fetched` zasobu frappe-ui) -- ta
 *     funkcja dostaje gotowy wynik i w obu przypadkach zwraca `filtryBazowe`
 *     bez zmian, co jest poprawnym zachowaniem dla "bez ograniczenia", ale
 *     wywolujacy NIE powinien jej wolac zanim zapytanie nie wrocilo (patrz
 *     JSDoc w Link.vue dla wzorca "nie odpytuj, dopoki null").
 *   - tablica (moze byc pusta) -> `{...filtryBazowe, name: ['in', lista]}`,
 *     pusta lista daje wartownika `['in', ['']]` (nie dopasowuje zadnego
 *     wiersza) -- dokladnie jak w Link.vue::effectiveFilters sprzed
 *     wydzielenia.
 *   - kazda inna wartosc (np. obiekt z posredniego cache'a, zla odpowiedz
 *     API) -> traktowana jak "bez ograniczenia", bezpieczny fallback
 *     zamiast rzucania TypeError na `.length`.
 *
 * Nie mutuje `filtryBazowe` (immutability, coding-style.md): zwraca zawsze
 * NOWY obiekt.
 *
 * @param {Object|null|undefined} filtryBazowe
 * @param {string[]|null|undefined} lista
 * @returns {Object}
 */
export function filtrZakresuUzytkownikow(filtryBazowe, lista) {
  const baza =
    filtryBazowe && typeof filtryBazowe === 'object' && !Array.isArray(filtryBazowe)
      ? { ...filtryBazowe }
      : {}
  if (!Array.isArray(lista)) return baza
  baza.name = lista.length ? ['in', lista] : ['in', ['']]
  return baza
}

/**
 * Dokleja opcje "@me" jako PIERWSZA pozycja listy opcji wyniku search_link
 * (doctype='User'), z etykieta `etykietaMoje` (patrz utils/etykietaMoje.js).
 * `pomin` (domyslnie false) odpowiada `hideMe` w Link.vue -- gdy prawda,
 * opcja nie jest dokladana (formularze/przydzialy, gdzie "@me" nie ma
 * sensu, np. SidePanelLayout).
 *
 * Nie mutuje `opcje` (immutability): zwraca zawsze NOWA tablice.
 *
 * @param {Array<{label:string,value:string}>} opcje
 * @param {string} etykietaMoje
 * @param {boolean} [pomin]
 * @returns {Array<{label:string,value:string}>}
 */
export function dolozOpcjeMoje(opcje, etykietaMoje, pomin = false) {
  const lista = Array.isArray(opcje) ? opcje : []
  if (pomin) return [...lista]
  return [{ label: etykietaMoje, value: '@me' }, ...lista]
}
