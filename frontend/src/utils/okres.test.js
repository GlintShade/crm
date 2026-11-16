import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  PRESETY,
  OPCJE_WG,
  KLUCZ_STORAGE,
  DOMYSLNY_WYBOR,
  czyOkresGotowy,
  zakresOkresu,
  etykietaZakresu,
  okresDlaApi,
  zapiszWybor,
  odczytajWybor,
  parsujDate,
  formatujDate,
} from './okres'

const d = (r, m, dz) => new Date(r, m - 1, dz)
// 2026-10-15 to czwartek
const DZIS = d(2026, 10, 15)

describe('presety i opcje', () => {
  it('ma 12 presetow, "Wszystkie okresy" na poczatku', () => {
    expect(PRESETY).toHaveLength(12)
    expect(PRESETY[0]).toEqual({ klucz: 'wszystko', etykieta: 'Wszystkie okresy' })
    expect(PRESETY.map((p) => p.klucz)).toContain('wlasny')
  })
  it('ma 5 opcji wg, z osia "termin"', () => {
    expect(OPCJE_WG.map((o) => o.klucz)).toEqual(['podpisanie', 'termin', 'wyplata', 'utworzenie', 'oznaczenie'])
  })
  it('nazywa daty: termin wyplaty i wyplacono dnia', () => {
    const et = Object.fromEntries(OPCJE_WG.map((o) => [o.klucz, o.etykieta]))
    expect(et.termin).toBe('Termin wypłaty')
    expect(et.wyplata).toBe('Wypłacono dnia')
    expect(Object.values(et)).not.toContain('Data wypłaty')
  })
})

describe('zakresOkresu', () => {
  it('dzisiaj', () => {
    expect(zakresOkresu('dzisiaj', DZIS)).toEqual({ od: '2026-10-15', do: '2026-10-15' })
  })
  it('ten tydzien od poniedzialku do niedzieli', () => {
    expect(zakresOkresu('ten_tydzien', DZIS)).toEqual({ od: '2026-10-12', do: '2026-10-18' })
  })
  it('ten tydzien w niedziele nalezy do tygodnia konczacego sie tego dnia', () => {
    expect(zakresOkresu('ten_tydzien', d(2026, 10, 18))).toEqual({ od: '2026-10-12', do: '2026-10-18' })
  })
  it('ten tydzien w poniedzialek zaczyna sie tego dnia', () => {
    expect(zakresOkresu('ten_tydzien', d(2026, 10, 12))).toEqual({ od: '2026-10-12', do: '2026-10-18' })
  })
  it('poprzedni tydzien', () => {
    expect(zakresOkresu('poprzedni_tydzien', DZIS)).toEqual({ od: '2026-10-05', do: '2026-10-11' })
  })
  it('tydzien przez granice miesiaca', () => {
    expect(zakresOkresu('ten_tydzien', d(2026, 11, 2))).toEqual({ od: '2026-11-02', do: '2026-11-08' })
    expect(zakresOkresu('poprzedni_tydzien', d(2026, 11, 2))).toEqual({ od: '2026-10-26', do: '2026-11-01' })
  })
  it('ten miesiac', () => {
    expect(zakresOkresu('ten_miesiac', DZIS)).toEqual({ od: '2026-10-01', do: '2026-10-31' })
  })
  it('poprzedni miesiac', () => {
    expect(zakresOkresu('poprzedni_miesiac', DZIS)).toEqual({ od: '2026-09-01', do: '2026-09-30' })
  })
  it('poprzedni miesiac w styczniu cofa sie na grudzien', () => {
    expect(zakresOkresu('poprzedni_miesiac', d(2027, 1, 10))).toEqual({ od: '2026-12-01', do: '2026-12-31' })
  })
  it('luty w roku nieprzestepnym i przestepnym', () => {
    expect(zakresOkresu('ten_miesiac', d(2027, 2, 10))).toEqual({ od: '2027-02-01', do: '2027-02-28' })
    expect(zakresOkresu('ten_miesiac', d(2028, 2, 10))).toEqual({ od: '2028-02-01', do: '2028-02-29' })
  })
  it('ten kwartal', () => {
    expect(zakresOkresu('ten_kwartal', DZIS)).toEqual({ od: '2026-10-01', do: '2026-12-31' })
    expect(zakresOkresu('ten_kwartal', d(2026, 2, 3))).toEqual({ od: '2026-01-01', do: '2026-03-31' })
  })
  it('poprzedni kwartal', () => {
    expect(zakresOkresu('poprzedni_kwartal', DZIS)).toEqual({ od: '2026-07-01', do: '2026-09-30' })
  })
  it('poprzedni kwartal w pierwszym kwartale to czwarty z poprzedniego roku', () => {
    expect(zakresOkresu('poprzedni_kwartal', d(2026, 2, 3))).toEqual({ od: '2025-10-01', do: '2025-12-31' })
  })
  it('ten rok', () => {
    expect(zakresOkresu('ten_rok', DZIS)).toEqual({ od: '2026-01-01', do: '2026-12-31' })
  })
  it('ostatnie 30 dni wlacznie z dzisiaj', () => {
    expect(zakresOkresu('ostatnie_30_dni', DZIS)).toEqual({ od: '2026-09-16', do: '2026-10-15' })
  })
  it('ostatnie 90 dni wlacznie z dzisiaj', () => {
    expect(zakresOkresu('ostatnie_90_dni', DZIS)).toEqual({ od: '2026-07-18', do: '2026-10-15' })
  })
  it('wlasny zwraca podane daty', () => {
    expect(zakresOkresu('wlasny', DZIS, '2026-09-15', '2026-10-15')).toEqual({
      od: '2026-09-15',
      do: '2026-10-15',
    })
  })
  it('wlasny dopuszcza ten sam dzien', () => {
    expect(zakresOkresu('wlasny', DZIS, '2026-09-15', '2026-09-15')).toEqual({
      od: '2026-09-15',
      do: '2026-09-15',
    })
  })
  it('wlasny z od > do jest niepoprawny', () => {
    expect(zakresOkresu('wlasny', DZIS, '2026-10-16', '2026-10-15')).toBeNull()
  })
  it('wlasny bez dat lub z bledna data jest niepoprawny', () => {
    expect(zakresOkresu('wlasny', DZIS)).toBeNull()
    expect(zakresOkresu('wlasny', DZIS, '2026-02-30', '2026-03-01')).toBeNull()
    expect(zakresOkresu('wlasny', DZIS, 'abc', '2026-03-01')).toBeNull()
  })
  it('nieznany preset daje null', () => {
    expect(zakresOkresu('zly', DZIS)).toBeNull()
  })
  it('godzina w dacie dzisiejszej nie zmienia wyniku', () => {
    expect(zakresOkresu('dzisiaj', new Date(2026, 9, 15, 23, 59))).toEqual({ od: '2026-10-15', do: '2026-10-15' })
  })
})

