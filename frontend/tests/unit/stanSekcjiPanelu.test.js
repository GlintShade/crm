import { describe, it, expect, beforeEach } from 'vitest'
import {
  PREFIKS_STANU,
  kluczStanuSekcji,
  parsujStan,
  wczytajStanSekcji,
  zapiszStanSekcji,
  rozstrzygnijOtwarcie,
  domyslnieOtwartaKarta,
  SEKCJA_ZADANIA,
  SEKCJA_NOTATKI,
  WIDOK_SZCZEGOLY,
  doctypeDlaWidoku,
  wczytajSynchronizujSekcje,
  zapiszSynchronizujSekcje,
} from '@/utils/stanSekcjiPanelu'

// Magazyn w pamieci z interfejsem localStorage (getItem/setItem/key/length).
function magazynTestowy(poczatek = {}) {
  const dane = new Map(Object.entries(poczatek))
  return {
    getItem: (k) => (dane.has(k) ? dane.get(k) : null),
    setItem: (k, v) => dane.set(k, String(v)),
    key: (i) => [...dane.keys()][i] ?? null,
    get length() {
      return dane.size
    },
    dane,
  }
}

function magazynRzucajacy() {
  const blad = () => {
    throw new Error('SecurityError')
  }
  return { getItem: blad, setItem: blad, key: blad, length: 0 }
}

describe('kluczStanuSekcji', () => {
  it('zawiera uzytkownika i doctype', () => {
    expect(kluczStanuSekcji('jan@x.pl', 'CRM Lead')).toBe(
      `${PREFIKS_STANU}::jan@x.pl::CRM Lead`,
    )
  })
  it('rozroznia uzytkownikow i doctype', () => {
    const a = kluczStanuSekcji('a@x.pl', 'CRM Lead')
    expect(kluczStanuSekcji('b@x.pl', 'CRM Lead')).not.toBe(a)
    expect(kluczStanuSekcji('a@x.pl', 'CRM Deal')).not.toBe(a)
  })
  it('brak uzytkownika daje Guest', () => {
    expect(kluczStanuSekcji(null, 'CRM Lead')).toBe(
      `${PREFIKS_STANU}::Guest::CRM Lead`,
    )
  })
})

describe('parsujStan', () => {
  it('zostawia tylko wartosci logiczne', () => {
    expect(parsujStan('{"a":true,"b":false,"c":1,"d":"tak"}')).toEqual({
      a: true,
      b: false,
    })
  })
  it('smieci, tablica i pusty tekst daja pusty obiekt', () => {
    expect(parsujStan('{nie json')).toEqual({})
    expect(parsujStan('[true]')).toEqual({})
    expect(parsujStan('null')).toEqual({})
    expect(parsujStan('')).toEqual({})
    expect(parsujStan(null)).toEqual({})
  })
})

describe('wczytajStanSekcji / zapiszStanSekcji', () => {
  let m
  beforeEach(() => {
    m = magazynTestowy()
  })

  it('brak zapisu daje pusty obiekt', () => {
    expect(wczytajStanSekcji('jan@x.pl', 'CRM Lead', m)).toEqual({})
  })

  it('zapis i odczyt per uzytkownik', () => {
    const stan = { 'Dane teleadresowe': false, Handlowe: true }
    expect(zapiszStanSekcji('jan@x.pl', 'CRM Lead', stan, m)).toBe(true)
    expect(wczytajStanSekcji('jan@x.pl', 'CRM Lead', m)).toEqual(stan)
    expect(wczytajStanSekcji('ola@x.pl', 'CRM Lead', m)).toEqual({})
    expect(wczytajStanSekcji('jan@x.pl', 'CRM Deal', m)).toEqual({})
  })

  it('przejmuje stare klucze ops#326 tylko dla danego doctype', () => {
    m = magazynTestowy({
      'volteo.panel.sekcja.CRM Lead.zrodlo': '0',
      'volteo.panel.sekcja.CRM Lead.handlowe': '1',
      'volteo.panel.sekcja.CRM Lead.zly': 'x',
      'volteo.panel.sekcja.CRM Deal.zrodlo': '1',
      inny: '1',
    })
    expect(wczytajStanSekcji('jan@x.pl', 'CRM Lead', m)).toEqual({
      zrodlo: false,
      handlowe: true,
    })
  })

  it('nowy zapis ma pierwszenstwo przed starymi kluczami', () => {
    m = magazynTestowy({ 'volteo.panel.sekcja.CRM Lead.zrodlo': '0' })
    zapiszStanSekcji('jan@x.pl', 'CRM Lead', { zrodlo: true }, m)
    expect(wczytajStanSekcji('jan@x.pl', 'CRM Lead', m)).toEqual({ zrodlo: true })
  })

  it('magazyn rzucajacy wyjatkiem (tryb prywatny) nie psuje widoku', () => {
    const r = magazynRzucajacy()
    expect(wczytajStanSekcji('jan@x.pl', 'CRM Lead', r)).toEqual({})
    expect(zapiszStanSekcji('jan@x.pl', 'CRM Lead', { a: true }, r)).toBe(false)
  })

  it('brak magazynu nie psuje widoku', () => {
    expect(wczytajStanSekcji('jan@x.pl', 'CRM Lead', null)).toEqual({})
    expect(zapiszStanSekcji('jan@x.pl', 'CRM Lead', { a: true }, null)).toBe(false)
  })

  it('domyslnie uzywa localStorage', () => {
    localStorage.clear()
    zapiszStanSekcji('jan@x.pl', 'CRM Lead', { a: false })
    expect(localStorage.getItem(kluczStanuSekcji('jan@x.pl', 'CRM Lead'))).toBe(
      '{"a":false}',
    )
    expect(wczytajStanSekcji('jan@x.pl', 'CRM Lead')).toEqual({ a: false })
    localStorage.clear()
  })
})

