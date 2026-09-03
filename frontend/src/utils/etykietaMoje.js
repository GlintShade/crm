// Etykieta dla opcji filtra "@me" (Controls/Link.vue), zależna od doctype'u
// LISTY, na której stoi filtr — nie od doctype'u samego pola (to zawsze
// 'User'). Wartość filtra zostaje '@me' (backend crm.api.doc.get_data
// podmienia ją na frappe.session.user); zmienia się wyłącznie podpis.
//
// Właściciel (2026-09-03, ops#71): surowe "@me" w dropdownie myli — każda
// lista ma dostać czytelną polską etykietę.
//
// Literały wprost, bez __() — pułapka eager-chunk (patrz notatka projektowa
// volteo-eager-chunk-translation-trap.md): __() wołane na poziomie modułu
// (poza script setup / ciałem funkcji) potrafi wysadzić eager chunk
// ReferenceErrorem. Ta funkcja jest zwykłą funkcją, więc wołanie __() w jej
// ciele byłoby technicznie bezpieczne, ale zostajemy przy literałach dla
// spójności z resztą tego modułu.
export function etykietaMoje(doctype) {
  const etykiety = {
    'CRM Deal': 'Moje szanse',
    Contact: 'Moi klienci',
    'CRM Lead': 'Moje leady',
  }
  return etykiety[doctype] || 'Moje'
}
