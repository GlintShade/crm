import { describe, it, expect } from 'vitest'
import { SIATKA_GODZIN, generujSiatke, czyWybrane, pad } from './siatkaGodzin'

describe('pad', () => {
  it('dopelnia jednocyfrowa liczbe zerem', () => {
    expect(pad(8)).toBe('08')
  })

  it('nie zmienia dwucyfrowej liczby', () => {
    expect(pad(22)).toBe('22')
  })
})

describe('generujSiatke', () => {
  it('domyslna siatka ma 29 pol', () => {
    expect(generujSiatke()).toHaveLength(29)
  })

  it('pierwsze pole to 08:00', () => {
    const [pierwsze] = generujSiatke()
    expect(pierwsze).toEqual({ wartosc: '08:00:00', etykieta: '08:00' })
  })

  it('ostatnie pole to 22:00 (zakres wlacznie)', () => {
    const pola = generujSiatke()
    expect(pola[pola.length - 1]).toEqual({ wartosc: '22:00:00', etykieta: '22:00' })
  })

  it('kazda wartosc pasuje do formatu HH:mm:00', () => {
    const pola = generujSiatke()
    for (const p of pola) {
      expect(p.wartosc).toMatch(/^\d{2}:\d{2}:00$/)
    }
  })

  it('krok 15 minut daje 57 pol', () => {
    const pola = generujSiatke({ od: '08:00', do: '22:00', krokMin: 15 })
    expect(pola).toHaveLength(57)
  })

  it('krokMin rowny 0 rzuca blad', () => {
    expect(() => generujSiatke({ od: '08:00', do: '22:00', krokMin: 0 })).toThrow()
  })

  it('krokMin ujemny rzuca blad', () => {
    expect(() => generujSiatke({ od: '08:00', do: '22:00', krokMin: -15 })).toThrow()
  })

  it('domyslny eksport SIATKA_GODZIN to zakres 08:00 do 22:00 co 30 min', () => {
    expect(SIATKA_GODZIN).toEqual({ od: '08:00', do: '22:00', krokMin: 30 })
  })
})

describe('czyWybrane', () => {
  const pole = { wartosc: '16:30:00', etykieta: '16:30' }

  it('true, gdy godzina z sekundami zgadza sie z polem', () => {
    expect(czyWybrane(pole, '16:30:00')).toBe(true)
  })

  it('true, gdy godzina bez sekund zgadza sie z polem', () => {
    expect(czyWybrane(pole, '16:30')).toBe(true)
  })

  it('false, gdy godzina inna niz pole', () => {
    expect(czyWybrane(pole, '16:00:00')).toBe(false)
  })

  it('false, gdy godzina pusta', () => {
    expect(czyWybrane(pole, '')).toBe(false)
  })

  it('false, gdy godzina niezdefiniowana', () => {
    expect(czyWybrane(pole, undefined)).toBe(false)
  })
})
