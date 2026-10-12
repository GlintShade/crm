import { describe, expect, it } from 'vitest'
import {
  OPERATOR_W_DNIU,
  czesciZakresuDat,
  czyPustyWarunekDaty,
  dzienZFiltraSzybkiegoDaty,
  spakujFiltrSzybkiDaty,
} from './filtrDaty'

describe('czesciZakresuDat', () => {
  it('tablica z DateRangePicker', () => {
    expect(czesciZakresuDat(['2026-10-03', '2026-10-04'])).toEqual([
      '2026-10-03',
      '2026-10-04',
    ])
  })
  it('string "od,do"', () => {
    expect(czesciZakresuDat('2026-10-03, 2026-10-04')).toEqual([
      '2026-10-03',
      '2026-10-04',
    ])
  })
  it('puste wartosci daja []', () => {
    for (const v of [[], null, undefined, '', [null, null], ['', '']]) {
      expect(czesciZakresuDat(v)).toEqual([])
    }
  })
  it('jedna granica zostaje jako pol zakresu', () => {
    expect(czesciZakresuDat(['2026-10-03'])).toEqual(['2026-10-03', ''])
  })
  it('nie mutuje wejscia', () => {
    const wejscie = ['2026-10-03', '2026-10-04']
    czesciZakresuDat(wejscie)
    expect(wejscie).toEqual(['2026-10-03', '2026-10-04'])
  })
})

describe('czyPustyWarunekDaty', () => {
  it('w dniu bez daty jest pusty', () => {
    for (const v of [null, undefined, '', '  ']) {
      expect(czyPustyWarunekDaty(OPERATOR_W_DNIU, v)).toBe(true)
    }
  })
  it('w dniu z data (takze @dzis) nie jest pusty', () => {
    expect(czyPustyWarunekDaty(OPERATOR_W_DNIU, '2026-10-03')).toBe(false)
    expect(czyPustyWarunekDaty(OPERATOR_W_DNIU, '@dzis')).toBe(false)
  })
  it('between wymaga obu granic', () => {
    expect(czyPustyWarunekDaty('between', [])).toBe(true)
    expect(czyPustyWarunekDaty('between', null)).toBe(true)
    expect(czyPustyWarunekDaty('between', ['2026-10-03'])).toBe(true)
    expect(czyPustyWarunekDaty('between', ['2026-10-03', '2026-10-04'])).toBe(false)
    expect(czyPustyWarunekDaty('between', ['2026-10-03', '2026-10-03'])).toBe(false)
  })
  it('inne operatory nie sa uznawane za puste', () => {
    expect(czyPustyWarunekDaty('equals', null)).toBe(false)
    expect(czyPustyWarunekDaty('<', '')).toBe(false)
  })
})

describe('pasek szybki daty', () => {
  it('pakuje dzien do ["w dniu", D] i obcina godzine', () => {
    expect(spakujFiltrSzybkiDaty('2026-10-03')).toEqual(['w dniu', '2026-10-03'])
    expect(spakujFiltrSzybkiDaty('2026-10-03 16:30:00')).toEqual(['w dniu', '2026-10-03'])
  })
  it('pusta wartosc usuwa klucz', () => {
    expect(spakujFiltrSzybkiDaty('')).toBeUndefined()
    expect(spakujFiltrSzybkiDaty(null)).toBeUndefined()
  })
  it('odczytuje dzien z filtra', () => {
    expect(dzienZFiltraSzybkiegoDaty(['w dniu', '2026-10-03'])).toBe('2026-10-03')
    expect(dzienZFiltraSzybkiegoDaty(['W Dniu', '2026-10-03'])).toBe('2026-10-03')
    expect(dzienZFiltraSzybkiegoDaty(['w dniu', '@dzis'])).toBe('')
  })
  it('inne ksztalty daja null', () => {
    expect(dzienZFiltraSzybkiegoDaty('2026-10-03')).toBeNull()
    expect(dzienZFiltraSzybkiegoDaty(['like', '%x%'])).toBeNull()
    expect(dzienZFiltraSzybkiegoDaty(['between', ['a', 'b']])).toBeNull()
  })
})
