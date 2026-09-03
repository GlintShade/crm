import { etykietaMoje } from '@/utils/etykietaMoje'

describe('etykietaMoje', () => {
  it('zwraca "Moje szanse" dla CRM Deal', () => {
    expect(etykietaMoje('CRM Deal')).toBe('Moje szanse')
  })

  it('zwraca "Moi klienci" dla Contact', () => {
    expect(etykietaMoje('Contact')).toBe('Moi klienci')
  })

  it('zwraca "Moje leady" dla CRM Lead', () => {
    expect(etykietaMoje('CRM Lead')).toBe('Moje leady')
  })

  it('zwraca "Moje" dla nieznanego doctype', () => {
    expect(etykietaMoje('CRM Task')).toBe('Moje')
  })

  it('zwraca "Moje" dla pustego lub brakującego doctype', () => {
    expect(etykietaMoje('')).toBe('Moje')
    expect(etykietaMoje(undefined)).toBe('Moje')
    expect(etykietaMoje(null)).toBe('Moje')
  })
})
