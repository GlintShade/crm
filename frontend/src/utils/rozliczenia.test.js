import { describe, it, expect } from 'vitest'
import {
  parsujOdbiorcow,
  kolorStanu,
  opisTokenow,
  klasaKropki,
  kropkiOdbiorcow,
} from './rozliczenia'

describe('parsujOdbiorcow', () => {
  it('parsuje pelny zapis', () => {
    expect(parsujOdbiorcow('H:W;M:D;P:S')).toEqual({ H: 'W', M: 'D', P: 'S' })
  })
  it('puste i nie-string daja pusty obiekt', () => {
    expect(parsujOdbiorcow('')).toEqual({})
    expect(parsujOdbiorcow(null)).toEqual({})
    expect(parsujOdbiorcow(undefined)).toEqual({})
    expect(parsujOdbiorcow(5)).toEqual({})
  })
  it('brak roli oznacza brak klucza', () => {
    expect(parsujOdbiorcow('H:W')).toEqual({ H: 'W' })
  })
  it('pomija nieznane litery stanu', () => {
    expect(parsujOdbiorcow('H:X;M:D')).toEqual({ M: 'D' })
  })
  it('pomija nieznane role', () => {
    expect(parsujOdbiorcow('Z:W;P:N')).toEqual({ P: 'N' })
  })
  it('toleruje spacje i male litery', () => {
    expect(parsujOdbiorcow(' h : w ; m:d ')).toEqual({ H: 'W', M: 'D' })
  })
  it('toleruje smieciowe fragmenty i puste segmenty', () => {
    expect(parsujOdbiorcow(';;H:W;;abc;M')).toEqual({ H: 'W' })
  })
  it('stan N jest zachowany', () => {
    expect(parsujOdbiorcow('H:N')).toEqual({ H: 'N' })
  })
})

describe('kolorStanu', () => {
  it('mapuje statusy na motywy', () => {
    expect(kolorStanu('Nierozliczone')).toBe('gray')
    expect(kolorStanu('Częściowo rozliczone')).toBe('orange')
    expect(kolorStanu('Rozliczone')).toBe('green')
    expect(kolorStanu('Wstrzymane')).toBe('red')
    expect(kolorStanu('Nie dotyczy')).toBe('gray')
  })
  it('puste i nieznane to gray', () => {
    expect(kolorStanu('')).toBe('gray')
    expect(kolorStanu(null)).toBe('gray')
    expect(kolorStanu('cos')).toBe('gray')
  })
})

describe('opisTokenow', () => {
  it('opisuje wszystkie role po polsku', () => {
    expect(opisTokenow('H:W;M:D;P:S')).toBe(
      'Handlowiec: wypłacone, Manager: do wypłaty, Partner: wstrzymane',
    )
  })
  it('pomija brakujace role', () => {
    expect(opisTokenow('M:N')).toBe('Manager: nie dotyczy')
  })
  it('puste daje pusty tekst', () => {
    expect(opisTokenow('')).toBe('')
  })
  it('bez myslnikow em/en', () => {
    expect(opisTokenow('H:W;M:D;P:S')).not.toMatch(/[\u2013\u2014]/)
  })
})

describe('kropki', () => {
  it('klasaKropki zwraca null dla braku litery', () => {
    expect(klasaKropki(null)).toBeNull()
    expect(klasaKropki('X')).toBeNull()
  })
  it('klasy sa tokenami, bez surface-white', () => {
    for (const s of ['W', 'D', 'S', 'N']) {
      expect(klasaKropki(s)).not.toContain('surface-white')
    }
  })
  it('kropkiOdbiorcow zawsze zwraca H M P', () => {
    const k = kropkiOdbiorcow('H:W;P:S')
    expect(k.map((x) => x.rola)).toEqual(['H', 'M', 'P'])
    expect(k[1].stan).toBeNull()
    expect(k[1].klasa).toBeNull()
    expect(k[0].stan).toBe('W')
  })
})
