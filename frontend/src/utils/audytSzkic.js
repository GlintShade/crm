// Szkic audytu OZE (AudytTab.vue, etap Szkic): czysta logika wyglądu w stylu
// formularza kredytowego. Bez Vue i bez Frappe, testowana osobno.
//
// Zasady wymagalności są te same co dotąd w AudytTab (pole z `required`, reguła
// `positive` = liczba większa od zera, reszta = niepusty tekst); ten moduł tylko
// je przenosi i dodaje stany wizualne (brak / błąd po próbie przesłania),
// liczniki sekcji, tekst banera i identyfikator pierwszego braku.

import { odmianaPol } from '@/utils/kredytForm'

/** Czy pole spełnia swoją regułę (ta sama semantyka co dawne fieldOk). */
export function poleWypelnione(f, value) {
  if (f?.rule === 'positive') return Number(value) > 0
  return String(value ?? '').trim() !== ''
}

/** Pole liczbowe z regułą `positive`: zapisane 0 oznacza "nie wpisano". */
function zeroToPuste(f, value) {
  return f?.rule === 'positive' && value !== '' && value !== null && value !== undefined && Number(value) === 0
}

/**
 * Wartość pokazywana w polu. Zapisane 0 w polu `positive` wyświetlamy jako puste,
 * dopóki użytkownik sam go nie ruszył (`edytowane` = zbiór nazw pól, które
 * użytkownik edytował w tej sesji). To tylko widok: `form` pozostaje bez zmian,
 * więc samo wyświetlenie nigdy nie uruchamia autozapisu.
 */
export function wartoscWyswietlana(f, value, edytowane) {
  if (edytowane && edytowane.has(f?.fieldname)) return value ?? ''
  if (zeroToPuste(f, value)) return ''
  return value ?? ''
}

/** Znacznik przy etykiecie: wymagane bez znacznika, opcjonalne z dopiskiem. */
export function znacznikPola(f) {
  return f?.required ? '' : 'opcjonalne'
}

/**
 * Stan wizualny pola: '' (ok lub opcjonalne), 'brak' (niebieskie, w trakcie
 * wypełniania) albo 'blad' (czerwone, po nieudanej próbie przesłania).
 */
export function stanPolaAudytu(f, value, proba) {
  if (!f?.required || poleWypelnione(f, value)) return { stan: '', komunikat: '' }
  return proba
    ? { stan: 'blad', komunikat: 'Uzupełnij to pole' }
    : { stan: 'brak', komunikat: '' }
}

/** Podtytuł karty sekcji wg tego, które pola są wymagane. */
export function podtytulSekcji(pola) {
  const lista = pola || []
  const wymagane = lista.filter((f) => f.required).length
  if (!wymagane) return ''
  if (wymagane === lista.length) return 'Wszystkie pola są wymagane.'
  return 'Wszystkie pola są wymagane, poza oznaczonymi jako opcjonalne.'
}

/**
 * Licznik karty pól. `null` gdy sekcja nie ma pól wymaganych (brak plakietki).
 * stan: 'komplet' | 'brak' | 'blad'.
 */
export function licznikSekcji(pola, wartosci, proba) {
  const wymagane = (pola || []).filter((f) => f.required)
  if (!wymagane.length) return null
  const liczba = wymagane.filter((f) => !poleWypelnione(f, wartosci?.[f.fieldname])).length
  if (!liczba) return { liczba: 0, stan: 'komplet' }
  return { liczba, stan: proba ? 'blad' : 'brak' }
}

/** Licznik karty zdjęć (tylko wymagane sloty). */
export function licznikZdjec(sloty, zdjecia, proba) {
  const liczba = (sloty || []).filter((s) => !zdjecia?.[s.key]).length
  if (!liczba) return { liczba: 0, stan: 'komplet' }
  return { liczba, stan: proba ? 'blad' : 'brak' }
}

/** Stan brakującego wymaganego zdjęcia: '' | 'brak' | 'blad'. */
export function stanZdjecia(slotWymagany, url, proba) {
  if (!slotWymagany || url) return ''
  return proba ? 'blad' : 'brak'
}

/** Odmiana "zdjęcie": biernik 1 zdjęcie, 2-4 zdjęcia, reszta zdjęć; dopełniacz 1 zdjęcia, reszta zdjęć. */
export function odmianaZdjec(n, przypadek) {
  if (n === 1) return przypadek === 'dopelniacz' ? 'zdjęcia' : 'zdjęcie'
  if (przypadek === 'biernik') {
    const jednostki = n % 10
    const dziesiatki = n % 100
    if (jednostki >= 2 && jednostki <= 4 && !(dziesiatki >= 12 && dziesiatki <= 14)) return 'zdjęcia'
  }
  return 'zdjęć'
}

/**
 * Część zdania z liczbami braków, np. "6 pól i 3 zdjęć". Pomija część równą 0.
 * `przypadek`: 'dopelniacz' ("Brakuje ...") albo 'biernik' ("Uzupełnij ...").
 */
export function frazaBrakow(pola, zdjecia, przypadek) {
  const czesci = []
  if (pola > 0) czesci.push(`${pola} ${odmianaPol(pola, przypadek)}`)
  if (zdjecia > 0) czesci.push(`${zdjecia} ${odmianaZdjec(zdjecia, przypadek)}`)
  return czesci.join(' i ')
}

/**
 * Podsumowanie braków całego Szkicu.
 *
 * @param {{label: string, fields: object[]}[]} sekcje  widoczne sekcje pól
 * @param {{key: string, label?: string}[]} slotyWymagane  widoczne wymagane sloty zdjęć
 * @param {object} wartosci  form
 * @param {object} zdjecia  mapa slot -> url
 * @param {string} etykietaZdjec  nazwa sekcji zdjęć w liście
 * @returns {{pola: number, zdjecia: number, sekcje: {label: string, liczba: number}[], pierwszy: ({typ: 'pole'|'zdjecie', klucz: string}|null)}}
 */
export function podsumowanieSzkicu(sekcje, slotyWymagane, wartosci, zdjecia, etykietaZdjec) {
  const lista = []
  let pola = 0
  let pierwszy = null
  ;(sekcje || []).forEach((sek) => {
    const braki = (sek.fields || []).filter(
      (f) => f.required && !poleWypelnione(f, wartosci?.[f.fieldname]),
    )
    if (!braki.length) return
    pola += braki.length
    lista.push({ label: sek.label, liczba: braki.length })
    if (!pierwszy) pierwszy = { typ: 'pole', klucz: braki[0].fieldname }
  })
  const brakujaceZdjecia = (slotyWymagane || []).filter((s) => !zdjecia?.[s.key])
  if (brakujaceZdjecia.length) {
    lista.push({ label: etykietaZdjec, liczba: brakujaceZdjecia.length })
    if (!pierwszy) pierwszy = { typ: 'zdjecie', klucz: brakujaceZdjecia[0].key }
  }
  return { pola, zdjecia: brakujaceZdjecia.length, sekcje: lista, pierwszy }
}

/** Postęp 0-100 do paska (pola i zdjęcia razem). */
export function procentPostepu(polaGotowe, polaRazem, zdjeciaGotowe, zdjeciaRazem) {
  const razem = polaRazem + zdjeciaRazem
  if (!razem) return 0
  return Math.round(((polaGotowe + zdjeciaGotowe) / razem) * 100)
}
