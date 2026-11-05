import { describe, expect, it } from 'vitest'
import {
  LICZBA_KOLOROW,
  MAX_PX_NA_GODZINE,
  MIN_PX_NA_GODZINE,
  PROPORCJA_KARTY,
  czyJednaLinia,
  czyJednaLiniaBloku,
  dlugosciBlokowPion,
  DLUGOSC_SPOTKANIA_H,
  MIN_DLUGOSC_BLOKU_H,
  godzinyEtykietPion,
  pxNaGodzineZSzerokosci,
  OS_DO,
  OS_OD,
  MIN_SZEROKOSC_PASKA_PX,
  WYSOKOSC_NAGLOWKA_DNI_PX,
  etykietaChipa,
  godzinyEtykiet,
  liniePionowe,
  nazwisko,
  numerDnia,
  opisDymka,
  osWspolna,
  pozycjaBlokuPx,
  pozycjaGodzinyPct,
  skrotDnia,
  stylPaskaPoziomo,
  wymiaryTorow,
  wysokoscSiatkiPion,
  czyDzis,
  czyUmowiony,
  czyWeekend,
  dataTerminu,
  dniTygodnia,
  dodajDni,
  dzisIso,
  etykietaDnia,
  etykietaDniaKrotka,
  etykietaDniaZMiesiacem,
  etykietaUmowionych,
  etykietaZakresu,
  godzinaTekst,
  godzinaZKlikniecia,
  godzinaZKliknieciaPion,
  blokKlikniecia,
  blokKliknieciaPion,
  godzinyOsi,
  indeksDniaTygodnia,
  inicjaly,
  kluczStanu,
  kolorHandlowca,
  liczbaUmowionych,
  opcjeGodzin,
  opisSpotkania,
  osGodzin,
  podpowiedzDnia,
  pogrupujPoDniach,
  pozycjaBlokuPion,
  skalaPionowa,
  PX_NA_GODZINE_KOMPAKT,
  pozycjaPaska,
  pozycjaTeraz,
  przesunKotwice,
  rozbierzDate,
  rozbierzTermin,
  terminDoApi,
  wczytajStan,
  zakresTygodnia,
  zakresWidoku,
  zaokraglijDo30,
} from '@/utils/kalendarz'

const sp = (termin, extra = {}) => ({
  name: 'L1',
  lead_name: 'Jan Kowalski',
  termin,
  miasto: 'Poznań',
  status: 'Umówiony',
  ...extra,
})

describe('daty', () => {
  it('rozbierzDate poprawna i niepoprawna', () => {
    expect(rozbierzDate('2026-11-04')).toEqual({
      rok: 2026,
      miesiac: 11,
      dzien: 4,
    })
    expect(rozbierzDate('2026-02-30')).toBeNull()
    expect(rozbierzDate('04.11.2026')).toBeNull()
    expect(rozbierzDate(null)).toBeNull()
  })

  it('rozbierzDate akceptuje doklejoną godzinę', () => {
    expect(rozbierzDate('2026-11-04 10:30:00')).toEqual({
      rok: 2026,
      miesiac: 11,
      dzien: 4,
    })
  })

  it('rozbierzTermin tekstowo, bez przesunięcia strefy', () => {
    expect(rozbierzTermin('2026-09-10 17:00:00')).toMatchObject({
      godzina: 17,
      minuta: 0,
      dzien: 10,
    })
    expect(rozbierzTermin('2026-09-10T08:05')).toMatchObject({
      godzina: 8,
      minuta: 5,
    })
    expect(rozbierzTermin('2026-09-10 15:19:56.291762')).toMatchObject({
      godzina: 15,
      minuta: 19,
    })
  })

  it('rozbierzTermin odrzuca śmieci', () => {
    expect(rozbierzTermin('2026-09-10')).toBeNull()
    expect(rozbierzTermin('2026-09-10 25:00')).toBeNull()
    expect(rozbierzTermin(123)).toBeNull()
  })

  it('dataTerminu i godzinaTekst', () => {
    expect(dataTerminu('2026-09-10 17:30:00')).toBe('2026-09-10')
    expect(godzinaTekst('2026-09-10 07:05:00')).toBe('07:05')
    expect(dataTerminu('x')).toBe('')
    expect(godzinaTekst('x')).toBe('')
  })

  it('dodajDni przez granicę miesiąca i roku', () => {
    expect(dodajDni('2026-12-31', 1)).toBe('2027-01-01')
    expect(dodajDni('2026-03-01', -1)).toBe('2026-02-28')
    expect(dodajDni('2026-11-02', 7)).toBe('2026-11-09')
    expect(dodajDni('zle', 1)).toBe('')
  })

  it('indeksDniaTygodnia: poniedziałek 0, niedziela 6', () => {
    expect(indeksDniaTygodnia('2026-11-02')).toBe(0)
    expect(indeksDniaTygodnia('2026-11-08')).toBe(6)
    expect(indeksDniaTygodnia('zle')).toBe(-1)
  })

  it('czyWeekend', () => {
    expect(czyWeekend('2026-11-07')).toBe(true)
    expect(czyWeekend('2026-11-08')).toBe(true)
    expect(czyWeekend('2026-11-06')).toBe(false)
  })

  it('dzisIso i czyDzis', () => {
    const teraz = new Date(2026, 10, 4, 12, 0)
    expect(dzisIso(teraz)).toBe('2026-11-04')
    expect(czyDzis('2026-11-04', teraz)).toBe(true)
    expect(czyDzis('2026-11-05', teraz)).toBe(false)
  })
})

