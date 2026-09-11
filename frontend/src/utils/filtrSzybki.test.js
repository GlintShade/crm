import {
  czyWielokrotnyFiltrSzybki,
  etykietaChipaFiltraSzybkiego,
  przelaczWartoscWielokrotna,
  rozpakujWartoscFiltraSzybkiego,
  spakujWartoscFiltraSzybkiego,
  ustawWartoscWielokrotna,
} from './filtrSzybki'

describe('rozpakujWartoscFiltraSzybkiego', () => {
  it('skalar (dotychczasowy kształt jednej wartości) -> tablica jednoelementowa', () => {
    expect(rozpakujWartoscFiltraSzybkiego('Nowy')).toEqual(['Nowy'])
  })

  it('["in", [...]] -> tablica wartości, operator bez względu na wielkość liter', () => {
    expect(
      rozpakujWartoscFiltraSzybkiego(['in', ['Nowy', 'Próba kontaktu']]),
    ).toEqual(['Nowy', 'Próba kontaktu'])
    expect(
      rozpakujWartoscFiltraSzybkiego(['IN', ['Nowy', 'Odłożony']]),
    ).toEqual(['Nowy', 'Odłożony'])
  })

  it('inny kształt tablicowy (np. like z rozwiniętego filtra) -> pusta tablica', () => {
    expect(rozpakujWartoscFiltraSzybkiego(['like', '%Jan%'])).toEqual([])
    expect(rozpakujWartoscFiltraSzybkiego(['not in', ['Nowy']])).toEqual([])
  })

  it('brak wartości -> pusta tablica', () => {
    expect(rozpakujWartoscFiltraSzybkiego(undefined)).toEqual([])
    expect(rozpakujWartoscFiltraSzybkiego(null)).toEqual([])
    expect(rozpakujWartoscFiltraSzybkiego('')).toEqual([])
  })
})

describe('spakujWartoscFiltraSzybkiego', () => {
  it('0 wartości -> undefined (klucz do usunięcia)', () => {
    expect(spakujWartoscFiltraSzybkiego([])).toBeUndefined()
    expect(spakujWartoscFiltraSzybkiego(null)).toBeUndefined()
  })

  it('1 wartość -> sam string, dotychczasowy kształt', () => {
    expect(spakujWartoscFiltraSzybkiego(['Nowy'])).toBe('Nowy')
  })

  it('N wartości -> ["in", [...]]', () => {
    expect(spakujWartoscFiltraSzybkiego(['Nowy', 'Odłożony'])).toEqual([
      'in',
      ['Nowy', 'Odłożony'],
    ])
  })

  it('odrzuca puste/białoznakowe wpisy przed zliczeniem', () => {
    expect(spakujWartoscFiltraSzybkiego(['Nowy', '', '  '])).toBe('Nowy')
    expect(spakujWartoscFiltraSzybkiego(['', '  '])).toBeUndefined()
  })
})

describe('etykietaChipaFiltraSzybkiego', () => {
  it('brak zaznaczeń -> sama etykieta pola', () => {
    expect(etykietaChipaFiltraSzybkiego('Status CC', [])).toBe('Status CC')
    expect(etykietaChipaFiltraSzybkiego('Status CC', null)).toBe('Status CC')
  })

  it('jedna wartość -> "Etykieta: Wartość"', () => {
    expect(etykietaChipaFiltraSzybkiego('Status CC', ['Nowy'])).toBe(
      'Status CC: Nowy',
    )
  })

  it('dwie wartości -> "Etykieta: Pierwsza +1"', () => {
    expect(
      etykietaChipaFiltraSzybkiego('Status CC', ['Nowy', 'Próba kontaktu']),
    ).toBe('Status CC: Nowy +1')
  })

  it('trzy wartości -> "Etykieta: Pierwsza +2"', () => {
    expect(
      etykietaChipaFiltraSzybkiego('Status CC', [
        'Nowy',
        'Próba kontaktu',
        'Odłożony',
      ]),
    ).toBe('Status CC: Nowy +2')
  })

  it('puste/nullowe wpisy w liście etykiet są pomijane przy liczeniu', () => {
    expect(
      etykietaChipaFiltraSzybkiego('Status CC', ['Nowy', '', null]),
    ).toBe('Status CC: Nowy')
  })
})

