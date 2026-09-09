import { describe, expect, it } from 'vitest'
import { czyZablokowana, TRASY_LEADOW } from './strazTras'

describe('czyZablokowana', () => {
  it('blokuje trasy leadów, gdy hideLeads=true', () => {
    for (const trasa of TRASY_LEADOW) {
      expect(czyZablokowana(trasa, { hideLeads: true })).toBe(true)
    }
  })

  it('nie blokuje tras leadów, gdy hideLeads=false', () => {
    for (const trasa of TRASY_LEADOW) {
      expect(czyZablokowana(trasa, { hideLeads: false })).toBe(false)
    }
  })

  it('nie blokuje tras leadów, gdy flaga jest nieustawiona (fail-open)', () => {
    for (const trasa of TRASY_LEADOW) {
      expect(czyZablokowana(trasa, {})).toBe(false)
      expect(czyZablokowana(trasa)).toBe(false)
    }
  })

  it('nie blokuje innych tras, nawet gdy hideLeads=true', () => {
    expect(czyZablokowana('Deals', { hideLeads: true })).toBe(false)
    expect(czyZablokowana('Kalkulator', { hideLeads: true })).toBe(false)
    expect(czyZablokowana('Not Permitted', { hideLeads: true })).toBe(false)
  })

  it('nie blokuje, gdy nazwa trasy jest pusta/nieznana', () => {
    expect(czyZablokowana(undefined, { hideLeads: true })).toBe(false)
    expect(czyZablokowana(null, { hideLeads: true })).toBe(false)
  })
})
