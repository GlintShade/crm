import {
  parsujKosztRzeczywisty,
  parseSnapshot,
  przeliczRzeczywiste,
  zbudujPayload,
} from '@/utils/montazKoszty'

function deepFreeze(value) {
  Object.freeze(value)
  for (const child of Object.values(value)) {
    if (child && typeof child === 'object' && !Object.isFrozen(child)) {
      deepFreeze(child)
    }
  }
  return value
}

const CP_LINIA = {
  klucz: 'pompa_ciepla',
  etykieta: 'Pompa ciepła',
  ilosc: '140.00',
  jednostka: 'm2',
  netto: '35000.00',
  prowizja_plan: '2200.00',
  koszt_plan: '18000.00',
  koszt_rzeczywisty: null,
}

const PV_LINIA = {
  klucz: 'falownik',
  etykieta: 'Falownik',
  ilosc: null,
  jednostka: null,
  netto: null,
  prowizja_plan: null,
  koszt_plan: '5000.00',
  koszt_rzeczywisty: null,
}

function cpSnapshot(overrides = {}) {
  return {
    wersja: 1,
    linia_produktowa: 'cp',
    utworzono: '2026-08-19T10:00:00',
    zmodyfikowano: null,
    zmodyfikowal: null,
    linie: [CP_LINIA],
    skladniki_marzy: [],
    dodatkowe: [],
    podsumowanie: {
      netto: '35000.00',
      koszt_plan: '18000.00',
      marza_plan: '17000.00',
      prowizja_plan: '2200.00',
      zysk_plan: '14800.00',
    },
    podsumowanie_rzeczywiste: null,
    ...overrides,
  }
}

function pvSnapshot(overrides = {}) {
  return {
    wersja: 1,
    linia_produktowa: 'pv',
    utworzono: '2026-08-19T10:00:00',
    zmodyfikowano: null,
    zmodyfikowal: null,
    linie: [PV_LINIA],
    skladniki_marzy: [{ klucz: 'marza_proenergy', etykieta: 'Marża ProEnergy', kwota: '3000.00' }],
    dodatkowe: [],
    podsumowanie: {
      netto: '10000.00',
      koszt_plan: '5000.00',
      marza_plan: '5000.00',
      prowizja_plan: null,
      zysk_plan: '5000.00',
    },
    podsumowanie_rzeczywiste: null,
    ...overrides,
  }
}

