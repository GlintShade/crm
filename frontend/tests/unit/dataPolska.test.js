import { describe, it, expect } from 'vitest'
import { formatujDzienMiesiac } from '@/utils/dataPolska'
describe('formatujDzienMiesiac', () => {
  it('krotka data bez godziny', () => {
    expect(formatujDzienMiesiac('2026-11-01 10:00:00')).toBe('1 lis')
    expect(formatujDzienMiesiac('2026-10-30 08:15:00.123')).toBe('30 paź')
    expect(formatujDzienMiesiac('')).toBe('')
    expect(formatujDzienMiesiac(null)).toBe('')
  })
})
