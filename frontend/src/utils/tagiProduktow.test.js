import { czyPoleTagow, opcjeTagow, rozbijTagi, zlaczTagi } from './tagiProduktow'

describe('czyPoleTagow', () => {
  it('true gdy field.volteo_tagi ustawione', () => {
    expect(czyPoleTagow({ fieldname: 'cokolwiek', volteo_tagi: 1 })).toBe(true)
  })

  it('true dla obu znanych nazw pól nawet bez volteo_tagi (fallback panelu bocznego)', () => {
    expect(czyPoleTagow({ fieldname: 'custom_posiadane_produkty' })).toBe(true)
    expect(czyPoleTagow({ fieldname: 'custom_produkt_procesu' })).toBe(true)
  })

  it('false dla innego pola bez flagi', () => {
    expect(czyPoleTagow({ fieldname: 'status' })).toBe(false)
  })

  it('false dla brakującego/pustego field', () => {
    expect(czyPoleTagow(null)).toBe(false)
    expect(czyPoleTagow(undefined)).toBe(false)
    expect(czyPoleTagow({})).toBe(false)
  })
})

describe('rozbijTagi', () => {
  it('rozbija string złączony +', () => {
    expect(rozbijTagi('PV+PC+AUDYT')).toEqual(['PV', 'PC', 'AUDYT'])
  })

  it('jeden token bez +', () => {
    expect(rozbijTagi('PV')).toEqual(['PV'])
  })

  it('pusty string -> pusta tablica', () => {
    expect(rozbijTagi('')).toEqual([])
  })

  it('podwójny + i białe znaki odrzucone', () => {
    expect(rozbijTagi('PV++PC')).toEqual(['PV', 'PC'])
    expect(rozbijTagi(' PV + PC ')).toEqual(['PV', 'PC'])
  })

  it('wartość nie-string -> pusta tablica', () => {
    expect(rozbijTagi(null)).toEqual([])
    expect(rozbijTagi(undefined)).toEqual([])
    expect(rozbijTagi(42)).toEqual([])
  })
})

describe('zlaczTagi', () => {
  const KOLEJNOSC = ['PV', 'ME', 'PC', 'PP', 'AUDYT', 'TERMO', 'REKU', 'OKNA', 'GRUNT']

  it('składa w kanonicznej kolejności, niezależnie od kolejności wejściowej', () => {
    expect(zlaczTagi(['PC', 'PV'], KOLEJNOSC)).toBe('PV+PC')
  })

  it('jeden token', () => {
    expect(zlaczTagi(['AUDYT'], KOLEJNOSC)).toBe('AUDYT')
  })

  it('pusta lista -> pusty string', () => {
    expect(zlaczTagi([], KOLEJNOSC)).toBe('')
  })

  it('duplikaty scalane', () => {
    expect(zlaczTagi(['PV', 'PV', 'ME'], KOLEJNOSC)).toBe('PV+ME')
  })

  it('token spoza kolejnosci pominięty (bez wolnego tekstu, model A+)', () => {
    expect(zlaczTagi(['PV', 'NIEZNANY'], KOLEJNOSC)).toBe('PV')
  })

  it('inna kolejność kanoniczna (custom_produkt_procesu)', () => {
    expect(zlaczTagi(['CP', 'PV', 'PVME'], ['PV', 'PVME', 'ME', 'PC', 'CP'])).toBe(
      'PV+PVME+CP',
    )
  })
})

describe('opcjeTagow', () => {
  it('rozbija field.options złączone \\n', () => {
    expect(opcjeTagow({ options: 'PV\nME\nPC' })).toEqual(['PV', 'ME', 'PC'])
  })

  it('jedna opcja bez \\n', () => {
    expect(opcjeTagow({ options: 'PV' })).toEqual(['PV'])
  })

  it('brak field -> pusta tablica', () => {
    expect(opcjeTagow(null)).toEqual([])
    expect(opcjeTagow(undefined)).toEqual([])
  })

  it('options puste/brak/nie-string -> pusta tablica', () => {
    expect(opcjeTagow({})).toEqual([])
    expect(opcjeTagow({ options: '' })).toEqual([])
    expect(opcjeTagow({ options: null })).toEqual([])
    expect(opcjeTagow({ options: 42 })).toEqual([])
  })
})
