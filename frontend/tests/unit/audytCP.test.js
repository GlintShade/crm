import {
  KLUCZ_ZDJECIA,
  MAX_NOTATKA,
  MAX_ZDJEC,
  SLOTY,
  brakiDoPrzeslania,
  cpAggregate,
  cpElements,
  parsujListe,
  parsujMape,
} from '@/utils/audytCP'

describe('Audyt CP — katalog i stałe', () => {
  it('ma dokładnie 7 slotów', () => {
    expect(SLOTY).toHaveLength(7)
  })

  it('ma dokładnie 5 slotów wymaganych', () => {
    expect(SLOTY.filter((slot) => slot.required)).toHaveLength(5)
  })

  it('ma unikalne klucze slotów', () => {
    const klucze = SLOTY.map((slot) => slot.key)
    expect(new Set(klucze).size).toBe(klucze.length)
  })

  it('każdy slot ma klucz i etykietę', () => {
    SLOTY.forEach((slot) => {
      expect(typeof slot.key).toBe('string')
      expect(slot.key.length).toBeGreaterThan(0)
      expect(typeof slot.label).toBe('string')
      expect(slot.label.length).toBeGreaterThan(0)
      expect(typeof slot.required).toBe('boolean')
    })
  })

  it('klucz grupy zdjęć i limity są zamrożone', () => {
    expect(KLUCZ_ZDJECIA).toBe('dok:zdjecia')
    expect(MAX_ZDJEC).toBe(20)
    expect(MAX_NOTATKA).toBe(500)
  })
})

describe('parsujMape', () => {
  it.each([null, undefined, '', '{broken', 'null', '[]', '"not a map"', 42, '42'])(
    'zwraca pustą mapę dla niepoprawnego wejścia: %p',
    (raw) => expect(parsujMape(raw)).toEqual({}),
  )

  it('parsuje mapę z surowego obiektu', () => {
    const map = { 'dok:ankieta_cp': '/files/a.pdf' }
    expect(parsujMape(map)).toEqual(map)
  })

  it('parsuje mapę zakodowaną jako JSON string', () => {
    const map = { 'dok:ankieta_cp': '/files/a.pdf', 'dok:zgoda_wspolmalzonka': '/files/b.pdf' }
    expect(parsujMape(JSON.stringify(map))).toEqual(map)
  })

  it('obsługuje podwójnie zakodowany JSON', () => {
    const map = { 'dok:ankieta_cp': '/files/a.pdf' }
    expect(parsujMape(JSON.stringify(JSON.stringify(map)))).toEqual(map)
  })

  it('traktuje śmieci (liczby, tablice) jako pustą mapę', () => {
    expect(parsujMape([1, 2, 3])).toEqual({})
    expect(parsujMape(true)).toEqual({})
  })
})

describe('parsujListe', () => {
  it.each([null, undefined, '', '{broken', 'null', '{}', '"not a list"', 42])(
    'zwraca pustą listę dla niepoprawnego wejścia: %p',
    (raw) => expect(parsujListe(raw)).toEqual([]),
  )

  it('parsuje listę z surowej tablicy', () => {
    const list = ['/files/1.jpg', '/files/2.jpg']
    expect(parsujListe(list)).toEqual(list)
  })

  it('parsuje listę zakodowaną jako JSON string', () => {
    const list = ['/files/1.jpg', '/files/2.jpg']
    expect(parsujListe(JSON.stringify(list))).toEqual(list)
  })

  it('obsługuje podwójnie zakodowany JSON', () => {
    const list = ['/files/1.jpg']
    expect(parsujListe(JSON.stringify(JSON.stringify(list)))).toEqual(list)
  })

  it('traktuje obiekt jako pustą listę', () => {
    expect(parsujListe({ a: 1 })).toEqual([])
  })
})

describe('cpElements', () => {
  it('zwraca klucze slotów z plikiem w kolejności katalogu, plus grupę zdjęć na końcu', () => {
    const dokumenty = {
      'dok:umowa_obsluga_dotacji': '/files/u.pdf',
      'dok:ankieta_cp': '/files/a.pdf',
    }
    expect(cpElements(dokumenty, ['/files/1.jpg'])).toEqual([
      'dok:ankieta_cp',
      'dok:umowa_obsluga_dotacji',
      KLUCZ_ZDJECIA,
    ])
  })

  it('wyklucza slot opcjonalny bez pliku', () => {
    const dokumenty = { 'dok:ankieta_cp': '/files/a.pdf' }
    const result = cpElements(dokumenty, [])
    expect(result).not.toContain('dok:zgoda_wspolmalzonka')
    expect(result).not.toContain('dok:zgoda_wspolwlascicieli')
  })

  it('wyklucza slot wymagany bez pliku (jeszcze nie ma czego oceniać)', () => {
    const result = cpElements({}, [])
    SLOTY.forEach((slot) => expect(result).not.toContain(slot.key))
  })

  it('grupa zdjęć jest zawsze na końcu, nawet gdy zdjęć jest zero', () => {
    const result = cpElements({}, [])
    expect(result).toEqual([KLUCZ_ZDJECIA])
  })

  it('grupa zdjęć jest zawsze na końcu przy pełnym komplecie dokumentów', () => {
    const dokumenty = Object.fromEntries(SLOTY.map((slot) => [slot.key, '/files/x.pdf']))
    const result = cpElements(dokumenty, ['/files/1.jpg'])
    expect(result.at(-1)).toBe(KLUCZ_ZDJECIA)
    expect(result).toHaveLength(SLOTY.length + 1)
  })

  it('toleruje niepoprawny kształt dokumentów', () => {
    expect(cpElements(null, [])).toEqual([KLUCZ_ZDJECIA])
    expect(cpElements('garbage', [])).toEqual([KLUCZ_ZDJECIA])
  })
})

