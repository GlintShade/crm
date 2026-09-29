import { describe, it, expect } from 'vitest'
import { KODY_RODZAJU_UMOWY, KOD_NIEZNANY, opisRodzajuUmowy } from '@/utils/rodzajUmowy'

describe('opisRodzajuUmowy', () => {
  it('mapuje wszystkie 4 znane rodzaje na kod i pelna nazwe', () => {
    expect(opisRodzajuUmowy('Fotowoltaika')).toEqual({ kod: 'PV', pelnaNazwa: 'Fotowoltaika' })
    expect(opisRodzajuUmowy('Fotowoltaika + Magazyn')).toEqual({
      kod: 'PV+ME',
      pelnaNazwa: 'Fotowoltaika + Magazyn',
    })
    expect(opisRodzajuUmowy('Magazyn energii')).toEqual({ kod: 'ME', pelnaNazwa: 'Magazyn energii' })
    expect(opisRodzajuUmowy('Czyste Powietrze')).toEqual({ kod: 'CP', pelnaNazwa: 'Czyste Powietrze' })
  })

  it('zwraca XX dla pustego/brakujacego rodzaju', () => {
    expect(opisRodzajuUmowy('')).toEqual({ kod: 'XX', pelnaNazwa: 'Brak rodzaju umowy' })
    expect(opisRodzajuUmowy(null)).toEqual({ kod: 'XX', pelnaNazwa: 'Brak rodzaju umowy' })
    expect(opisRodzajuUmowy(undefined)).toEqual({ kod: 'XX', pelnaNazwa: 'Brak rodzaju umowy' })
  })

  it('zwraca XX dla nieznanej wartosci, pelna nazwa niesie oryginalna wartosc', () => {
    expect(opisRodzajuUmowy('Cos Innego')).toEqual({
      kod: 'XX',
      pelnaNazwa: 'Nieznany rodzaj umowy (Cos Innego)',
    })
  })

  it('KODY_RODZAJU_UMOWY ma dokladnie 4 wpisy, KOD_NIEZNANY to XX', () => {
    expect(Object.keys(KODY_RODZAJU_UMOWY)).toHaveLength(4)
    expect(KOD_NIEZNANY).toBe('XX')
  })
})
