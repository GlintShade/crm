import { describe, expect, it } from 'vitest'
import { formatujCzasBlokady, stanBlokady } from '@/utils/umowaBlokada'

describe('formatujCzasBlokady', () => {
  it('formatuje po napisie, bez przesuniecia stref', () => {
    expect(formatujCzasBlokady('2026-10-23 17:46:37')).toBe('23.10.2026 17:46')
  })
  it('pusty lub zly napis daje pusty wynik', () => {
    expect(formatujCzasBlokady(null)).toBe('')
    expect(formatujCzasBlokady('abc')).toBe('')
  })
})

describe('stanBlokady', () => {
  it('brak blokady daje stan neutralny', () => {
    for (const b of [undefined, null, 5]) {
      expect(stanBlokady(b)).toEqual({
        zablokowany: false,
        odblokowanyPoPodpisie: false,
        tekstBanera: '',
        pokazOdblokuj: false,
        pokazZablokuj: false,
      })
    }
  })
  it('zablokowana z data podpisu', () => {
    const s = stanBlokady({
      zablokowany: true,
      powod: 'podpis_czesciowy',
      pierwszy_podpis: '2026-10-23 17:46:37',
      moze_odblokowac: true,
    })
    expect(s.zablokowany).toBe(true)
    expect(s.tekstBanera).toBe(
      'Formularz zablokowany. Umowa została podpisana w Autenti (pierwszy podpis: 23.10.2026 17:46). Zmiany może odblokować administrator.',
    )
    expect(s.pokazOdblokuj).toBe(true)
    expect(s.pokazZablokuj).toBe(false)
  })
  it('podpisana bez daty pomija nawias', () => {
    const s = stanBlokady({ zablokowany: true, powod: 'podpisana', pierwszy_podpis: null })
    expect(s.tekstBanera).toBe(
      'Formularz zablokowany. Umowa została podpisana w Autenti. Zmiany może odblokować administrator.',
    )
    expect(s.pokazOdblokuj).toBe(false)
  })
  it('odblokowana: baner bursztynowy i zablokuj tylko dla admina', () => {
    const b = {
      zablokowany: false,
      odblokowany: true,
      odblokowal: 'Jan Kowalski',
      odblokowano_dnia: '2026-11-17 09:05:00',
    }
    const s = stanBlokady({ ...b, moze_odblokowac: true })
    expect(s.odblokowanyPoPodpisie).toBe(true)
    expect(s.tekstBanera).toBe(
      'Formularz odblokowany przez Jan Kowalski dnia 17.11.2026 09:05. Podpisany dokument w Autenti się nie zmienia.',
    )
    expect(s.pokazZablokuj).toBe(true)
    expect(stanBlokady({ ...b, moze_odblokowac: false }).pokazZablokuj).toBe(false)
  })
  it('niezablokowana i nieodblokowana: nic', () => {
    const s = stanBlokady({ zablokowany: false, odblokowany: false, moze_odblokowac: true })
    expect(s.tekstBanera).toBe('')
    expect(s.pokazOdblokuj).toBe(false)
  })
})
