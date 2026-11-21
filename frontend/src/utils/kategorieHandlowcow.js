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
