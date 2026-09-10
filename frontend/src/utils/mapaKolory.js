// Logika kolorowania pinezek i legendy na mapie leadów (MapaLeadow.vue,
// issue #101).
//
// Frappe-free (bez importu `frappe-ui` / `@/`), testowalne bezpośrednio przez
// vitest, ten sam wzorzec co mapaFiltry.js. Zapis/odczyt z `localStorage` też
// żyje tu, żeby MapaLeadow.vue tylko wołał gotowe funkcje.

// Paleta dla kolorowania wg użytkownika (Handlowiec / CC) -- celowo osobna
// od HEX_PO_NAZWIE_KOLORU w MapaLeadow.vue (tamta mapuje NAZWY kolorów
// statusów, ta losuje deterministycznie z hasha e-maila, więc kolizja
// wartości nie ma znaczenia).
const PALETA_UZYTKOWNIKOW = [
  '#2563eb',
  '#15803d',
  '#dc2626',
  '#d97706',
  '#7c3aed',
  '#0891b2',
  '#db2777',
  '#ca8a04',
  '#0d9488',
  '#9333ea',
  '#ea580c',
  '#4338ca',
  '#65a30d',
  '#be185d',
]

// Kolor dla leadów bez przypisania (brak lead_owner / brak custom_cc).
export const KOLOR_BRAK = '#9ca3af'

/**
 * Hash 32-bit z ciągu znaków, deterministyczny między przeładowaniami.
 * Ten sam algorytm co dawny lokalny `hashString` w MapaLeadow.vue (jitter
 * współrzędnych) -- przeniesiony tutaj jako jedno źródło prawdy.
 *
 * @param {string} str
 * @returns {number}
 */
export function hashString(str) {
  const s = String(str ?? '')
  let hash = 0
  for (let i = 0; i < s.length; i++) {
    hash = (hash << 5) - hash + s.charCodeAt(i)
    hash |= 0
  }
  return hash
}

/**
 * Deterministyczny hex dla danego użytkownika (e-mail), stały między
 * przeładowaniami mapy i między sesjami.
 *
 * @param {string} email
 * @returns {string} kolor hex
 */
export function kolorDlaUzytkownika(email) {
  if (!email) return KOLOR_BRAK
  const h = Math.abs(hashString(email))
  return PALETA_UZYTKOWNIKOW[h % PALETA_UZYTKOWNIKOW.length]
}

export const TRYBY_KOLOROWANIA = ['status', 'handlowiec', 'cc']
export const DOMYSLNY_TRYB_KOLOROWANIA = 'status'

/**
 * Klucz grupowania leada dla danego trybu kolorowania (status/handlowiec/cc).
 *
 * @param {object} lead
 * @param {'status'|'handlowiec'|'cc'} tryb
 * @param {string} brakEtykiety etykieta dla leadów bez wartości w danym trybie
 * @returns {string}
 */
export function kluczKoloru(lead, tryb, brakEtykiety) {
  if (tryb === 'handlowiec') return lead.lead_owner || brakEtykiety
  if (tryb === 'cc') return lead.custom_cc || brakEtykiety
  return lead.status || brakEtykiety
}

/**
 * Buduje wpisy legendy (klucz, kolor, liczba) dla danego trybu kolorowania,
 * posortowane malejąco po liczbie leadów. Etykiety czytelne dla człowieka
 * (np. pełne imię i nazwisko z usersStore) resolwuje wołający -- ten moduł
 * nie importuje store'ów.
 *
 * @param {object[]} leady
 * @param {'status'|'handlowiec'|'cc'} tryb
 * @param {{kolorStatusu?: (status: string) => string, brakEtykiety?: string}} opcje
 * @returns {{klucz: string, kolor: string, liczba: number}[]}
 */
export function legenda(leady, tryb, opcje = {}) {
  const brak = opcje.brakEtykiety || '(brak)'
  const liczniki = new Map()
  for (const lead of leady || []) {
    const klucz = kluczKoloru(lead, tryb, brak)
    liczniki.set(klucz, (liczniki.get(klucz) || 0) + 1)
  }
  return [...liczniki.entries()]
    .map(([klucz, liczba]) => ({
      klucz,
      liczba,
      kolor: kolorDlaKlucza(klucz, tryb, brak, opcje.kolorStatusu),
    }))
    .sort((a, b) => b.liczba - a.liczba)
}

