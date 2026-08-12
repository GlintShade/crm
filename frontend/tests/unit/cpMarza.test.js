import {
  parsujStawke,
  parsujKwote,
  stawkiPoczatkowe,
  scalStawki,
  kosztyPoczatkowe,
  scalKoszty,
  przeliczPodzial,
} from '@/utils/cpMarza'

function deepFreeze(value) {
  Object.freeze(value)
  for (const child of Object.values(value)) {
    if (child && typeof child === 'object' && !Object.isFrozen(child)) {
      deepFreeze(child)
    }
  }
  return value
}

describe('Czyste Powietrze — modelowanie prowizji (cpMarza)', () => {
  describe('parsujStawke', () => {
    it.each([
      ['', 0],
      ['3000', 3000],
      ['3 000', 3000],
      ['3 000', 3000],
      ['3000,50', 3000.5],
      ['3000.50', 3000.5],
      ['3 000,50', 3000.5],
      [3000, 3000],
      [3000.5, 3000.5],
      [0, 0],
      ['0', 0],
      [null, 0],
      [undefined, 0],
      [-100, 0],
      ['-100', 0],
      ['abc', 0],
      ['3000abc', 0],
      [NaN, 0],
      [{}, 0],
      [[], 0],
      [true, 0],
    ])('parsujStawke(%p) === %p', (wartosc, expected) => {
      expect(parsujStawke(wartosc)).toBe(expected)
    })

    it('never returns NaN for any input', () => {
      const wejscia = ['', 'zjadl', null, undefined, -5, '-5', NaN, {}, [], 'NaN', '   ']
      for (const wejscie of wejscia) {
        expect(Number.isNaN(parsujStawke(wejscie))).toBe(false)
      }
    })

    it('clamps negative values to zero instead of returning them', () => {
      expect(parsujStawke(-3000)).toBe(0)
      expect(parsujStawke('-3000')).toBe(0)
      expect(parsujStawke('-3 000,50')).toBe(0)
    })
  })

  describe('stawkiPoczatkowe', () => {
    it('builds a rate map keyed by line code from stawka_prowizji', () => {
      const linie = [
        { kod: 'pompa_ciepla', stawka_prowizji: '3000.00' },
        { kod: 'elewacja', stawka_prowizji: '2500,50' },
      ]
      expect(stawkiPoczatkowe(linie)).toEqual({
        pompa_ciepla: 3000,
        elewacja: 2500.5,
      })
    })

    it('returns an empty object for missing or empty input', () => {
      expect(stawkiPoczatkowe(undefined)).toEqual({})
      expect(stawkiPoczatkowe([])).toEqual({})
    })
  })

  describe('scalStawki', () => {
    it('preserves a manually edited rate for a code that still exists', () => {
      const poprzednie = { pompa_ciepla: 5000 }
      const linie = [{ kod: 'pompa_ciepla', stawka_prowizji: '3000.00' }]
      expect(scalStawki(poprzednie, linie)).toEqual({ pompa_ciepla: 5000 })
    })

    it('assigns the catalogue rate to a newly appeared code', () => {
      const poprzednie = { pompa_ciepla: 5000 }
      const linie = [
        { kod: 'pompa_ciepla', stawka_prowizji: '3000.00' },
        { kod: 'elewacja', stawka_prowizji: '2500.00' },
      ]
      expect(scalStawki(poprzednie, linie)).toEqual({
        pompa_ciepla: 5000,
        elewacja: 2500,
      })
    })

    it('drops a code that is no longer in the offer', () => {
      const poprzednie = { pompa_ciepla: 5000, elewacja: 2500 }
      const linie = [{ kod: 'pompa_ciepla', stawka_prowizji: '3000.00' }]
      expect(scalStawki(poprzednie, linie)).toEqual({ pompa_ciepla: 5000 })
    })

    it('handles a missing previous rates object', () => {
      const linie = [{ kod: 'elewacja', stawka_prowizji: '2500.00' }]
      expect(scalStawki(undefined, linie)).toEqual({ elewacja: 2500 })
    })

    it('does not mutate its arguments', () => {
      const poprzednie = deepFreeze({ pompa_ciepla: 5000 })
      const linie = deepFreeze([
        { kod: 'pompa_ciepla', stawka_prowizji: '3000.00' },
        { kod: 'elewacja', stawka_prowizji: '2500.00' },
      ])
      expect(() => scalStawki(poprzednie, linie)).not.toThrow()
    })

    it('returns a fresh object, not the previous one', () => {
      const poprzednie = { pompa_ciepla: 5000 }
      const scalone = scalStawki(poprzednie, [
        { kod: 'pompa_ciepla', stawka_prowizji: '3000.00' },
      ])
      expect(scalone).not.toBe(poprzednie)
    })
  })

  describe('parsujKwote', () => {
    it('is the same parsing behaviour as parsujStawke (alias, not a copy)', () => {
      expect(parsujKwote).toBe(parsujStawke)
    })

    it.each([
      ['', 0],
      ['3000', 3000],
      ['3 000', 3000],
      ['3000,50', 3000.5],
      [-100, 0],
      ['-100', 0],
      ['abc', 0],
      [NaN, 0],
    ])('parsujKwote(%p) === %p', (wartosc, expected) => {
      expect(parsujKwote(wartosc)).toBe(expected)
    })
  })

  describe('kosztyPoczatkowe', () => {
    it('builds a {jednostkowy, staly} cost map keyed by line code', () => {
      const linie = [
        { kod: 'pompa_ciepla', koszt_jednostkowy: '26500.00', koszt_staly: '0.00' },
        { kod: 'elewacja', koszt_jednostkowy: '145.00', koszt_staly: '3000.00' },
      ]
      expect(kosztyPoczatkowe(linie)).toEqual({
        pompa_ciepla: { jednostkowy: 26500, staly: 0 },
        elewacja: { jednostkowy: 145, staly: 3000 },
      })
    })

    it('returns staly: 3000 for elewacja specifically', () => {
      const linie = [{ kod: 'elewacja', koszt_jednostkowy: '145.00', koszt_staly: '3000.00' }]
      expect(kosztyPoczatkowe(linie).elewacja.staly).toBe(3000)
    })

    it('returns an empty object for missing or empty input', () => {
      expect(kosztyPoczatkowe(undefined)).toEqual({})
      expect(kosztyPoczatkowe([])).toEqual({})
    })
  })

  describe('scalKoszty', () => {
    it('preserves a manually edited cost for a code that still exists', () => {
      const poprzednie = { pompa_ciepla: { jednostkowy: 30000, staly: 0 } }
      const linie = [{ kod: 'pompa_ciepla', koszt_jednostkowy: '26500.00', koszt_staly: '0.00' }]
      expect(scalKoszty(poprzednie, linie)).toEqual({
        pompa_ciepla: { jednostkowy: 30000, staly: 0 },
      })
    })

    it('assigns the catalogue cost to a newly appeared code', () => {
      const poprzednie = { pompa_ciepla: { jednostkowy: 30000, staly: 0 } }
      const linie = [
        { kod: 'pompa_ciepla', koszt_jednostkowy: '26500.00', koszt_staly: '0.00' },
        { kod: 'elewacja', koszt_jednostkowy: '145.00', koszt_staly: '3000.00' },
      ]
      expect(scalKoszty(poprzednie, linie)).toEqual({
        pompa_ciepla: { jednostkowy: 30000, staly: 0 },
        elewacja: { jednostkowy: 145, staly: 3000 },
      })
    })

    it('drops a code that is no longer in the offer', () => {
      const poprzednie = {
        pompa_ciepla: { jednostkowy: 30000, staly: 0 },
        elewacja: { jednostkowy: 200, staly: 3000 },
      }
      const linie = [{ kod: 'pompa_ciepla', koszt_jednostkowy: '26500.00', koszt_staly: '0.00' }]
      expect(scalKoszty(poprzednie, linie)).toEqual({
        pompa_ciepla: { jednostkowy: 30000, staly: 0 },
      })
    })

    it('handles a missing previous costs object', () => {
      const linie = [{ kod: 'elewacja', koszt_jednostkowy: '145.00', koszt_staly: '3000.00' }]
      expect(scalKoszty(undefined, linie)).toEqual({
        elewacja: { jednostkowy: 145, staly: 3000 },
      })
    })

    it('does not mutate its arguments', () => {
      const poprzednie = deepFreeze({ pompa_ciepla: { jednostkowy: 30000, staly: 0 } })
      const linie = deepFreeze([
        { kod: 'pompa_ciepla', koszt_jednostkowy: '26500.00', koszt_staly: '0.00' },
        { kod: 'elewacja', koszt_jednostkowy: '145.00', koszt_staly: '3000.00' },
      ])
      expect(() => scalKoszty(poprzednie, linie)).not.toThrow()
    })

    it('returns a fresh object, not the previous one, and a fresh inner object', () => {
      const poprzednie = { pompa_ciepla: { jednostkowy: 30000, staly: 0 } }
      const scalone = scalKoszty(poprzednie, [
        { kod: 'pompa_ciepla', koszt_jednostkowy: '26500.00', koszt_staly: '0.00' },
      ])
      expect(scalone).not.toBe(poprzednie)
      expect(scalone.pompa_ciepla).not.toBe(poprzednie.pompa_ciepla)
    })
  })

  describe('przeliczPodzial', () => {
    it('returns empty results for missing or empty input', () => {
      expect(przeliczPodzial(undefined, {})).toEqual({
        linie: [],
        razem: { netto: 0, koszt: 0, pula: 0, prowizja: 0, zysk: 0, zyskProc: 0, marzaProc: 0 },
      })
      expect(przeliczPodzial([], {})).toEqual({
        linie: [],
        razem: { netto: 0, koszt: 0, pula: 0, prowizja: 0, zysk: 0, zyskProc: 0, marzaProc: 0 },
      })
    })

    // Regresja: `result.wewnetrzne` w komponencie jest `null` (nie usuwany
    // kluczem `delete`) przed pierwszą odpowiedzią serwera i po każdym
    // czyszczeniu wyniku — patrz komentarz przy `hasInternal` w
    // KalkulatorCPTab.vue. `przeliczPodzial(null, …)` musi więc być
    // bezpieczne, inaczej `podzial` computed rzuca TypeError zamiast zwijać
    // się do pustego podziału.
    it('does not throw and returns empty results for null input', () => {
      expect(() => przeliczPodzial(null, {})).not.toThrow()
      expect(przeliczPodzial(null, {})).toEqual({
        linie: [],
        razem: { netto: 0, koszt: 0, pula: 0, prowizja: 0, zysk: 0, zyskProc: 0, marzaProc: 0 },
      })
      expect(() => przeliczPodzial(null, null)).not.toThrow()
    })

    it('computes pool/profit/percent for two ordinary lines', () => {
      const linie = [
        {
          kod: 'pompa_ciepla',
          ilosc_rozliczeniowa: '1',
          jednostka_rozliczeniowa: 'szt',
          netto: '35200.00',
          koszt: '26500.00',
          koszt_jednostkowy: '26500.00',
          koszt_staly: '0.00',
          stawka_prowizji: '3000.00',
        },
        {
          kod: 'okna',
          ilosc_rozliczeniowa: '20',
          jednostka_rozliczeniowa: 'm2',
          netto: '10000.00',
          koszt: '6000.00',
          koszt_jednostkowy: '300.00',
          koszt_staly: '0.00',
          stawka_prowizji: '50.00',
        },
      ]
      const stawki = { pompa_ciepla: 3000, okna: 50 }
      const { linie: wynik, razem } = przeliczPodzial(linie, stawki)

      expect(wynik[0]).toMatchObject({
        kod: 'pompa_ciepla',
        netto: 35200,
        koszt: 26500,
        pula: 8700,
        prowizja: 3000,
        zysk: 5700,
      })
      expect(wynik[0].zyskProc).toBeCloseTo((5700 / 35200) * 100, 6)

      expect(wynik[1]).toMatchObject({
        kod: 'okna',
        netto: 10000,
        koszt: 6000,
        pula: 4000,
        prowizja: 1000,
        zysk: 3000,
      })
      expect(wynik[1].zyskProc).toBeCloseTo(30, 6)

      expect(razem.netto).toBe(45200)
      expect(razem.koszt).toBe(32500)
      expect(razem.pula).toBe(12700)
      expect(razem.prowizja).toBe(4000)
      expect(razem.zysk).toBe(8700)
      expect(razem.zysk).toBe(razem.pula - razem.prowizja)
      expect(razem.marzaProc).toBeCloseTo((12700 / 45200) * 100, 6)
    })

    it('drzwi: multiplies the rate by ilosc_rozliczeniowa (piece count), never by client-facing m2', () => {
      const linie = [
        {
          kod: 'drzwi',
          ilosc_rozliczeniowa: 2,
          jednostka_rozliczeniowa: 'szt',
          netto: '2000.00',
          koszt: '1200.00',
          koszt_jednostkowy: '600.00',
          koszt_staly: '0.00',
          stawka_prowizji: '200.00',
        },
      ]
      const { linie: wynik } = przeliczPodzial(linie, { drzwi: 200 })
      expect(wynik[0].prowizja).toBe(400)
      // Regression guard: if this ever gets multiplied by client-facing m2
      // (e.g. 0.45) instead of ilosc_rozliczeniowa, the assertion above fails.
    })

    it('elewacja: does not double-count koszt_staly, which the server already folded into koszt', () => {
      const linie = [
        {
          kod: 'elewacja',
          ilosc_rozliczeniowa: '140',
          jednostka_rozliczeniowa: 'm2',
          netto: '40000.00',
          koszt: '23300.00', // 140 * 145 + 3000, already includes koszt_staly
          koszt_jednostkowy: '145.00',
          koszt_staly: '3000.00',
          stawka_prowizji: '0.00',
        },
      ]
      const { linie: wynik } = przeliczPodzial(linie, { elewacja: 0 })
      expect(wynik[0].koszt).toBe(23300)
      expect(wynik[0].pula).toBe(40000 - 23300)
    })

    it('allows zysk to go negative without clamping when the rate exceeds the pool', () => {
      const linie = [
        {
          kod: 'okna',
          ilosc_rozliczeniowa: '20',
          jednostka_rozliczeniowa: 'm2',
          netto: '10000.00',
          koszt: '6000.00',
          koszt_jednostkowy: '300.00',
          koszt_staly: '0.00',
          stawka_prowizji: '50.00',
        },
      ]
      // pula = 4000; rate of 500/m2 * 20 = 10000 commission, far above the pool
      const { linie: wynik, razem } = przeliczPodzial(linie, { okna: 500 })
      expect(wynik[0].prowizja).toBe(10000)
      expect(wynik[0].zysk).toBe(4000 - 10000)
      expect(wynik[0].zysk).toBeLessThan(0)
      expect(razem.zysk).toBeLessThan(0)
    })

    it('does not mutate the input lines or rates', () => {
      const linie = deepFreeze([
        {
          kod: 'pompa_ciepla',
          ilosc_rozliczeniowa: '1',
          jednostka_rozliczeniowa: 'szt',
          netto: '35200.00',
          koszt: '26500.00',
          koszt_jednostkowy: '26500.00',
          koszt_staly: '0.00',
          stawka_prowizji: '3000.00',
        },
      ])
      const stawki = deepFreeze({ pompa_ciepla: 3000 })
      expect(() => przeliczPodzial(linie, stawki)).not.toThrow()
    })

    it('falls back to zero for missing numeric fields instead of NaN', () => {
      const linie = [{ kod: 'nieznana', jednostka_rozliczeniowa: 'szt' }]
      const { linie: wynik } = przeliczPodzial(linie, {})
      expect(wynik[0]).toMatchObject({
        netto: 0,
        koszt: 0,
        pula: 0,
        prowizja: 0,
        zysk: 0,
        zyskProc: 0,
      })
    })

    describe('koszty override (third argument)', () => {
      const linia = {
        kod: 'pompa_ciepla',
        ilosc_rozliczeniowa: '1',
        jednostka_rozliczeniowa: 'szt',
        netto: '35200.00',
        koszt: '26500.00',
        koszt_jednostkowy: '26500.00',
        koszt_staly: '0.00',
        stawka_prowizji: '3000.00',
      }

      it('calling without a third argument gives an identical result to calling with catalogue values', () => {
        const bezArgumentu = przeliczPodzial([linia], { pompa_ciepla: 3000 })
        const zKatalogiem = przeliczPodzial([linia], { pompa_ciepla: 3000 }, {
          pompa_ciepla: { jednostkowy: 26500, staly: 0 },
        })
        expect(bezArgumentu).toEqual(zKatalogiem)
      })

      it('an overridden unit cost changes koszt/pula/zysk, and razem sums the override', () => {
        const { linie: wynik, razem } = przeliczPodzial(
          [linia],
          { pompa_ciepla: 3000 },
          { pompa_ciepla: { jednostkowy: 30000, staly: 0 } },
        )
        expect(wynik[0].kosztJednostkowy).toBe(30000)
        expect(wynik[0].koszt).toBe(30000) // 30000 * 1 + 0
        expect(wynik[0].pula).toBe(35200 - 30000)
        expect(wynik[0].zysk).toBe((35200 - 30000) - 3000)
        expect(razem.koszt).toBe(30000)
        expect(razem.pula).toBe(razem.netto - razem.koszt)
      })

      it('an overridden fixed cost is applied exactly once, not multiplied by ilosc_rozliczeniowa', () => {
        const elewacja = {
          kod: 'elewacja',
          ilosc_rozliczeniowa: '140',
          jednostka_rozliczeniowa: 'm2',
          netto: '40000.00',
          koszt: '23300.00',
          koszt_jednostkowy: '145.00',
          koszt_staly: '3000.00',
          stawka_prowizji: '0.00',
        }
        const { linie: wynik } = przeliczPodzial(
          [elewacja],
          { elewacja: 0 },
          { elewacja: { jednostkowy: 145, staly: 5000 } },
        )
        // 145 * 140 + 5000, NOT 145 * 140 + 5000 * 140
        expect(wynik[0].koszt).toBe(145 * 140 + 5000)
      })

      it('overriding only the unit cost keeps the catalogue fixed cost, and vice versa', () => {
        const elewacja = {
          kod: 'elewacja',
          ilosc_rozliczeniowa: '140',
          jednostka_rozliczeniowa: 'm2',
          netto: '40000.00',
          koszt: '23300.00',
          koszt_jednostkowy: '145.00',
          koszt_staly: '3000.00',
          stawka_prowizji: '0.00',
        }
        const tylkoJednostkowy = przeliczPodzial(
          [elewacja],
          {},
          { elewacja: { jednostkowy: 200, staly: undefined } },
        )
        expect(tylkoJednostkowy.linie[0].koszt).toBe(200 * 140 + 3000)

        const tylkoStaly = przeliczPodzial(
          [elewacja],
          {},
          { elewacja: { jednostkowy: undefined, staly: 6000 } },
        )
        expect(tylkoStaly.linie[0].koszt).toBe(145 * 140 + 6000)
      })

      it('a negative or garbage override cost clamps to zero, never NaN', () => {
        const { linie: wynik } = przeliczPodzial(
          [linia],
          { pompa_ciepla: 3000 },
          { pompa_ciepla: { jednostkowy: -500, staly: 'zjadl' } },
        )
        expect(wynik[0].kosztJednostkowy).toBe(0)
        expect(wynik[0].kosztStaly).toBe(0)
        expect(wynik[0].koszt).toBe(0)
        expect(Number.isNaN(wynik[0].koszt)).toBe(false)
      })

      it('does not mutate the koszty argument', () => {
        const koszty = deepFreeze({ pompa_ciepla: { jednostkowy: 30000, staly: 0 } })
        expect(() => przeliczPodzial([linia], { pompa_ciepla: 3000 }, koszty)).not.toThrow()
      })

      it('exposes the catalogue values alongside the effective ones for override indicators', () => {
        const { linie: wynik } = przeliczPodzial(
          [linia],
          { pompa_ciepla: 3000 },
          { pompa_ciepla: { jednostkowy: 30000, staly: 0 } },
        )
        expect(wynik[0].kosztJednostkowyKatalogowy).toBe(26500)
        expect(wynik[0].kosztJednostkowy).toBe(30000)
        expect(wynik[0].stawkaKatalogowa).toBe(3000)
      })
    })

    describe('zaokrąglanie do groszy (grosze)', () => {
      it('zaokrągla prowizję ułamkową: stawka 3.33 razy 7 sztuk daje dokładnie 23.31', () => {
        const linia = {
          kod: 'okna',
          ilosc_rozliczeniowa: '7',
          jednostka_rozliczeniowa: 'szt',
          netto: '1000.00',
          koszt: '500.00',
          koszt_jednostkowy: '71.43', // 71.43 * 7 = 500.01, celowo nieokrągłe
          koszt_staly: '0.00',
          stawka_prowizji: '3.33',
        }
        const { linie: wynik } = przeliczPodzial([linia], { okna: 3.33 })
        expect(wynik[0].prowizja).toBe(23.31)
        // Każde pole pieniężne w wierszu ma dokładnie 2 miejsca po przecinku.
        expect(wynik[0].koszt).toBe(500.01)
      })

      it('razem to suma już zaokrąglonych wierszy dla KAŻDEGO wyświetlanego pola (netto włącznie) — kolumna musi się sumować na ekranie', () => {
        // Dwa wiersze z surowym netto 10.125 — każdy zaokrągla się osobno
        // do 10.13 (widoczne w kolumnie), więc `razem.netto` MUSI być
        // 10.13 + 10.13 = 20.26, nie zaokrągleniem surowej sumy
        // (10.125 + 10.125 = 20.25 → 20.25). Gdyby `razem.netto` było
        // 20.25, administrator widziałby dwa wiersze po "10,13" i wiersz
        // „razem" na "20,25" — kolumna, która się nie sumuje. To jest
        // dokładnie ta usterka, którą to zaokrąglanie ma wykluczyć.
        const linie = [
          {
            kod: 'a',
            ilosc_rozliczeniowa: '1',
            jednostka_rozliczeniowa: 'szt',
            netto: '10.125',
            koszt: '0',
            koszt_jednostkowy: '0',
            koszt_staly: '0',
            stawka_prowizji: '0',
          },
          {
            kod: 'b',
            ilosc_rozliczeniowa: '1',
            jednostka_rozliczeniowa: 'szt',
            netto: '10.125',
            koszt: '0',
            koszt_jednostkowy: '0',
            koszt_staly: '0',
            stawka_prowizji: '0',
          },
        ]
        const { linie: wynik, razem } = przeliczPodzial(linie, { a: 0, b: 0 })
        expect(wynik[0].netto).toBe(10.13)
        expect(wynik[1].netto).toBe(10.13)
        expect(wynik[0].pula).toBe(10.13)
        expect(wynik[1].pula).toBe(10.13)
        // Rekoncyliacja: `razem` jest osiągalne przez zsumowanie tego, co
        // administrator faktycznie widzi w każdym wierszu — nie tylko dla
        // pula/koszt/prowizja/zysk, ale też dla netto.
        expect(razem.netto).toBe(20.26)
        expect(razem.pula).toBe(20.26)
        for (const pole of ['netto', 'koszt', 'pula', 'prowizja', 'zysk']) {
          const sumaWyswietlanychWierszy = wynik.reduce((suma, linia) => suma + linia[pole], 0)
          expect(razem[pole]).toBe(sumaWyswietlanychWierszy)
        }
      })

      it('każde pole pieniężne wiersza jest dokładne co do grosza (brak reszt zmiennoprzecinkowych)', () => {
        const linia = {
          kod: 'okna',
          ilosc_rozliczeniowa: '3',
          jednostka_rozliczeniowa: 'm2',
          netto: '100.10',
          koszt: '30.30',
          koszt_jednostkowy: '10.10',
          koszt_staly: '0',
          stawka_prowizji: '3.33',
        }
        const { linie: wynik } = przeliczPodzial([linia], { okna: 3.33 })
        for (const pole of ['koszt', 'pula', 'prowizja', 'zysk']) {
          const wartosc = wynik[0][pole]
          expect(Number.isFinite(wartosc)).toBe(true)
          // Pomnożenie przez 100 i zaokrąglenie do liczby całkowitej nie
          // zmienia wartości — czyli faktycznie ma najwyżej 2 miejsca po
          // przecinku, bez rozjazgotanego ogona (np. 30.299999999999997).
          expect(Math.round(wartosc * 100)).toBe(wartosc * 100)
        }
      })

      it('zysk pozostaje dokładny mimo reszt zmiennoprzecinkowych, gdy netto == koszt + prowizja policzone inną arytmetyką', () => {
        // 0.1 + 0.2 - 0.3 === 5.551115123125783e-17 w IEEE-754 — klasyczna
        // pułapka, którą ma obsłużyć roundPln (patrz money.js). Budujemy
        // linię tak, żeby zysk wypadł jako różnica dwóch bliskich sobie
        // wartości powstałych inną drogą arytmetyczną.
        const linia = {
          kod: 'test',
          ilosc_rozliczeniowa: '1',
          jednostka_rozliczeniowa: 'szt',
          netto: '0.3',
          koszt: '0.1',
          koszt_jednostkowy: '0.1',
          koszt_staly: '0',
          stawka_prowizji: '0.2',
        }
        const { linie: wynik, razem } = przeliczPodzial([linia], { test: 0.2 })
        expect(Number.isNaN(wynik[0].zysk)).toBe(false)
        expect(Number.isNaN(razem.zysk)).toBe(false)
        // Math.abs zamiast bezpośredniego toBe(0): resztka rzędu 1e-17 jest
        // ujemna, więc roundPln zwraca tu -0, nie +0 — poprawnie co do
        // wartości (-0 === 0, wyświetla się identycznie jako "0,00"), ale
        // vitest/Jest `toBe` porównuje przez Object.is, który -0 i 0
        // rozróżnia. To nie jest błąd roundPln, tylko własność IEEE-754.
        expect(Math.abs(wynik[0].zysk)).toBe(0)
        expect(Math.abs(razem.zysk)).toBe(0)
      })

      it('razem.zysk === razem.pula - razem.prowizja pozostaje dokładne po zaokrągleniu', () => {
        const linie = [
          {
            kod: 'a',
            ilosc_rozliczeniowa: '7',
            jednostka_rozliczeniowa: 'szt',
            netto: '1000.00',
            koszt: '500.01',
            koszt_jednostkowy: '71.43',
            koszt_staly: '0.00',
            stawka_prowizji: '3.33',
          },
          {
            kod: 'b',
            ilosc_rozliczeniowa: '3',
            jednostka_rozliczeniowa: 'm2',
            netto: '100.10',
            koszt: '30.30',
            koszt_jednostkowy: '10.10',
            koszt_staly: '0',
            stawka_prowizji: '3.33',
          },
        ]
        const { linie: wynik, razem } = przeliczPodzial(linie, { a: 3.33, b: 3.33 })
        expect(razem.zysk).toBe(razem.pula - razem.prowizja)
        // Regresja: `razem.netto` musi być osiągalne dodając to, co
        // administrator widzi w każdym wierszu netto na ekranie — nie
        // przeliczeniem surowej sumy z serwera.
        expect(razem.netto).toBe(wynik.reduce((suma, linia) => suma + linia.netto, 0))
      })

      it('parsujStawke/parsujKwote nie zaokrąglają wejścia — pełna precyzja wpisana przez administratora jest zachowana', () => {
        expect(parsujStawke('3.336')).toBe(3.336)
        expect(parsujKwote('71.4285')).toBe(71.4285)
      })

      it('zyskProc/marzaProc pozostają liczone z surowych proporcji (bez zaokrąglenia do 2 miejsc)', () => {
        const linia = {
          kod: 'okna',
          ilosc_rozliczeniowa: '7',
          jednostka_rozliczeniowa: 'szt',
          netto: '1000.00',
          koszt: '500.01',
          koszt_jednostkowy: '71.43',
          koszt_staly: '0.00',
          stawka_prowizji: '3.33',
        }
        const { linie: wynik, razem } = przeliczPodzial([linia], { okna: 3.33 })
        // Surowy zysk = 1000 - 500.01 - 23.31 = 476.68 (bez zaokrąglenia
        // pośrednich kroków) — zyskProc liczony wprost z tej wartości, nie
        // z już zaokrąglonego pola `zysk`.
        const surowyZysk = 1000 - 71.43 * 7 - 3.33 * 7
        expect(wynik[0].zyskProc).toBeCloseTo((surowyZysk / 1000) * 100, 10)
        expect(razem.zyskProc).toBeCloseTo((surowyZysk / 1000) * 100, 10)
      })
    })
  })
})