describe('zakresy i etykiety', () => {
  it('zakresTygodnia', () => {
    expect(zakresTygodnia('2026-11-04')).toEqual({
      od: '2026-11-02',
      do: '2026-11-08',
    })
    expect(zakresTygodnia('2026-11-08')).toEqual({
      od: '2026-11-02',
      do: '2026-11-08',
    })
    expect(zakresTygodnia('2026-12-31')).toEqual({
      od: '2026-12-28',
      do: '2027-01-03',
    })
    expect(zakresTygodnia('zle')).toEqual({ od: '', do: '' })
  })

  it('dniTygodnia daje 7 dat', () => {
    const dni = dniTygodnia('2026-11-02')
    expect(dni).toHaveLength(7)
    expect(dni[0]).toBe('2026-11-02')
    expect(dni[6]).toBe('2026-11-08')
    expect(dniTygodnia('zle')).toEqual([])
  })

  it('zakresWidoku i przesunKotwice', () => {
    expect(zakresWidoku('2026-11-04', 'tydzien')).toEqual({
      od: '2026-11-02',
      do: '2026-11-08',
    })
    expect(zakresWidoku('2026-11-04', 'dzien')).toEqual({
      od: '2026-11-04',
      do: '2026-11-04',
    })
    expect(przesunKotwice('2026-11-04', 'tydzien', 1)).toBe('2026-11-11')
    expect(przesunKotwice('2026-11-04', 'tydzien', -1)).toBe('2026-10-28')
    expect(przesunKotwice('2026-11-04', 'dzien', 1)).toBe('2026-11-05')
  })

  it('etykietaZakresu w jednym roku i przez przełom roku', () => {
    expect(etykietaZakresu('2026-11-02', '2026-11-08')).toBe(
      '2 lis do 8 lis 2026',
    )
    expect(etykietaZakresu('2026-12-28', '2027-01-03')).toBe(
      '28 gru 2026 do 3 sty 2027',
    )
    expect(etykietaZakresu('zle', '2026-11-08')).toBe('')
  })

  it('etykietaDnia po polsku', () => {
    expect(etykietaDnia('2026-11-02')).toBe('poniedziałek, 2 lis 2026')
    expect(etykietaDnia('2026-11-04')).toBe('środa, 4 lis 2026')
    expect(etykietaDnia('zle')).toBe('')
  })

  it('etykietaDniaKrotka i etykietaDniaZMiesiacem', () => {
    expect(etykietaDniaKrotka('2026-11-02')).toBe('pon. 2')
    expect(etykietaDniaZMiesiacem('2026-11-08')).toBe('niedz. 8 lis')
  })
})