describe('daty i etykieta', () => {
  it('etykietaZakresu', () => {
    expect(etykietaZakresu('2026-09-15', '2026-10-15')).toBe('od 2026-09-15 do 2026-10-15')
  })
  it('etykieta nie zawiera myslnikow em ani en', () => {
    expect(etykietaZakresu('2026-09-15', '2026-10-15')).not.toMatch(new RegExp('[' + String.fromCharCode(0x2013, 0x2014) + ']'))
  })
  it('parsujDate i formatujDate sa odwrotne', () => {
    expect(formatujDate(parsujDate('2026-01-05'))).toBe('2026-01-05')
    expect(parsujDate('2026-13-01')).toBeNull()
    expect(parsujDate(null)).toBeNull()
  })
})

describe('okresDlaApi', () => {
  it('sklada wg z zakresem', () => {
    expect(okresDlaApi({ wg: 'wyplata', preset: 'ten_miesiac' }, DZIS)).toEqual({
      wg: 'wyplata',
      od: '2026-10-01',
      do: '2026-10-31',
    })
  })
  it('zwraca null dla niepoprawnego wyboru', () => {
    expect(okresDlaApi({ wg: 'wyplata', preset: 'wlasny' }, DZIS)).toBeNull()
    expect(okresDlaApi(null, DZIS)).toBeNull()
  })
  it('zwraca null celowo dla "wszystko"', () => {
    expect(okresDlaApi({ wg: 'podpisanie', preset: 'wszystko' }, DZIS)).toBeNull()
    expect(zakresOkresu('wszystko', DZIS)).toBeNull()
  })
})

