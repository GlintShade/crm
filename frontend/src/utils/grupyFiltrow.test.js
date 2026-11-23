import {
  KLUCZ_GRUP,
  KLUCZ_NIEAKTYWNE,
  MAX_GRUP,
  dodajGrupe,
  dodajWarunekDoGrupy,
  liczbaWarunkowLacznie,
  liczbaWierszyLacznie,
  odtworzGrupy,
  odtworzWspolne,
  polaczGrupy,
  podmienWarunekWGrupy,
  przelaczGrupe,
  przelaczWarunekWGrupie,
  uporzadkujWgPoprzednich,
  usunGrupe,
  usunWarunekZGrupy,
  wydzielGrupy,
  wydzielNieaktywne,
  zbudujPrzewod,
} from './grupyFiltrow'

describe('wydzielGrupy', () => {
  it('brak klucza grup → filtryWspolne bez zmian, grupy puste', () => {
    const filtry = { status: 'Odłożony', custom_cc: '@me' }
    expect(wydzielGrupy(filtry)).toEqual({ filtryWspolne: filtry, grupy: [] })
  })

  it('nie mutuje wejściowego obiektu', () => {
    const filtry = { status: 'Lead', [KLUCZ_GRUP]: [{ a: 1 }] }
    const kopia = { ...filtry }
    wydzielGrupy(filtry)
    expect(filtry).toEqual(kopia)
  })

  it('wydziela grupy i usuwa klucz z reszty', () => {
    const filtry = {
      custom_cc: '@me',
      [KLUCZ_GRUP]: [
        { status: 'Odłożony', custom_kolejny_kontakt: ['<=', '@dzis'] },
        { status: ['in', ['Nowy', 'Próba kontaktu']] },
      ],
    }
    const { filtryWspolne, grupy } = wydzielGrupy(filtry)
    expect(filtryWspolne).toEqual({ custom_cc: '@me' })
    expect(KLUCZ_GRUP in filtryWspolne).toBe(false)
    expect(grupy).toHaveLength(2)
    expect(grupy[0].status).toBe('Odłożony')
  })

  it('klucz obecny, ale nie jest tablicą → grupy puste', () => {
    const filtry = { status: 'Lead', [KLUCZ_GRUP]: 'nie tablica' }
    expect(wydzielGrupy(filtry).grupy).toEqual([])
  })

  it('puste/złe wejście → oba puste', () => {
    expect(wydzielGrupy(null)).toEqual({ filtryWspolne: {}, grupy: [] })
    expect(wydzielGrupy(undefined)).toEqual({ filtryWspolne: {}, grupy: [] })
    expect(wydzielGrupy({})).toEqual({ filtryWspolne: {}, grupy: [] })
  })
})

describe('polaczGrupy', () => {
  it('bez grup → tylko filtry wspólne, bez klucza grup', () => {
    const wynik = polaczGrupy({ status: 'Lead' }, [])
    expect(wynik).toEqual({ status: 'Lead' })
    expect(KLUCZ_GRUP in wynik).toBe(false)
  })

  it('grupy niepuste → dołączone pod KLUCZ_GRUP', () => {
    const grupy = [{ status: 'Odłożony' }, { status: ['in', ['Nowy']] }]
    const wynik = polaczGrupy({ custom_cc: '@me' }, grupy)
    expect(wynik).toEqual({ custom_cc: '@me', [KLUCZ_GRUP]: grupy })
  })

  it('grupy puste (0 warunków) są odsiane, klucz pominięty gdy nic nie zostało', () => {
    const wynik = polaczGrupy({ status: 'Lead' }, [{}, {}])
    expect(wynik).toEqual({ status: 'Lead' })
    expect(KLUCZ_GRUP in wynik).toBe(false)
  })

  it('mieszanka pustych i niepustych grup → tylko niepuste przechodzą', () => {
    const wynik = polaczGrupy({}, [{}, { status: 'Won' }])
    expect(wynik).toEqual({ [KLUCZ_GRUP]: [{ status: 'Won' }] })
  })

  it('nie mutuje wejściowych obiektów', () => {
    const filtryWspolne = { status: 'Lead' }
    const grupy = [{ status: 'Won' }]
    polaczGrupy(filtryWspolne, grupy)
    expect(filtryWspolne).toEqual({ status: 'Lead' })
    expect(grupy).toEqual([{ status: 'Won' }])
  })

  it('filtryWspolne/grupy puste lub null → pusty obiekt', () => {
    expect(polaczGrupy(null, null)).toEqual({})
    expect(polaczGrupy(undefined, undefined)).toEqual({})
  })

  it('round-trip z wydzielGrupy odtwarza oryginał (poza kluczami undefined)', () => {
    const oryginal = {
      custom_cc: '@me',
      [KLUCZ_GRUP]: [
        { status: 'Odłożony', custom_kolejny_kontakt: ['<=', '@dzis'] },
        { status: ['in', ['Nowy', 'Próba kontaktu']] },
      ],
    }
    const { filtryWspolne, grupy } = wydzielGrupy(oryginal)
    expect(polaczGrupy(filtryWspolne, grupy)).toEqual(oryginal)
  })
})

