// Logika czysta (bez importu frappe-ui / @) do wyswietlania uzytkownikow
// (doctype 'User') po imieniu i nazwisku zamiast po e-mailu w kontrolce
// Link.vue: filtr "Przypisany handlowiec" na liscie leadow, filtry szybkie i
// popover Filtr na leadach/szansach/klientach.
//
// Powod fixu: frappe.desk.search.search_link dla doctype 'User' zwraca
// `value` = e-mail i `description` = pelna nazwa jako HTML, bez `label` w
// ogole, wiec Link.vue::transform() ("label: option.label || option.value")
// pokazywal w dropdownie pogrubiony e-mail zamiast nazwiska, a zamknieta
// kontrolka (Autocomplete::displayValue) zawsze wyswietlala e-mail. Operator
// domyslny 'like' dodatkowo otwieral zwykle pole tekstowe zamiast
// autouzupelniania (patrz Filter.vue::getDefaultOperator). Zapytanie do
// serwera (user_query) juz dopasowuje wpisany tekst do pelnej nazwy, wiec
// wystarczy poprawic tylko etykiety po stronie klienta.
//
// Zrodlem prawdy o nazwisku jest usersStore().getUser(email).full_name
// (frontend/src/stores/users.js) -- ten sam wzorzec co
// FieldLayout/Field.vue dla pol fieldtype='User'. getUser nigdy nie rzuca
// wyjatku: dla nieznanego e-maila zwraca zaslepke z full_name =
// email.split('@')[0].

/**
 * Usuwa znaczniki HTML i encje &nbsp; z opisu zwracanego przez search_link
 * (dla doctype User pole `description` to pelna nazwa opakowana w HTML),
 * scala wielokrotne biale znaki i przycina. Ta sama logika co lokalny
 * stripHtml w Controls/Link.vue, zduplikowana celowo, zeby ten modul zostal
 * frappe-free i mozliwy do przetestowania bez montowania komponentu Vue.
 */
function stripHtml(html) {
  if (!html) return ''
  return html
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

/**
 * Mapuje surowe wiersze frappe.desk.search.search_link dla doctype 'User'
 * (`{ value, description?, label? }`) na ksztalt oczekiwany przez
 * Autocomplete (`{ label, value, description }`), z pelna nazwa jako etykieta
 * zamiast e-maila.
 *
 * Kolejnosc pierwszenstwa etykiety:
 * 1. getUser(value).full_name (przycieta), gdy niepusta,
 * 2. description z serwera, oczyszczone z HTML,
 * 3. surowa wartosc (e-mail), jako ostatni fallback.
 *
 * `description` w zwroconym obiekcie to zawsze e-mail (`value`) -- to on
 * pokazuje sie jako mala szara linia pod nazwa w dropdownie, patrz szablon
 * #item-label w Controls/Link.vue.
 *
 * Nie mutuje `wiersze`; zwraca nowa tablice nowych obiektow.
 */
export function opcjeUzytkownikow(wiersze, getUser) {
  if (!Array.isArray(wiersze)) return []
  return wiersze.map((wiersz) => {
    const wartosc = wiersz?.value ?? ''
    const uzytkownik = getUser ? getUser(wartosc) : null
    const pelnaNazwa =
      typeof uzytkownik?.full_name === 'string' ? uzytkownik.full_name.trim() : ''
    const label = pelnaNazwa || stripHtml(wiersz?.description) || wartosc
    return {
      label,
      value: wartosc,
      description: wartosc,
    }
  })
}

/**
 * Etykieta zamknietej kontrolki Link.vue dla doctype 'User': pelna nazwa
 * zamiast e-maila. `value` to surowa wartosc modelu (e-mail albo '@me'),
 * `meLabel` to etykieta dla '@me' (patrz utils/etykietaMoje.js), a
 * `getUser` to usersStore().getUser.
 *
 * Pusta/nullowa wartosc zwraca pusty string (kontrolka bez zaznaczenia),
 * '@me' zwraca meLabel bez zadnego odpytania getUser, kazda inna wartosc
 * zwraca getUser(value).full_name (przycieta, jesli niepusta) albo samo
 * value jako fallback.
 */
export function etykietaWartosciUzytkownika(value, getUser, meLabel) {
  if (!value) return ''
  if (value === '@me') return meLabel
  const uzytkownik = getUser ? getUser(value) : null
  const pelnaNazwa =
    typeof uzytkownik?.full_name === 'string' ? uzytkownik.full_name.trim() : ''
  return pelnaNazwa || value
}