describe('Montaż — koszty rzeczywiste (montazKoszty)', () => {
  describe('parsujKosztRzeczywisty', () => {
    it.each([
      ['', null],
      ['3000', 3000],
      ['3 000', 3000],
      ['3 000', 3000],
      ['3000,50', 3000.5],
      ['3000.50', 3000.5],
      [3000, 3000],
      [3000.5, 3000.5],
      [0, 0],
      ['0', 0],
      [null, null],
      [undefined, null],
      [-100, null],
      ['-100', null],
      ['abc', null],
      ['3000abc', null],
      [NaN, null],
      [{}, null],
      [[], null],
      [true, null],
    ])('parsujKosztRzeczywisty(%p) === %p', (surowa, expected) => {
      expect(parsujKosztRzeczywisty(surowa)).toBe(expected)
    })

    it('treats zero as a valid entered amount, distinct from empty', () => {
      expect(parsujKosztRzeczywisty('0')).toBe(0)
      expect(parsujKosztRzeczywisty('')).toBe(null)
    })

    it('never returns NaN for any input', () => {
      const wejscia = ['', 'zjadl', null, undefined, -5, '-5', NaN, {}, [], 'NaN', '   ']
      for (const wejscie of wejscia) {
        const wynik = parsujKosztRzeczywisty(wejscie)
        expect(wynik === null || Number.isFinite(wynik)).toBe(true)
      }
    })
  })

  describe('parseSnapshot', () => {
    it('parses a well-formed wersja-1 snapshot', () => {
      const json = JSON.stringify(cpSnapshot())
      expect(parseSnapshot(json)).toEqual(cpSnapshot())
    })

    it.each([
      ['garbage json', 'not json at all {{{'],
      ['null', null],
      ['undefined', undefined],
      ['empty string', ''],
      ['number', 42],
      ['array', '[]'],
      ['wrong wersja', JSON.stringify({ ...cpSnapshot(), wersja: 2 })],
      ['missing wersja', JSON.stringify({ ...cpSnapshot(), wersja: undefined })],
      ['missing linie', JSON.stringify({ ...cpSnapshot(), linie: undefined })],
      ['linie not array', JSON.stringify({ ...cpSnapshot(), linie: {} })],
      ['missing podsumowanie', JSON.stringify({ ...cpSnapshot(), podsumowanie: undefined })],
      ['podsumowanie not object', JSON.stringify({ ...cpSnapshot(), podsumowanie: 'x' })],
    ])('returns null for %s', (_label, input) => {
      expect(parseSnapshot(input)).toBe(null)
    })

    it('accepts an already-parsed object defensively', () => {
      expect(parseSnapshot(cpSnapshot())).toEqual(cpSnapshot())
    })

    it('never throws', () => {
      expect(() => parseSnapshot('{{{')).not.toThrow()
      expect(() => parseSnapshot(Symbol('x'))).not.toThrow()
    })
  })

  describe('przeliczRzeczywiste — fallback to plan and pozycjeWgPlanu', () => {
    it('falls back to koszt_plan when no actual is entered', () => {
      const snapshot = cpSnapshot()
      const wynik = przeliczRzeczywiste(snapshot, {}, [])
      expect(wynik.linie[0].wgPlanu).toBe(true)
      expect(wynik.linie[0].kosztUzyty).toBe(18000)
      expect(wynik.linie[0].kosztRzeczywisty).toBe(null)
      expect(wynik.razem.pozycjeWgPlanu).toBe(1)
      expect(wynik.razem.kosztRzeczywisty).toBe(18000)
      expect(wynik.bledy).toEqual([])
    })

    it('uses the entered actual once typed, and drops out of pozycjeWgPlanu', () => {
      const snapshot = cpSnapshot()
      const wynik = przeliczRzeczywiste(snapshot, { pompa_ciepla: '19500' }, [])
      expect(wynik.linie[0].wgPlanu).toBe(false)
      expect(wynik.linie[0].kosztUzyty).toBe(19500)
      expect(wynik.linie[0].delta).toBe(1500)
      expect(wynik.razem.pozycjeWgPlanu).toBe(0)
      expect(wynik.razem.kosztRzeczywisty).toBe(19500)
      expect(wynik.razem.marzaRzeczywista).toBe(35000 - 19500)
    })

    it('does not mutate the snapshot or edycje inputs', () => {
      const snapshot = deepFreeze(cpSnapshot())
      const edycje = deepFreeze({ pompa_ciepla: '19500' })
      const dodatkowe = deepFreeze([{ nazwa: 'Transport', kwota: '500' }])
      expect(() => przeliczRzeczywiste(snapshot, edycje, dodatkowe)).not.toThrow()
    })
  })

  describe('przeliczRzeczywiste — dodatkowe pozycje', () => {
    it('sums valid dodatkowe rows into razem.kosztRzeczywisty', () => {
      const snapshot = cpSnapshot()
      const dodatkowe = [
        { nazwa: 'Transport', kwota: '500' },
        { nazwa: 'Dźwig', kwota: '1 200,50' },
      ]
      const wynik = przeliczRzeczywiste(snapshot, {}, dodatkowe)
      // 18000 (plan fallback) + 500 + 1200.50
      expect(wynik.razem.kosztRzeczywisty).toBe(19700.5)
      expect(wynik.bledy).toEqual([])
    })

    it('treats an entirely empty row as a no-op, no error', () => {
      const snapshot = cpSnapshot()
      const wynik = przeliczRzeczywiste(snapshot, {}, [{ nazwa: '', kwota: '' }])
      expect(wynik.razem.kosztRzeczywisty).toBe(18000)
      expect(wynik.bledy).toEqual([])
    })

    it('flags a named row with an invalid amount as an error, contributing 0', () => {
      const snapshot = cpSnapshot()
      const wynik = przeliczRzeczywiste(snapshot, {}, [{ nazwa: 'Coś', kwota: 'abc' }])
      expect(wynik.razem.kosztRzeczywisty).toBe(18000)
      expect(wynik.bledy.length).toBe(1)
    })

    it('flags a valid amount with no name as an error, but still sums it', () => {
      const snapshot = cpSnapshot()
      const wynik = przeliczRzeczywiste(snapshot, {}, [{ nazwa: '', kwota: '500' }])
      expect(wynik.razem.kosztRzeczywisty).toBe(18500)
      expect(wynik.bledy.length).toBe(1)
    })
  })

  describe('przeliczRzeczywiste — comma/space parsing', () => {
    it('parses "3 000,50" style input the same as cpMarza conventions', () => {
      const snapshot = cpSnapshot()
      const wynik = przeliczRzeczywiste(snapshot, { pompa_ciepla: '18 500,25' }, [])
      expect(wynik.linie[0].kosztRzeczywisty).toBe(18500.25)
    })
  })

  describe('przeliczRzeczywiste — dodatkowe pozycja name too long (mirrors server 140-char cap)', () => {
    it('flags a name over 140 chars as an error but still sums the amount', () => {
      const snapshot = cpSnapshot()
      const dlugaNazwa = 'x'.repeat(141)
      const wynik = przeliczRzeczywiste(snapshot, {}, [{ nazwa: dlugaNazwa, kwota: '500' }])
      expect(wynik.razem.kosztRzeczywisty).toBe(18500)
      expect(wynik.bledy.length).toBe(1)
    })

    it('does not flag a name exactly at the 140-char cap', () => {
      const snapshot = cpSnapshot()
      const nazwa = 'x'.repeat(140)
      const wynik = przeliczRzeczywiste(snapshot, {}, [{ nazwa, kwota: '500' }])
      expect(wynik.bledy).toEqual([])
    })
  })

  describe('przeliczRzeczywiste — negative input rejected', () => {
    it('treats a negative typed actual as invalid (falls back to plan) and reports an error', () => {
      const snapshot = cpSnapshot()
      const wynik = przeliczRzeczywiste(snapshot, { pompa_ciepla: '-500' }, [])
      expect(wynik.linie[0].wgPlanu).toBe(true)
      expect(wynik.linie[0].kosztUzyty).toBe(18000)
      expect(wynik.bledy.length).toBe(1)
    })
  })

  describe('przeliczRzeczywiste — CP vs PV shapes', () => {
    it('CP line carries a numeric marzaLinii (netto - kosztUzyty)', () => {
      const snapshot = cpSnapshot()
      const wynik = przeliczRzeczywiste(snapshot, {}, [])
      expect(wynik.linie[0].marzaLinii).toBe(35000 - 18000)
      expect(wynik.linie[0].netto).toBe(35000)
    })

    it('PV line has marzaLinii and netto null (no per-line netto)', () => {
      const snapshot = pvSnapshot()
      const wynik = przeliczRzeczywiste(snapshot, {}, [])
      expect(wynik.linie[0].marzaLinii).toBe(null)
      expect(wynik.linie[0].netto).toBe(null)
      expect(wynik.linie[0].prowizjaPlan).toBe(null)
    })

    it('PV razem.zyskRzeczywisty equals marzaRzeczywista when prowizjaPlan is null', () => {
      const snapshot = pvSnapshot()
      const wynik = przeliczRzeczywiste(snapshot, {}, [])
      expect(wynik.razem.prowizjaPlan).toBe(null)
      expect(wynik.razem.zyskRzeczywisty).toBe(wynik.razem.marzaRzeczywista)
    })

    it('CP razem.zyskRzeczywisty subtracts prowizjaPlan from marzaRzeczywista', () => {
      const snapshot = cpSnapshot()
      const wynik = przeliczRzeczywiste(snapshot, {}, [])
      expect(wynik.razem.zyskRzeczywisty).toBe(wynik.razem.marzaRzeczywista - 2200)
    })
  })

  describe('zbudujPayload', () => {
    it('sends an explicit null for every line with no valid actual entered', () => {
      const snapshot = cpSnapshot()
      const payload = zbudujPayload(snapshot, {}, [])
      expect(payload.koszty_rzeczywiste).toEqual({ pompa_ciepla: null })
    })

    it('sends an explicit null for a cleared field (empty string)', () => {
      const snapshot = cpSnapshot()
      const payload = zbudujPayload(snapshot, { pompa_ciepla: '' }, [])
      expect(payload.koszty_rzeczywiste.pompa_ciepla).toBe(null)
    })

    it('sends the parsed number for a valid entered actual', () => {
      const snapshot = cpSnapshot()
      const payload = zbudujPayload(snapshot, { pompa_ciepla: '19 500,75' }, [])
      expect(payload.koszty_rzeczywiste.pompa_ciepla).toBe(19500.75)
    })

    it('sends an entry for EVERY line, even ones absent from edycje', () => {
      const snapshot = cpSnapshot({ linie: [CP_LINIA, PV_LINIA] })
      const payload = zbudujPayload(snapshot, { pompa_ciepla: '100' }, [])
      expect(Object.keys(payload.koszty_rzeczywiste).sort()).toEqual(['falownik', 'pompa_ciepla'])
      expect(payload.koszty_rzeczywiste.falownik).toBe(null)
    })

    it('keeps id when present on a dodatkowa row, omits it when absent', () => {
      const snapshot = cpSnapshot()
      const payload = zbudujPayload(snapshot, {}, [
        { id: 'abc123', nazwa: 'Transport', kwota: '500' },
        { nazwa: 'Dźwig', kwota: '1200' },
      ])
      expect(payload.dodatkowe).toEqual([
        { id: 'abc123', nazwa: 'Transport', kwota: 500 },
        { nazwa: 'Dźwig', kwota: 1200 },
      ])
    })

    it('trims whitespace from dodatkowa nazwa', () => {
      const snapshot = cpSnapshot()
      const payload = zbudujPayload(snapshot, {}, [{ nazwa: '  Transport  ', kwota: '500' }])
      expect(payload.dodatkowe[0].nazwa).toBe('Transport')
    })

    it('skips a dodatkowa row entirely empty', () => {
      const snapshot = cpSnapshot()
      const payload = zbudujPayload(snapshot, {}, [{ nazwa: '', kwota: '' }])
      expect(payload.dodatkowe).toEqual([])
    })

    it('skips a dodatkowa row with a name but no valid amount', () => {
      const snapshot = cpSnapshot()
      const payload = zbudujPayload(snapshot, {}, [{ nazwa: 'Coś', kwota: 'abc' }])
      expect(payload.dodatkowe).toEqual([])
    })

    it('skips a dodatkowa row with an amount but no name', () => {
      const snapshot = cpSnapshot()
      const payload = zbudujPayload(snapshot, {}, [{ nazwa: '', kwota: '500' }])
      expect(payload.dodatkowe).toEqual([])
    })

    it('skips a dodatkowa row whose name exceeds the server 140-char cap', () => {
      const snapshot = cpSnapshot()
      const payload = zbudujPayload(snapshot, {}, [{ nazwa: 'x'.repeat(141), kwota: '500' }])
      expect(payload.dodatkowe).toEqual([])
    })

    it('does not mutate snapshot, edycje, or dodatkowe inputs', () => {
      const snapshot = deepFreeze(cpSnapshot())
      const edycje = deepFreeze({ pompa_ciepla: '19500' })
      const dodatkowe = deepFreeze([{ nazwa: 'Transport', kwota: '500' }])
      expect(() => zbudujPayload(snapshot, edycje, dodatkowe)).not.toThrow()
    })
  })

  describe('rounding edges', () => {
    it('rounds half-up to two decimals in kosztUzyty and delta', () => {
      const snapshot = cpSnapshot({
        linie: [{ ...CP_LINIA, koszt_plan: '18000.005' }],
      })
      const wynik = przeliczRzeczywiste(snapshot, {}, [])
      expect(wynik.linie[0].kosztPlan).toBe(18000.01)
    })

    it('sums dodatkowe amounts to exactly two decimals without float residue', () => {
      const snapshot = cpSnapshot()
      const dodatkowe = [
        { nazwa: 'A', kwota: '10.10' },
        { nazwa: 'B', kwota: '10.10' },
        { nazwa: 'C', kwota: '10.10' },
      ]
      const wynik = przeliczRzeczywiste(snapshot, {}, dodatkowe)
      expect(wynik.razem.kosztRzeczywisty).toBe(18000 + 30.3)
    })
  })
})
