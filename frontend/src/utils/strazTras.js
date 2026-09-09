// Straż tras leadów, analogiczna do straży OZE/CP w router.js (issue #16), ale na
// fladze `window.hide_leads` zamiast `window.volteo_linia_oze`/`window.volteo_linia_cp`.
// Bez dostępu bez flagi Leady serwer i tak zwraca pustą listę/dane, ale bez tej straży
// użytkownik wpisujący wprost `/crm/leads` albo `/crm/mapa-leadow` widział pustą stronę
// zamiast czytelnego „Not Permitted” (issue ops#106).
//
// Frappe-free (bez importu `frappe-ui` / `@/`), testowalne bezpośrednio przez vitest,
// ten sam wzorzec co etapFiltr.js/etykietaMoje.js. Sam plik nie czyta `window`, router.js
// przekazuje flagi jawnie, żeby ta funkcja została czystą funkcją bez efektów ubocznych.

// Trasy leadów chronione tą samą flagą co menu boczne (AppSidebar.vue/MobileSidebar.vue,
// `condition: () => !window.hide_leads`, issue ops#26): 'Leads' (lista), 'Lead' (widok
// pojedynczego leada, desktop i mobile dzielą tę samą nazwę trasy przez handleMobileView),
// 'MapaLeadow' (mapa leadów, issue ops#26).
export const TRASY_LEADOW = ['Leads', 'Lead', 'MapaLeadow']

/**
 * Czy wejście na trasę `nazwaTrasy` powinno zostać zablokowane (przekierowane na
 * „Not Permitted”) przy podanych flagach boot.
 *
 * @param {string} nazwaTrasy - `to.name` z vue-router.
 * @param {{ hideLeads?: boolean }} flagi - flagi boot przekazane jawnie przez wołającego
 *   (router.js czyta je z `window.hide_leads`).
 * @returns {boolean}
 */
export function czyZablokowana(nazwaTrasy, flagi = {}) {
  if (Boolean(flagi.hideLeads) && TRASY_LEADOW.includes(nazwaTrasy)) {
    return true
  }
  return false
}
