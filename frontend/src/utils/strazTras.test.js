import { describe, expect, it } from 'vitest'
import {
  czyZablokowana,
  trasaStartowa,
  TRASY_KLIENTOW,
  TRASY_LEADOW,
  TRASY_UMOW,
} from './strazTras'

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

  it('obejmuje kalendarz spotkań (ops#318)', () => {
    expect(TRASY_LEADOW).toContain('Kalendarz')
    expect(czyZablokowana('Kalendarz', { hideLeads: true })).toBe(true)
    expect(czyZablokowana('Kalendarz', { hideLeads: false })).toBe(false)
  })

  it('trasa Leads (także /leads/view/kalendarz, ops#318) jest blokowana bez linii Leady', () => {
    expect(czyZablokowana('Leads', { hideLeads: true })).toBe(true)
    expect(czyZablokowana('Leads', { hideLeads: false })).toBe(false)
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

describe('ukrywanie zakładek Umowy i Klienci (ops#425)', () => {
  it('blokuje trasy umów tylko przy ukryjUmowy', () => {
    for (const trasa of TRASY_UMOW) {
      expect(czyZablokowana(trasa, { ukryjUmowy: true })).toBe(true)
      expect(czyZablokowana(trasa, { ukryjUmowy: false })).toBe(false)
      expect(czyZablokowana(trasa, { ukryjKlienci: true })).toBe(false)
      expect(czyZablokowana(trasa, {})).toBe(false)
    }
  })

  it('blokuje trasy klientów tylko przy ukryjKlienci', () => {
    for (const trasa of TRASY_KLIENTOW) {
      expect(czyZablokowana(trasa, { ukryjKlienci: true })).toBe(true)
      expect(czyZablokowana(trasa, { ukryjKlienci: false })).toBe(false)
      expect(czyZablokowana(trasa, { ukryjUmowy: true })).toBe(false)
    }
  })

  it('nie rusza leadów ani zadań', () => {
    const flagi = { ukryjUmowy: true, ukryjKlienci: true }
    expect(czyZablokowana('Leads', flagi)).toBe(false)
    expect(czyZablokowana('Tasks', flagi)).toBe(false)
  })
})

describe('trasaStartowa (ops#425)', () => {
  it('zostawia trasę, gdy nie jest zablokowana', () => {
    expect(trasaStartowa('Deals', {})).toBe('Deals')
    expect(trasaStartowa('Contacts', { ukryjUmowy: true })).toBe('Contacts')
  })

  it('zablokowane Umowy kierują na Leady', () => {
    expect(trasaStartowa('Deals', { ukryjUmowy: true })).toBe('Leads')
    expect(trasaStartowa('Contacts', { ukryjKlienci: true })).toBe('Leads')
  })

  it('gdy Leady też niedostępne, na Zadania', () => {
    expect(trasaStartowa('Deals', { ukryjUmowy: true, hideLeads: true })).toBe('Tasks')
  })
})