describe('czyWielokrotnyFiltrSzybki', () => {
  it('Select → true', () => {
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'custom_status_handlowy',
        fieldtype: 'Select',
        options: 'A\nB',
      }),
    ).toBe(true)
  })

  it('Link poza User → true', () => {
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'status',
        fieldtype: 'Link',
        options: 'CRM Lead Status',
      }),
    ).toBe(true)
  })

  it('Link options===User (custom_cc, lead_owner) → false', () => {
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'custom_cc',
        fieldtype: 'Link',
        options: 'User',
      }),
    ).toBe(false)
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'lead_owner',
        fieldtype: 'Link',
        options: 'User',
      }),
    ).toBe(false)
  })

  it('Date/Datetime → false', () => {
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'custom_kolejny_kontakt',
        fieldtype: 'Date',
      }),
    ).toBe(false)
  })

  it('CRM Deal status (Etap) → false mimo Link poza User, wyjątek na własną listę opcji procesu', () => {
    expect(
      czyWielokrotnyFiltrSzybki('CRM Deal', {
        fieldname: 'status',
        fieldtype: 'Link',
        options: 'CRM Deal Status',
      }),
    ).toBe(false)
  })

  it('status na innym doctype niż CRM Deal (np. CRM Lead) → true, wyjątek dotyczy tylko Deal', () => {
    expect(
      czyWielokrotnyFiltrSzybki('CRM Lead', {
        fieldname: 'status',
        fieldtype: 'Link',
        options: 'CRM Lead Status',
      }),
    ).toBe(true)
  })
})

describe('przelaczWartoscWielokrotna', () => {
  it('wartości nie ma -> dodana na końcu', () => {
    expect(przelaczWartoscWielokrotna(['Nowy'], 'Odłożony')).toEqual([
      'Nowy',
      'Odłożony',
    ])
  })

  it('wartość już jest -> usunięta', () => {
    expect(
      przelaczWartoscWielokrotna(['Nowy', 'Odłożony'], 'Nowy'),
    ).toEqual(['Odłożony'])
  })

  it('pusta lista wejściowa -> tablica jednoelementowa', () => {
    expect(przelaczWartoscWielokrotna([], 'Nowy')).toEqual(['Nowy'])
    expect(przelaczWartoscWielokrotna(null, 'Nowy')).toEqual(['Nowy'])
  })

  it('nie mutuje wejściowej tablicy (immutability)', () => {
    const wejscie = ['Nowy']
    const wynik = przelaczWartoscWielokrotna(wejscie, 'Odłożony')
    expect(wejscie).toEqual(['Nowy'])
    expect(wynik).not.toBe(wejscie)
  })
})

// Regresja 2026-09-11 (issue #127 follow-up): frappe-ui's Checkbox.vue
// emituje update:modelValue dwa razy na jedno kliknięcie z tym samym
// argumentem. ustawWartoscWielokrotna (w przeciwieństwie do
// przelaczWartoscWielokrotna) musi być idempotentna wobec tego -- ta sama
// para (wartość, zaznaczona) wywołana dwukrotnie musi dać ten sam wynik co
// raz, patrz komentarz przy funkcji w filtrSzybki.js.
describe('ustawWartoscWielokrotna', () => {
  it('zaznaczona=true, wartości nie ma -> dodana na końcu', () => {
    expect(ustawWartoscWielokrotna(['Nowy'], 'Odłożony', true)).toEqual([
      'Nowy',
      'Odłożony',
    ])
  })

  it('zaznaczona=false, wartość jest -> usunięta', () => {
    expect(
      ustawWartoscWielokrotna(['Nowy', 'Odłożony'], 'Nowy', false),
    ).toEqual(['Odłożony'])
  })

  it('idempotentność: dwa wywołania zaznaczona=true z tą samą wartością dają ten sam wynik co jedno', () => {
    let wynik = ustawWartoscWielokrotna([], 'Nowy', true)
    wynik = ustawWartoscWielokrotna(wynik, 'Nowy', true)
    expect(wynik).toEqual(['Nowy'])
  })

  it('idempotentność: dwa wywołania zaznaczona=false z tą samą wartością dają ten sam wynik co jedno', () => {
    let wynik = ustawWartoscWielokrotna(['Nowy'], 'Nowy', false)
    wynik = ustawWartoscWielokrotna(wynik, 'Nowy', false)
    expect(wynik).toEqual([])
  })

  it('pusta lista wejściowa -> tablica jednoelementowa (zaznaczona=true)', () => {
    expect(ustawWartoscWielokrotna([], 'Nowy', true)).toEqual(['Nowy'])
    expect(ustawWartoscWielokrotna(null, 'Nowy', true)).toEqual(['Nowy'])
  })

  it('zaznaczona=false, wartości nie ma -> lista bez zmian', () => {
    expect(ustawWartoscWielokrotna(['Odłożony'], 'Nowy', false)).toEqual([
      'Odłożony',
    ])
  })

  it('nie mutuje wejściowej tablicy (immutability)', () => {
    const wejscie = ['Nowy']
    const wynik = ustawWartoscWielokrotna(wejscie, 'Odłożony', true)
    expect(wejscie).toEqual(['Nowy'])
    expect(wynik).not.toBe(wejscie)
  })
})