describe('cpAggregate', () => {
  it('0 elementów nigdy nie liczy się jako w pełni zaakceptowane', () => {
    expect(cpAggregate({}, [])).toEqual({
      total: 0,
      accepted: 0,
      errors: 0,
      waiting: 0,
      allAccepted: false,
    })
  })

  it('liczy oczekujące elementy dla pustej mapy werdyktów', () => {
    const elementy = ['dok:ankieta_cp', 'dok:gops_zaswiadczenie', KLUCZ_ZDJECIA]
    expect(cpAggregate({}, elementy)).toEqual({
      total: 3,
      accepted: 0,
      errors: 0,
      waiting: 3,
      allAccepted: false,
    })
  })

  it('zwraca mieszane liczniki', () => {
    const elementy = ['dok:ankieta_cp', 'dok:gops_zaswiadczenie', KLUCZ_ZDJECIA]
    const weryfikacja = {
      'dok:ankieta_cp': { status: 'accepted' },
      'dok:gops_zaswiadczenie': { status: 'error', note: 'Nieczytelne' },
    }
    expect(cpAggregate(weryfikacja, elementy)).toEqual({
      total: 3,
      accepted: 1,
      errors: 1,
      waiting: 1,
      allAccepted: false,
    })
  })

  it('uznaje komplet za zaakceptowany tylko gdy każdy element ma werdykt "accepted"', () => {
    const elementy = ['dok:ankieta_cp', KLUCZ_ZDJECIA]
    const weryfikacja = {
      'dok:ankieta_cp': { status: 'accepted' },
      [KLUCZ_ZDJECIA]: { status: 'accepted' },
    }
    expect(cpAggregate(weryfikacja, elementy)).toEqual({
      total: 2,
      accepted: 2,
      errors: 0,
      waiting: 0,
      allAccepted: true,
    })
  })

  it('ignoruje werdykt zapisany dla elementu spoza listy', () => {
    const weryfikacja = { hidden: { status: 'accepted' }, 'dok:ankieta_cp': { status: 'accepted' } }
    expect(cpAggregate(weryfikacja, ['dok:ankieta_cp'])).toEqual({
      total: 1,
      accepted: 1,
      errors: 0,
      waiting: 0,
      allAccepted: true,
    })
  })
})

describe('brakiDoPrzeslania', () => {
  const kompletDokumentow = Object.fromEntries(
    SLOTY.filter((slot) => slot.required).map((slot) => [slot.key, '/files/x.pdf']),
  )

  it('brak braków przy komplecie wymaganych dokumentów i co najmniej jednym zdjęciu', () => {
    expect(brakiDoPrzeslania(kompletDokumentow, ['/files/1.jpg'])).toEqual([])
  })

  it('zgłasza brak każdego brakującego wymaganego dokumentu', () => {
    const bezJednego = { ...kompletDokumentow }
    delete bezJednego['dok:ankieta_cp']
    const braki = brakiDoPrzeslania(bezJednego, ['/files/1.jpg'])
    expect(braki).toHaveLength(1)
    expect(braki[0]).toContain('Ankieta danych Czyste Powietrze')
  })

  it('zgłasza braki dla wszystkich 5 wymaganych dokumentów gdy nic nie jest wgrane', () => {
    const braki = brakiDoPrzeslania({}, ['/files/1.jpg'])
    expect(braki).toHaveLength(5)
  })

  it('brak opcjonalnego dokumentu nie blokuje', () => {
    const braki = brakiDoPrzeslania(kompletDokumentow, ['/files/1.jpg'])
    expect(braki.some((b) => b.includes('współmałżonka'))).toBe(false)
    expect(braki.some((b) => b.includes('współwłaścicieli'))).toBe(false)
  })

  it('0 zdjęć blokuje przesłanie', () => {
    const braki = brakiDoPrzeslania(kompletDokumentow, [])
    expect(braki).toContain('Brak zdjęć — wymagane co najmniej 1 zdjęcie')
  })

  it('21 zdjęć blokuje przesłanie (ponad limit)', () => {
    const zdjecia = Array.from({ length: 21 }, (_, i) => `/files/${i}.jpg`)
    const braki = brakiDoPrzeslania(kompletDokumentow, zdjecia)
    expect(braki).toContain('Zbyt wiele zdjęć — maksymalnie 20')
  })

  it('20 zdjęć nie blokuje przesłania', () => {
    const zdjecia = Array.from({ length: 20 }, (_, i) => `/files/${i}.jpg`)
    expect(brakiDoPrzeslania(kompletDokumentow, zdjecia)).toEqual([])
  })

  it('toleruje niepoprawny kształt wejścia zamiast rzucać wyjątkiem', () => {
    expect(() => brakiDoPrzeslania(null, null)).not.toThrow()
    expect(brakiDoPrzeslania(null, null)).toContain('Brak zdjęć — wymagane co najmniej 1 zdjęcie')
  })
})