describe('rozstrzygnijOtwarcie', () => {
  it('zapis wygrywa z ukladem', () => {
    expect(rozstrzygnijOtwarcie({ a: false }, 'a', true)).toBe(false)
    expect(rozstrzygnijOtwarcie({ a: true }, 'a', false)).toBe(true)
  })
  it('bez zapisu stan domyslny z ukladu', () => {
    expect(rozstrzygnijOtwarcie({}, 'a', true)).toBe(true)
    expect(rozstrzygnijOtwarcie({ b: false }, 'a', false)).toBe(false)
    expect(rozstrzygnijOtwarcie(null, 'a', true)).toBe(true)
  })
  it('sekcja bez nazwy zawsze z ukladu', () => {
    expect(rozstrzygnijOtwarcie({ '': false }, '', true)).toBe(true)
  })
})

describe('domyslnieOtwartaKarta', () => {
  it('lead: otwarta tylko pierwsza widoczna', () => {
    expect(domyslnieOtwartaKarta({ pierwszaWidoczna: true })).toBe(true)
    expect(domyslnieOtwartaKarta({ pierwszaWidoczna: false })).toBe(false)
  })
  it('szansa (startZwiniete): wszystkie zwiniete', () => {
    expect(
      domyslnieOtwartaKarta({ startZwiniete: true, pierwszaWidoczna: true }),
    ).toBe(false)
  })
  it('szansa: zapis uzytkownika wygrywa ze startZwiniete', () => {
    const domyslny = domyslnieOtwartaKarta({ startZwiniete: true, pierwszaWidoczna: true })
    expect(rozstrzygnijOtwarcie({ handlowe: true }, 'handlowe', domyslny)).toBe(true)
    expect(rozstrzygnijOtwarcie({}, 'handlowe', domyslny)).toBe(false)
  })
})

describe('SEKCJA_ZADANIA', () => {
  it('klucz karty Zadania nie wyglada jak nazwa sekcji z ukladu', () => {
    expect(SEKCJA_ZADANIA.startsWith('__')).toBe(true)
  })
})

describe('SEKCJA_NOTATKI', () => {
  it('rozny od klucza Zadan i z prefiksem "__"', () => {
    expect(SEKCJA_NOTATKI).not.toBe(SEKCJA_ZADANIA)
    expect(SEKCJA_NOTATKI.startsWith('__')).toBe(true)
  })
})

// Przelacznik "Synchronizuj sekcje" (b84, zadanie F): prawy panel leada
// (bez widoku) i zakladka "Szczegoly" (WIDOK_SZCZEGOLY) dziela dzis jeden
// klucz; wylaczona synchronizacja ma dac kazdemu z nich osobny.
describe('doctypeDlaWidoku', () => {
  it('synchronizacja wlaczona: ten sam klucz dla obu widokow', () => {
    const bazowy = kluczStanuSekcji('jan@x.pl', 'CRM Lead')
    const prawyPanel = kluczStanuSekcji(
      'jan@x.pl',
      doctypeDlaWidoku('CRM Lead', '', true),
    )
    const szczegoly = kluczStanuSekcji(
      'jan@x.pl',
      doctypeDlaWidoku('CRM Lead', WIDOK_SZCZEGOLY, true),
    )
    expect(prawyPanel).toBe(bazowy)
    expect(szczegoly).toBe(bazowy)
  })

  it('domyslnie (bez podania synchronizuj) tak samo jak wlaczona', () => {
    expect(doctypeDlaWidoku('CRM Lead', WIDOK_SZCZEGOLY)).toBe('CRM Lead')
  })

  it('synchronizacja wylaczona: rozne klucze dla prawego panelu i Szczegolow', () => {
    const prawyPanel = kluczStanuSekcji(
      'jan@x.pl',
      doctypeDlaWidoku('CRM Lead', '', false),
    )
    const szczegoly = kluczStanuSekcji(
      'jan@x.pl',
      doctypeDlaWidoku('CRM Lead', WIDOK_SZCZEGOLY, false),
    )
    expect(szczegoly).not.toBe(prawyPanel)
    expect(prawyPanel).toBe(kluczStanuSekcji('jan@x.pl', 'CRM Lead'))
  })

  it('wylaczona, ale bez widoku (prawy panel): zostaje na dotychczasowym kluczu', () => {
    expect(doctypeDlaWidoku('CRM Lead', '', false)).toBe('CRM Lead')
    expect(doctypeDlaWidoku('CRM Lead', undefined, false)).toBe('CRM Lead')
  })
})

describe('wczytajSynchronizujSekcje / zapiszSynchronizujSekcje', () => {
  let m
  beforeEach(() => {
    m = magazynTestowy()
  })

  it('brak zapisu (i brak magazynu) daje domyslnie wlaczony', () => {
    expect(wczytajSynchronizujSekcje('jan@x.pl', m)).toBe(true)
    expect(wczytajSynchronizujSekcje('jan@x.pl', null)).toBe(true)
  })

  it('zapis i odczyt per uzytkownik', () => {
    expect(zapiszSynchronizujSekcje('jan@x.pl', false, m)).toBe(true)
    expect(wczytajSynchronizujSekcje('jan@x.pl', m)).toBe(false)
    expect(wczytajSynchronizujSekcje('ola@x.pl', m)).toBe(true)
  })

  it('magazyn rzucajacy wyjatkiem (tryb prywatny) nie psuje widoku', () => {
    const r = magazynRzucajacy()
    expect(wczytajSynchronizujSekcje('jan@x.pl', r)).toBe(true)
    expect(zapiszSynchronizujSekcje('jan@x.pl', false, r)).toBe(false)
  })
})
