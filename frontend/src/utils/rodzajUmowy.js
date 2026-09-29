// Kod rodzaju umowy (custom_rodzaj_umowy) dla kolumny "Rodzaj" listy Umowy
// (wariant B, b65) - krotki kod tekstowy w komorce, pelna nazwa w atrybucie
// title. Frappe-free, testowalne bezposrednio przez vitest, ten sam wzorzec
// co dealPipeline.js/etapFiltr.js.
//
// LUSTRO crm.volteo_naming.UMOWA_CODES (crm/volteo_naming.py) - ten sam
// mapping rodzaju na kod, ale kod UI dla "Fotowoltaika + Magazyn" to
// "PV+ME" (czytelniejsze w waskiej kolumnie listy), podczas gdy nazwa
// dokumentu (PRO/<KOD>/...) uzywa "PVME" bez znaku "+" (plus w nazwie
// dokumentu bylby mylacy). Przy kazdej zmianie UMOWA_CODES w forku
// zaktualizuj tez KODY_RODZAJU_UMOWY nizej.

export const KODY_RODZAJU_UMOWY = {
  Fotowoltaika: 'PV',
  'Fotowoltaika + Magazyn': 'PV+ME',
  'Magazyn energii': 'ME',
  'Czyste Powietrze': 'CP',
}

export const KOD_NIEZNANY = 'XX'

/**
 * Kod i pelna nazwa rodzaju umowy do komorki "Rodzaj" (kod widoczny w
 * kolumnie, pelna nazwa w atrybucie `title`).
 *
 * @param {string|null|undefined} rodzaj - surowa wartosc `custom_rodzaj_umowy`
 * @returns {{kod: string, pelnaNazwa: string}}
 */
export function opisRodzajuUmowy(rodzaj) {
  if (!rodzaj) {
    return { kod: KOD_NIEZNANY, pelnaNazwa: 'Brak rodzaju umowy' }
  }
  const kod = KODY_RODZAJU_UMOWY[rodzaj]
  if (!kod) {
    return { kod: KOD_NIEZNANY, pelnaNazwa: `Nieznany rodzaj umowy (${rodzaj})` }
  }
  return { kod, pelnaNazwa: rodzaj }
}