describe('dodajGrupe / usunGrupe', () => {
  it('dodajGrupe dokłada na końcu, nie mutuje', () => {
    const grupy = [['a']]
    const wynik = dodajGrupe(grupy, ['b'])
    expect(wynik).toEqual([['a'], ['b']])
    expect(grupy).toEqual([['a']])
  })

  it('dodajGrupe na pustym/undefined wejściu', () => {
    expect(dodajGrupe(undefined, ['a'])).toEqual([['a']])
    expect(dodajGrupe([], ['a'])).toEqual([['a']])
  })

  it('usunGrupe usuwa po indeksie, nie mutuje', () => {
    const grupy = [['a'], ['b'], ['c']]
    const wynik = usunGrupe(grupy, 1)
    expect(wynik).toEqual([['a'], ['c']])
    expect(grupy).toHaveLength(3)
  })

  it('usunGrupe z indeksem poza zakresem zwraca kopię bez zmian', () => {
    const grupy = [['a']]
    expect(usunGrupe(grupy, 5)).toEqual([['a']])
  })
})

const G = (...warunki) => ({ wylaczona: false, warunki })

describe('dodajWarunekDoGrupy / usunWarunekZGrupy / podmienWarunekWGrupy', () => {
  it('dodajWarunekDoGrupy dokłada warunek do właściwej grupy, nie mutuje', () => {
    const grupy = [G('w1'), G('w2')]
    const wynik = dodajWarunekDoGrupy(grupy, 0, 'w3')
    expect(wynik.map((g) => g.warunki)).toEqual([['w1', 'w3'], ['w2']])
    expect(grupy[0].warunki).toEqual(['w1'])
  })

  it('dodajWarunekDoGrupy z indeksem poza zakresem zwraca bez zmian', () => {
    const grupy = [G('w1')]
    expect(dodajWarunekDoGrupy(grupy, 3, 'w2')).toBe(grupy)
  })

  it('dodajWarunekDoGrupy zachowuje flagę wylaczona grupy', () => {
    const grupy = [{ wylaczona: true, warunki: ['w1'] }]
    expect(dodajWarunekDoGrupy(grupy, 0, 'w2')[0].wylaczona).toBe(true)
  })

  it('usunWarunekZGrupy usuwa warunek, grupa zostaje jeśli ma inne warunki', () => {
    expect(usunWarunekZGrupy([G('w1', 'w2')], 0, 0)[0].warunki).toEqual(['w2'])
  })

  it('usunWarunekZGrupy usuwa CAŁĄ grupę, gdy to był ostatni warunek', () => {
    const wynik = usunWarunekZGrupy([G('jedyny'), G('inna')], 0, 0)
    expect(wynik).toHaveLength(1)
    expect(wynik[0].warunki).toEqual(['inna'])
  })

  it('podmienWarunekWGrupy zamienia jeden warunek, reszta bez zmian', () => {
    const grupy = [G('stary1', 'stary2')]
    const wynik = podmienWarunekWGrupy(grupy, 0, 1, 'nowy2')
    expect(wynik[0].warunki).toEqual(['stary1', 'nowy2'])
    expect(grupy[0].warunki).toEqual(['stary1', 'stary2'])
  })
})

const W = (fieldname, extra = {}) => ({ fieldname, operator: 'equals', value: fieldname, ...extra })

