import { describe, expect, it } from 'vitest'
import {
  LICZBA_KOLOROW,
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
  it('osGodzin domyślnie 8 do 18', () => {
    expect(osGodzin([sp('2026-11-02 10:00:00')])).toEqual({ od: 8, do: 18 })
    expect(osGodzin([])).toEqual({ od: 8, do: 18 })
  })

  it('osGodzin rozszerza się o spotkanie poza zakresem', () => {
    expect(osGodzin([sp('2026-11-02 06:30:00')])).toEqual({ od: 6, do: 18 })
    expect(osGodzin([sp('2026-11-02 17:30:00')])).toEqual({ od: 8, do: 19 })
    expect(osGodzin([sp('2026-11-02 20:00:00')])).toEqual({ od: 8, do: 22 })
  })

  it('osGodzin ignoruje spotkania bez poprawnego terminu', () => {
    expect(osGodzin([sp(null), sp('zle')])).toEqual({ od: 8, do: 18 })
  })

  it('godzinyOsi', () => {
    expect(godzinyOsi(8, 11)).toEqual([8, 9, 10, 11])
  })

  it('pozycjaPaska od pełnej godziny', () => {
    const p = pozycjaPaska('2026-11-02 08:00:00')
    expect(p.leftPct).toBe(0)
    expect(p.widthPct).toBeCloseTo(15, 5)
  })

  it('pozycjaPaska w środku osi', () => {
    const p = pozycjaPaska('2026-11-02 13:00:00')
    expect(p.leftPct).toBeCloseTo(50, 5)
    expect(p.widthPct).toBeCloseTo(15, 5)
  })

  it('pozycjaPaska przycina do prawego brzegu', () => {
    const p = pozycjaPaska('2026-11-02 17:30:00')
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
      topPx: 2.5 * 48,
      heightPx: 72,
    })
    expect(pozycjaBlokuPion('zle')).toEqual({ topPx: 0, heightPx: 0 })
  })

  it('skalaPionowa: pełna i kompaktowa', () => {
    expect(skalaPionowa(false)).toBe(48)
    expect(skalaPionowa(true)).toBe(PX_NA_GODZINE_KOMPAKT)
    expect(PX_NA_GODZINE_KOMPAKT).toBeGreaterThanOrEqual(28)
    expect(PX_NA_GODZINE_KOMPAKT).toBeLessThanOrEqual(32)
  })

  it('pozycjaBlokuPion i klik w skali kompaktowej', () => {
    const k = PX_NA_GODZINE_KOMPAKT
    expect(pozycjaBlokuPion('2026-11-02 10:00:00', 8, k)).toEqual({
      topPx: 2 * k,
      heightPx: 1.5 * k,
    })
    expect(godzinaZKliknieciaPion(k, 8, 18, k)).toBe('09:00')
    expect(godzinaZKliknieciaPion(2.5 * k, 8, 18, k)).toBe('10:30')
  })

  it('pozycjaTeraz w osi i poza nią', () => {
    expect(pozycjaTeraz(new Date(2026, 10, 2, 13, 0))).toBeCloseTo(50, 5)
    expect(pozycjaTeraz(new Date(2026, 10, 2, 7, 59))).toBeNull()
    expect(pozycjaTeraz(new Date(2026, 10, 2, 18, 30))).toBeNull()
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
    expect(godzinaZKlikniecia(50)).toBe('13:00')
    expect(godzinaZKlikniecia(100)).toBe('17:30')
    expect(godzinaZKlikniecia(-20)).toBe('08:00')
    expect(godzinaZKlikniecia(150)).toBe('17:30')
  })

  it('godzinaZKlikniecia zaokrągla do 30 minut', () => {
    // 8 + 0.12 * 10 = 9.2 h => 9:12 => 9:00 ; 8 + 0.17*10 = 9.7 => 9:42 => 9:30
    expect(godzinaZKlikniecia(12)).toBe('09:00')
    expect(godzinaZKlikniecia(17)).toBe('09:30')
  })

  it('godzinaZKliknieciaPion', () => {
    expect(godzinaZKliknieciaPion(0)).toBe('08:00')
    expect(godzinaZKliknieciaPion(48)).toBe('09:00')
    expect(godzinaZKliknieciaPion(48 * 1.5)).toBe('09:30')
    expect(godzinaZKliknieciaPion(9999)).toBe('17:30')
  })

  it('opcjeGodzin i terminDoApi', () => {
    const o = opcjeGodzin()
    expect(o[0]).toBe('06:00')
    expect(o[o.length - 1]).toBe('21:00')
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
      c: [sp('2026-11-02 18:00:00')],
    }
    expect(osWspolna(mapa, ['a'])).toEqual({ od: 8, do: 18 })
    expect(osWspolna(mapa, ['a', 'b'])).toEqual({ od: 6, do: 18 })
    expect(osWspolna(mapa, ['a', 'b', 'c'])).toEqual({ od: 6, do: 20 })
    expect(osWspolna(mapa, [])).toEqual({ od: 8, do: 18 })
    expect(osWspolna(null, ['x'])).toEqual({ od: 8, do: 18 })
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
    expect(etykietaChipa([sp('a', { status: 'Nowy' })]).wolny).toBe(true)
    expect(
      etykietaChipa([sp('a'), sp('b', { status: 'Nowy' })]).tekst,
    ).not.toMatch(/potwierdzenia/)
  })

  it('wymiaryTorow: duży 36/8, kompakt 24/6, kolumna dni 64', () => {
    expect(wymiaryTorow(true)).toEqual({
      sciezkaPx: 36,
      odstepPx: 8,
      kolumnaDniPx: 64,
    })
    expect(wymiaryTorow(false)).toEqual({
      sciezkaPx: 24,
      odstepPx: 6,
      kolumnaDniPx: 64,
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
    expect(WYSOKOSC_NAGLOWKA_DNI_PX).toBe(32)
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
