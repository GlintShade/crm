import { describe, it, expect } from 'vitest'
import { DNI_TYGODNIA_SKROT, MIESIACE_SKROT, formatujTermin } from '@/utils/dataPolska'

describe('DNI_TYGODNIA_SKROT / MIESIACE_SKROT', () => {
  it('mają po 7 i 12 wpisów', () => {
    expect(DNI_TYGODNIA_SKROT).toHaveLength(7)
    expect(MIESIACE_SKROT).toHaveLength(12)
  })
})

describe('formatujTermin', () => {
  it('formatuje pełny Datetime z sekundami (piątek)', () => {
    expect(formatujTermin('2026-09-25 17:00:00')).toBe('pt., 25 wrz 2026, 17:00')
  })

  it('formatuje Datetime bez sekund tak samo', () => {
    expect(formatujTermin('2026-09-25 17:00')).toBe('pt., 25 wrz 2026, 17:00')
  })

  it('toleruje separator "T"', () => {
    expect(formatujTermin('2026-09-25T17:00:00')).toBe('pt., 25 wrz 2026, 17:00')
  })

  it('dzień bez zera wiodącego, minuta z zerem (czwartek)', () => {
    // new Date(2026, 0, 1).getDay() === 4 -> czwartek
    expect(formatujTermin('2026-01-01 00:05:00')).toBe('czw., 1 sty 2026, 00:05')
  })

  it('niedziela', () => {
    // new Date(2026, 11, 6).getDay() === 0 -> niedziela
    expect(formatujTermin('2026-12-06 09:30:00')).toBe('niedz., 6 gru 2026, 09:30')
  })

  it('grudzień (skrót "gru")', () => {
    expect(formatujTermin('2026-12-25 12:00:00')).toBe('pt., 25 gru 2026, 12:00')
  })

  it('przyjmuje obiekt Date', () => {
    expect(formatujTermin(new Date(2026, 8, 25, 17, 0))).toBe('pt., 25 wrz 2026, 17:00')
  })

  it('zwraca "" dla pustego/niepoprawnego wejścia', () => {
    expect(formatujTermin('')).toBe('')
    expect(formatujTermin(null)).toBe('')
    expect(formatujTermin(undefined)).toBe('')
    expect(formatujTermin('abc')).toBe('')
  })

  it('zwraca "" dla nieistniejącej daty (31 lutego)', () => {
    expect(formatujTermin('2026-02-31 10:00:00')).toBe('')
  })

  it('zwraca "" dla niepoprawnego miesiąca (13)', () => {
    expect(formatujTermin('2026-13-01 10:00:00')).toBe('')
  })
})
