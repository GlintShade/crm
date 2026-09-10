// VOLTEO: mapowanie wartości `custom_zasady_dotacji` (literały "Nowe
// zasady" / "Stare zasady", współdzielone z `CRM Deal.custom_zasady_dotacji`
// - patrz CLAUDE.md, sekcja "Product-line map") na etykietę i kolor badge'a
// frappe-ui. Jedno źródło prawdy dla listy leadów (Leads.vue::parseRows,
// LeadsListView.vue) oraz - gdziekolwiek indziej to samo pole trafi na
// ekran - dymka na mapie leadów i panelu "Szybki podgląd".
//
// Frappe-free (bez importu 'frappe-ui' / '@/'), testowalne bezpośrednio
// przez vitest, ten sam wzorzec co utils/mapaKolory.js i utils/leadyInline.js
// (zero importu z barelu '@/utils' - eager-ladowane ikony psuja tam testy).
//
// frappe-ui Badge (node_modules/frappe-ui/src/components/Badge/Badge.vue)
// ma tylko sześć motywów: gray, blue, green, amber, red, violet - nie ma
// ciemnoróżowego/pink ani purple. "Stare zasady" dostaje `violet` jako
// najbliższy dostępny odpowiednik.
const MAPA_ZASAD = {
  'Nowe zasady': { etykieta: 'Nowe', kolor: 'green' },
  'Stare zasady': { etykieta: 'Stare', kolor: 'violet' },
}

/**
 * Zwraca {etykieta, kolor} dla wartości `custom_zasady_dotacji`, albo
 * `null` gdy wartość jest pusta lub nierozpoznana (pole Select nie
 * ogranicza wartości do dwóch literałów na poziomie bazy - nierozpoznana
 * wartość renderuje się jako puste, nie jako błąd).
 *
 * @param {string} wartosc
 * @returns {{etykieta: string, kolor: string}|null}
 */
export function zasadyDotacjiBadge(wartosc) {
  if (!wartosc) return null
  return MAPA_ZASAD[wartosc] || null
}
