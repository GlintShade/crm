import {
  OPERATOR_TAGOW,
  czyPoleTagow,
  czyZlozonyFiltrTagow,
  opcjeTagow,
  rozbijTagi,
  rozpakujZlozonyFiltrTagow,
  spakujZlozonyFiltrTagow,
  zlaczTagi,
} from './tagiProduktow'

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

describe('czyZlozonyFiltrTagow', () => {
  it('true dla ksztaltu zlozonego', () => {
    expect(czyZlozonyFiltrTagow([OPERATOR_TAGOW, { ma: ['PV'], nie_ma: ['AUDYT'] }])).toBe(
      true,
    )
  })

  it('true bez wzgledu na wielkosc liter operatora', () => {
    expect(czyZlozonyFiltrTagow(['VOLTEO_TAGI', { ma: ['PV'] }])).toBe(true)
    expect(czyZlozonyFiltrTagow(['Volteo_Tagi', {}])).toBe(true)
  })

  it('false dla in/not in/skalara', () => {
    expect(czyZlozonyFiltrTagow(['in', ['PV']])).toBe(false)
    expect(czyZlozonyFiltrTagow(['not in', ['PV']])).toBe(false)
    expect(czyZlozonyFiltrTagow('PV')).toBe(false)
  })

  it('false gdy slot 1 nie jest obiektem (tablica, string, brak)', () => {
    expect(czyZlozonyFiltrTagow([OPERATOR_TAGOW, ['PV']])).toBe(false)
    expect(czyZlozonyFiltrTagow([OPERATOR_TAGOW, 'PV'])).toBe(false)
    expect(czyZlozonyFiltrTagow([OPERATOR_TAGOW])).toBe(false)
    expect(czyZlozonyFiltrTagow([OPERATOR_TAGOW, null])).toBe(false)
  })

  it('false dla brakujacej/nie-tablicowej wartosci', () => {
    expect(czyZlozonyFiltrTagow(null)).toBe(false)
    expect(czyZlozonyFiltrTagow(undefined)).toBe(false)
    expect(czyZlozonyFiltrTagow({})).toBe(false)
  })
})

describe('rozpakujZlozonyFiltrTagow', () => {
  it('ksztalt zlozony -> obie strony', () => {
    expect(
      rozpakujZlozonyFiltrTagow([OPERATOR_TAGOW, { ma: ['PV'], nie_ma: ['AUDYT', 'ME'] }]),
    ).toEqual({ ma: ['PV'], nie_ma: ['AUDYT', 'ME'] })
  })

  it('ksztalt zlozony z brakujacym kluczem -> pusta lista z tej strony', () => {
    expect(rozpakujZlozonyFiltrTagow([OPERATOR_TAGOW, { ma: ['PV'] }])).toEqual({
      ma: ['PV'],
      nie_ma: [],
    })
    expect(rozpakujZlozonyFiltrTagow([OPERATOR_TAGOW, { nie_ma: ['AUDYT'] }])).toEqual({
      ma: [],
      nie_ma: ['AUDYT'],
    })
  })

  it('["in", [...]] -> tylko ma', () => {
    expect(rozpakujZlozonyFiltrTagow(['in', ['PV', 'ME']])).toEqual({
      ma: ['PV', 'ME'],
      nie_ma: [],
    })
  })

  it('["not in", [...]] -> tylko nie_ma', () => {
    expect(rozpakujZlozonyFiltrTagow(['not in', ['AUDYT']])).toEqual({
      ma: [],
      nie_ma: ['AUDYT'],
    })
  })

  it('skalar -> tylko ma (zgodnosc z dotychczasowym zapisem)', () => {
    expect(rozpakujZlozonyFiltrTagow('PV')).toEqual({ ma: ['PV'], nie_ma: [] })
  })

  it('smieci (inny ksztalt tablicowy, brak wartosci) -> obie strony puste', () => {
    expect(rozpakujZlozonyFiltrTagow(['like', '%PV%'])).toEqual({ ma: [], nie_ma: [] })
    expect(rozpakujZlozonyFiltrTagow(null)).toEqual({ ma: [], nie_ma: [] })
    expect(rozpakujZlozonyFiltrTagow(undefined)).toEqual({ ma: [], nie_ma: [] })
    expect(rozpakujZlozonyFiltrTagow(42)).toEqual({ ma: [], nie_ma: [] })
  })
})

describe('spakujZlozonyFiltrTagow', () => {
  it('obie strony puste -> undefined', () => {
    expect(spakujZlozonyFiltrTagow({ ma: [], nie_ma: [] })).toBeUndefined()
    expect(spakujZlozonyFiltrTagow({})).toBeUndefined()
    expect(spakujZlozonyFiltrTagow()).toBeUndefined()
  })

  it('tylko ma -> ["in", ma]', () => {
    expect(spakujZlozonyFiltrTagow({ ma: ['PV'], nie_ma: [] })).toEqual(['in', ['PV']])
  })

  it('tylko nie_ma -> ["not in", nie_ma]', () => {
    expect(spakujZlozonyFiltrTagow({ ma: [], nie_ma: ['AUDYT'] })).toEqual([
      'not in',
      ['AUDYT'],
    ])
  })

  it('obie niepuste -> ksztalt zlozony', () => {
    expect(spakujZlozonyFiltrTagow({ ma: ['PV'], nie_ma: ['AUDYT', 'ME'] })).toEqual([
      OPERATOR_TAGOW,
      { ma: ['PV'], nie_ma: ['AUDYT', 'ME'] },
    ])
  })

  it('JSON round-trip zachowuje semantyke', () => {
    const spakowane = spakujZlozonyFiltrTagow({ ma: ['PV'], nie_ma: ['AUDYT', 'ME'] })
    const poJson = JSON.parse(JSON.stringify(spakowane))
    expect(rozpakujZlozonyFiltrTagow(poJson)).toEqual({ ma: ['PV'], nie_ma: ['AUDYT', 'ME'] })
  })
})
