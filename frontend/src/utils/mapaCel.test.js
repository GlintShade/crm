import {
  KLUCZ_CELU,
  ZOOM_CELU,
  adresBezCelu,
  czyMoznaPokazacNaMapie,
  odczytajCelMapy,
  queryBezCelu,
  trasaMapyDlaLeada,
  znajdzCel,
} from '@/utils/mapaCel'

describe('stałe', () => {
  it('zoom celu to 14, klucz query to "lead"', () => {
    expect(ZOOM_CELU).toBe(14)
    expect(KLUCZ_CELU).toBe('lead')
  })
})

describe('czyMoznaPokazacNaMapie', () => {
  it('true dla liczb niezerowych', () => {
    expect(czyMoznaPokazacNaMapie({ custom_lat: 52.1, custom_lng: 21 })).toBe(true)
  })

  it('true dla stringów z serwera', () => {
    expect(czyMoznaPokazacNaMapie({ custom_lat: '52.1', custom_lng: '21.0' })).toBe(true)
  })

  it('false dla zera, "0" i "0.0" w szerokości', () => {
    expect(czyMoznaPokazacNaMapie({ custom_lat: 0, custom_lng: 0 })).toBe(false)
    expect(czyMoznaPokazacNaMapie({ custom_lat: '0', custom_lng: '0' })).toBe(false)
    expect(czyMoznaPokazacNaMapie({ custom_lat: '0.0', custom_lng: '21' })).toBe(false)
  })

  it('false dla null, undefined i pustego obiektu', () => {
    expect(czyMoznaPokazacNaMapie(null)).toBe(false)
    expect(czyMoznaPokazacNaMapie(undefined)).toBe(false)
    expect(czyMoznaPokazacNaMapie({})).toBe(false)
  })

  it('false dla pustych stringów i nieliczbowych wartości', () => {
    expect(czyMoznaPokazacNaMapie({ custom_lat: '', custom_lng: '' })).toBe(false)
    expect(czyMoznaPokazacNaMapie({ custom_lat: 'abc', custom_lng: '21' })).toBe(false)
    expect(czyMoznaPokazacNaMapie({ custom_lat: '  ', custom_lng: '21' })).toBe(false)
  })

  it('false, gdy brakuje długości', () => {
    expect(czyMoznaPokazacNaMapie({ custom_lat: 52 })).toBe(false)
    expect(czyMoznaPokazacNaMapie({ custom_lat: 52, custom_lng: null })).toBe(false)
  })

  it('zerowa długość przy niezerowej szerokości jest dozwolona', () => {
    expect(czyMoznaPokazacNaMapie({ custom_lat: 51.5, custom_lng: 0 })).toBe(true)
  })

  it('wartości ujemne są poprawne', () => {
    expect(czyMoznaPokazacNaMapie({ custom_lat: -10, custom_lng: -20 })).toBe(true)
  })
})

describe('odczytajCelMapy', () => {
  it('zwraca nazwę z query', () => {
    expect(odczytajCelMapy({ lead: 'CRM-LEAD-2026-00001' })).toBe('CRM-LEAD-2026-00001')
  })

  it('przycina białe znaki', () => {
    expect(odczytajCelMapy({ lead: '  CRM-LEAD-2026-00001 ' })).toBe('CRM-LEAD-2026-00001')
  })

  it('null dla braku, pustego i nie-stringa', () => {
    expect(odczytajCelMapy({})).toBeNull()
    expect(odczytajCelMapy({ lead: '' })).toBeNull()
    expect(odczytajCelMapy({ lead: '   ' })).toBeNull()
    expect(odczytajCelMapy({ lead: 5 })).toBeNull()
    expect(odczytajCelMapy({ lead: null })).toBeNull()
  })

  it('null dla query null i undefined', () => {
    expect(odczytajCelMapy(null)).toBeNull()
    expect(odczytajCelMapy(undefined)).toBeNull()
  })

  it('dla tablicy bierze pierwszy niepusty element', () => {
    expect(odczytajCelMapy({ lead: ['', 'A', 'B'] })).toBe('A')
    expect(odczytajCelMapy({ lead: [null, '  ', 'B'] })).toBe('B')
    expect(odczytajCelMapy({ lead: [] })).toBeNull()
  })
})

