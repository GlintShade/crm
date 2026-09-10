import {
  KLUCZ_GRUP,
  MAX_GRUP,
  dodajGrupe,
  dodajWarunekDoGrupy,
  liczbaWarunkowLacznie,
  polaczGrupy,
  podmienWarunekWGrupy,
  usunGrupe,
  usunWarunekZGrupy,
  wydzielGrupy,
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

describe('dodajWarunekDoGrupy / usunWarunekZGrupy / podmienWarunekWGrupy', () => {
  it('dodajWarunekDoGrupy dokłada warunek do właściwej grupy, nie mutuje', () => {
    const grupy = [['w1'], ['w2']]
    const wynik = dodajWarunekDoGrupy(grupy, 0, 'w3')
    expect(wynik).toEqual([['w1', 'w3'], ['w2']])
    expect(grupy).toEqual([['w1'], ['w2']])
  })

  it('dodajWarunekDoGrupy z indeksem poza zakresem zwraca bez zmian', () => {
    const grupy = [['w1']]
    expect(dodajWarunekDoGrupy(grupy, 3, 'w2')).toBe(grupy)
  })

  it('usunWarunekZGrupy usuwa warunek, grupa zostaje jeśli ma inne warunki', () => {
    const grupy = [['w1', 'w2']]
    const wynik = usunWarunekZGrupy(grupy, 0, 0)
    expect(wynik).toEqual([['w2']])
  })

  it('usunWarunekZGrupy usuwa CAŁĄ grupę, gdy to był ostatni warunek', () => {
    const grupy = [['jedyny'], ['inna']]
    const wynik = usunWarunekZGrupy(grupy, 0, 0)
    expect(wynik).toEqual([['inna']])
  })

  it('podmienWarunekWGrupy zamienia jeden warunek, reszta bez zmian', () => {
    const grupy = [['stary1', 'stary2']]
    const wynik = podmienWarunekWGrupy(grupy, 0, 1, 'nowy2')
    expect(wynik).toEqual([['stary1', 'nowy2']])
    expect(grupy).toEqual([['stary1', 'stary2']])
  })
})

describe('liczbaWarunkowLacznie', () => {
  it('same warunki wspólne, bez grup', () => {
    expect(liczbaWarunkowLacznie(3, [])).toBe(3)
    expect(liczbaWarunkowLacznie(3, undefined)).toBe(3)
  })

  it('wspólne plus suma warunków w grupach', () => {
    expect(liczbaWarunkowLacznie(1, [['a', 'b'], ['c']])).toBe(4)
  })

  it('zero wszędzie', () => {
    expect(liczbaWarunkowLacznie(0, [])).toBe(0)
    expect(liczbaWarunkowLacznie(undefined, undefined)).toBe(0)
  })
})

describe('MAX_GRUP jest sensownym, dodatnim limitem', () => {
  it('MAX_GRUP > 0', () => {
    expect(MAX_GRUP).toBeGreaterThan(0)
  })
})