describe('przelaczGrupe / przelaczWarunekWGrupie (ops#410)', () => {
  it('przelaczGrupe odwraca flagę tylko wskazanej grupy, nie mutuje', () => {
    const grupy = [G(W('a')), G(W('b'))]
    const wynik = przelaczGrupe(grupy, 1)
    expect(wynik.map((g) => g.wylaczona)).toEqual([false, true])
    expect(grupy[1].wylaczona).toBe(false)
    expect(przelaczGrupe(wynik, 1)[1].wylaczona).toBe(false)
  })

  it('przelaczWarunekWGrupie zmienia tylko ten warunek i nie rusza flagi grupy', () => {
    const grupy = [G(W('a'), W('b'))]
    const wynik = przelaczWarunekWGrupie(grupy, 0, 1)
    expect(wynik[0].warunki.map((w) => !!w.nieaktywny)).toEqual([false, true])
    expect(wynik[0].wylaczona).toBe(false)
    expect(grupy[0].warunki[1].nieaktywny).toBeUndefined()
  })

  it('przelaczWarunekWGrupie poza zakresem zwraca bez zmian', () => {
    const grupy = [G(W('a'))]
    expect(przelaczWarunekWGrupie(grupy, 0, 5)).toBe(grupy)
    expect(przelaczWarunekWGrupie(grupy, 4, 0)).toBe(grupy)
  })
})

describe('liczbaWarunkowLacznie (tylko aktywne)', () => {
  it('same warunki wspólne, bez grup', () => {
    expect(liczbaWarunkowLacznie([W('a'), W('b'), W('c')], [])).toBe(3)
    expect(liczbaWarunkowLacznie(new Set([W('a')]), undefined)).toBe(1)
  })

  it('wspólne plus warunki w grupach', () => {
    expect(liczbaWarunkowLacznie([W('x')], [G(W('a'), W('b')), G(W('c'))])).toBe(4)
  })

  it('pomija wiersze nieaktywne i całe grupy wyłączone', () => {
    const grupy = [
      G(W('a'), W('b', { nieaktywny: true })),
      { wylaczona: true, warunki: [W('c'), W('d')] },
    ]
    expect(liczbaWarunkowLacznie([W('x', { nieaktywny: true }), W('y')], grupy)).toBe(2)
  })

  it('zero wszędzie', () => {
    expect(liczbaWarunkowLacznie([], [])).toBe(0)
    expect(liczbaWarunkowLacznie(undefined, undefined)).toBe(0)
  })

  it('liczbaWierszyLacznie liczy też wyłączone', () => {
    const grupy = [{ wylaczona: true, warunki: [W('c')] }]
    expect(liczbaWierszyLacznie([W('x', { nieaktywny: true })], grupy)).toBe(2)
  })
})

// Przewód testowy: słownik {pole: wartość} z tablicy wierszy.
const doPrzewodu = (wiersze) => Object.fromEntries(wiersze.map((w) => [w.fieldname, w.value]))
const doWierszy = (slownik) => Object.entries(slownik).map(([k, v]) => W(k, { value: v }))

describe('zbudujPrzewod (ops#410)', () => {
  it('bez niczego wyłączonego kształt jest taki jak sprzed zmiany', () => {
    const wynik = zbudujPrzewod([W('a')], [G(W('b')), G(W('c'))], doPrzewodu)
    expect(wynik).toEqual({ a: 'a', [KLUCZ_GRUP]: [{ b: 'b' }, { c: 'c' }] })
    expect(wynik[KLUCZ_NIEAKTYWNE]).toBeUndefined()
  })

  it('wiersz wspólny wyłączony: poza filtrami, w KLUCZ_NIEAKTYWNE', () => {
    const wynik = zbudujPrzewod([W('a'), W('b', { nieaktywny: true })], [], doPrzewodu)
    expect(wynik.a).toBe('a')
    expect(wynik.b).toBeUndefined()
    expect(wynik[KLUCZ_NIEAKTYWNE]).toEqual({ wspolne: { b: 'b' } })
  })

  it('grupa wyłączona znika z volteo_grupy, zostaje w zrzucie z własnymi flagami', () => {
    const grupy = [
      G(W('a')),
      { wylaczona: true, warunki: [W('b'), W('c', { nieaktywny: true })] },
    ]
    const wynik = zbudujPrzewod([], grupy, doPrzewodu)
    expect(wynik[KLUCZ_GRUP]).toEqual([{ a: 'a' }])
    expect(wynik[KLUCZ_NIEAKTYWNE].grupy).toEqual([
      { wylaczona: false, warunki: { a: 'a' }, wylaczone: [] },
      { wylaczona: true, warunki: { b: 'b', c: 'c' }, wylaczone: ['c'] },
    ])
  })

  it('wszystkie grupy wyłączone: bez volteo_grupy, tylko filtry wspólne', () => {
    const wynik = zbudujPrzewod([W('a')], [{ wylaczona: true, warunki: [W('b')] }], doPrzewodu)
    expect(wynik[KLUCZ_GRUP]).toBeUndefined()
    expect(wynik.a).toBe('a')
  })

  it('grupa z jedynym warunkiem wyłączonym nie trafia do volteo_grupy', () => {
    const wynik = zbudujPrzewod([], [G(W('a', { nieaktywny: true }))], doPrzewodu)
    expect(wynik[KLUCZ_GRUP]).toBeUndefined()
    expect(wynik[KLUCZ_NIEAKTYWNE].grupy[0].wylaczone).toEqual(['a'])
  })

  it('pomin wyklucza wiersz z obu części', () => {
    const wynik = zbudujPrzewod(
      [W('a', { nieaktywny: true }), W('b')],
      [],
      doPrzewodu,
      (w) => w.fieldname === 'a',
    )
    expect(wynik).toEqual({ b: 'b' })
  })
})