describe('trasaMapyDlaLeada', () => {
  it('buduje trasę Leads z viewType mapa i celem w query', () => {
    expect(trasaMapyDlaLeada('L1')).toEqual({
      name: 'Leads',
      params: { viewType: 'mapa' },
      query: { lead: 'L1' },
    })
  })

  it('zachowuje istniejące query i nie mutuje wejścia', () => {
    const query = Object.freeze({ view: 'abc' })
    const trasa = trasaMapyDlaLeada('L1', query)
    expect(trasa.query).toEqual({ view: 'abc', lead: 'L1' })
    expect(query).toEqual({ view: 'abc' })
  })

  it('nadpisuje poprzedni cel', () => {
    expect(trasaMapyDlaLeada('L2', { lead: 'L1' }).query).toEqual({ lead: 'L2' })
  })

  it('każde wywołanie zwraca nowy obiekt', () => {
    expect(trasaMapyDlaLeada('L1')).not.toBe(trasaMapyDlaLeada('L1'))
  })
})

describe('queryBezCelu', () => {
  it('usuwa klucz lead i zachowuje resztę', () => {
    expect(queryBezCelu({ lead: 'L1', view: 'v' })).toEqual({ view: 'v' })
  })

  it('nie mutuje wejścia', () => {
    const query = { lead: 'L1', view: 'v' }
    queryBezCelu(query)
    expect(query).toEqual({ lead: 'L1', view: 'v' })
  })

  it('null i undefined dają pusty obiekt', () => {
    expect(queryBezCelu(null)).toEqual({})
    expect(queryBezCelu(undefined)).toEqual({})
  })

  it('bez klucza lead zwraca kopię', () => {
    const query = { view: 'v' }
    const wynik = queryBezCelu(query)
    expect(wynik).toEqual(query)
    expect(wynik).not.toBe(query)
  })
})

describe('znajdzCel', () => {
  const leady = [{ name: 'A' }, { name: 'B', status: 'Nowy' }]

  it('znajduje wiersz po nazwie', () => {
    expect(znajdzCel(leady, 'B')).toEqual({ name: 'B', status: 'Nowy' })
  })

  it('null, gdy nie ma', () => {
    expect(znajdzCel(leady, 'C')).toBeNull()
  })

  it('null dla złych wejść', () => {
    expect(znajdzCel(null, 'A')).toBeNull()
    expect(znajdzCel(undefined, 'A')).toBeNull()
    expect(znajdzCel(leady, null)).toBeNull()
    expect(znajdzCel(leady, '')).toBeNull()
    expect(znajdzCel([], 'A')).toBeNull()
  })
})

describe('adresBezCelu', () => {
  it('usuwa parametr lead z pełnego URL-a', () => {
    expect(adresBezCelu('http://crm.localhost:8080/crm/leads/view/mapa?lead=L1')).toBe(
      '/crm/leads/view/mapa',
    )
  })

  it('zachowuje pozostałe parametry i hash', () => {
    expect(adresBezCelu('/crm/leads/view/mapa?view=v1&lead=L1&x=2#h')).toBe(
      '/crm/leads/view/mapa?view=v1&x=2#h',
    )
  })

  it('bez parametru lead zwraca ten sam adres', () => {
    expect(adresBezCelu('/crm/leads/view/mapa?view=v1')).toBe('/crm/leads/view/mapa?view=v1')
  })

  it('zakodowana nazwa leada też jest usuwana', () => {
    expect(adresBezCelu('/crm/leads/view/mapa?lead=CRM%20LEAD')).toBe('/crm/leads/view/mapa')
  })
})
