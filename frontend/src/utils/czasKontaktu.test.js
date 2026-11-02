import { describe, it, expect } from 'vitest'
import {
  czyCzasPoprawny,
  formatujGgMm,
  parsujGgMm,
} from '@/utils/czasKontaktu'
import { KOLUMNY_INLINE, surowaWartoscKomorki } from '@/utils/leadyInline'

describe('formatujGgMm', () => {
  it('puste dla 0, null, undefined, ujemnych', () => {
    for (const v of [0, null, undefined, '', -5, NaN]) {
      expect(formatujGgMm(v)).toBe('')
    }
  })
  it('formatuje z zerami wiodacymi', () => {
    expect(formatujGgMm(5400)).toBe('01:30')
    expect(formatujGgMm(60)).toBe('00:01')
    expect(formatujGgMm(86400)).toBe('24:00')
    expect(formatujGgMm('3600')).toBe('01:00')
  })
})

describe('parsujGgMm', () => {
  it('dwukropek', () => {
    expect(parsujGgMm('1:30')).toBe(5400)
    expect(parsujGgMm('01:30')).toBe(5400)
    expect(parsujGgMm('24:00')).toBe(86400)
    expect(parsujGgMm(' 0:05 ')).toBe(300)
  })
  it('cyfry', () => {
    expect(parsujGgMm('0130')).toBe(5400)
    expect(parsujGgMm('130')).toBe(5400)
    expect(parsujGgMm('2')).toBe(7200)
    expect(parsujGgMm('12')).toBe(43200)
  })
  it('niepoprawne daje null', () => {
    for (const v of ['abc', '1:60', '', null, undefined, '1:2:3', '12345', '-1:00', '1,5']) {
      expect(parsujGgMm(v)).toBeNull()
    }
  })
  it('ponad 24:00 parsuje sie i jest poprawne', () => {
    expect(parsujGgMm('25:00')).toBe(90000)
    expect(parsujGgMm('38:20')).toBe(138000)
    expect(parsujGgMm('999:59')).toBe(3599940)
    expect(czyCzasPoprawny(90000)).toBe(true)
    expect(formatujGgMm(138000)).toBe('38:20')
  })
  it('granice poprawnosci', () => {
    expect(czyCzasPoprawny(0)).toBe(true)
    expect(czyCzasPoprawny(86400)).toBe(true)
    expect(czyCzasPoprawny(3599940)).toBe(true)
    expect(czyCzasPoprawny(NaN)).toBe(false)
    expect(czyCzasPoprawny(-1)).toBe(false)
  })
  it('round trip', () => {
    for (const s of [60, 5400, 86400]) expect(parsujGgMm(formatujGgMm(s))).toBe(s)
  })
})

describe('leadyInline: nowe kolumny', () => {
  it('sa kolumnami inline', () => {
    expect(KOLUMNY_INLINE.has('custom_czas_do_kontaktu')).toBe(true)
    expect(KOLUMNY_INLINE.has('custom_proby_kontaktu')).toBe(true)
  })
  it('Duration zwraca surowe sekundy', () => {
    const kol = { key: 'custom_czas_do_kontaktu', type: 'Duration' }
    expect(surowaWartoscKomorki(kol, 5400)).toBe(5400)
    expect(surowaWartoscKomorki(kol, null)).toBe(0)
    expect(surowaWartoscKomorki(kol, '')).toBe(0)
  })
  it('Select zwraca goly string', () => {
    const kol = { key: 'custom_proby_kontaktu', type: 'Select' }
    expect(surowaWartoscKomorki(kol, '3')).toBe('3')
  })
})
