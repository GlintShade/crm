import {
  parsujKosztRzeczywisty,
  parseSnapshot,
  przeliczRzeczywiste,
  zbudujPayload,
  czyEdytowalnyPlan,
  edycjePlanuStart,
  przeliczPlan,
  zbudujPayloadPlanu,
  czyPayloadPlanuMaZmiany,
  czyZmienioneRzeczywiste,
  skladnikiMarzyStart,
  przeliczSkladnikiMarzy,
  zbudujPayloadMarz,
  czyPayloadMarzMaZmiany,
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


// ---------------------------------------------------------------------------
// Edycja kosztów planowanych (ops#335)
// ---------------------------------------------------------------------------
function planSnapshot(overrides = {}) {
  const linie = [
    { ...PV_LINIA, klucz: 'k_falownik', etykieta: 'Falownik', koszt_plan: '5000.00' },
    { ...PV_LINIA, klucz: 'k_bateria', etykieta: 'Bateria', koszt_plan: '12000.00' },
    { ...PV_LINIA, klucz: 'k_montaz_pv', etykieta: 'Montaż PV', koszt_plan: '3000.00' },
  ]
  return {
    ...pvSnapshot(),
    linie,
    podsumowanie: {
      netto: '30000.00',
      koszt_plan: '20000.00',
      marza_plan: '10000.00',
      prowizja_plan: null,
      zysk_plan: '10000.00',
    },
    ...overrides,
  }
}

describe('Edycja kosztów planowanych (montazKoszty)', () => {
  describe('czyEdytowalnyPlan', () => {
    it('pv i oze tak, cp i brak nie', () => {
      expect(czyEdytowalnyPlan({ linia_produktowa: 'pv' })).toBe(true)
      expect(czyEdytowalnyPlan({ linia_produktowa: 'oze' })).toBe(true)
      expect(czyEdytowalnyPlan({ linia_produktowa: 'cp' })).toBe(false)
      expect(czyEdytowalnyPlan(null)).toBe(false)
    })
  })

  describe('przeliczPlan', () => {
    it('bez zmian: wartości zapisane', () => {
      const snap = planSnapshot()
      const w = przeliczPlan(snap, edycjePlanuStart(snap), null)
      expect(w.razem.kosztPlan).toBe(20000)
      expect(w.razem.marzaPlan).toBe(10000)
      expect(w.razem.zyskPlan).toBe(10000)
      expect(w.roznicaSumy).toBe(0)
      expect(w.linie.every((l) => !l.zmieniona)).toBe(true)
    })

    it('zmiana jednej linii przesuwa sumę, marżę i zysk', () => {
      const snap = planSnapshot()
      const w = przeliczPlan(snap, { ...edycjePlanuStart(snap), k_bateria: '13 000,50' }, null)
      expect(w.razem.kosztPlan).toBe(21000.5)
      expect(w.razem.marzaPlan).toBe(8999.5)
      const bateria = w.linie.find((l) => l.klucz === 'k_bateria')
      expect(bateria.zmieniona).toBe(true)
      expect(bateria.pierwotny).toBe(12000)
    })

    it('zysk uwzględnia prowizję planu', () => {
      const snap = planSnapshot({
        podsumowanie: { netto: '30000.00', koszt_plan: '20000.00', marza_plan: '10000.00', prowizja_plan: '500.00', zysk_plan: '9500.00' },
      })
      const w = przeliczPlan(snap, { ...edycjePlanuStart(snap), k_bateria: '13000' }, null)
      expect(w.razem.zyskPlan).toBe(8500)
    })

    it('wpisana suma wyższa niż suma linii: różnica idzie do korekty, wygrywa suma', () => {
      const snap = planSnapshot()
      const w = przeliczPlan(snap, { ...edycjePlanuStart(snap), k_bateria: '13000' }, '21500')
      expect(w.razem.kosztPlan).toBe(21500)
      expect(w.roznicaSumy).toBe(500)
      expect(w.korekta).toBe(500)
      expect(w.razem.marzaPlan).toBe(8500)
    })

    it('wpisana suma niższa: ujemna korekta', () => {
      const snap = planSnapshot()
      const w = przeliczPlan(snap, edycjePlanuStart(snap), '18000')
      expect(w.roznicaSumy).toBe(-2000)
      expect(w.korekta).toBe(-2000)
    })

    it('suma równa sumie linii: brak różnicy', () => {
      const snap = planSnapshot()
      const w = przeliczPlan(snap, { ...edycjePlanuStart(snap), k_bateria: '13000' }, '21000')
      expect(w.roznicaSumy).toBe(0)
      expect(w.korekta).toBe(0)
    })

    it('istniejąca korekta (ujemny koszt_plan) zostaje i można ją usunąć', () => {
      const korekta = { klucz: 'korekta_sumy_plan', etykieta: 'Korekta sumy kosztów planowanych', ilosc: null, jednostka: null, netto: null, prowizja_plan: null, koszt_plan: '-500.00', koszt_rzeczywisty: null }
      const snap = planSnapshot()
      snap.linie = [...snap.linie, korekta]
      snap.podsumowanie = { ...snap.podsumowanie, koszt_plan: '19500.00', marza_plan: '10500.00', zysk_plan: '10500.00' }
      const bez = przeliczPlan(snap, edycjePlanuStart(snap), null)
      expect(bez.razem.kosztPlan).toBe(19500)
      expect(bez.korekta).toBe(-500)
      expect(bez.korektaIstnieje).toBe(true)
      expect(Object.keys(edycjePlanuStart(snap))).not.toContain('korekta_sumy_plan')
      const usun = przeliczPlan(snap, edycjePlanuStart(snap), null, true)
      expect(usun.razem.kosztPlan).toBe(20000)
      expect(usun.korekta).toBe(0)
    })

    it('suma planu stara różna od sumy linii: delta, nie suma od zera', () => {
      const snap = planSnapshot()
      snap.podsumowanie = { ...snap.podsumowanie, koszt_plan: '20500.00' }
      const w = przeliczPlan(snap, { ...edycjePlanuStart(snap), k_bateria: '13000' }, null)
      expect(w.razem.kosztPlan).toBe(21500)
    })

    it('zapisana wartość pierwotna jest pokazana i służy do przywrócenia', () => {
      const snap = planSnapshot()
      snap.linie = snap.linie.map((l) => (l.klucz === 'k_bateria' ? { ...l, koszt_plan: '13000.00', koszt_plan_pierwotny: '12000.00' } : l))
      const w = przeliczPlan(snap, edycjePlanuStart(snap), null)
      expect(w.linie.find((l) => l.klucz === 'k_bateria').pierwotny).toBe(12000)
    })

    it('błędne wartości zgłaszane jako błędy, traktowane jako bez zmiany', () => {
      const snap = planSnapshot()
      const w = przeliczPlan(snap, { ...edycjePlanuStart(snap), k_bateria: 'abc', k_falownik: '-1' }, 'xyz')
      expect(w.bledy).toHaveLength(3)
      expect(w.razem.kosztPlan).toBe(20000)
    })

    it('puste pole linii = bez zmiany, bez błędu', () => {
      const snap = planSnapshot()
      const w = przeliczPlan(snap, { ...edycjePlanuStart(snap), k_bateria: '' }, '')
      expect(w.bledy).toEqual([])
      expect(w.razem.kosztPlan).toBe(20000)
    })

    it('nie mutuje argumentów (zamrożone wejście)', () => {
      const snap = deepFreeze(planSnapshot())
      const edycje = deepFreeze({ ...edycjePlanuStart(snap), k_bateria: '13000' })
      expect(() => przeliczPlan(snap, edycje, '21000')).not.toThrow()
    })

    it('grosze: brak błędów zmiennoprzecinkowych', () => {
      const snap = planSnapshot()
      const w = przeliczPlan(snap, { ...edycjePlanuStart(snap), k_falownik: '5000.10', k_bateria: '12000.20' }, null)
      expect(w.razem.kosztPlan).toBe(20000.3)
    })
  })

  describe('zbudujPayloadPlanu', () => {
    it('wysyła tylko zmienione linie jako stringi z groszami', () => {
      const snap = planSnapshot()
      const p = zbudujPayloadPlanu(snap, { ...edycjePlanuStart(snap), k_bateria: '13 000,5' }, null)
      expect(p).toEqual({ koszty_plan: { k_bateria: '13000.50' }, suma_plan: null })
      expect(czyPayloadPlanuMaZmiany(p)).toBe(true)
    })

    it('brak zmian: pusty payload', () => {
      const snap = planSnapshot()
      const p = zbudujPayloadPlanu(snap, edycjePlanuStart(snap), null)
      expect(p).toEqual({ koszty_plan: {}, suma_plan: null })
      expect(czyPayloadPlanuMaZmiany(p)).toBe(false)
    })

    it('suma wpisana trafia jako string, razem ze zmianą linii', () => {
      const snap = planSnapshot()
      const p = zbudujPayloadPlanu(snap, { ...edycjePlanuStart(snap), k_bateria: '13000' }, '21 500')
      expect(p.suma_plan).toBe('21500.00')
      expect(p.koszty_plan).toEqual({ k_bateria: '13000.00' })
    })

    it('przywrócenie do pierwotnej wysyła wartość pierwotną', () => {
      const snap = planSnapshot()
      snap.linie = snap.linie.map((l) => (l.klucz === 'k_bateria' ? { ...l, koszt_plan: '13000.00', koszt_plan_pierwotny: '12000.00' } : l))
      const p = zbudujPayloadPlanu(snap, { ...edycjePlanuStart(snap), k_bateria: '12000.00' }, null)
      expect(p.koszty_plan).toEqual({ k_bateria: '12000.00' })
    })

    it('usunięcie korekty wysyła null na kluczu korekty', () => {
      const p = zbudujPayloadPlanu(planSnapshot(), {}, null, true)
      expect(p.koszty_plan).toEqual({ korekta_sumy_plan: null })
      expect(czyPayloadPlanuMaZmiany(p)).toBe(true)
    })

    it('śmieciowe wartości pomijane', () => {
      const snap = planSnapshot()
      const p = zbudujPayloadPlanu(snap, { ...edycjePlanuStart(snap), k_bateria: 'abc' }, 'xyz')
      expect(p).toEqual({ koszty_plan: {}, suma_plan: null })
    })
  })

  describe('linia korekty w kosztach rzeczywistych', () => {
    const korekta = { klucz: 'korekta_sumy_plan', etykieta: 'Korekta sumy kosztów planowanych', ilosc: null, jednostka: null, netto: null, prowizja_plan: null, koszt_plan: '-500.00', koszt_rzeczywisty: null }

    it('przeliczRzeczywiste liczy ujemną korektę wg planu i oznacza linię', () => {
      const snap = planSnapshot()
      snap.linie = [...snap.linie, korekta]
      const w = przeliczRzeczywiste(snap, {}, [])
      const lk = w.linie.find((l) => l.klucz === 'korekta_sumy_plan')
      expect(lk.czyKorekta).toBe(true)
      expect(lk.kosztPlan).toBe(-500)
      expect(w.razem.kosztRzeczywisty).toBe(19500)
    })

    it('zbudujPayload nie wysyła klucza korekty', () => {
      const snap = planSnapshot()
      snap.linie = [...snap.linie, korekta]
      const p = zbudujPayload(snap, {}, [])
      expect(Object.keys(p.koszty_rzeczywiste)).not.toContain('korekta_sumy_plan')
    })

    it('przeliczRzeczywiste niesie koszt_plan_pierwotny linii', () => {
      const snap = planSnapshot()
      snap.linie = snap.linie.map((l) => (l.klucz === 'k_bateria' ? { ...l, koszt_plan: '13000.00', koszt_plan_pierwotny: '12000.00' } : l))
      const w = przeliczRzeczywiste(snap, {}, [])
      expect(w.linie.find((l) => l.klucz === 'k_bateria').kosztPlanPierwotny).toBe(12000)
      expect(w.linie.find((l) => l.klucz === 'k_falownik').kosztPlanPierwotny).toBeNull()
    })

    it('parseSnapshot przyjmuje snapshot z korektą i edycja_planu', () => {
      const snap = planSnapshot()
      snap.linie = [...snap.linie, korekta]
      snap.edycja_planu = { kiedy: '2026-11-13 10:00:00', kto: 'a@x.pl', koszt_plan_przed: '20000.00', koszt_plan_pierwotny: '20000.00' }
      expect(parseSnapshot(JSON.stringify(snap)).edycja_planu.kto).toBe('a@x.pl')
    })
  })

  describe('czyZmienioneRzeczywiste', () => {
    it('stan startowy: brak zmian', () => {
      const snap = planSnapshot()
      const edycje = { k_falownik: '', k_bateria: '', k_montaz_pv: '' }
      expect(czyZmienioneRzeczywiste(snap, edycje, [])).toBe(false)
    })

    it('wpisany koszt rzeczywisty albo nowy wiersz dodatkowy to zmiana', () => {
      const snap = planSnapshot()
      expect(czyZmienioneRzeczywiste(snap, { k_falownik: '4000', k_bateria: '', k_montaz_pv: '' }, [])).toBe(true)
      expect(czyZmienioneRzeczywiste(snap, { k_falownik: '', k_bateria: '', k_montaz_pv: '' }, [{ nazwa: '', kwota: '' }])).toBe(true)
    })
  })
})

describe('Edycja składników marży (montazKoszty, ops#339)', () => {
  function marzeSnapshot() {
    return {
      wersja: 1,
      linia_produktowa: 'pv',
      linie: [],
      skladniki_marzy: [
        { klucz: 'marza_proenergy', etykieta: 'Marża ProEnergy', kwota: '5000.00' },
        { klucz: 'narzut', etykieta: 'Narzut handlowca', kwota: '1000.00', kwota_pierwotna: '800.00' },
      ],
      podsumowanie: { netto: '30000.00', koszt_plan: '20000.00', marza_plan: '10000.00', zysk_plan: '10000.00' },
    }
  }

  it('start: zapisane kwoty jako napisy', () => {
    expect(skladnikiMarzyStart(marzeSnapshot())).toEqual({ marza_proenergy: '5000.00', narzut: '1000.00' })
    expect(skladnikiMarzyStart(null)).toEqual({})
  })

  it('bez zmian: suma i nierozdzielona marża', () => {
    const snap = marzeSnapshot()
    const w = przeliczSkladnikiMarzy(snap, skladnikiMarzyStart(snap))
    expect(w.suma).toBe(6000)
    expect(w.marzaPlan).toBe(10000)
    expect(w.nierozdzielona).toBe(4000)
    expect(w.skladniki.every((s) => !s.zmieniony)).toBe(true)
    expect(w.skladniki[1].pierwotny).toBe(800)
    expect(w.bledy).toEqual([])
  })

  it('zmiana przesuwa sumę i marżę nierozdzieloną na żywo, pierwotny z niezapisanej zmiany', () => {
    const snap = marzeSnapshot()
    const w = przeliczSkladnikiMarzy(snap, { marza_proenergy: '5 500,50', narzut: '1000.00' })
    expect(w.suma).toBe(6500.5)
    expect(w.nierozdzielona).toBe(3499.5)
    expect(w.skladniki[0].zmieniony).toBe(true)
    expect(w.skladniki[0].pierwotny).toBe(5000)
  })

  it('nierozdzielona ujemna, gdy suma przekracza marżę', () => {
    const snap = marzeSnapshot()
    expect(przeliczSkladnikiMarzy(snap, { marza_proenergy: '12000' }).nierozdzielona).toBe(-3000)
  })

  it('błędny wpis: błąd i brak zmiany, pusty: brak zmiany', () => {
    const snap = marzeSnapshot()
    const w = przeliczSkladnikiMarzy(snap, { marza_proenergy: 'abc', narzut: '' })
    expect(w.bledy).toHaveLength(1)
    expect(w.suma).toBe(6000)
  })

  it('nie mutuje argumentów', () => {
    const snap = deepFreeze(marzeSnapshot())
    const edycje = Object.freeze({ narzut: '2000' })
    expect(() => przeliczSkladnikiMarzy(snap, edycje)).not.toThrow()
    expect(() => zbudujPayloadMarz(snap, edycje)).not.toThrow()
  })

  it('payload: tylko zmienione, kwota z dwoma miejscami', () => {
    const snap = marzeSnapshot()
    const p = zbudujPayloadMarz(snap, { marza_proenergy: '5000', narzut: '1 500,5' })
    expect(p).toEqual({ skladniki: { narzut: '1500.50' } })
    expect(czyPayloadMarzMaZmiany(p)).toBe(true)
    expect(czyPayloadMarzMaZmiany(zbudujPayloadMarz(snap, skladnikiMarzyStart(snap)))).toBe(false)
    expect(czyPayloadMarzMaZmiany(null)).toBe(false)
  })
})
