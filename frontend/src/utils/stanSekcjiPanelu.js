// Pamiec zwinietych i rozwinietych sekcji panelu bocznego (ops#330).
//
// Jeden wpis localStorage na uzytkownika i doctype:
//   volteo_panel_sekcje::<user>::<doctype>  ->  {"<nazwa sekcji>": true|false}
// Klucz sekcji to `section.name` z ukladu CRM Fields Layout (backend
// uzupelnia go etykieta, gdy brak nazwy), nigdy indeks: dodanie lub
// przestawienie sekcji w ukladzie nie przesuwa zapamietanych stanow.
//
// Kazdy dostep do magazynu w try/catch (tryb prywatny, zablokowane dane
// witryny): bez magazynu panel dziala na stanach domyslnych z ukladu.
// Frappe-free (bez importow `frappe-ui` / `@/`), testowalne przez vitest.

export const PREFIKS_STANU = 'volteo_panel_sekcje'

// Klucze sprzed ops#330 (panel w kartach, ops#326): per doctype, bez
// uzytkownika, jeden klucz na sekcje z wartoscia '1'/'0'.
const PREFIKS_STARY = 'volteo.panel.sekcja.'

export function kluczStanuSekcji(user, doctype) {
  return `${PREFIKS_STANU}::${user || 'Guest'}::${doctype}`
}

function domyslnyMagazyn() {
  try {
    return globalThis.localStorage || null
  } catch (e) {
    return null
  }
}

/** Tekst z magazynu -> {nazwa: boolean}; smieci i zle typy sa pomijane. */
export function parsujStan(tekst) {
  if (!tekst) return {}
  let surowy
  try {
    surowy = JSON.parse(tekst)
  } catch (e) {
    return {}
  }
  if (!surowy || typeof surowy !== 'object' || Array.isArray(surowy)) return {}
  const stan = {}
  for (const [nazwa, wartosc] of Object.entries(surowy)) {
    if (typeof wartosc === 'boolean') stan[nazwa] = wartosc
  }
  return stan
}

/** Stany ze starych kluczy ops#326 dla danego doctype (tylko odczyt). */
function wczytajStareKlucze(doctype, magazyn) {
  const prefiks = `${PREFIKS_STARY}${doctype}.`
  const stan = {}
  for (let i = 0; i < magazyn.length; i++) {
    const klucz = magazyn.key(i)
    if (!klucz || !klucz.startsWith(prefiks)) continue
    const v = magazyn.getItem(klucz)
    if (v === '1' || v === '0') stan[klucz.slice(prefiks.length)] = v === '1'
  }
  return stan
}

/**
 * Zapamietany stan sekcji uzytkownika dla doctype. Gdy nowego wpisu jeszcze
 * nie ma, przejmuje stany ze starych kluczy ops#326 (bez ich kasowania).
 * @returns {Object<string, boolean>} pusty obiekt, gdy brak zapisu lub magazynu
 */
export function wczytajStanSekcji(user, doctype, magazyn = domyslnyMagazyn()) {
  if (!magazyn) return {}
  try {
    const tekst = magazyn.getItem(kluczStanuSekcji(user, doctype))
    if (tekst !== null && tekst !== undefined) return parsujStan(tekst)
    return wczytajStareKlucze(doctype, magazyn)
  } catch (e) {
    return {}
  }
}

/** @returns {boolean} false, gdy zapis sie nie udal (stan zyje do odswiezenia) */
export function zapiszStanSekcji(user, doctype, stan, magazyn = domyslnyMagazyn()) {
  if (!magazyn) return false
  try {
    magazyn.setItem(kluczStanuSekcji(user, doctype), JSON.stringify(stan || {}))
    return true
  } catch (e) {
    return false
  }
}

/**
 * Stan karty panelu (wariant karty, ops#326) bez zapisu uzytkownika:
 * otwarta tylko pierwsza widoczna; ze `startZwiniete` (szansa) wszystkie
 * zwiniete. Zapis uzytkownika zawsze wygrywa (rozstrzygnijOtwarcie).
 */
export function domyslnieOtwartaKarta({ startZwiniete = false, pierwszaWidoczna = false } = {}) {
  return !startZwiniete && !!pierwszaWidoczna
}

// Klucz karty Zadania (TasksSection) w tym samym zapisie co sekcje ukladu;
// prefiks "__" nie koliduje z nazwami sekcji z CRM Fields Layout.
export const SEKCJA_ZADANIA = '__zadania'

/** Czy sekcja ma byc otwarta: zapis uzytkownika, a bez zapisu `domyslny`. */
export function rozstrzygnijOtwarcie(stan, nazwa, domyslny) {
  if (stan && nazwa && typeof stan[nazwa] === 'boolean') return stan[nazwa]
  return !!domyslny
}
