import {
  DOMYSLNE_KLASTROWANIE,
  DOMYSLNY_TRYB_KOLOROWANIA,
  KOLOR_BRAK,
  domyslneUstawieniaDymka,
  hashString,
  kolorDlaUzytkownika,
  legenda,
  poleObecneWDanych,
  wczytajKlastrowanie,
  wczytajTrybKolorowania,
  wczytajUstawieniaDymka,
  zapiszKlastrowanie,
  zapiszTrybKolorowania,
  zapiszUstawieniaDymka,
} from '@/utils/mapaKolory'

beforeEach(() => {
  localStorage.clear()
})

describe('hashString', () => {
  it('jest deterministyczny dla tego samego wejścia', () => {
    expect(hashString('rep@proenergy.pro')).toBe(hashString('rep@proenergy.pro'))
  })

  it('rozróżnia różne wejścia (nie jest stałą)', () => {
    expect(hashString('a@proenergy.pro')).not.toBe(hashString('b@proenergy.pro'))
  })

  it('nie wybucha na pustym/undefined wejściu', () => {
    expect(hashString('')).toBe(0)
    expect(hashString(undefined)).toBe(0)
  })
})

describe('kolorDlaUzytkownika', () => {
  it('zwraca ten sam kolor dla tego samego e-maila', () => {
    const a = kolorDlaUzytkownika('rep@proenergy.pro')
    const b = kolorDlaUzytkownika('rep@proenergy.pro')
    expect(a).toBe(b)
  })

  it('zwraca hex (na canvas Leafleta), nie klasę Tailwind', () => {
    expect(kolorDlaUzytkownika('rep@proenergy.pro')).toMatch(/^#[0-9a-f]{6}$/)
  })

  it('różni się dla różnych użytkowników (zazwyczaj)', () => {
    const kolory = new Set([
      kolorDlaUzytkownika('a@proenergy.pro'),
      kolorDlaUzytkownika('b@proenergy.pro'),
      kolorDlaUzytkownika('c@proenergy.pro'),
      kolorDlaUzytkownika('d@proenergy.pro'),
    ])
    expect(kolory.size).toBeGreaterThan(1)
  })

  it('brak e-maila daje KOLOR_BRAK', () => {
    expect(kolorDlaUzytkownika('')).toBe(KOLOR_BRAK)
    expect(kolorDlaUzytkownika(null)).toBe(KOLOR_BRAK)
  })
})

function lead(overrides) {
  return {
    status: 'Nowy',
    lead_owner: 'rep@proenergy.pro',
    custom_cc: 'cc@proenergy.pro',
    ...overrides,
  }
}

describe('legenda', () => {
  it('grupuje po statusie i liczy leady', () => {
    const leady = [lead({ status: 'Nowy' }), lead({ status: 'Nowy' }), lead({ status: 'Umówiony' })]
    const wynik = legenda(leady, 'status')
    expect(wynik).toEqual([
      { klucz: 'Nowy', liczba: 2, kolor: KOLOR_BRAK },
      { klucz: 'Umówiony', liczba: 1, kolor: KOLOR_BRAK },
    ])
  })

  it('używa kolorStatusu() gdy przekazane', () => {
    const leady = [lead({ status: 'Nowy' })]
    const kolorStatusu = (s) => (s === 'Nowy' ? '#111111' : '#222222')
    const wynik = legenda(leady, 'status', { kolorStatusu })
    expect(wynik[0].kolor).toBe('#111111')
  })

  it('grupuje po handlowcu (lead_owner) i koloruje z palety użytkowników', () => {
    const leady = [
      lead({ lead_owner: 'a@proenergy.pro' }),
      lead({ lead_owner: 'a@proenergy.pro' }),
      lead({ lead_owner: 'b@proenergy.pro' }),
    ]
    const wynik = legenda(leady, 'handlowiec')
    expect(wynik[0]).toEqual({
      klucz: 'a@proenergy.pro',
      liczba: 2,
      kolor: kolorDlaUzytkownika('a@proenergy.pro'),
    })
  })

  it('grupuje po CC (custom_cc)', () => {
    const leady = [lead({ custom_cc: 'cc1@proenergy.pro' }), lead({ custom_cc: 'cc2@proenergy.pro' })]
    const wynik = legenda(leady, 'cc')
    expect(wynik.map((w) => w.klucz).sort()).toEqual(['cc1@proenergy.pro', 'cc2@proenergy.pro'])
  })

  it('leady bez wartości trafiają pod etykietę brakEtykiety z kolorem KOLOR_BRAK', () => {
    const leady = [lead({ lead_owner: '' }), lead({ lead_owner: '' })]
    const wynik = legenda(leady, 'handlowiec', { brakEtykiety: '(brak)' })
    expect(wynik).toEqual([{ klucz: '(brak)', liczba: 2, kolor: KOLOR_BRAK }])
  })

  it('sortuje malejąco po liczbie', () => {
    const leady = [
      lead({ lead_owner: 'a@proenergy.pro' }),
      lead({ lead_owner: 'b@proenergy.pro' }),
      lead({ lead_owner: 'b@proenergy.pro' }),
      lead({ lead_owner: 'b@proenergy.pro' }),
    ]
    const wynik = legenda(leady, 'handlowiec')
    expect(wynik[0].klucz).toBe('b@proenergy.pro')
    expect(wynik[0].liczba).toBe(3)
  })

  it('pusta lista daje pustą legendę', () => {
    expect(legenda([], 'handlowiec')).toEqual([])
    expect(legenda(undefined, 'status')).toEqual([])
  })
})

describe('poleObecneWDanych', () => {
  it('true gdy pole jest w pierwszym leadzie', () => {
    expect(poleObecneWDanych([{ custom_cc: 'x@proenergy.pro' }], 'custom_cc')).toBe(true)
  })

  it('true nawet gdy wartość pola jest pusta/null (klucz istnieje)', () => {
    expect(poleObecneWDanych([{ custom_cc: null }], 'custom_cc')).toBe(true)
  })

  it('false gdy klucz nie istnieje w odpowiedzi (permlevel wyciął pole)', () => {
    expect(poleObecneWDanych([{ status: 'Nowy' }], 'custom_cc')).toBe(false)
  })

  it('false gdy lista pusta', () => {
    expect(poleObecneWDanych([], 'custom_cc')).toBe(false)
  })
})

describe('trwałość ustawień w localStorage', () => {
  it('domyślny tryb kolorowania to status, gdy nic nie zapisano', () => {
    expect(wczytajTrybKolorowania()).toBe(DOMYSLNY_TRYB_KOLOROWANIA)
  })

  it('zapisany tryb wraca po odczycie', () => {
    zapiszTrybKolorowania('handlowiec')
    expect(wczytajTrybKolorowania()).toBe('handlowiec')
  })

  it('nieznana wartość w localStorage nie wybucha, wraca domyślny tryb', () => {
    localStorage.setItem('volteo.mapa.kolor', 'coś-nieznanego')
    expect(wczytajTrybKolorowania()).toBe(DOMYSLNY_TRYB_KOLOROWANIA)
  })

  it('domyślne ustawienia dymka mają wszystkie pola włączone', () => {
    expect(wczytajUstawieniaDymka()).toEqual(domyslneUstawieniaDymka())
  })

  it('zapisane ustawienia dymka wracają po odczycie', () => {
    zapiszUstawieniaDymka({ zrodlo: false, produkty: true, statusZrodla: false, terminSpotkania: true })
    expect(wczytajUstawieniaDymka()).toEqual({
      zrodlo: false,
      produkty: true,
      statusZrodla: false,
      terminSpotkania: true,
    })
  })

  it('uszkodzony JSON w localStorage nie wybucha, wraca domyślne', () => {
    localStorage.setItem('volteo.mapa.dymek', '{nie-json')
    expect(wczytajUstawieniaDymka()).toEqual(domyslneUstawieniaDymka())
  })

  it('częściowo zapisane ustawienia dopełnia domyślnymi', () => {
    localStorage.setItem('volteo.mapa.dymek', JSON.stringify({ zrodlo: false }))
    expect(wczytajUstawieniaDymka()).toEqual({
      zrodlo: false,
      produkty: true,
      statusZrodla: true,
      terminSpotkania: true,
    })
  })

  it('domyślnie klastrowanie jest wyłączone, gdy nic nie zapisano', () => {
    expect(wczytajKlastrowanie()).toBe(DOMYSLNE_KLASTROWANIE)
    expect(wczytajKlastrowanie()).toBe(false)
  })

  it('zapisane włączenie klastrowania wraca po odczycie', () => {
    zapiszKlastrowanie(true)
    expect(wczytajKlastrowanie()).toBe(true)
  })

  it('zapisane wyłączenie klastrowania wraca po odczycie', () => {
    zapiszKlastrowanie(true)
    zapiszKlastrowanie(false)
    expect(wczytajKlastrowanie()).toBe(false)
  })

  it('uszkodzona wartość w localStorage nie wybucha, wraca domyślne ustawienie', () => {
    localStorage.setItem('volteo.mapa.klastrowanie', 'coś-nieznanego')
    expect(wczytajKlastrowanie()).toBe(DOMYSLNE_KLASTROWANIE)
  })
})
