// Logika filtra listy leadów na mapie (MapaLeadow.vue, issue ops#113).
//
// Frappe-free (bez importu `frappe-ui` / `@/`), testowalne bezpośrednio
// przez vitest, ten sam wzorzec co dealPipeline.js/etapFiltr.js.
//
// PUŁAPKA odwrócona tu celowo: filtr trzyma zbiór statusów WYŁĄCZONYCH
// przez użytkownika, nie zbiór statusów AKTYWNYCH. `aktywneStatusy` w
// MapaLeadow.vue był inicjalizowany ze statusów OBECNYCH w załadowanych
// leadach (jednorazowo, po odpowiedzi API): status, który lead dostał
// dopiero przez edycję w panelu "Szybki podgląd" (np. Nowy -> Umówiony),
// nigdy nie trafiał do tego zbioru, więc `widocznyLead` odrzucał lead i
// pinezka znikała z mapy zamiast zmienić kolor. Zbiór WYŁĄCZONYCH startuje
// pusty (nic nie jest ukryte na starcie), więc status nieznany w chwili
// inicjalizacji jest widoczny domyślnie -- odwrotność poprzedniej pułapki.

/**
 * Czy dany lead ma być widoczny na mapie po zastosowaniu filtrów.
 *
 * @param {{status?: string, lead_owner?: string, custom_install_city?: string}} lead
 * @param {{wylaczone: Set<string>, handlowiec?: string, miasto?: string}} filtry
 * @param {string} brakStatusu etykieta dla leadów bez statusu (np. '(brak)')
 * @returns {boolean}
 */
export function widocznyLead(lead, filtry, brakStatusu) {
  const status = lead.status || brakStatusu
  if (filtry.wylaczone.has(status)) return false
  if (filtry.handlowiec && lead.lead_owner !== filtry.handlowiec) return false
  const miasto = (filtry.miasto || '').trim().toLowerCase()
  if (miasto && !(lead.custom_install_city || '').toLowerCase().includes(miasto)) {
    return false
  }
  return true
}
