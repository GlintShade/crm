import { describe, expect, it } from 'vitest'
import {
  OZE_RODZAJE,
  TYPY_PLIKOW_NOTATKI,
  ZAKLADKI,
  czyOze,
  etykietaZakladki,
  nazwaAutora,
  plikiDoPodgladu,
  podzielPliki,
  typyDla,
} from './notatki'

describe('ZAKLADKI', () => {
  it('zna wszystkie osiem zakładek strumienia notatek', () => {
    expect(Object.keys(ZAKLADKI).sort()).toEqual(
      ['Dotacja', 'Faktury', 'Kredyt', 'Montaz', 'OSD', 'Trify', 'Umowa', 'Zestaw'].sort(),
    )
  })

  it('każda zakładka ma etykietę, niepustą listę typów, placeholder i tekst pusty', () => {
    for (const [klucz, konfig] of Object.entries(ZAKLADKI)) {
      expect(konfig.etykieta, klucz).toBeTruthy()
      expect(Array.isArray(konfig.typy), klucz).toBe(true)
      expect(konfig.typy.length, klucz).toBeGreaterThan(0)
      expect(konfig.placeholder, klucz).toBeTruthy()
      expect(konfig.pusty, klucz).toBeTruthy()
    }
  })
})

describe('typyDla', () => {
  it('zwraca bazowy zestaw typów dla Zestaw/Umowa/Kredyt/Faktury/OSD/Dotacja', () => {
    const baza = ['Notatka', 'Telefon', 'Wizyta', 'Ustalenie', 'Problem', 'Dokument']
    for (const zakladka of ['Zestaw', 'Umowa', 'Kredyt', 'Faktury', 'OSD', 'Dotacja']) {
      expect(typyDla(zakladka), zakladka).toEqual(baza)
    }
  })

  it('Montaż dokłada "Termin montażu" na końcu bazowego zestawu', () => {
    expect(typyDla('Montaz')).toEqual([
      'Notatka',
      'Telefon',
      'Wizyta',
      'Ustalenie',
      'Problem',
      'Dokument',
      'Termin montażu',
    ])
  })

  it('Trify ma własny, odrębny zestaw typów', () => {
    expect(typyDla('Trify')).toEqual([
      'Notatka',
      'Wniosek Trify',
      'Decyzja Trify',
      'Umowa Trify',
      'Wypłata Trify',
      'Problem',
    ])
  })

  it('zwraca pustą tablicę dla nieznanej zakładki', () => {
    expect(typyDla('CośNieistniejącego')).toEqual([])
    expect(typyDla(undefined)).toEqual([])
  })
})

describe('etykietaZakladki', () => {
  it('zwraca polską etykietę znanej zakładki', () => {
    expect(etykietaZakladki('Zestaw')).toBe('Zestaw')
    expect(etykietaZakladki('Montaz')).toBe('Montaż')
  })

  it('dla nieznanego klucza zwraca sam klucz, nigdy pusty string', () => {
    expect(etykietaZakladki('Cokolwiek')).toBe('Cokolwiek')
  })

  it('dla braku klucza zwraca pusty string, nie undefined/null', () => {
    expect(etykietaZakladki(undefined)).toBe('')
    expect(etykietaZakladki(null)).toBe('')
    expect(etykietaZakladki('')).toBe('')
  })
})

describe('TYPY_PLIKOW_NOTATKI', () => {
  it('zawiera MIME plus kropka-rozszerzenie dla PDF i obrazów, nigdy samo image/*', () => {
    expect(TYPY_PLIKOW_NOTATKI).toEqual([
      'application/pdf',
      'image/jpeg',
      'image/png',
      'image/webp',
      '.pdf',
      '.jpg',
      '.jpeg',
      '.png',
      '.webp',
    ])
    expect(TYPY_PLIKOW_NOTATKI).not.toContain('image/*')
  })
})