describe('oś godzin i pozycje', () => {
  it('osGodzin domyślnie 8 do 22', () => {
    expect(osGodzin([sp('2026-11-02 10:00:00')])).toEqual({ od: 8, do: 22 })
    expect(osGodzin([])).toEqual({ od: 8, do: 22 })
    expect(OS_OD).toBe(8)
    expect(OS_DO).toBe(22)
  })

  it('osGodzin rozszerza się o spotkanie poza zakresem', () => {
    expect(osGodzin([sp('2026-11-02 06:30:00')])).toEqual({ od: 6, do: 22 })
    expect(osGodzin([sp('2026-11-02 17:30:00')])).toEqual({ od: 8, do: 22 })
    expect(osGodzin([sp('2026-11-02 21:00:00')])).toEqual({ od: 8, do: 23 })
  })

  it('osGodzin ignoruje spotkania bez poprawnego terminu', () => {
    expect(osGodzin([sp(null), sp('zle')])).toEqual({ od: 8, do: 22 })
  })

  it('godzinyOsi', () => {
    expect(godzinyOsi(8, 11)).toEqual([8, 9, 10, 11])
  })

  it('pozycjaPaska od pełnej godziny', () => {
    const p = pozycjaPaska('2026-11-02 08:00:00')
    expect(p.leftPct).toBe(0)
    expect(p.widthPct).toBeCloseTo((2 / 14) * 100, 5)
  })

  it('pozycjaPaska w środku osi', () => {
    const p = pozycjaPaska('2026-11-02 13:00:00')
    expect(p.leftPct).toBeCloseTo((5 / 14) * 100, 5)
    expect(p.widthPct).toBeCloseTo((2 / 14) * 100, 5)
  })

  it('pozycjaPaska przycina do prawego brzegu', () => {
    const p = pozycjaPaska('2026-11-02 21:30:00')
    expect(p.leftPct + p.widthPct).toBeLessThanOrEqual(100.0000001)
  })

  it('pozycjaPaska przed początkiem osi zaczyna od 0', () => {
    expect(pozycjaPaska('2026-11-02 06:00:00').leftPct).toBe(0)
  })

  it('pozycjaPaska dla niepoprawnego terminu', () => {
    expect(pozycjaPaska('zle')).toEqual({ leftPct: 0, widthPct: 0 })
  })

  it('pozycjaBlokuPion', () => {
    expect(pozycjaBlokuPion('2026-11-02 10:30:00')).toEqual({
      topPx: 2.5 * 36,
      heightPx: 2 * 36,
    })
    expect(pozycjaBlokuPion('zle')).toEqual({ topPx: 0, heightPx: 0 })
  })

  it('skalaPionowa: pełna i kompaktowa', () => {
    expect(skalaPionowa(false)).toBe(36)
    // 14 godzin osi 8 do 22 mieści się bez przewijania na 900 px wysokości
    expect(14 * skalaPionowa(false)).toBeLessThan(600)
    expect(skalaPionowa(true)).toBe(PX_NA_GODZINE_KOMPAKT)
    expect(PX_NA_GODZINE_KOMPAKT).toBe(27)
  })

  it('pozycjaBlokuPion i klik w skali kompaktowej', () => {
    const k = PX_NA_GODZINE_KOMPAKT
    expect(pozycjaBlokuPion('2026-11-02 10:00:00', 8, k)).toEqual({
      topPx: 2 * k,
      heightPx: 2 * k,
    })
    expect(godzinaZKliknieciaPion(k, 8, 18, k)).toBe('09:00')
    expect(godzinaZKliknieciaPion(2.5 * k, 8, 18, k)).toBe('10:30')
  })

  it('blokKlikniecia zgadza sie z godzinaZKlikniecia na granicach', () => {
    const w = 100 / 14
    for (const x of [0, 1, w / 4, w / 2, w, 1.5 * w, 50, 99, 100]) {
      expect(blokKlikniecia(x).godzina).toBe(godzinaZKlikniecia(x))
    }
    const pierwszy = blokKlikniecia(0)
    expect(pierwszy.godzina).toBe('08:00')
    expect(pierwszy.left).toBe('0%')
    expect(parseFloat(pierwszy.width)).toBeCloseTo((0.5 / 14) * 100, 8)
    const ost = blokKlikniecia(100)
    expect(ost.godzina).toBe('21:30')
    expect(parseFloat(ost.left) + parseFloat(ost.width)).toBeCloseTo(100, 8)
    const b = blokKlikniecia((0.5 / 14) * 100)
    expect(b.godzina).toBe('08:30')
    expect(parseFloat(b.left)).toBeCloseTo((0.5 / 14) * 100, 8)
  })

  it('blokKliknieciaPion zgadza sie z godzinaZKliknieciaPion', () => {
    const k = PX_NA_GODZINE_KOMPAKT
    for (const y of [-5, 0, k / 4, k / 2, k, 1.5 * k, 13.9 * k, 20 * k]) {
      expect(blokKliknieciaPion(y, 8, 22, k).godzina).toBe(
        godzinaZKliknieciaPion(y, 8, 22, k),
      )
    }
    const p = blokKliknieciaPion(0, 8, 22, k)
    expect(p.godzina).toBe('08:00')
    expect(p.top).toBe('0px')
    expect(p.height).toBe(`${0.5 * k}px`)
    const ost = blokKliknieciaPion(20 * k, 8, 22, k)
    expect(ost.godzina).toBe('21:30')
    expect(ost.top).toBe(`${13.5 * k}px`)
    expect(blokKliknieciaPion(0.5 * k, 8, 22, k).godzina).toBe('08:30')
  })

  it('pozycjaTeraz w osi i poza nią', () => {
    expect(pozycjaTeraz(new Date(2026, 10, 2, 13, 0))).toBeCloseTo(
      (5 / 14) * 100,
      5,
    )
    expect(pozycjaTeraz(new Date(2026, 10, 2, 7, 59))).toBeNull()
    expect(pozycjaTeraz(new Date(2026, 10, 2, 22, 30))).toBeNull()
  })
})

