import { describe, it, expect } from 'vitest'
import {
  ZAKLADKI_ZADAN,
  czyPrzeterminowane,
  filtryDlaRol,
  filtryDlaZakladki,
  stanRol,
  tekstDoWiadomosci,
  tekstPoTerminie,
  zakladkaZFiltra,
} from './zadaniaLista'

// Stala "teraz": 16 listopada 2026, 12:00 czasu lokalnego.
const TERAZ = new Date(2026, 10, 16, 12, 0, 0)

describe('czyPrzeterminowane', () => {
  it('brak terminu daje false', () => {
    expect(czyPrzeterminowane(null, 'Todo', TERAZ)).toBe(false)
    expect(czyPrzeterminowane(undefined, 'Todo', TERAZ)).toBe(false)
    expect(czyPrzeterminowane('', 'Todo', TERAZ)).toBe(false)
  })

  it('termin za godzine daje false', () => {
    expect(czyPrzeterminowane('2026-11-16 13:00:00', 'Todo', TERAZ)).toBe(false)
  })

  it('termin godzine temu i status Todo daje true', () => {
    expect(czyPrzeterminowane('2026-11-16 11:00:00', 'Todo', TERAZ)).toBe(true)
    expect(
      czyPrzeterminowane('2026-11-16 11:00:00', 'In Progress', TERAZ),
    ).toBe(true)
  })

  it('status koncowy daje false mimo minionego terminu', () => {
    expect(czyPrzeterminowane('2026-11-10 11:00:00', 'Done', TERAZ)).toBe(false)
    expect(czyPrzeterminowane('2026-11-10 11:00:00', 'Canceled', TERAZ)).toBe(
      false,
    )
  })

  it('niepoprawny string daje false', () => {
    expect(czyPrzeterminowane('jutro', 'Todo', TERAZ)).toBe(false)
    expect(czyPrzeterminowane('2026-13-40 10:00:00', 'Todo', TERAZ)).toBe(false)
    expect(czyPrzeterminowane('2026-02-31 10:00:00', 'Todo', TERAZ)).toBe(false)
    expect(czyPrzeterminowane(12345, 'Todo', TERAZ)).toBe(false)
  })

  it('wartosc z mikrosekundami', () => {
    expect(
      czyPrzeterminowane('2026-11-13 09:00:00.000000', 'Todo', TERAZ),
    ).toBe(true)
    expect(
      czyPrzeterminowane('2026-11-20 09:00:00.000000', 'Todo', TERAZ),
    ).toBe(false)
  })

  it('termin dokladnie teraz nie jest po terminie', () => {
    expect(czyPrzeterminowane('2026-11-16 12:00:00', 'Todo', TERAZ)).toBe(false)
  })

  it('separator T i brak sekund', () => {
    expect(czyPrzeterminowane('2026-11-16T11:00', 'Todo', TERAZ)).toBe(true)
  })

  it('niepoprawne teraz daje false', () => {
    expect(
      czyPrzeterminowane('2026-11-10 11:00:00', 'Todo', new Date('x')),
    ).toBe(false)
  })
})

describe('tekstPoTerminie', () => {
  it('pusty, gdy nie po terminie albo niepoprawny', () => {
    expect(tekstPoTerminie('2026-11-16 13:00:00', TERAZ)).toBe('')
    expect(tekstPoTerminie(null, TERAZ)).toBe('')
    expect(tekstPoTerminie('zle', TERAZ)).toBe('')
  })

  it('mniej niz doba daje "po terminie"', () => {
    expect(tekstPoTerminie('2026-11-16 11:00:00', TERAZ)).toBe('po terminie')
    expect(tekstPoTerminie('2026-11-15 12:00:01', TERAZ)).toBe('po terminie')
  })

  it('dokladnie 1 doba daje "1 dzień po terminie"', () => {
    expect(tekstPoTerminie('2026-11-15 12:00:00', TERAZ)).toBe(
      '1 dzień po terminie',
    )
  })

  it('3 dni i 5 godzin temu daje "3 dni po terminie"', () => {
    expect(tekstPoTerminie('2026-11-13 07:00:00', TERAZ)).toBe(
      '3 dni po terminie',
    )
  })

  it('wartosc z mikrosekundami', () => {
    expect(tekstPoTerminie('2026-11-13 09:00:00.000000', TERAZ)).toBe(
      '3 dni po terminie',
    )
  })

  it('doby liczone kalendarzowo przez zmiane czasu', () => {
    // Zmiana czasu w nocy 25 pazdziernika 2026: dwa dni wczesniej o tej samej
    // godzinie to nadal pelne 2 doby na zegarze.
    const teraz = new Date(2026, 9, 27, 12, 0, 0)
    expect(tekstPoTerminie('2026-10-25 12:00:00', teraz)).toBe(
      '2 dni po terminie',
    )
  })
})

describe('ZAKLADKI_ZADAN', () => {
  it('trzy zakladki w kolejnosci', () => {
    expect(ZAKLADKI_ZADAN.map((z) => z.klucz)).toEqual([
      'aktywne',
      'wykonane',
      'anulowane',
    ])
    expect(ZAKLADKI_ZADAN.map((z) => z.etykieta)).toEqual([
      'Aktywne',
      'Wykonane',
      'Anulowane',
    ])
  })
})

