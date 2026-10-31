import { describe, it, expect } from 'vitest'
import { formatujWiekLeada, PROG_WIEKU_MS } from './wiekLeada'

const T = Date.UTC(2026, 9, 31, 12, 0, 0)
const min = 60000
const godz = 60 * min

describe('formatujWiekLeada', () => {
  it('0 minut', () => expect(formatujWiekLeada(T, T)).toBe('00 h 00 m temu'))
  it('7 minut', () =>
    expect(formatujWiekLeada(T - 7 * min, T)).toBe('00 h 07 m temu'))
  it('5 h 32 m', () =>
    expect(formatujWiekLeada(T - (5 * godz + 32 * min), T)).toBe(
      '05 h 32 m temu',
    ))
  it('47 h 59 m', () =>
    expect(formatujWiekLeada(T - (47 * godz + 59 * min + 30000), T)).toBe(
      '47 h 59 m temu',
    ))
  it('dokladnie 48 h daje null', () =>
    expect(formatujWiekLeada(T - PROG_WIEKU_MS, T)).toBeNull())
  it('3 dni daje null', () =>
    expect(formatujWiekLeada(T - 72 * godz, T)).toBeNull())
  it('przyszlosc daje null', () =>
    expect(formatujWiekLeada(T + min, T)).toBeNull())
  it('NaN daje null', () => {
    expect(formatujWiekLeada(NaN, T)).toBeNull()
    expect(formatujWiekLeada(T, NaN)).toBeNull()
  })
})