describe('podzielPliki', () => {
  it('rozdziela pliki na dokumenty i obrazy po rozszerzeniu nazwy', () => {
    const pliki = [
      { name: 'f1', file_name: 'umowa.pdf', file_url: '/files/umowa.pdf' },
      { name: 'f2', file_name: 'zdjecie.jpg', file_url: '/files/zdjecie.jpg' },
      { name: 'f3', file_name: 'plan.PNG', file_url: '/files/plan.PNG' },
      { name: 'f4', file_name: 'skan.webp', file_url: '/files/skan.webp' },
    ]
    const { dokumenty, obrazy } = podzielPliki(pliki)
    expect(dokumenty.map((p) => p.name)).toEqual(['f1'])
    expect(obrazy.map((p) => p.name)).toEqual(['f2', 'f3', 'f4'])
  })

  it('rozpoznaje rozszerzenie z file_url, gdy file_name brak', () => {
    const pliki = [{ name: 'f1', file_url: '/private/files/notatka.jpeg?x=1' }]
    const { obrazy } = podzielPliki(pliki)
    expect(obrazy.map((p) => p.name)).toEqual(['f1'])
  })

  it('traktuje nieznane/brakujące rozszerzenie jako dokument, nie obraz', () => {
    const pliki = [
      { name: 'f1', file_name: 'bez_rozszerzenia' },
      { name: 'f2', file_name: 'archiwum.zip' },
    ]
    const { dokumenty, obrazy } = podzielPliki(pliki)
    expect(dokumenty.map((p) => p.name)).toEqual(['f1', 'f2'])
    expect(obrazy).toEqual([])
  })

  it('zachowuje kolejność wejściową w obu listach i nie mutuje wejścia', () => {
    const pliki = [
      { name: 'a', file_name: 'a.jpg' },
      { name: 'b', file_name: 'b.pdf' },
      { name: 'c', file_name: 'c.png' },
    ]
    const kopiaPrzed = JSON.stringify(pliki)
    const { dokumenty, obrazy } = podzielPliki(pliki)
    expect(obrazy.map((p) => p.name)).toEqual(['a', 'c'])
    expect(dokumenty.map((p) => p.name)).toEqual(['b'])
    expect(JSON.stringify(pliki)).toBe(kopiaPrzed)
  })

  it('dla braku/niepoprawnego wejścia zwraca dwie puste listy', () => {
    expect(podzielPliki(undefined)).toEqual({ dokumenty: [], obrazy: [] })
    expect(podzielPliki(null)).toEqual({ dokumenty: [], obrazy: [] })
    expect(podzielPliki([null, undefined])).toEqual({ dokumenty: [], obrazy: [] })
  })
})

describe('plikiDoPodgladu', () => {
  it('mapuje obrazy na kształt {klucz, url, etykieta}, pomijając wiersze bez name/file_url', () => {
    const obrazy = [
      { name: 'f2', file_name: 'zdjecie.jpg', file_url: '/files/zdjecie.jpg' },
      { name: '', file_name: 'brak_name.jpg', file_url: '/files/brak_name.jpg' },
      { name: 'f3', file_name: 'plan.png', file_url: '' },
    ]
    expect(plikiDoPodgladu(obrazy)).toEqual([
      { klucz: 'f2', url: '/files/zdjecie.jpg', etykieta: 'zdjecie.jpg' },
    ])
  })

  it('dla pustej listy zwraca pustą listę', () => {
    expect(plikiDoPodgladu([])).toEqual([])
  })
})

describe('nazwaAutora', () => {
  const getUser = (email) => {
    if (email === 'znany@proenergy.pro') return { full_name: 'Jan Kowalski' }
    if (email === 'bez_nazwiska@proenergy.pro') return { full_name: '' }
    return null
  }

  it('preferuje autor_nazwa z API, gdy jest obecne', () => {
    expect(nazwaAutora({ autor_nazwa: 'Anna Nowak', owner: 'znany@proenergy.pro' }, getUser)).toBe(
      'Anna Nowak',
    )
  })

  it('spada na getUser(owner).full_name, gdy autor_nazwa brak', () => {
    expect(nazwaAutora({ owner: 'znany@proenergy.pro' }, getUser)).toBe('Jan Kowalski')
  })

  it('spada ostatecznie na sam e-mail (owner), gdy nic innego nie ma', () => {
    expect(nazwaAutora({ owner: 'nieznany@proenergy.pro' }, getUser)).toBe('nieznany@proenergy.pro')
    expect(nazwaAutora({ owner: 'bez_nazwiska@proenergy.pro' }, getUser)).toBe(
      'bez_nazwiska@proenergy.pro',
    )
  })

  it('zwraca pusty string dla braku wpisu, nie rzuca wyjątku', () => {
    expect(nazwaAutora(null, getUser)).toBe('')
    expect(nazwaAutora(undefined, getUser)).toBe('')
  })

  it('działa bez getUser (nie jest funkcją)', () => {
    expect(nazwaAutora({ owner: 'ktos@proenergy.pro' }, undefined)).toBe('ktos@proenergy.pro')
  })
})

describe('OZE_RODZAJE / czyOze', () => {
  it('rozpoznaje dokładnie trzy rodzaje OZE', () => {
    expect(OZE_RODZAJE.size).toBe(3)
    expect(czyOze('Fotowoltaika')).toBe(true)
    expect(czyOze('Fotowoltaika + Magazyn')).toBe(true)
    expect(czyOze('Magazyn energii')).toBe(true)
  })

  it('odrzuca Czyste Powietrze i wartości puste/nieznane', () => {
    expect(czyOze('Czyste Powietrze')).toBe(false)
    expect(czyOze('')).toBe(false)
    expect(czyOze(undefined)).toBe(false)
    expect(czyOze(null)).toBe(false)
  })
})