describe('kliknięcia', () => {
  it('zaokraglijDo30', () => {
    expect(zaokraglijDo30(0)).toBe(0)
    expect(zaokraglijDo30(14)).toBe(0)
    expect(zaokraglijDo30(15)).toBe(30)
    expect(zaokraglijDo30(44)).toBe(30)
    expect(zaokraglijDo30(46)).toBe(60)
  })

  it('godzinaZKlikniecia środek i brzegi', () => {
    expect(godzinaZKlikniecia(0)).toBe('08:00')
    expect(godzinaZKlikniecia(50)).toBe('15:00')
    expect(godzinaZKlikniecia(100)).toBe('21:30')
    expect(godzinaZKlikniecia(-20)).toBe('08:00')
    expect(godzinaZKlikniecia(150)).toBe('21:30')
  })

  it('godzinaZKlikniecia zaokrągla do 30 minut', () => {
    // 8 + 0.08 * 14 = 9.12 h => 9:07 => 9:00 ; 8 + 0.10 * 14 = 9.4 h => 9:24 => 9:30
    expect(godzinaZKlikniecia(8)).toBe('09:00')
    expect(godzinaZKlikniecia(10)).toBe('09:30')
  })

  it('godzinaZKliknieciaPion', () => {
    expect(godzinaZKliknieciaPion(0)).toBe('08:00')
    expect(godzinaZKliknieciaPion(36)).toBe('09:00')
    expect(godzinaZKliknieciaPion(36 * 1.5)).toBe('09:30')
    expect(godzinaZKliknieciaPion(9999)).toBe('21:30')
  })

  it('opcjeGodzin i terminDoApi', () => {
    const o = opcjeGodzin()
    expect(o[0]).toBe('06:00')
    expect(o[o.length - 1]).toBe('22:00')
    expect(o).toContain('13:30')
    expect(terminDoApi('2026-11-04', '10:30')).toBe('2026-11-04 10:30:00')
    expect(terminDoApi('2026-11-04', '')).toBe('')
    expect(terminDoApi('zle', '10:30')).toBe('')
  })
})