describe('zakladkaZFiltra', () => {
  it('Done daje wykonane, Canceled anulowane', () => {
    expect(zakladkaZFiltra('Done')).toBe('wykonane')
    expect(zakladkaZFiltra('Canceled')).toBe('anulowane')
  })

  it('zbior {Todo, In Progress} w dowolnej kolejnosci daje aktywne', () => {
    expect(zakladkaZFiltra(['in', ['Todo', 'In Progress']])).toBe('aktywne')
    expect(zakladkaZFiltra(['in', ['In Progress', 'Todo']])).toBe('aktywne')
  })

  it('wszystko inne daje null', () => {
    expect(zakladkaZFiltra(undefined)).toBeNull()
    expect(zakladkaZFiltra(null)).toBeNull()
    expect(zakladkaZFiltra('Todo')).toBeNull()
    expect(zakladkaZFiltra(['in', ['Todo']])).toBeNull()
    expect(zakladkaZFiltra(['in', ['Todo', 'In Progress', 'Done']])).toBeNull()
    expect(zakladkaZFiltra(['not in', ['Todo', 'In Progress']])).toBeNull()
    expect(zakladkaZFiltra(['in', undefined])).toBeNull()
  })
})

describe('filtryDlaZakladki', () => {
  it('podmienia status i zachowuje reszte filtrow', () => {
    const filtry = { assigned_to: 'a@b.pl', status: 'Done' }
    expect(filtryDlaZakladki(filtry, 'aktywne')).toEqual({
      assigned_to: 'a@b.pl',
      status: ['in', ['Todo', 'In Progress']],
    })
    expect(filtryDlaZakladki(filtry, 'anulowane')).toEqual({
      assigned_to: 'a@b.pl',
      status: 'Canceled',
    })
  })

  it('nie mutuje argumentu i zwraca nowy obiekt', () => {
    const filtry = { status: 'Done' }
    const wynik = filtryDlaZakladki(filtry, 'wykonane')
    expect(filtry).toEqual({ status: 'Done' })
    expect(wynik).not.toBe(filtry)
  })

  it('dziala dla pustych i brakujacych filtrow', () => {
    expect(filtryDlaZakladki({}, 'wykonane')).toEqual({ status: 'Done' })
    expect(filtryDlaZakladki(undefined, 'wykonane')).toEqual({ status: 'Done' })
  })

  it('wynik aktywne nie dzieli tablicy ze stala zakladki', () => {
    const wynik = filtryDlaZakladki({}, 'aktywne')
    wynik.status[1].push('Done')
    expect(ZAKLADKI_ZADAN[0].status[1]).toEqual(['Todo', 'In Progress'])
  })

  it('wynik wraca do tej samej zakladki przez zakladkaZFiltra', () => {
    for (const z of ZAKLADKI_ZADAN) {
      expect(zakladkaZFiltra(filtryDlaZakladki({}, z.klucz).status)).toBe(
        z.klucz,
      )
    }
  })

  it('nieznany klucz zwraca kopie bez zmiany', () => {
    const filtry = { status: 'Done' }
    const wynik = filtryDlaZakladki(filtry, 'nic')
    expect(wynik).toEqual(filtry)
    expect(wynik).not.toBe(filtry)
  })
})

describe('tekstDoWiadomosci', () => {
  it('puste wejscie daje pusty tekst', () => {
    expect(tekstDoWiadomosci([])).toBe('')
    expect(tekstDoWiadomosci(undefined)).toBe('')
  })

  it('do dwoch nazwisk bez dopisku', () => {
    expect(tekstDoWiadomosci(['Jan Kowalski'])).toBe('Jan Kowalski')
    expect(tekstDoWiadomosci(['Jan Kowalski', 'Anna Nowak'])).toBe(
      'Jan Kowalski, Anna Nowak',
    )
  })

  it('powyzej dwoch dopisek +N', () => {
    expect(tekstDoWiadomosci(['A', 'B', 'C', 'D', 'E'])).toBe('A, B +3')
    expect(tekstDoWiadomosci(['A', 'B', 'C'])).toBe('A, B +1')
  })
})

describe('filtry rol (Moje / Do mojej wiadomosci)', () => {
  const JA = 'ja@x.pl'

  it('stan z pustych filtrow', () => {
    expect(stanRol({}, JA)).toEqual({ moje: false, dw: false })
    expect(stanRol(undefined, JA)).toEqual({ moje: false, dw: false })
    expect(stanRol({ assigned_to: JA }, '')).toEqual({ moje: false, dw: false })
  })

  it('stan z pojedynczych filtrow', () => {
    expect(stanRol({ assigned_to: JA }, JA)).toEqual({ moje: true, dw: false })
    expect(stanRol({ _dw: JA }, JA)).toEqual({ moje: false, dw: true })
    expect(stanRol({ _dw: ['in', [JA]] }, JA).dw).toBe(true)
    expect(stanRol({ assigned_to: 'inny@x.pl' }, JA).moje).toBe(false)
  })

  it('suma zapala oba przyciski', () => {
    expect(stanRol({ _rola_ja: 1 }, JA)).toEqual({ moje: true, dw: true })
  })

  it('ustawia dokladnie jeden filtr serwera na kombinacje', () => {
    expect(filtryDlaRol({}, JA, { moje: true, dw: false })).toEqual({ assigned_to: JA })
    expect(filtryDlaRol({}, JA, { moje: false, dw: true })).toEqual({ _dw: JA })
    expect(filtryDlaRol({}, JA, { moje: true, dw: true })).toEqual({ _rola_ja: 1 })
    expect(filtryDlaRol({ _rola_ja: 1, _dw: JA }, JA, { moje: false, dw: false })).toEqual({})
  })

  it('zachowuje inne filtry i nie mutuje argumentu', () => {
    const wejscie = { status: 'Done', assigned_to: JA }
    const wynik = filtryDlaRol(wejscie, JA, { moje: false, dw: true })
    expect(wynik).toEqual({ status: 'Done', _dw: JA })
    expect(wejscie).toEqual({ status: 'Done', assigned_to: JA })
  })
})