describe('czyOkresGotowy', () => {
  it('true dla "wszystko" i poprawnych zakresow', () => {
    expect(czyOkresGotowy({ wg: 'podpisanie', preset: 'wszystko' }, DZIS)).toBe(true)
    expect(czyOkresGotowy({ wg: 'podpisanie', preset: 'ten_miesiac' }, DZIS)).toBe(true)
    expect(czyOkresGotowy({ wg: 'podpisanie', preset: 'wlasny', od: '2026-01-01', do: '2026-02-01' }, DZIS)).toBe(true)
  })
  it('false dla niepoprawnego wlasnego zakresu, nieznanego presetu i pustego wyboru', () => {
    expect(czyOkresGotowy({ wg: 'podpisanie', preset: 'wlasny' }, DZIS)).toBe(false)
    expect(czyOkresGotowy({ wg: 'podpisanie', preset: 'wlasny', od: '2026-05-01', do: '2026-04-01' }, DZIS)).toBe(false)
    expect(czyOkresGotowy({ wg: 'podpisanie', preset: 'zly' }, DZIS)).toBe(false)
    expect(czyOkresGotowy(null, DZIS)).toBe(false)
  })
})

describe('localStorage', () => {
  beforeEach(() => {
    const magazyn = {}
    vi.stubGlobal('localStorage', {
      getItem: (k) => (k in magazyn ? magazyn[k] : null),
      setItem: (k, v) => {
        magazyn[k] = String(v)
      },
    })
  })
  it('domyslnie wszystko wg podpisanie', () => {
    expect(DOMYSLNY_WYBOR).toEqual({ wg: 'podpisanie', preset: 'wszystko' })
    expect(odczytajWybor()).toEqual({ wg: 'podpisanie', preset: 'wszystko' })
  })
  it('klucz storage jest w wersji v2, stary klucz jest ignorowany', () => {
    expect(KLUCZ_STORAGE).toBe('volteo_rozliczenia_okres_v2')
    localStorage.setItem(
      'volteo_rozliczenia_okres',
      JSON.stringify({ wg: 'wyplata', preset: 'ten_miesiac' }),
    )
    expect(odczytajWybor()).toEqual({ wg: 'podpisanie', preset: 'wszystko' })
  })
  it('zapis i odczyt "wszystko" z osia termin', () => {
    zapiszWybor({ wg: 'termin', preset: 'wszystko' })
    expect(odczytajWybor()).toEqual({ wg: 'termin', preset: 'wszystko' })
  })
  it('zapis i odczyt', () => {
    zapiszWybor({ wg: 'wyplata', preset: 'ten_rok' })
    expect(odczytajWybor()).toEqual({ wg: 'wyplata', preset: 'ten_rok' })
  })
  it('zapis i odczyt wlasnego zakresu', () => {
    zapiszWybor({ wg: 'utworzenie', preset: 'wlasny', od: '2026-01-01', do: '2026-02-01' })
    expect(odczytajWybor()).toEqual({ wg: 'utworzenie', preset: 'wlasny', od: '2026-01-01', do: '2026-02-01' })
  })
  it('uszkodzony JSON daje domyslny', () => {
    localStorage.setItem(KLUCZ_STORAGE, '{zle')
    expect(odczytajWybor()).toEqual({ wg: 'podpisanie', preset: 'wszystko' })
  })
  it('nieznany preset lub wg daje domyslny', () => {
    localStorage.setItem(KLUCZ_STORAGE, JSON.stringify({ wg: 'x', preset: 'ten_rok' }))
    expect(odczytajWybor().wg).toBe('podpisanie')
    localStorage.setItem(KLUCZ_STORAGE, JSON.stringify({ wg: 'wyplata', preset: 'zly' }))
    expect(odczytajWybor().preset).toBe('wszystko')
  })
  it('wlasny z niepoprawnymi datami daje domyslny', () => {
    localStorage.setItem(KLUCZ_STORAGE, JSON.stringify({ wg: 'wyplata', preset: 'wlasny', od: '2026-05-01', do: '2026-04-01' }))
    expect(odczytajWybor()).toEqual({ wg: 'podpisanie', preset: 'wszystko' })
  })
  it('brak localStorage nie rzuca', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new Error('x')
      },
      setItem: () => {
        throw new Error('x')
      },
    })
    expect(() => zapiszWybor({ wg: 'wyplata', preset: 'ten_rok' })).not.toThrow()
    expect(odczytajWybor()).toEqual({ wg: 'podpisanie', preset: 'wszystko' })
  })
})
