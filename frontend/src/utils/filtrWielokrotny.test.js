import { parsujWartoscWielokrotna, scalOpcjeZZaznaczonymi } from './filtrWielokrotny'

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