describe('kolory, inicjały, statusy', () => {
  it('kolorHandlowca cyklicznie, ze stałą paletą', () => {
    expect(kolorHandlowca(0)).toEqual(kolorHandlowca(LICZBA_KOLOROW))
    expect(kolorHandlowca(0)).not.toEqual(kolorHandlowca(1))
    expect(kolorHandlowca(-1)).toEqual(kolorHandlowca(0))
    expect(kolorHandlowca('x')).toEqual(kolorHandlowca(0))
  })

  it('paleta używa wyłącznie istniejących tokenów motywu', () => {
    for (let i = 0; i < LICZBA_KOLOROW; i += 1) {
      const k = kolorHandlowca(i)
      const wszystkie = Object.values(k).join(' ')
      expect(wszystkie).not.toMatch(/rose|emerald|sky|lime/)
      expect(k.pelny).toMatch(/^bg-surface-[a-z]+-\d+$/)
      expect(k.tekst).toMatch(/^text-ink-[a-z]+-\d+$/)
    }
  })

  it('inicjaly', () => {
    expect(inicjaly('Jan Kowalski')).toBe('JK')
    expect(inicjaly('anna maria nowak')).toBe('AN')
    expect(inicjaly('Jan')).toBe('J')
    expect(inicjaly('')).toBe('')
    expect(inicjaly(null)).toBe('')
    expect(inicjaly('Łukasz Żak')).toBe('ŁŻ')
  })

  it('czyUmowiony i liczbaUmowionych', () => {
    expect(czyUmowiony('Umówiony')).toBe(true)
    expect(czyUmowiony('Nowy')).toBe(false)
    expect(
      liczbaUmowionych([sp('a'), sp('b', { status: 'Nowy' }), sp('c')]),
    ).toBe(2)
    expect(liczbaUmowionych(null)).toBe(0)
  })

  it('etykietaUmowionych', () => {
    expect(etykietaUmowionych(0)).toBe('0 umówionych')
    expect(etykietaUmowionych(1)).toBe('1 umówione')
    expect(etykietaUmowionych(3)).toBe('3 umówione')
    expect(etykietaUmowionych(5)).toBe('5 umówionych')
    expect(etykietaUmowionych(12)).toBe('12 umówionych')
    expect(etykietaUmowionych(22)).toBe('22 umówione')
  })
})

describe('grupowanie i opisy', () => {
  it('pogrupujPoDniach sortuje w dniu', () => {
    const lista = [
      sp('2026-11-03 12:00:00', { name: 'B' }),
      sp('2026-11-03 09:00:00', { name: 'A' }),
      sp('2026-11-02 10:00:00', { name: 'C' }),
      sp(null, { name: 'X' }),
    ]
    const g = pogrupujPoDniach(lista)
    expect(Object.keys(g).sort()).toEqual(['2026-11-02', '2026-11-03'])
    expect(g['2026-11-03'].map((s) => s.name)).toEqual(['A', 'B'])
  })

  it('pogrupujPoDniach nie mutuje wejścia i toleruje null', () => {
    const lista = [sp('2026-11-03 12:00:00'), sp('2026-11-03 09:00:00')]
    const kopia = [...lista]
    pogrupujPoDniach(lista)
    expect(lista).toEqual(kopia)
    expect(pogrupujPoDniach(null)).toEqual({})
  })

  it('opisSpotkania', () => {
    expect(opisSpotkania(sp('2026-11-02 10:00:00'))).toBe(
      '10:00 Jan Kowalski, Poznań',
    )
    expect(opisSpotkania(sp('2026-11-02 10:00:00', { miasto: null }))).toBe(
      '10:00 Jan Kowalski',
    )
  })

  it('podpowiedzDnia', () => {
    const lista = [
      sp('2026-11-02 13:30:00'),
      sp('2026-11-02 10:00:00'),
      sp('2026-11-03 10:00:00'),
    ]
    expect(podpowiedzDnia('Anna', lista, '2026-11-02')).toBe(
      'Anna ma tego dnia 2 spotkania: 10:00, 13:30',
    )
    expect(podpowiedzDnia('Anna', lista, '2026-11-03')).toBe(
      'Anna ma tego dnia 1 spotkanie: 10:00',
    )
    expect(podpowiedzDnia('Anna', lista, '2026-11-09')).toBe('')
  })
})

describe('stan w localStorage', () => {
  it('kluczStanu', () => {
    expect(kluczStanu('a@x.pl')).toBe('volteo_kalendarz:a@x.pl')
  })

  it('wczytajStan domyślny zależny od zakresu', () => {
    expect(wczytajStan(null, 'wszyscy')).toMatchObject({
      tryb: 'tablica',
      orientacja: 'poziomo',
      widok: 'tydzien',
    })
    expect(wczytajStan(null, 'wlasny').orientacja).toBe('pionowo')
  })

  it('wczytajStan odtwarza poprawny stan', () => {
    const s = wczytajStan(
      JSON.stringify({
        widok: 'dzien',
        tryb: 'jeden',
        orientacja: 'pionowo',
        handlowiec: 'a@x.pl',
        filtr: ['a@x.pl'],
      }),
      'wszyscy',
    )
    expect(s).toEqual({
      widok: 'dzien',
      tryb: 'jeden',
      orientacja: 'pionowo',
      handlowiec: 'a@x.pl',
      filtr: ['a@x.pl'],
    })
  })

  it('wczytajStan odrzuca śmieci i uszkodzony JSON', () => {
    expect(wczytajStan('{nie json', 'wszyscy').tryb).toBe('tablica')
    const s = wczytajStan(
      JSON.stringify({ widok: 'rok', tryb: 5, filtr: 'x', handlowiec: 3 }),
      'wszyscy',
    )
    expect(s).toMatchObject({
      widok: 'tydzien',
      tryb: 'tablica',
      handlowiec: '',
      filtr: [],
    })
  })
})

