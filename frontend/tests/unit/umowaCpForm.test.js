import { describe, expect, it } from 'vitest'
import { etykietaWariantu, formatujParaKwot, wariantOptions } from '@/utils/umowaCpForm'

describe('etykietaWariantu', () => {
  it('formats numeric-string amounts with thousands separator and comma decimals', () => {
    expect(etykietaWariantu({ netto: '1600.00', brutto: '1968.00' })).toBe(
      '1 600,00 zł netto (1 968,00 zł brutto)',
    )
  })

  it('formats plain number amounts the same way', () => {
    expect(etykietaWariantu({ netto: 2400, brutto: 2952 })).toBe(
      '2 400,00 zł netto (2 952,00 zł brutto)',
    )
  })

  it('formats large amounts with a grouped thousands separator', () => {
    expect(etykietaWariantu({ netto: 12345.5, brutto: 15185}).includes('12 345,50')).toBe(
      true,
    )
  })

  it('returns a placeholder, never "NaN"/"undefined", when netto is null', () => {
    const wynik = etykietaWariantu({ netto: null, brutto: '1968.00' })
    expect(wynik).not.toMatch(/NaN|undefined/)
    expect(wynik).toBe('brak danych')
  })

  it('returns a placeholder when brutto is undefined', () => {
    const wynik = etykietaWariantu({ netto: '1600.00', brutto: undefined })
    expect(wynik).not.toMatch(/NaN|undefined/)
    expect(wynik).toBe('brak danych')
  })

  it('returns a placeholder when both amounts are empty strings', () => {
    expect(etykietaWariantu({ netto: '', brutto: '' })).toBe('brak danych')
  })

  it('returns a placeholder when called with no argument at all', () => {
    expect(etykietaWariantu()).toBe('brak danych')
    expect(etykietaWariantu(undefined)).toBe('brak danych')
  })

  it('treats a real numeric zero as a valid amount, not as missing', () => {
    const wynik = etykietaWariantu({ netto: 0, brutto: 0 })
    expect(wynik).not.toBe('brak danych')
    expect(wynik).toBe('0,00 zł netto (0,00 zł brutto)')
  })
})

describe('wariantOptions', () => {
  it('builds a blank option plus one entry per wariant, values as strings', () => {
    const warianty = [
      { wariant: '1', netto: '1600.00', brutto: '1968.00' },
      { wariant: '2', netto: '2400.00', brutto: '2952.00' },
    ]
    const opcje = wariantOptions(warianty)
    expect(opcje).toHaveLength(3)
    expect(opcje[0]).toEqual({ label: '', value: '' })
    expect(opcje[1].value).toBe('1')
    expect(typeof opcje[1].value).toBe('string')
    expect(opcje[1].label).toBe('1 600,00 zł netto (1 968,00 zł brutto)')
    expect(opcje[2].value).toBe('2')
    expect(opcje[2].label).toBe('2 400,00 zł netto (2 952,00 zł brutto)')
  })

  it('coerces a numeric wariant value to a string', () => {
    const opcje = wariantOptions([{ wariant: 1, netto: '1600.00', brutto: '1968.00' }])
    expect(opcje[1].value).toBe('1')
    expect(typeof opcje[1].value).toBe('string')
  })

  it('drops entries with no usable wariant value', () => {
    const warianty = [
      { wariant: '1', netto: '1600.00', brutto: '1968.00' },
      { wariant: null, netto: '2400.00', brutto: '2952.00' },
      { wariant: undefined, netto: '100.00', brutto: '123.00' },
      { wariant: '', netto: '200.00', brutto: '246.00' },
      {},
    ]
    const opcje = wariantOptions(warianty)
    expect(opcje).toHaveLength(2)
    expect(opcje[1].value).toBe('1')
  })

  it('returns only the blank option for a non-array input', () => {
    expect(wariantOptions(null)).toEqual([{ label: '', value: '' }])
    expect(wariantOptions(undefined)).toEqual([{ label: '', value: '' }])
    expect(wariantOptions('malformed')).toEqual([{ label: '', value: '' }])
    expect(wariantOptions({})).toEqual([{ label: '', value: '' }])
    expect(wariantOptions(42)).toEqual([{ label: '', value: '' }])
  })

  it('returns only the blank option for an empty array', () => {
    expect(wariantOptions([])).toEqual([{ label: '', value: '' }])
  })
})

describe('formatujParaKwot', () => {
  it('formats a netto/brutto pair as one slash-separated line', () => {
    expect(formatujParaKwot('1600.00', '1968.00')).toBe(
      '1 600,00 zł netto / 1 968,00 zł brutto',
    )
  })

  it('formats plain number inputs the same way', () => {
    expect(formatujParaKwot(2400, 2952)).toBe('2 400,00 zł netto / 2 952,00 zł brutto')
  })

  it('returns empty string when netto is null', () => {
    expect(formatujParaKwot(null, '1968.00')).toBe('')
  })

  it('returns empty string when brutto is undefined', () => {
    expect(formatujParaKwot('1600.00', undefined)).toBe('')
  })

  it('returns empty string when both are empty strings', () => {
    expect(formatujParaKwot('', '')).toBe('')
  })

  it('never contains the literal strings "NaN" or "undefined"', () => {
    expect(formatujParaKwot(null, null)).not.toMatch(/NaN|undefined/)
    expect(formatujParaKwot('x', 'y')).not.toMatch(/NaN|undefined/)
  })

  it('treats a real numeric zero as a valid amount, not as missing', () => {
    expect(formatujParaKwot(0, 0)).toBe('0,00 zł netto / 0,00 zł brutto')
  })
})
