import { describe, it, expect } from 'vitest'
import {
  KODY_RODZAJU_UMOWY,
  KOD_NIEZNANY,
  RODZAJE_OZE,
  RODZAJE_OZE_NOWE,
  RODZAJE_OZE_PV,
  czyOze,
  czyOzeNowy,
  czyOzePv,
  opisRodzajuUmowy,
  umowaWPrzygotowaniu,
  umowaTylkoBaner,
  zakladkiSzansy,
} from '@/utils/rodzajUmowy'

describe('opisRodzajuUmowy', () => {
  it('mapuje wszystkie 4 stare rodzaje na kod i pelna nazwe', () => {
    expect(opisRodzajuUmowy('Fotowoltaika')).toEqual({ kod: 'PV', pelnaNazwa: 'Fotowoltaika' })
    expect(opisRodzajuUmowy('Fotowoltaika + Magazyn')).toEqual({
      kod: 'PV+ME',
      pelnaNazwa: 'Fotowoltaika + Magazyn',
    })
    expect(opisRodzajuUmowy('Magazyn energii')).toEqual({ kod: 'ME', pelnaNazwa: 'Magazyn energii' })
    expect(opisRodzajuUmowy('Czyste Powietrze')).toEqual({ kod: 'CP', pelnaNazwa: 'Czyste Powietrze' })
  })

  it('mapuje wszystkie 4 nowe rodzaje (b68) na kod ROZ/KL/PC/PP i pelna nazwe', () => {
    expect(opisRodzajuUmowy('Rozbudowa PV/ME')).toEqual({ kod: 'ROZ', pelnaNazwa: 'Rozbudowa PV/ME' })
    expect(opisRodzajuUmowy('Klimatyzacja')).toEqual({ kod: 'KL', pelnaNazwa: 'Klimatyzacja' })
    expect(opisRodzajuUmowy('Pompa ciepła')).toEqual({ kod: 'PC', pelnaNazwa: 'Pompa ciepła' })
    expect(opisRodzajuUmowy('Kocioł')).toEqual({ kod: 'PP', pelnaNazwa: 'Kocioł' })
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

  it('KODY_RODZAJU_UMOWY ma dokladnie 8 wpisow, KOD_NIEZNANY to XX', () => {
    expect(Object.keys(KODY_RODZAJU_UMOWY)).toHaveLength(8)
    expect(KOD_NIEZNANY).toBe('XX')
  })
})

describe('RODZAJE_OZE_PV / RODZAJE_OZE_NOWE / RODZAJE_OZE', () => {
  it('RODZAJE_OZE_PV ma dokladnie trzy stare rodzaje', () => {
    expect(RODZAJE_OZE_PV.size).toBe(3)
    expect(RODZAJE_OZE_PV.has('Fotowoltaika')).toBe(true)
    expect(RODZAJE_OZE_PV.has('Fotowoltaika + Magazyn')).toBe(true)
    expect(RODZAJE_OZE_PV.has('Magazyn energii')).toBe(true)
  })

  it('RODZAJE_OZE_NOWE ma dokladnie cztery nowe rodzaje (b68)', () => {
    expect(RODZAJE_OZE_NOWE.size).toBe(4)
    expect(RODZAJE_OZE_NOWE.has('Rozbudowa PV/ME')).toBe(true)
    expect(RODZAJE_OZE_NOWE.has('Klimatyzacja')).toBe(true)
    expect(RODZAJE_OZE_NOWE.has('Pompa ciepła')).toBe(true)
    expect(RODZAJE_OZE_NOWE.has('Kocioł')).toBe(true)
  })

  it('RODZAJE_OZE ma dokladnie siedem wpisow (stare trzy plus nowe cztery), bez duplikatow', () => {
    expect(RODZAJE_OZE.size).toBe(7)
    for (const rodzaj of RODZAJE_OZE_PV) expect(RODZAJE_OZE.has(rodzaj)).toBe(true)
    for (const rodzaj of RODZAJE_OZE_NOWE) expect(RODZAJE_OZE.has(rodzaj)).toBe(true)
  })

  it('RODZAJE_OZE nie zawiera Czyste Powietrze', () => {
    expect(RODZAJE_OZE.has('Czyste Powietrze')).toBe(false)
  })
})

describe('czyOze / czyOzePv / czyOzeNowy', () => {
  it('czyOze rozpoznaje wszystkie siedem rodzajow OZE', () => {
    for (const rodzaj of [
      'Fotowoltaika',
      'Fotowoltaika + Magazyn',
      'Magazyn energii',
      'Rozbudowa PV/ME',
      'Klimatyzacja',
      'Pompa ciepła',
      'Kocioł',
    ]) {
      expect(czyOze(rodzaj), rodzaj).toBe(true)
    }
  })

  it('czyOze odrzuca Czyste Powietrze i wartosci puste/nieznane', () => {
    expect(czyOze('Czyste Powietrze')).toBe(false)
    expect(czyOze('')).toBe(false)
    expect(czyOze(undefined)).toBe(false)
    expect(czyOze(null)).toBe(false)
  })

  it('czyOzePv rozpoznaje wylacznie trzy stare rodzaje', () => {
    expect(czyOzePv('Fotowoltaika')).toBe(true)
    expect(czyOzePv('Magazyn energii')).toBe(true)
    expect(czyOzePv('Rozbudowa PV/ME')).toBe(false)
    expect(czyOzePv('Czyste Powietrze')).toBe(false)
  })

  it('czyOzeNowy rozpoznaje wylacznie cztery nowe rodzaje', () => {
    expect(czyOzeNowy('Rozbudowa PV/ME')).toBe(true)
    expect(czyOzeNowy('Klimatyzacja')).toBe(true)
    expect(czyOzeNowy('Pompa ciepła')).toBe(true)
    expect(czyOzeNowy('Kocioł')).toBe(true)
    expect(czyOzeNowy('Fotowoltaika')).toBe(false)
    expect(czyOzeNowy('Czyste Powietrze')).toBe(false)
  })
})

describe('zakladkiSzansy', () => {
  it('PV/PV+ME/ME: osd i dotacja prawda, wszystkie zakladki OZE prawda', () => {
    for (const rodzaj of ['Fotowoltaika', 'Fotowoltaika + Magazyn', 'Magazyn energii']) {
      expect(zakladkiSzansy(rodzaj), rodzaj).toEqual({
        osd: true,
        dotacja: true,
        kredyt: true,
        notatki: true,
        montazOze: true,
        plikiOze: true,
        umowaOze: true,
        audytOze: true,
      })
    }
  })

  it('Rozbudowa PV/ME: osd prawda, dotacja falsz, reszta OZE prawda', () => {
    expect(zakladkiSzansy('Rozbudowa PV/ME')).toEqual({
      osd: true,
      dotacja: false,
      kredyt: true,
      notatki: true,
      montazOze: true,
      plikiOze: true,
      umowaOze: true,
      audytOze: true,
    })
  })

  it('Klimatyzacja / Pompa ciepła / Kocioł: osd i dotacja falsz, reszta OZE prawda', () => {
    for (const rodzaj of ['Klimatyzacja', 'Pompa ciepła', 'Kocioł']) {
      expect(zakladkiSzansy(rodzaj), rodzaj).toEqual({
        osd: false,
        dotacja: false,
        kredyt: true,
        notatki: true,
        montazOze: true,
        plikiOze: true,
        umowaOze: true,
        audytOze: true,
      })
    }
  })

  it('Czyste Powietrze: wszystko falsz (ma wlasne odpowiedniki Trify/UmowaCP/AudytCP)', () => {
    expect(zakladkiSzansy('Czyste Powietrze')).toEqual({
      osd: false,
      dotacja: false,
      kredyt: false,
      notatki: false,
      montazOze: false,
      plikiOze: false,
      umowaOze: false,
      audytOze: false,
    })
  })

  it('rodzaj pusty/nierozpoznany: umowaOze i audytOze fail-open (prawda), reszta falsz', () => {
    for (const rodzaj of ['', null, undefined, 'Cos Innego']) {
      expect(zakladkiSzansy(rodzaj), String(rodzaj)).toEqual({
        osd: false,
        dotacja: false,
        kredyt: false,
        notatki: false,
        montazOze: false,
        plikiOze: false,
        umowaOze: true,
        audytOze: true,
      })
    }
  })
})

describe('umowaWPrzygotowaniu', () => {
  it('prawda wylacznie dla trzech rodzajow bez wzoru (Rozbudowa ma juz wzor)', () => {
    expect(umowaWPrzygotowaniu('Rozbudowa PV/ME')).toBe(false)
    expect(umowaTylkoBaner('Rozbudowa PV/ME')).toBe(false)
    expect(umowaTylkoBaner('Klimatyzacja')).toBe(true)
    expect(umowaTylkoBaner('Pompa ciepła')).toBe(true)
    expect(umowaTylkoBaner('Kocioł')).toBe(true)
    expect(umowaTylkoBaner('Fotowoltaika')).toBe(false)
    expect(umowaWPrzygotowaniu('Klimatyzacja')).toBe(true)
    expect(umowaWPrzygotowaniu('Pompa ciepła')).toBe(true)
    expect(umowaWPrzygotowaniu('Kocioł')).toBe(true)
  })

  it('falsz dla starych rodzajow OZE, Czyste Powietrze i rodzaju pustego/nieznanego', () => {
    expect(umowaWPrzygotowaniu('Fotowoltaika')).toBe(false)
    expect(umowaWPrzygotowaniu('Magazyn energii')).toBe(false)
    expect(umowaWPrzygotowaniu('Czyste Powietrze')).toBe(false)
    expect(umowaWPrzygotowaniu('')).toBe(false)
    expect(umowaWPrzygotowaniu(undefined)).toBe(false)
  })
})
