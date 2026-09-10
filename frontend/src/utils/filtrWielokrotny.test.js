import {
  czyWielokrotnyWybor,
  parsujWartoscWielokrotna,
  scalOpcjeZZaznaczonymi,
} from './filtrWielokrotny'

describe('parsujWartoscWielokrotna', () => {
  it('tablica stringów → ta sama tablica, przycięta', () => {
    expect(parsujWartoscWielokrotna(['Nowy', 'Próba kontaktu'])).toEqual([
      'Nowy',
      'Próba kontaktu',
    ])
    expect(parsujWartoscWielokrotna([' Nowy ', ' Odłożony '])).toEqual([
      'Nowy',
      'Odłożony',
    ])
  })

  it('tablica z pustymi/białoznakowymi wpisami → odrzucone', () => {
    expect(parsujWartoscWielokrotna(['Nowy', '', '   '])).toEqual(['Nowy'])
  })

  it('string rozdzielony przecinkami (kompatybilność wsteczna) → tablica', () => {
    expect(parsujWartoscWielokrotna('Nowy, Próba kontaktu')).toEqual([
      'Nowy',
      'Próba kontaktu',
    ])
  })

  it('string z pustymi segmentami → odrzucone', () => {
    expect(parsujWartoscWielokrotna('Nowy,,  ,Odłożony')).toEqual([
      'Nowy',
      'Odłożony',
    ])
  })

  it('null/undefined/liczba → pusta tablica', () => {
    expect(parsujWartoscWielokrotna(null)).toEqual([])
    expect(parsujWartoscWielokrotna(undefined)).toEqual([])
    expect(parsujWartoscWielokrotna(42)).toEqual([])
  })

  it('pusta tablica/pusty string → pusta tablica', () => {
    expect(parsujWartoscWielokrotna([])).toEqual([])
    expect(parsujWartoscWielokrotna('')).toEqual([])
  })
})

describe('scalOpcjeZZaznaczonymi', () => {
  const opcjeStatusow = [
    { label: 'Nowy', value: 'Nowy' },
    { label: 'Próba kontaktu', value: 'Próba kontaktu' },
    { label: 'Odłożony', value: 'Odłożony' },
  ]

  it('zaznaczone wartości już w opcjach → lista bez zmian', () => {
    expect(scalOpcjeZZaznaczonymi(opcjeStatusow, ['Nowy'])).toEqual(
      opcjeStatusow,
    )
  })

  it('zaznaczona wartość spoza opcji (np. wynik wyszukiwania Link zawężony przez zapytanie) → dopisana na końcu', () => {
    expect(
      scalOpcjeZZaznaczonymi(opcjeStatusow, ['Nowy', 'Umówiony']),
    ).toEqual([...opcjeStatusow, { label: 'Umówiony', value: 'Umówiony' }])
  })

  it('brak zaznaczonych → opcje bez zmian', () => {
    expect(scalOpcjeZZaznaczonymi(opcjeStatusow, [])).toEqual(opcjeStatusow)
    expect(scalOpcjeZZaznaczonymi(opcjeStatusow, null)).toEqual(opcjeStatusow)
  })

  it('brak opcji (np. wyszukiwanie Link jeszcze nie odpowiedziało) → same zaznaczone jako placeholdery', () => {
    expect(scalOpcjeZZaznaczonymi([], ['Nowy', 'Odłożony'])).toEqual([
      { label: 'Nowy', value: 'Nowy' },
      { label: 'Odłożony', value: 'Odłożony' },
    ])
    expect(scalOpcjeZZaznaczonymi(null, ['Nowy'])).toEqual([
      { label: 'Nowy', value: 'Nowy' },
    ])
  })

  it('nie duplikuje, gdy zaznaczona wartość jest już w opcjach mimo powtórki na wejściu', () => {
    expect(
      scalOpcjeZZaznaczonymi(opcjeStatusow, ['Nowy', 'Nowy']),
    ).toEqual(opcjeStatusow)
  })
})
describe('czyWielokrotnyWybor', () => {
  it('Select + in/not in → true', () => {
    expect(czyWielokrotnyWybor({ fieldtype: 'Select', options: 'A\nB' }, 'in')).toBe(true)
    expect(czyWielokrotnyWybor({ fieldtype: 'Select', options: 'A\nB' }, 'not in')).toBe(true)
  })

  it('Link (options != User) + in/not in → true', () => {
    expect(czyWielokrotnyWybor({ fieldtype: 'Link', options: 'CRM Lead Status' }, 'in')).toBe(true)
    expect(czyWielokrotnyWybor({ fieldtype: 'Link', options: 'CRM Deal Status' }, 'not in')).toBe(true)
  })

  it('Link z options === "User" (lead_owner, custom_cc, deal_owner, custom_opiekun...) → false, zostaje pole tekstowe', () => {
    expect(czyWielokrotnyWybor({ fieldtype: 'Link', options: 'User' }, 'in')).toBe(false)
    expect(czyWielokrotnyWybor({ fieldtype: 'Link', options: 'User' }, 'not in')).toBe(false)
  })

  it('Dynamic Link → false, doctype zmienia się per wiersz', () => {
    expect(czyWielokrotnyWybor({ fieldtype: 'Dynamic Link', options: 'reference_doctype' }, 'in')).toBe(false)
  })

  it('inny operator (equals, like...) → zawsze false, nawet dla Select/Link', () => {
    expect(czyWielokrotnyWybor({ fieldtype: 'Select', options: 'A\nB' }, 'equals')).toBe(false)
    expect(czyWielokrotnyWybor({ fieldtype: 'Link', options: 'CRM Lead Status' }, 'like')).toBe(false)
  })

  it('inny fieldtype (Data, Int...) na in/not in → false, zostaje pole tekstowe', () => {
    expect(czyWielokrotnyWybor({ fieldtype: 'Data', options: null }, 'in')).toBe(false)
    expect(czyWielokrotnyWybor({ fieldtype: 'Int', options: null }, 'not in')).toBe(false)
  })

  it('brak pola → false', () => {
    expect(czyWielokrotnyWybor(null, 'in')).toBe(false)
    expect(czyWielokrotnyWybor(undefined, 'in')).toBe(false)
  })
})
