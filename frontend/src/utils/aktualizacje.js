// Konfiguracje strumieni aktualizacji na szansie (zakładki typu "wpis + oś
// czasu"): Montaż (Volteo Montaz Update) i Trify (Volteo Trify Update).
// Renderuje je jeden wspólny komponent, AktualizacjeTab.vue — ten plik
// niesie wyłącznie dane (nazwy pól, typy wpisów, teksty UI), a komponent
// decyduje jak je pokazać. Przyszła trzecia zakładka strumieniowa (np.
// kredyt CP) dokłada tu kolejny obiekt konfiguracji, bez nowego komponentu.
//
// PUŁAPKA (patrz CLAUDE.md → "Eager chunk a __()"): __() wolno wywoływać
// tylko w script setup / funkcjach komponentu, NIGDY na poziomie modułu —
// dlatego napisy poniżej są surowym polskim tekstem, a tłumaczenie przez
// __() dzieje się w AktualizacjeTab.vue, nie tutaj.
//
// ODSTĘPSTWO OD BRIEFU: `htmlToText` NIE jest importowane z `@/utils` (choć
// tam istnieje, ~linia 316) — ten barrel eagerly importuje `~icons/lucide/*`
// przez unplugin-icons, który vite.config.js podłącza dynamicznie przez
// `frappe-ui/vite` (lucideIcons: true), a vitest.config.js tego pluginu nie
// ma. Import `{ htmlToText } from '@/utils'` w tym pliku psuje więc KAŻDY
// test, który go choćby tranzytywnie załaduje (potwierdzone: cały plugin
// stack ładuje się przy imporcie modułu, nie tylko użyty eksport). Zamiast
// dorabiać konfigurację testową, ten plik trzyma własną, identyczną kopię
// algorytmu (div.innerHTML → textContent) — ta sama sztuczka, ale bez
// zależności od reszty barrela. Trzymać w zgodzie z `@/utils`.htmlToText,
// jeśli tamta implementacja się zmieni.
function htmlNaTekst(html) {
  const div = document.createElement('div')
  div.innerHTML = html
  return div.textContent || div.innerText || ''
}

export const MONTAZ = {
  name: 'Montaz',
  doctype: 'Volteo Montaz Update',
  html: false,
  typy: ['Notatka', 'Telefon', 'Wizyta', 'Termin montażu', 'Problem'],
  placeholder: 'Np. Umówiono termin montażu na 20.07…',
  pusty: 'Brak aktualizacji montażu.',
  przycisk: 'Dodaj aktualizację',
  blad: 'Nie udało się dodać aktualizacji',
}

export const TRIFY = {
  name: 'Trify',
  doctype: 'Volteo Trify Update',
  html: true,
  // Lustro: crm/volteo_trify.py TYPY oraz ops/crm-trify.py — zmieniać razem.
  typy: ['Notatka', 'Wniosek Trify', 'Decyzja Trify', 'Umowa Trify', 'Wypłata Trify', 'Problem'],
  placeholder: 'Np. Złożono wniosek Trify 03.09… (@ aby wspomnieć użytkownika)',
  pusty: 'Brak wpisów Trify.',
  przycisk: 'Dodaj wpis',
  blad: 'Nie udało się dodać wpisu',
}

// Czy wpis (tekst zwykły albo HTML z edytora) jest w praktyce pusty.
// TipTap po wyczyszczeniu treści zwraca "<p></p>" (albo "<p><br></p>"), nie
// pusty string — htmlToText() to rozbraja, bo div.textContent z takiego
// znacznika jest pusty. &nbsp; w treści (np. po samym spacjowaniu w
// edytorze) zamieniamy na zwykłą spację przed trim(), żeby nie została
// rozpoznana jako "prawdziwa" treść.
export function tekstPusty(html) {
  return !htmlNaTekst(html || '')
    .replace(/\u00A0/g, ' ')
    .trim()
}
