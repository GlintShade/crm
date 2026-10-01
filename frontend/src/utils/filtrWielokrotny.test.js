import {
  czyWielokrotnyWybor,
  domyslnaWartoscFiltra,
  domyslnyOperatorWielokrotny,
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

  it('issue #214: Link z options === "User" (lead_owner, custom_cc, deal_owner, custom_opiekun...) → true, dostaje wielokrotny wybór jak każdy inny Link', () => {
    expect(czyWielokrotnyWybor({ fieldtype: 'Link', options: 'User' }, 'in')).toBe(true)
    expect(czyWielokrotnyWybor({ fieldtype: 'Link', options: 'User' }, 'not in')).toBe(true)
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

  it('ops#150: pole tagów (Data + volteo_tagi) + in/not in → true', () => {
    const field = {
      fieldtype: 'Data',
      fieldname: 'custom_posiadane_produkty',
      options: 'PV\nME\nPC',
      volteo_tagi: 1,
    }
    expect(czyWielokrotnyWybor(field, 'in')).toBe(true)
    expect(czyWielokrotnyWybor(field, 'not in')).toBe(true)
  })

  it('ops#150: pole tagów rozpoznane po fieldname nawet bez volteo_tagi (fallback panelu bocznego) → true', () => {
    expect(
      czyWielokrotnyWybor({ fieldtype: 'Data', fieldname: 'custom_produkt_procesu' }, 'in'),
    ).toBe(true)
  })

  it('ops#150: pole tagów na inny operator → false, zostaje bez zmian', () => {
    const field = {
      fieldtype: 'Data',
      fieldname: 'custom_posiadane_produkty',
      volteo_tagi: 1,
    }
    expect(czyWielokrotnyWybor(field, 'equals')).toBe(false)
  })

  it('issue #218: pole z wartościami z serwera (Data + volteo_wartosci) + in/not in → true', () => {
    const field = {
      fieldtype: 'Data',
      fieldname: 'custom_powiat',
      volteo_wartosci: {
        url: 'crm.api.volteo_leady.powiaty_filtra',
        zalezy_od: 'custom_voivodeship',
        parametr: 'wojewodztwa',
      },
    }
    expect(czyWielokrotnyWybor(field, 'in')).toBe(true)
    expect(czyWielokrotnyWybor(field, 'not in')).toBe(true)
  })

  it('issue #218: pole z wartościami z serwera na inny operator → false, zostaje bez zmian', () => {
    const field = {
      fieldtype: 'Data',
      fieldname: 'custom_powiat',
      volteo_wartosci: { url: 'x', zalezy_od: 'y', parametr: 'z' },
    }
    expect(czyWielokrotnyWybor(field, 'equals')).toBe(false)
  })
})

describe('domyslnyOperatorWielokrotny', () => {
  it('Select → "in"', () => {
    expect(domyslnyOperatorWielokrotny({ fieldtype: 'Select', options: 'A\nB' })).toBe('in')
  })

  it('Link, w tym options === "User" (issue #214/#215) → "in"', () => {
    expect(domyslnyOperatorWielokrotny({ fieldtype: 'Link', options: 'CRM Lead Status' })).toBe(
      'in',
    )
    expect(domyslnyOperatorWielokrotny({ fieldtype: 'Link', options: 'User' })).toBe('in')
  })

  it('pole tagów (ops#150) → "in"', () => {
    expect(
      domyslnyOperatorWielokrotny({ fieldtype: 'Data', fieldname: 'custom_produkt_procesu' }),
    ).toBe('in')
  })

  it('issue #215/#218: pole z wartościami z serwera (ops#150-podobne) → "in"', () => {
    expect(
      domyslnyOperatorWielokrotny({
        fieldtype: 'Data',
        fieldname: 'custom_powiat',
        volteo_wartosci: { url: 'x', zalezy_od: 'y', parametr: 'z' },
      }),
    ).toBe('in')
  })

  it('Dynamic Link → null, wołający decyduje sam', () => {
    expect(
      domyslnyOperatorWielokrotny({ fieldtype: 'Dynamic Link', options: 'reference_doctype' }),
    ).toBeNull()
  })

  it('inny fieldtype (Data, Int, Check, Date...) → null, wołający decyduje sam', () => {
    expect(domyslnyOperatorWielokrotny({ fieldtype: 'Data' })).toBeNull()
    expect(domyslnyOperatorWielokrotny({ fieldtype: 'Int' })).toBeNull()
    expect(domyslnyOperatorWielokrotny({ fieldtype: 'Check' })).toBeNull()
    expect(domyslnyOperatorWielokrotny({ fieldtype: 'Date' })).toBeNull()
  })

  it('brak pola → null', () => {
    expect(domyslnyOperatorWielokrotny(null)).toBeNull()
    expect(domyslnyOperatorWielokrotny(undefined)).toBeNull()
  })
})

describe('domyslnaWartoscFiltra', () => {
  // Fix regresji po #215 (zgłoszone przy #218): Filter.vue::updateOperator
  // wołał getDefaultValue(field) (BEZ operatora) nawet przy przełączeniu
  // NA operator jednowartościowy, a stara getDefaultValue sprawdzała tylko
  // domyslnyOperatorWielokrotny(field) (operator na sztywno "in") -- więc
  // Select/Link/tagi/Powiat dostawały [] zamiast skalara przy "equals"/
  // "like"/"is". domyslnaWartoscFiltra naprawia to, biorąc operator jako
  // osobny argument.
  const pole = { fieldtype: 'Select', options: 'A\nB\nC' }
  const poleLink = { fieldtype: 'Link', options: 'CRM Lead Status' }
  const poleUser = { fieldtype: 'Link', options: 'User' }
  const poleTagow = {
    fieldtype: 'Data',
    fieldname: 'custom_produkt_procesu',
    volteo_tagi: 1,
  }
  const polePowiat = {
    fieldtype: 'Data',
    fieldname: 'custom_powiat',
    volteo_wartosci: { url: 'x', zalezy_od: 'custom_voivodeship', parametr: 'wojewodztwa' },
  }

  describe('operator in/not in → [] dla każdego pola z wielokrotnym wyborem', () => {
    it.each([
      ['Select', pole],
      ['Link', poleLink],
      ['Link + User', poleUser],
      ['tagi', poleTagow],
      ['Powiat (volteo_wartosci)', polePowiat],
    ])('%s', (_nazwa, field) => {
      expect(domyslnaWartoscFiltra(field, 'in')).toEqual([])
      expect(domyslnaWartoscFiltra(field, 'not in')).toEqual([])
    })
  })

  describe('Select, operator jednowartościowy → pierwsza opcja (regresja #215)', () => {
    it.each(['equals', 'not equals', 'like', 'not like', 'is'])('%s', (operator) => {
      expect(domyslnaWartoscFiltra(pole, operator, 'A')).toBe('A')
    })

    it('bez podanej pierwszaOpcja → pusty string, nie undefined', () => {
      expect(domyslnaWartoscFiltra(pole, 'equals')).toBe('')
    })
  })

  describe('Link (zwykły i User), operator jednowartościowy → pusty string (regresja #215)', () => {
    it.each(['equals', 'not equals', 'like', 'not like', 'is'])('Link %s', (operator) => {
      expect(domyslnaWartoscFiltra(poleLink, operator)).toBe('')
    })
    it.each(['equals', 'not equals', 'like', 'not like', 'is'])('Link + User %s', (operator) => {
      expect(domyslnaWartoscFiltra(poleUser, operator)).toBe('')
    })
  })

  describe('Powiat (volteo_wartosci), operator jednowartościowy → pusty string (regresja #218)', () => {
    it.each(['equals', 'like', 'is'])('%s', (operator) => {
      expect(domyslnaWartoscFiltra(polePowiat, operator)).toBe('')
    })
  })

  it('Check → zawsze "Yes", niezależnie od operatora (niewielokrotny)', () => {
    const poleCheck = { fieldtype: 'Check' }
    expect(domyslnaWartoscFiltra(poleCheck, 'equals')).toBe('Yes')
  })

  it('Date/Datetime → zawsze null, niezależnie od operatora', () => {
    expect(domyslnaWartoscFiltra({ fieldtype: 'Date' }, 'equals')).toBeNull()
    expect(domyslnaWartoscFiltra({ fieldtype: 'Datetime' }, 'between')).toBeNull()
  })

  it('inny fieldtype (Int, Currency...) operator jednowartościowy → pusty string', () => {
    expect(domyslnaWartoscFiltra({ fieldtype: 'Int' }, 'equals')).toBe('')
    expect(domyslnaWartoscFiltra({ fieldtype: 'Currency' }, '>')).toBe('')
  })

  it('brak pola → pusty string', () => {
    expect(domyslnaWartoscFiltra(null, 'in')).toBe('')
    expect(domyslnaWartoscFiltra(undefined, 'equals')).toBe('')
  })
})
