import { telHref, czyTelefon } from '@/utils/telefon'

describe('telHref', () => {
  it('strips spaces and keeps a leading plus', () => {
    expect(telHref('+48 690 596 452')).toBe('tel:+48690596452')
  })

  it('strips dashes', () => {
    expect(telHref('690-596-452')).toBe('tel:690596452')
  })

  it('strips parentheses and spaces', () => {
    expect(telHref('(22) 123 45 67')).toBe('tel:221234567')
  })

  it('strips dots', () => {
    expect(telHref('690.596.452')).toBe('tel:690596452')
  })

  it('returns empty string for empty input', () => {
    expect(telHref('')).toBe('')
  })

  it('returns empty string for null', () => {
    expect(telHref(null)).toBe('')
  })

  it('returns empty string for undefined', () => {
    expect(telHref(undefined)).toBe('')
  })

  it('returns empty string for letters-only input', () => {
    expect(telHref('brak numeru')).toBe('')
  })

  it('still builds a href for a short numeric value', () => {
    expect(telHref('123')).toBe('tel:123')
  })
})

describe('czyTelefon', () => {
  it('accepts a full Polish mobile number', () => {
    expect(czyTelefon('+48 690 596 452')).toBe(true)
  })

  it('accepts a number with dashes', () => {
    expect(czyTelefon('690-596-452')).toBe(true)
  })

  it('rejects a value with fewer than 7 digits', () => {
    expect(czyTelefon('123456')).toBe(false)
  })

  it('rejects empty input', () => {
    expect(czyTelefon('')).toBe(false)
  })

  it('rejects null', () => {
    expect(czyTelefon(null)).toBe(false)
  })

  it('rejects letters-only input', () => {
    expect(czyTelefon('brak numeru')).toBe(false)
  })
})
