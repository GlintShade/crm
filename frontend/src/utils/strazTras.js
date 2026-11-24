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
// 'MapaLeadow' (mapa leadów, issue ops#26), 'Kalendarz' (kalendarz spotkań handlowców,
// ops#318: spotkanie to lead z terminem, więc bez linii Leady nie ma czego pokazać).
export const TRASY_LEADOW = ['Leads', 'Lead', 'MapaLeadow', 'Kalendarz']

// ops#425: trasy ukrywane per konto flagami `window.volteo_ukryj_umowy` /
// `window.volteo_ukryj_klienci` (menu: AppSidebar.vue, MobileSidebar.vue). 'Deals' to
// lista umów (szans), 'Deal' pojedyncza szansa; 'Contacts' lista klientów, 'Contact'
// pojedynczy klient. Dane zawęża serwer, ta straż zmienia tylko menu i wejście z adresu.
export const TRASY_UMOW = ['Deals', 'Deal']
export const TRASY_KLIENTOW = ['Contacts', 'Contact']

/**
 * Czy wejście na trasę `nazwaTrasy` powinno zostać zablokowane (przekierowane na
 * „Not Permitted”) przy podanych flagach boot.
 *
 * @param {string} nazwaTrasy - `to.name` z vue-router.
 * @param {{ hideLeads?: boolean, ukryjUmowy?: boolean, ukryjKlienci?: boolean }} flagi -
 *   flagi boot przekazane jawnie przez wołającego (router.js czyta je z `window.hide_leads`,
 *   `window.volteo_ukryj_umowy`, `window.volteo_ukryj_klienci`).
 * @returns {boolean}
 */
export function czyZablokowana(nazwaTrasy, flagi = {}) {
  if (Boolean(flagi.hideLeads) && TRASY_LEADOW.includes(nazwaTrasy)) {
    return true
  }
  if (Boolean(flagi.ukryjUmowy) && TRASY_UMOW.includes(nazwaTrasy)) return true
  if (Boolean(flagi.ukryjKlienci) && TRASY_KLIENTOW.includes(nazwaTrasy)) return true
  return false
}

/**
 * Trasa startowa po zalogowaniu (ops#425): `zadana` (domyślny widok użytkownika albo
 * 'Deals'), a gdy jest zablokowana, 'Leads', a gdy i Leady są niedostępne, 'Tasks'.
 */
export function trasaStartowa(zadana, flagi = {}) {
  for (const nazwa of [zadana, 'Leads']) {
    if (!czyZablokowana(nazwa, flagi)) return nazwa
  }
  return 'Tasks'
}