describe('runda UI: oś wspólna, ścieżki, etykiety, dymek', () => {
  it('osWspolna rozszerza oś o spotkania wszystkich handlowców', () => {
    const mapa = {
      a: [sp('2026-11-02 10:00:00')],
      b: [sp('2026-11-02 06:30:00')],
      c: [sp('2026-11-02 22:00:00')],
    }
    expect(osWspolna(mapa, ['a'])).toEqual({ od: 8, do: 22 })
    expect(osWspolna(mapa, ['a', 'b'])).toEqual({ od: 6, do: 22 })
    expect(osWspolna(mapa, ['a', 'b', 'c'])).toEqual({ od: 6, do: 24 })
    expect(osWspolna(mapa, [])).toEqual({ od: 8, do: 22 })
    expect(osWspolna(null, ['x'])).toEqual({ od: 8, do: 22 })
  })

  it('etykietaChipa: tylko liczba umówionych, bez do potwierdzenia', () => {
    expect(etykietaChipa([])).toEqual({
      tekst: 'wolny cały tydzień',
      wolny: true,
    })
    expect(etykietaChipa([], 'dzien')).toEqual({
      tekst: 'wolny cały dzień',
      wolny: true,
    })
    expect(etykietaChipa([sp('a')])).toEqual({
      tekst: '1 umówione',
      wolny: false,
    })
    expect(etykietaChipa([sp('a'), sp('b'), sp('c')])).toEqual({
      tekst: '3 umówione',
      wolny: false,
    })
    expect(etykietaChipa([sp('a'), sp('b', { status: 'Nowy' })]).tekst).toBe(
      '1 umówione',
    )
    expect(
      etykietaChipa(Array.from({ length: 5 }, (_, i) => sp(String(i)))).tekst,
    ).toBe('5 umówionych')
    expect(
      etykietaChipa(Array.from({ length: 12 }, (_, i) => sp(String(i)))).tekst,
    ).toBe('12 umówionych')
    expect(etykietaChipa([sp('a', { status: 'Nowy' })])).toEqual({
      tekst: '0 umówionych',
      wolny: true,
    })
    expect(
      etykietaChipa([sp('a'), sp('b', { status: 'Nowy' })]).tekst,
    ).not.toMatch(/potwierdzenia/)
  })

  it('wymiaryTorow: duży 32/7, kompakt 22/5, kolumna dni 58', () => {
    expect(wymiaryTorow(true)).toEqual({
      sciezkaPx: 32,
      odstepPx: 7,
      kolumnaDniPx: 58,
    })
    expect(wymiaryTorow(false)).toEqual({
      sciezkaPx: 22,
      odstepPx: 5,
      kolumnaDniPx: 58,
    })
  })

  it('nazwisko to ostatni człon, skrotDnia bez kropki, numerDnia', () => {
    expect(nazwisko('Jan Maria Kowalski')).toBe('Kowalski')
    expect(nazwisko('Kowalski')).toBe('Kowalski')
    expect(nazwisko('')).toBe('')
    expect(nazwisko(null)).toBe('')
    expect(skrotDnia('2026-11-02')).toBe('pon')
    expect(skrotDnia('2026-11-08')).toBe('niedz')
    expect(skrotDnia('zle')).toBe('')
    expect(numerDnia('2026-11-02')).toBe('2')
    expect(numerDnia('zle')).toBe('')
  })

  it('pozycjaGodzinyPct i etykiety godzin z ostatnią', () => {
    expect(pozycjaGodzinyPct(8, 8, 18)).toBe(0)
    expect(pozycjaGodzinyPct(13, 8, 18)).toBe(50)
    expect(pozycjaGodzinyPct(18, 8, 18)).toBe(100)
    expect(pozycjaGodzinyPct(8, 8, 8)).toBe(0)
    expect(godzinyEtykiet(8, 12, 1)).toEqual([8, 9, 10, 11, 12])
    expect(godzinyEtykiet(8, 18, 2)).toEqual([8, 10, 12, 14, 16, 18])
    expect(godzinyEtykiet(8, 19, 2)).toEqual([8, 10, 12, 14, 16, 18, 19])
  })

  it('liniePionowe co 2 godziny, tylko wewnątrz osi', () => {
    expect(liniePionowe(8, 18)).toEqual([10, 12, 14, 16])
    expect(liniePionowe(8, 19)).toEqual([10, 12, 14, 16, 18])
    expect(liniePionowe(8, 9)).toEqual([])
  })

  it('stylPaskaPoziomo ma minimalną szerokość i nie wychodzi poza prawy brzeg', () => {
    const st = stylPaskaPoziomo('2026-11-02 17:30:00', 8, 19)
    expect(st.minWidth).toBe(MIN_SZEROKOSC_PASKA_PX + 'px')
    expect(st.left).toMatch(/^min\(.*%, calc\(100% - 44px\)\)$/)
    expect(st.width).toMatch(/%$/)
    expect(MIN_SZEROKOSC_PASKA_PX).toBe(44)
  })

  it('wysokoscSiatkiPion nie zawiera nagłówka dni, pozycjaBlokuPx w tym samym układzie', () => {
    expect(wysokoscSiatkiPion(8, 18, 48)).toBe(480)
    expect(wysokoscSiatkiPion(8, 18, 30)).toBe(300)
    expect(WYSOKOSC_NAGLOWKA_DNI_PX).toBe(28)
    // 10:00 przy osi od 8 i 48 px/h = 96 px od pierwszej linii, bez offsetu nagłówka
    expect(pozycjaBlokuPx('2026-11-02 10:00:00', 8, 48).topPx).toBe(96)
    expect(pozycjaBlokuPx('2026-11-02 08:00:00', 8, 48).topPx).toBe(0)
  })

  it('opisDymka daje trzy linie', () => {
    const d = opisDymka(sp('2026-11-03 10:00:00', { telefon: '600 100 200' }))
    expect(d.linia1).toBe('10:00, wtorek 3 lis 2026')
    expect(d.linia2).toBe('Jan Kowalski, Poznań')
    expect(d.linia3).toBe('Umówiony, 600 100 200')
    expect(opisDymka(sp('2026-11-03 10:00:00', { miasto: null })).linia2).toBe(
      'Jan Kowalski',
    )
    expect(opisDymka({ termin: 'zle' }).linia1).toBe('')
  })
})

