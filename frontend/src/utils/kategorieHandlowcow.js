// Kategorie handlowców (ops#393) i ich kolory. Ten sam kolor w Ustawieniach i w zakładce Leady.
export const KATEGORIE = ['Priorytet', 'Standard', 'Nie umawiać']

const KOLORY = {
  Priorytet: { wypelnienie: '#e2ab12', obwodka: '#e2ab12' },
  Standard: { wypelnienie: '#ffffff', obwodka: '#3b4252' },
  'Nie umawiać': { wypelnienie: '#6f7783', obwodka: '#6f7783' },
}

export function kolorKategorii(k) {
  return KOLORY[k] ? { ...KOLORY[k] } : null
}

const SLUGI = { Priorytet: 'priorytet', Standard: 'standard', 'Nie umawiać': 'nie-umawiac' }

export function slugKategorii(k) {
  return SLUGI[k] || ''
}

/** Klasa paska wiersza listy (style w LeadsListView.vue); brak kategorii: bez klasy. */
export function klasaWiersza(k) {
  return SLUGI[k] ? `kat-${SLUGI[k]}` : ''
}

/** Klik w aktywną kategorię wyłącza filtr (null), inaczej wybiera klikniętą. */
export function przelacz(aktywna, kliknieta) {
  return aktywna === kliknieta ? null : kliknieta
}

/** Styl ramki karty kalendarza: kolor obwódki kategorii; Standard (biały) dostaje cienki ciemny pierścień. */
export function stylRamki(k) {
  const c = kolorKategorii(k)
  if (!c) return null
  return k === 'Standard'
    ? { borderColor: c.wypelnienie, boxShadow: `0 0 0 1px ${c.obwodka}` }
    : { borderColor: c.obwodka }
}
