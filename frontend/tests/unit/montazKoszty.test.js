import {
  parsujKosztRzeczywisty,
  parseSnapshot,
  przeliczRzeczywiste,
  zbudujPayload,
  przeliczSkladnikiMarzy,
  etykietaKosztu,
  opisEdycjiRecznych,
  czytajZwiniecieKosztow,
  zapiszZwiniecieKosztow,
  KLUCZ_ZWINIECIA_KOSZTOW,
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

describe('Linia korekty i dane planu (montazKoszty)', () => {
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

  it('bez zmian: suma i nierozdzielona marża', () => {
    const snap = marzeSnapshot()
    const w = przeliczSkladnikiMarzy(snap, {})
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
  })
})

describe('etykietaKosztu', () => {
  it('mapuje znane klucze na etykiety do wyświetlenia', () => {
    expect(etykietaKosztu('k_montaz_pv', 'x')).toBe('Montaż PV')
    expect(etykietaKosztu('k_montaz_mag', 'x')).toBe('Montaż magazynu')
    expect(etykietaKosztu('kilometrowka', 'x')).toBe('Kilometrówka')
    expect(etykietaKosztu('k_spoldzielnia', 'x')).toBe('Spółdzielnia energetyczna')
    expect(etykietaKosztu('k_ppoz', 'x')).toBe('Uzgodnienia PPOŻ')
    expect(etykietaKosztu('k_ev', 'x')).toBe('Dodatek ładowarka EV')
    expect(etykietaKosztu('marza_proenergy', 'x')).toBe('Marża ProEnergy')
    expect(etykietaKosztu('marza_sps', 'x')).toBe('Marża SPS')
    expect(etykietaKosztu('bonus_liderki', 'x')).toBe('Bonus liderski')
    expect(etykietaKosztu('marza_dodatki', 'x')).toBe('Marża dodatki')
  })

  it('nieznany klucz zwraca zapisaną etykietę, a bez niej klucz', () => {
    expect(etykietaKosztu('k_falownik', 'Falownik')).toBe('Falownik')
    expect(etykietaKosztu('k_inny')).toBe('k_inny')
  })

  it('przeliczRzeczywiste i przeliczSkladnikiMarzy używają etykiet z mapy', () => {
    const snap = {
      wersja: 1,
      linia_produktowa: 'oze',
      linie: [{ klucz: 'bonus_liderki', etykieta: 'bonus_liderki', koszt_plan: '100.00' }],
      skladniki_marzy: [{ klucz: 'marza_sps', etykieta: 'Marza SPS', kwota: '50.00' }],
      podsumowanie: { netto: '1000.00', koszt_plan: '100.00', marza_plan: '900.00' },
    }
    expect(przeliczRzeczywiste(snap, {}, []).linie[0].etykieta).toBe('Bonus liderski')
    expect(przeliczSkladnikiMarzy(snap, {}).skladniki[0].etykieta).toBe('Marża SPS')
  })
})

describe('opisEdycjiRecznych', () => {
  const opcje = {
    formatujDate: (d) => `D(${d})`,
    nazwaUzytkownika: (k) => `U(${k})`,
    formatPln: (n) => `${n} zł`,
  }
  const baza = (extra) => ({ podsumowanie: { netto: '1000.00', koszt_plan: '600.00' }, ...extra })

  it('nic nie ustawione: pusta lista', () => {
    expect(opisEdycjiRecznych(baza({}), opcje)).toEqual([])
    expect(opisEdycjiRecznych(null, opcje)).toEqual([])
  })

  it('tylko edycja_reczna z powodem i bez zmiany ceny: jedna linia', () => {
    const s = baza({ edycja_reczna: { kiedy: '2026-11-13 12:00:00', kto: 'a', powod: 'Aneks', netto_przed: '1000.00' } })
    expect(opisEdycjiRecznych(s, opcje)).toEqual(['Zestaw, koszty lub marże zmienione ręcznie D(2026-11-13 12:00:00) (U(a)). Powód: Aneks.'])
  })

  it('zmieniona cena: druga linia', () => {
    const s = baza({ edycja_reczna: { kiedy: '2026-11-13 12:00:00', kto: 'a', powod: '', netto_przed: '900.00' } })
    const l = opisEdycjiRecznych(s, opcje)
    expect(l).toHaveLength(2)
    expect(l[0]).not.toContain('Powód')
    expect(l[1]).toBe('Cena netto przed zmianą: 900 zł.')
  })

  it('zmieniona suma planu: linia z pierwotną sumą', () => {
    const s = baza({ edycja_planu: { kiedy: '2026-11-13 12:00:00', kto: 'b', koszt_plan_pierwotny: '500.00' } })
    expect(opisEdycjiRecznych(s, opcje)).toEqual([
      'Zestaw, koszty lub marże zmienione ręcznie D(2026-11-13 12:00:00) (U(b)).',
      'Pierwotna suma kosztów planowanych: 500 zł.',
    ])
  })

  it('najnowsza z trzech wyznacza datę i osobę', () => {
    const s = baza({
      edycja_reczna: { kiedy: '2026-11-13 10:00:00', kto: 'a' },
      edycja_planu: { kiedy: '2026-11-13 11:00:00', kto: 'b' },
      edycja_marzy: { kiedy: '2026-11-13 09:00:00', kto: 'c' },
    })
    expect(opisEdycjiRecznych(s, opcje)[0]).toContain('(U(b))')
  })
})

describe('zwinięcie panelu kosztów (localStorage)', () => {
  const magazyn = (start = {}) => {
    const dane = { ...start }
    return { dane, getItem: (k) => (k in dane ? dane[k] : null), setItem: (k, v) => { dane[k] = String(v) } }
  }

  it('klucz brakujący: domyślnie rozwinięty', () => {
    expect(KLUCZ_ZWINIECIA_KOSZTOW).toBe('volteo_koszty_marza_zwiniety')
    expect(czytajZwiniecieKosztow(magazyn())).toBe(false)
    expect(czytajZwiniecieKosztow(null)).toBe(false)
  })

  it('"1" zwinięty, "0" rozwinięty', () => {
    expect(czytajZwiniecieKosztow(magazyn({ [KLUCZ_ZWINIECIA_KOSZTOW]: '1' }))).toBe(true)
    expect(czytajZwiniecieKosztow(magazyn({ [KLUCZ_ZWINIECIA_KOSZTOW]: '0' }))).toBe(false)
  })

  it('zapis i odczyt razem', () => {
    const m = magazyn()
    zapiszZwiniecieKosztow(m, true)
    expect(m.dane[KLUCZ_ZWINIECIA_KOSZTOW]).toBe('1')
    zapiszZwiniecieKosztow(m, false)
    expect(m.dane[KLUCZ_ZWINIECIA_KOSZTOW]).toBe('0')
  })

  it('getItem rzuca: domyślny stan, bez wyjątku', () => {
    const m = { getItem() { throw new Error('zablokowany') }, setItem() {} }
    expect(czytajZwiniecieKosztow(m)).toBe(false)
  })

  it('setItem rzuca: bez wyjątku', () => {
    const m = { getItem: () => null, setItem() { throw new Error('pełny') } }
    expect(() => zapiszZwiniecieKosztow(m, true)).not.toThrow()
  })
})