describe('proporcje karty pionowej 16:9', () => {
  it('stałe: proporcja 9/16, zakres 14 do 36', () => {
    expect(PROPORCJA_KARTY).toBeCloseTo(0.5625, 6)
    expect(MIN_PX_NA_GODZINE).toBe(14)
    expect(MAX_PX_NA_GODZINE).toBe(36)
  })

  it('karta kompaktowa na tablicy (585 px, nagłówek 48 + 12) dostaje małą skalę', () => {
    // 585 * 9/16 = 329; 329 - 30 - 60 - 28 - 8 = 203; 203 / 14 = 14,5
    expect(pxNaGodzineZSzerokosci(585, 14, { naglowekKarty: 60 })).toBe(14)
  })

  it('karta duża bez nagłówka (1190 px) dostaje maksimum', () => {
    // 1190 * 9/16 = 669; 669 - 66 = 603; 603 / 14 = 43 => max 36
    expect(pxNaGodzineZSzerokosci(1190, 14)).toBe(36)
  })

  it('wartość środkowa jest liczona z proporcji i zaokrąglana w dół', () => {
    // 800 * 9/16 = 450; 450 - 30 - 28 - 8 = 384; 384 / 14 = 27,4 => 27
    expect(pxNaGodzineZSzerokosci(800, 14)).toBe(27)
  })

  it('wysokość karty wychodzi bliska 16:9 w zakresie bez obcięcia', () => {
    const px = pxNaGodzineZSzerokosci(800, 14)
    const wysokosc = 30 + 28 + 14 * px + 8
    expect(Math.abs(wysokosc / 800 - PROPORCJA_KARTY)).toBeLessThan(0.02)
  })

  it('wąska karta nie schodzi poniżej minimum', () => {
    expect(pxNaGodzineZSzerokosci(200, 14, { naglowekKarty: 60 })).toBe(14)
  })

  it('niepoprawne wejście daje maksimum', () => {
    expect(pxNaGodzineZSzerokosci(0, 14)).toBe(36)
    expect(pxNaGodzineZSzerokosci(800, 0)).toBe(36)
    expect(pxNaGodzineZSzerokosci(NaN, 14)).toBe(36)
  })

  it('czyJednaLinia poniżej 24 px/h', () => {
    expect(czyJednaLinia(14)).toBe(true)
    expect(czyJednaLinia(23)).toBe(true)
    expect(czyJednaLinia(24)).toBe(false)
    expect(czyJednaLinia(36)).toBe(false)
  })

  it('godzinyEtykietPion: co 2 h poniżej 20 px/h, inaczej wszystkie', () => {
    expect(godzinyEtykietPion(8, 12, 19)).toEqual([8, 10, 12])
    expect(godzinyEtykietPion(8, 12, 20)).toEqual([8, 9, 10, 11, 12])
    expect(godzinyEtykietPion(8, 22, 14)).toEqual([
      8, 10, 12, 14, 16, 18, 20, 22,
    ])
  })
})

