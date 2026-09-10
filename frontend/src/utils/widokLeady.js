// Alias trwałości widoku „Mapa” dla listy leadów (issue #100).
//
// `CRM View Settings.type` to Select ograniczony do "list"/"group_by"/"kanban"
// (crm/fcrm/doctype/crm_view_settings/crm_view_settings.json) - nie istnieje
// wartość "mapa" w schemacie, i dopisanie jej byłoby migracją dotykającą
// wszystkie doctype'y z widokami, nie tylko leady. Zamiast tego Tabela i
// Mapa DZIELĄ jeden standardowy widok: zapisują się i odczytują pod tym
// samym kluczem co Tabela (`type: "list"`), a to, którą z dwóch reprezentacji
// widzi użytkownik, żyje wyłącznie w parametrze trasy `viewType`
// (`/leads/view/mapa` vs `/leads/view/list`), nigdy w zapisanym widoku.
//
// Frappe-free (bez importu `frappe-ui` / `@/`), testowalne bezpośrednio przez
// vitest - ten sam wzorzec co utils/strazTras.js.

/**
 * Zamienia typ widoku z parametru trasy na typ, pod którym widok jest
 * TRWALE zapisywany (`CRM View Settings.type` / `create_or_update_standard_view`).
 * Każdy inny typ (list/group_by/kanban) przechodzi bez zmian.
 *
 * @param {string} viewType - `route.params.viewType`.
 * @returns {string}
 */
export function typWidokuDoZapisu(viewType) {
  return viewType === 'mapa' ? 'list' : viewType
}
