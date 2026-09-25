// Ostrzeżenie przed usunięciem szansy (CRM Deal), pokazywane backoffice
// (Volteo Backend, ops#183) i adminowi jednakowo: obaj widzą to samo okno,
// backoffice po prostu jest jedyną rolą spoza admina, która w ogóle dojdzie
// do przycisku "Usuń" na liście szans (patrz DealsListView.vue/
// ListBulkActions.vue). Frappe-free (bez importu `frappe-ui` / `@/`),
// testowalne bezpośrednio przez vitest, ten sam wzorzec co cpForm.js /
// panelTekst.js. Czyste funkcje: nigdy nie mutują tablicę `nazwy` przekazaną
// przez wywołującego.

const AKAPIT_DRUGI =
  'Operacja jest nieodwracalna. Razem z szansą zostaną trwale usunięte powiązane dokumenty: ' +
  'umowy, formularze kredytowe, audyty, faktury, oferty oraz aktualizacje montażu i Trify.'

const AKAPIT_TRZECI =
  'Szansy z umową lub formularzem kredytowym wysłanym do podpisu albo podpisanym nie da się ' +
  'usunąć; szansę z audytem specjalnym CP lub zatwierdzonym audytem może usunąć tylko administrator.'

/**
 * Deklinacja rzeczownika "szansa" w bierniku, dla liczby `n`, do zdań typu
 * "Usuń {n} {odmiana}". Dla n === 1 zwraca formę biernika liczby
 * pojedynczej ("szansę"), używaną też w nagłówku/przycisku bez liczby
 * ("Usuń szansę").
 *
 * @param {number} n
 * @returns {'szansę' | 'szanse' | 'szans'}
 */
export function odmianaSzansy(n) {
  if (n === 1) return 'szansę'

  const reszta10 = n % 10
  const reszta100 = n % 100
  if (reszta10 >= 2 && reszta10 <= 4 && (reszta100 < 12 || reszta100 > 14)) {
    return 'szanse'
  }
  return 'szans'
}

function naglowekUsuwania(n) {
  if (n === 1) return 'Usuń szansę'
  return `Usuń ${n} ${odmianaSzansy(n)}`
}

function akapitPierwszy(nazwy) {
  const n = nazwy.length
  if (n === 1) {
    return `Usuwasz szansę ${nazwy[0]}.`
  }
  if (n <= 5) {
    return `Usuwasz szanse: ${nazwy.join(', ')}.`
  }
  return `Usuwasz ${n} zaznaczonych szans.`
}

/**
 * Treść okna ostrzeżenia przed usunięciem jednej albo wielu szans.
 * Nie mutuje `nazwy`.
 *
 * @param {string[]} nazwy nazwy dokumentów usuwanych szans (np. "PRO/PV/26/1060")
 * @returns {{tytul: string, akapity: string[], etykietaPrzycisku: string}}
 */
export function trescOstrzezenia(nazwy) {
  const lista = Array.isArray(nazwy) ? nazwy : []
  const n = lista.length
  const naglowek = naglowekUsuwania(n)

  return {
    tytul: naglowek,
    akapity: [akapitPierwszy(lista), AKAPIT_DRUGI, AKAPIT_TRZECI],
    etykietaPrzycisku: naglowek,
  }
}
