import { describe, it, expect } from 'vitest'
import { formatujDzienMiesiac, wiekZadania, zalozoneZadanie } from '@/utils/dataPolska'
describe('formatujDzienMiesiac', () => {
  it('krotka data bez godziny', () => {
    expect(formatujDzienMiesiac('2026-11-01 10:00:00')).toBe('1 lis')
    expect(formatujDzienMiesiac('2026-10-30 08:15:00.123')).toBe('30 paź')
    expect(formatujDzienMiesiac('')).toBe('')
    expect(formatujDzienMiesiac(null)).toBe('')
  })
})

describe('wiekZadania', () => {
  const teraz = new Date(2026, 10, 4, 0, 30)
  it('dziś, wczoraj (przez polnoc), N dni', () => {
    expect(wiekZadania('2026-11-04 00:10:00', teraz)).toBe('dziś')
    expect(wiekZadania('2026-11-03 23:59:00', teraz)).toBe('wczoraj')
    expect(wiekZadania('2026-11-02 12:00:00', teraz)).toBe('2 dni temu')
    expect(wiekZadania('2026-10-23 12:00:00', teraz)).toBe('12 dni temu')
    expect(wiekZadania('2025-09-30 12:00:00', teraz)).toBe('400 dni temu')
  })
  it('niepoprawne wejscie i przyszlosc daja pusty tekst', () => {
    expect(wiekZadania('', teraz)).toBe('')
    expect(wiekZadania(null, teraz)).toBe('')
    expect(wiekZadania('abc', teraz)).toBe('')
    expect(wiekZadania('2026-11-05 10:00:00', teraz)).toBe('')
  })
  it('tooltip', () => {
    expect(zalozoneZadanie('2026-11-01 09:12:33')).toBe('Założone 1 lis 2026, 09:12')
    expect(zalozoneZadanie('x')).toBe('')
  })
})
