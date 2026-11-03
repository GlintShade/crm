import { describe, expect, it } from 'vitest'
import {
  SZABLONY_GRAFIKU,
  czyDostepnyW,
  czyPozaGrafikiem,
  godzinaNaLiczbe,
  godzinyZOkien,
  oknaDnia,
  oknaZGodzin,
  odcinkiNiedostepne,
  opisOkien,
  ostrzezenieGrafiku,
  posortujWgDostepnosci,
  stylOdcinkaPion,
  stylOdcinkaPoziomo,
} from '@/utils/kalendarz'

const KAMIL = {
  '2026-11-02': [[0, 24]],
  '2026-11-05': [],
  '2026-11-06': [
    [8, 12],
    [14, 22],
  ],
  '2026-11-07': null,
}

describe('oknaDnia', () => {
  it('zwraca okna dnia', () => {
    expect(oknaDnia(KAMIL, '2026-11-02')).toEqual([[0, 24]])
    expect(oknaDnia(KAMIL, '2026-11-05')).toEqual([])
  })
  it('null dla braku grafiku dnia, handlowca i nieznanej daty', () => {
    expect(oknaDnia(KAMIL, '2026-11-07')).toBeNull()
    expect(oknaDnia(KAMIL, '2026-12-01')).toBeNull()
    expect(oknaDnia(null, '2026-11-02')).toBeNull()
    expect(oknaDnia(undefined, '2026-11-02')).toBeNull()
  })
})

describe('czyDostepnyW', () => {
  it('brak grafiku = dostępny', () => {
    expect(czyDostepnyW(null, 10)).toBe(true)
  })
  it('wolne = niedostępny', () => {
    expect(czyDostepnyW([], 10)).toBe(false)
  })
  it('całe 2 h w jednym oknie', () => {
    expect(czyDostepnyW([[8, 14]], 12)).toBe(true)
    expect(czyDostepnyW([[8, 14]], 12.5)).toBe(false)
    expect(czyDostepnyW([[8, 14]], 7.5)).toBe(false)
  })
  it('przerwa między oknami przerywa spotkanie', () => {
    expect(
      czyDostepnyW(
        [
          [8, 12],
          [14, 22],
        ],
        11,
      ),
    ).toBe(false)
    expect(
      czyDostepnyW(
        [
          [8, 12],
          [14, 22],
        ],
        14,
      ),
    ).toBe(true)
  })
  it('własna długość', () => {
    expect(czyDostepnyW([[8, 9]], 8, 1)).toBe(true)
  })
})

describe('odcinkiNiedostepne', () => {
  it('brak grafiku = brak cienia', () => {
    expect(odcinkiNiedostepne(null, 8, 22)).toEqual([])
  })
  it('wolne = cała oś', () => {
    expect(odcinkiNiedostepne([], 8, 22)).toEqual([[8, 22]])
  })
  it('cały dzień = brak cienia', () => {
    expect(odcinkiNiedostepne([[0, 24]], 8, 22)).toEqual([])
  })
  it('popołudnie', () => {
    expect(odcinkiNiedostepne([[14, 22]], 8, 22)).toEqual([[8, 14]])
  })
  it('dwa okna z przerwą', () => {
    expect(
      odcinkiNiedostepne(
        [
          [14, 18],
          [9, 12],
        ],
        8,
        22,
      ),
    ).toEqual([
      [8, 9],
      [12, 14],
      [18, 22],
    ])
  })
  it('okno wychodzące poza oś', () => {
    expect(odcinkiNiedostepne([[6, 10]], 8, 22)).toEqual([[10, 22]])
    expect(odcinkiNiedostepne([[20, 24]], 8, 22)).toEqual([[8, 20]])
    expect(odcinkiNiedostepne([[23, 24]], 8, 22)).toEqual([[8, 22]])
  })
})

describe('style odcinków', () => {
  it('poziomo w procentach osi', () => {
    expect(stylOdcinkaPoziomo(8, 15, 8, 22)).toEqual({
      left: '0%',
      width: '50%',
    })
  })
  it('pionowo w pikselach', () => {
    expect(stylOdcinkaPion(10, 12, 8, 30)).toEqual({
      top: '60px',
      height: '60px',
    })
  })
})