function kolorDlaKlucza(klucz, tryb, brak, kolorStatusu) {
  if (tryb === 'status') {
    if (klucz === brak) return typeof kolorStatusu === 'function' ? kolorStatusu('') : KOLOR_BRAK
    return typeof kolorStatusu === 'function' ? kolorStatusu(klucz) : KOLOR_BRAK
  }
  if (klucz === brak) return KOLOR_BRAK
  return kolorDlaUzytkownika(klucz)
}

/**
 * Czy dane pole jest w ogóle obecne w odpowiedzi API (np. `custom_cc` na
 * permlevel 2 -- `frappe.get_list` wycina go z odpowiedzi dla ról bez
 * odczytu). Sprawdza pierwszy lead z niepustą tablicą, bo klucz jest zawsze
 * obecny albo zawsze nieobecny dla całej odpowiedzi tego samego wywołania.
 *
 * @param {object[]} leady
 * @param {string} pole
 * @returns {boolean}
 */
export function poleObecneWDanych(leady, pole) {
  if (!leady || !leady.length) return false
  return Object.hasOwn(leady[0], pole)
}

// --- Trwałość ustawień (localStorage) ---------------------------------------

export const KLUCZ_KOLOR = 'volteo.mapa.kolor'
export const KLUCZ_DYMEK = 'volteo.mapa.dymek'
export const KLUCZ_KLASTROWANIE = 'volteo.mapa.klastrowanie'

// Domyślnie WŁĄCZONE (issue #101, klastrowanie przy oddaleniu) -- przy ~9900
// pinezkach dla admina klastrowanie jest korzyścią, nie ograniczeniem, więc
// próg wejścia jest odwrotny niż przy dymku/kolorowaniu: trzeba świadomie
// wyłączyć, nie świadomie włączyć.
export const DOMYSLNE_KLASTROWANIE = true

export function domyslneUstawieniaDymka() {
  return {
    zrodlo: true,
    produkty: true,
    statusZrodla: true,
    terminSpotkania: true,
  }
}

/**
 * @returns {'status'|'handlowiec'|'cc'}
 */
export function wczytajTrybKolorowania() {
  try {
    const surowy = localStorage.getItem(KLUCZ_KOLOR)
    if (surowy && TRYBY_KOLOROWANIA.includes(surowy)) return surowy
  } catch (e) {
    /* localStorage niedostępny (tryb prywatny itp.) -- domyślny tryb */
  }
  return DOMYSLNY_TRYB_KOLOROWANIA
}

export function zapiszTrybKolorowania(tryb) {
  try {
    localStorage.setItem(KLUCZ_KOLOR, tryb)
  } catch (e) {
    /* brak localStorage -- ustawienie po prostu nie przetrwa przeładowania */
  }
}

export function wczytajUstawieniaDymka() {
  const domyslne = domyslneUstawieniaDymka()
  try {
    const surowy = localStorage.getItem(KLUCZ_DYMEK)
    if (!surowy) return domyslne
    const zapisane = JSON.parse(surowy)
    if (!zapisane || typeof zapisane !== 'object') return domyslne
    return {
      zrodlo: typeof zapisane.zrodlo === 'boolean' ? zapisane.zrodlo : domyslne.zrodlo,
      produkty: typeof zapisane.produkty === 'boolean' ? zapisane.produkty : domyslne.produkty,
      statusZrodla:
        typeof zapisane.statusZrodla === 'boolean' ? zapisane.statusZrodla : domyslne.statusZrodla,
      terminSpotkania:
        typeof zapisane.terminSpotkania === 'boolean'
          ? zapisane.terminSpotkania
          : domyslne.terminSpotkania,
    }
  } catch (e) {
    return domyslne
  }
}

export function zapiszUstawieniaDymka(ustawienia) {
  try {
    localStorage.setItem(KLUCZ_DYMEK, JSON.stringify(ustawienia))
  } catch (e) {
    /* brak localStorage -- ustawienie po prostu nie przetrwa przeładowania */
  }
}

/**
 * @returns {boolean}
 */
export function wczytajKlastrowanie() {
  try {
    const surowy = localStorage.getItem(KLUCZ_KLASTROWANIE)
    if (surowy === 'true') return true
    if (surowy === 'false') return false
  } catch (e) {
    /* localStorage niedostępny (tryb prywatny itp.) -- domyślne ustawienie */
  }
  return DOMYSLNE_KLASTROWANIE
}

export function zapiszKlastrowanie(wlaczone) {
  try {
    localStorage.setItem(KLUCZ_KLASTROWANIE, wlaczone ? 'true' : 'false')
  } catch (e) {
    /* brak localStorage -- ustawienie po prostu nie przetrwa przeładowania */
  }
}
