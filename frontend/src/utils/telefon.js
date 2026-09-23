// Frappe-free helpers for making phone numbers clickable (tel: links)
// anywhere in the SPA. Pure formatting only: never validates, reformats,
// or persists the stored value. See TelefonLink.vue for the read-only
// rendering and the small "Zadzwon" icon button added next to editable
// phone-field inputs (Field.vue, DaneKlientaTab.vue, KredytTab.vue).

// Strips everything except digits and a single leading "+", so
// "+48 690 596 452", "690-596-452" and "(22) 123 45 67" all normalize to a
// dialable string. Returns '' for empty, null/undefined, or letters-only
// input, since there is nothing left to dial.
function oczyszczonyNumer(wartosc) {
  if (typeof wartosc !== 'string' && typeof wartosc !== 'number') return ''
  const tekst = String(wartosc).trim()
  if (!tekst) return ''
  const plus = tekst.startsWith('+') ? '+' : ''
  const cyfry = tekst.replace(/[^0-9]/g, '')
  if (!cyfry) return ''
  return plus + cyfry
}

/**
 * Builds a `tel:` href from a raw phone-number-shaped string. Returns ''
 * when there is nothing dialable in the input (empty, null, letters-only).
 */
export function telHref(numer) {
  const oczyszczony = oczyszczonyNumer(numer)
  return oczyszczony ? `tel:${oczyszczony}` : ''
}

/**
 * True when the value looks like a real phone number (at least 7 digits
 * once separators are stripped), not just any string of digits. Used to
 * decide whether an editable field gets the small "Zadzwon" icon button.
 */
export function czyTelefon(wartosc) {
  const oczyszczony = oczyszczonyNumer(wartosc)
  const cyfry = oczyszczony.replace('+', '')
  return cyfry.length >= 7
}
