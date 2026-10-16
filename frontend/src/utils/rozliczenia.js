// Rozliczenia prowizji na liscie szans (ops#284). Frappe-free, testowalne
// przez vitest. Lustro Pythona `crm/volteo_rozliczenie.py` (ops#280): ten sam
// format tokenow odbiorcow `H:W;M:D;P:S`.
//
// Role: H handlowiec, M manager, P partner.
// Litery stanu: W wyplacone, D do wyplaty, S wstrzymane, N nie dotyczy.

export const ROLE_ROZLICZENIA = ['H', 'M', 'P']

const NAZWY_ROLI = { H: 'Handlowiec', M: 'Manager', P: 'Partner' }
const OPISY_STANU = {
  W: 'wypłacone',
  D: 'do wypłaty',
  S: 'wstrzymane',
  N: 'nie dotyczy',
}

const MOTYWY_STATUSU = {
  Nierozliczone: 'gray',
  'Częściowo rozliczone': 'orange',
  Rozliczone: 'green',
  Wstrzymane: 'red',
  'Nie dotyczy': 'gray',
}

// Parsuje 'H:W;M:D;P:S' do { H: 'W', M: 'D', P: 'S' }. Tolerancyjny: puste,
// nie-string, nieznane role i nieznane litery stanu sa pomijane; brak roli
// oznacza "rola nie dotyczy" (klucza nie ma w wyniku).
export function parsujOdbiorcow(tekst) {
  const wynik = {}
  if (typeof tekst !== 'string') return wynik
  for (const czesc of tekst.split(';')) {
    const [rola, stan] = czesc.split(':').map((s) => (s || '').trim().toUpperCase())
    if (!ROLE_ROZLICZENIA.includes(rola)) continue
    if (!Object.prototype.hasOwnProperty.call(OPISY_STANU, stan)) continue
    wynik[rola] = stan
  }
  return wynik
}

// Theme Badge dla statusu rozliczenia; puste lub nieznane = 'gray'.
export function kolorStanu(status) {
  return MOTYWY_STATUSU[status] || 'gray'
}

// Tekst tooltipa po polsku, np. "Handlowiec: wypłacone, Manager: do wypłaty".
export function opisTokenow(tekst) {
  const odbiorcy = parsujOdbiorcow(tekst)
  return ROLE_ROZLICZENIA.filter((r) => odbiorcy[r])
    .map((r) => `${NAZWY_ROLI[r]}: ${OPISY_STANU[odbiorcy[r]]}`)
    .join(', ')
}

// Klasy kropki (tokeny kolorow) dla litery stanu; brak litery = null
// (rola nie dotyczy, kropki nie rysujemy).
export function klasaKropki(stan) {
  switch (stan) {
    case 'W':
      return 'bg-surface-green-3 border-outline-green-3'
    case 'D':
      return 'bg-surface-gray-2 border-outline-gray-3'
    case 'S':
      return 'bg-surface-red-4 border-outline-red-3'
    case 'N':
      return 'bg-transparent border-outline-gray-2 opacity-50'
    default:
      return null
  }
}

// Dane komorki "Odbiorcy": lista kropek w stalej kolejnosci H M P.
export function kropkiOdbiorcow(tekst) {
  const odbiorcy = parsujOdbiorcow(tekst)
  return ROLE_ROZLICZENIA.map((rola) => ({
    rola,
    stan: odbiorcy[rola] || null,
    klasa: klasaKropki(odbiorcy[rola]),
  }))
}