describe('odtworzGrupy / odtworzWspolne / wydzielNieaktywne (ops#410)', () => {
  it('przewód z zbudujPrzewod wraca do tego samego stanu grup', () => {
    const grupy = [
      G(W('a')),
      { wylaczona: true, warunki: [W('b'), W('c', { nieaktywny: true })] },
    ]
    const odtworzone = odtworzGrupy(zbudujPrzewod([], grupy, doPrzewodu), doWierszy)
    expect(odtworzone.map((g) => g.wylaczona)).toEqual([false, true])
    expect(odtworzone[1].warunki.map((w) => [w.fieldname, !!w.nieaktywny])).toEqual([
      ['b', false],
      ['c', true],
    ])
  })

  it('stary zapis bez klucza: grupy z volteo_grupy, wszystko aktywne', () => {
    const odtworzone = odtworzGrupy({ [KLUCZ_GRUP]: [{ a: 1 }, { b: 2 }] }, doWierszy)
    expect(odtworzone.map((g) => g.wylaczona)).toEqual([false, false])
    expect(odtworzone[0].warunki[0].nieaktywny).toBeUndefined()
    expect(odtworzGrupy({}, doWierszy)).toEqual([])
  })

  it('uszkodzony klucz (zły kształt) jest ignorowany', () => {
    expect(wydzielNieaktywne({ [KLUCZ_NIEAKTYWNE]: 'x' })).toEqual({ wspolne: {}, grupy: null })
    expect(wydzielNieaktywne({ [KLUCZ_NIEAKTYWNE]: { grupy: 5, wspolne: [] } })).toEqual({
      wspolne: {},
      grupy: null,
    })
    expect(wydzielNieaktywne(null)).toEqual({ wspolne: {}, grupy: null })
  })

  it('odtworzWspolne dokleja wyłączone, aktywne w echu wygrywa', () => {
    const filtry = { [KLUCZ_NIEAKTYWNE]: { wspolne: { b: 'b', a: 'stare' } } }
    const wynik = odtworzWspolne([W('a', { value: 'nowe' })], filtry, doWierszy)
    expect(wynik.map((w) => [w.fieldname, w.value, !!w.nieaktywny])).toEqual([
      ['a', 'nowe', false],
      ['b', 'b', true],
    ])
  })

  it('wydzielGrupy usuwa też KLUCZ_NIEAKTYWNE z filtrów wspólnych', () => {
    const { filtryWspolne } = wydzielGrupy({ a: 1, [KLUCZ_NIEAKTYWNE]: { wspolne: { b: 2 } } })
    expect(filtryWspolne).toEqual({ a: 1 })
  })

  it('uporzadkujWgPoprzednich trzyma dotychczasową kolejność, nowe na końcu', () => {
    const wynik = uporzadkujWgPoprzednich([W('c'), W('a'), W('z')], [W('a'), W('b'), W('c')])
    expect(wynik.map((w) => w.fieldname)).toEqual(['a', 'c', 'z'])
  })
})

describe('MAX_GRUP jest sensownym, dodatnim limitem', () => {
  it('MAX_GRUP > 0', () => {
    expect(MAX_GRUP).toBeGreaterThan(0)
  })
})