describe('domyślna długość spotkania 2 h i nakładanie spotkań', () => {
  const w = (name, termin) => ({ name, termin })

  it('stała długość to 2 h, szerokość paska i wysokość bloku z niej wynikają', () => {
    expect(DLUGOSC_SPOTKANIA_H).toBe(2)
    expect(pozycjaPaska('2026-11-02 10:00:00', 8, 22).widthPct).toBeCloseTo(
      (2 / 14) * 100,
      6,
    )
    expect(pozycjaBlokuPx('2026-11-02 10:00:00', 8, 36).heightPx).toBe(72)
  })

  it('oś rozszerza się o koniec spotkania liczony po 2 h', () => {
    expect(osGodzin([w('a', '2026-11-02 21:00:00')]).do).toBe(23)
    expect(osGodzin([w('a', '2026-11-02 20:00:00')]).do).toBe(22)
  })

  it('dlugosciBlokowPion: bez nakładania pełne 2 h', () => {
    const d = dlugosciBlokowPion([
      w('a', '2026-11-02 08:00:00'),
      w('b', '2026-11-02 12:00:00'),
    ])
    expect(d).toEqual({ a: 2, b: 2 })
  })

  it('dlugosciBlokowPion: wcześniejszy blok skracany do początku następnego', () => {
    // 09:30 i 11:00: odstęp 1,5 h < 2 h
    const d = dlugosciBlokowPion([
      w('b', '2026-11-02 11:00:00'),
      w('a', '2026-11-02 09:30:00'),
    ])
    expect(d).toEqual({ a: 1.5, b: 2 })
  })

  it('dlugosciBlokowPion: łańcuch nakładających się i minimum', () => {
    const d = dlugosciBlokowPion([
      w('a', '2026-11-02 09:00:00'),
      w('b', '2026-11-02 09:15:00'),
      w('c', '2026-11-02 09:15:00'),
      w('d', '2026-11-02 10:00:00'),
    ])
    expect(d.a).toBe(MIN_DLUGOSC_BLOKU_H)
    expect(d.b).toBe(MIN_DLUGOSC_BLOKU_H)
    expect(d.c).toBe(0.75)
    expect(d.d).toBe(2)
  })

  it('dlugosciBlokowPion: pusta lista i spotkania bez poprawnego terminu', () => {
    expect(dlugosciBlokowPion([])).toEqual({})
    expect(dlugosciBlokowPion(null)).toEqual({})
    expect(dlugosciBlokowPion([w('x', 'zle')])).toEqual({})
  })

  it('czyJednaLiniaBloku: mała skala albo krótki blok', () => {
    expect(czyJednaLiniaBloku(36, 2)).toBe(false)
    expect(czyJednaLiniaBloku(36, 0.5)).toBe(true)
    expect(czyJednaLiniaBloku(20, 2)).toBe(true)
    expect(czyJednaLiniaBloku(14, 2)).toBe(true)
  })
})