describe('czyPozaGrafikiem', () => {
  it('spotkanie w dniu wolnym', () => {
    expect(czyPozaGrafikiem({ termin: '2026-11-05 10:00:00' }, KAMIL)).toBe(
      true,
    )
  })
  it('spotkanie w oknie', () => {
    expect(czyPozaGrafikiem({ termin: '2026-11-06 15:00:00' }, KAMIL)).toBe(
      false,
    )
  })
  it('brak grafiku albo terminu = bez obwódki', () => {
    expect(czyPozaGrafikiem({ termin: '2026-11-05 10:00:00' }, null)).toBe(
      false,
    )
    expect(czyPozaGrafikiem({ termin: null }, KAMIL)).toBe(false)
  })
})

describe('opisOkien', () => {
  it('opisuje stany dnia', () => {
    expect(opisOkien(null)).toBe('brak grafiku')
    expect(opisOkien([])).toBe('wolne')
    expect(opisOkien([[0, 24]])).toBe('cały dzień')
    expect(
      opisOkien([
        [8, 12],
        [14, 18],
      ]),
    ).toBe('8 do 12, 14 do 18')
  })
})

describe('godzinyZOkien i oknaZGodzin', () => {
  it('w obie strony', () => {
    const okna = [
      [8, 12],
      [14, 22],
    ]
    expect(oknaZGodzin(godzinyZOkien(okna))).toEqual(okna)
  })
  it('cały dzień i wolne', () => {
    expect(oknaZGodzin(godzinyZOkien([[0, 24]]))).toEqual([[0, 24]])
    expect(oknaZGodzin(godzinyZOkien([]))).toEqual([])
    expect(godzinyZOkien(null).every((v) => v === false)).toBe(true)
  })
  it('szablony są poprawnymi oknami', () => {
    for (const okna of Object.values(SZABLONY_GRAFIKU)) {
      expect(oknaZGodzin(godzinyZOkien(okna))).toEqual(okna)
    }
  })
})

describe('godzinaNaLiczbe', () => {
  it('parsuje HH:MM', () => {
    expect(godzinaNaLiczbe('10:30')).toBe(10.5)
    expect(godzinaNaLiczbe('8:00')).toBe(8)
    expect(godzinaNaLiczbe('')).toBeNull()
    expect(godzinaNaLiczbe('dziesiąta')).toBeNull()
  })
})

describe('posortujWgDostepnosci', () => {
  const handlowcy = [
    { user: 'kamil', full_name: 'Kamil' },
    { user: 'pawel', full_name: 'Paweł' },
    { user: 'tomasz', full_name: 'Tomasz' },
  ]
  const dost = {
    kamil: { '2026-11-05': [] },
    pawel: { '2026-11-05': [[14, 22]] },
    tomasz: null,
  }
  it('dostępni na górze, kolejność w grupach zachowana', () => {
    const wynik = posortujWgDostepnosci(handlowcy, dost, '2026-11-05', '15:00')
    expect(wynik.map((h) => [h.user, h.dostepny])).toEqual([
      ['pawel', true],
      ['tomasz', true],
      ['kamil', false],
    ])
  })
  it('bez danych grafiku bez zmian', () => {
    const wynik = posortujWgDostepnosci(handlowcy, null, '2026-11-05', '15:00')
    expect(wynik.map((h) => h.user)).toEqual(['kamil', 'pawel', 'tomasz'])
    expect(wynik.every((h) => h.dostepny)).toBe(true)
  })
})

describe('ostrzezenieGrafiku', () => {
  it('pusty w oknie i bez grafiku', () => {
    expect(
      ostrzezenieGrafiku(
        'Kamil',
        { '2026-11-02': [[0, 24]] },
        '2026-11-02',
        '10:00',
      ),
    ).toBe('')
    expect(ostrzezenieGrafiku('Kamil', null, '2026-11-02', '10:00')).toBe('')
  })
  it('dzień wolny', () => {
    expect(
      ostrzezenieGrafiku('Kamil', { '2026-11-05': [] }, '2026-11-05', '10:00'),
    ).toContain('ma wolne')
  })
  it('poza oknem', () => {
    const t = ostrzezenieGrafiku(
      'Paweł',
      { '2026-11-05': [[14, 22]] },
      '2026-11-05',
      '10:00',
    )
    expect(t).toContain('jest dostępny 14 do 22')
  })
})
