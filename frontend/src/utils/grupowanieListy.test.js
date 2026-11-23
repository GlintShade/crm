import { describe, it, expect } from 'vitest'
import {
  STAN_PUSTY,
  czyZwinieta,
  dlugoscStrony,
  inicjaly,
  parsujStan,
  podsumowanie,
  powiekszStrone,
  przelaczZwiniecie,
  rozwinWszystkie,
  serializujStan,
  stanZWidoku,
  typTrasyWidoku,
  ustawPokazPuste,
  ustawPole,
  wierszeGrup,
  zbudujGrupy,
  zwinWszystkie,
} from './grupowanieListy'

const POLA = ['status', 'deal_owner']

describe('stan: parsowanie i zapis', () => {
  it('zle dane daja stan pusty', () => {
    expect(parsujStan('', POLA).pole).toBeNull()
    expect(parsujStan('{nie json', POLA).pole).toBeNull()
    expect(parsujStan('[1]', POLA).pole).toBeNull()
    expect(parsujStan(null, POLA).pole).toBeNull()
  })
  it('pole spoza dozwolonych jest odrzucone (np. rola straciła permlevel)', () => {
    const raw = JSON.stringify({ pole: 'custom_status_osd', zwiniete: ['x'] })
    expect(parsujStan(raw, POLA)).toEqual({ pole: null, pokazPuste: false, zwiniete: [] })
  })
  it('round trip', () => {
    const stan = { pole: 'status', pokazPuste: true, zwiniete: ['Lead', ''] }
    expect(parsujStan(serializujStan(stan), POLA)).toEqual(stan)
  })
  it('wylaczone grupowanie serializuje sie do pustego tekstu', () => {
    expect(serializujStan(STAN_PUSTY)).toBe('')
  })
})

describe('stanZWidoku i stare widoki group_by', () => {
  it('zapisany stan wygrywa', () => {
    const w = { volteo_grupowanie: JSON.stringify({ pole: 'deal_owner' }), type: 'group_by', group_by_field: 'status' }
    expect(stanZWidoku(w, POLA).pole).toBe('deal_owner')
  })
  it('stary widok group_by otwiera sie jako lista z polem grupy', () => {
    expect(stanZWidoku({ type: 'group_by', group_by_field: 'status' }, POLA).pole).toBe('status')
  })
  it('stary widok z polem spoza listy: bez grupowania', () => {
    expect(stanZWidoku({ type: 'group_by', group_by_field: 'owner' }, POLA).pole).toBeNull()
  })
  it('domyslne group_by_field "owner" zwyklej listy nie wlacza grupowania', () => {
    expect(stanZWidoku({ type: 'list', group_by_field: 'status' }, POLA).pole).toBeNull()
  })
  it('przekierowanie ze starej trasy', () => {
    expect(stanZWidoku(null, POLA, 'deal_owner').pole).toBe('deal_owner')
    expect(stanZWidoku(null, POLA, 'obce').pole).toBeNull()
  })
  it('typ trasy', () => {
    expect(typTrasyWidoku('group_by')).toBe('list')
    expect(typTrasyWidoku('kanban')).toBe('kanban')
  })
})

describe('zmiany stanu sa niemutujace', () => {
  it('zmiana pola zeruje zwiniete, zachowuje pokaz puste', () => {
    const s = { pole: 'status', pokazPuste: true, zwiniete: ['Lead'] }
    const n = ustawPole(s, 'deal_owner')
    expect(n).toEqual({ pole: 'deal_owner', pokazPuste: true, zwiniete: [] })
    expect(s.zwiniete).toEqual(['Lead'])
  })
  it('przelaczanie zwiniecia, takze pustej grupy', () => {
    let s = { pole: 'status', pokazPuste: false, zwiniete: [] }
    s = przelaczZwiniecie(s, '')
    expect(czyZwinieta(s, '')).toBe(true)
    s = przelaczZwiniecie(s, '')
    expect(czyZwinieta(s, '')).toBe(false)
  })
  it('zwin i rozwin wszystkie', () => {
    const s = { pole: 'status', pokazPuste: false, zwiniete: [] }
    const z = zwinWszystkie(s, ['a', 'b'])
    expect(z.zwiniete).toEqual(['a', 'b'])
    expect(rozwinWszystkie(z).zwiniete).toEqual([])
    expect(ustawPokazPuste(s, true).pokazPuste).toBe(true)
    expect(s.pokazPuste).toBe(false)
  })
})

describe('strony per grupa', () => {
  it('domyslnie rozmiar z paska, kolejne o jeden rozmiar', () => {
    expect(dlugoscStrony({}, 'a', 20)).toBe(20)
    const s1 = powiekszStrone({}, 'a', 20)
    expect(s1.a).toBe(40)
    expect(powiekszStrone(s1, 'a', 20).a).toBe(60)
    expect(powiekszStrone(s1, 'b', 20).b).toBe(40)
    expect(s1.b).toBeUndefined()
  })
})

describe('budowanie grup', () => {
  const grupy = [
    { klucz: 'Lead', etykieta: 'Lead', licznik: 57, pusta: false },
    { klucz: 'Montaż', etykieta: 'Montaż', licznik: 3, pusta: false },
    { klucz: '', etykieta: 'Brak wartości', licznik: 2, pusta: true },
  ]
  const stan = { pole: 'status', pokazPuste: false, zwiniete: ['Montaż'] }
  const dane = {
    Lead: { wiersze: [{ name: 'a' }, { name: 'b' }], wczytuje: false },
    Montaż: { wiersze: [{ name: 'x' }], wczytuje: false },
  }
  it('licznik jest z serwera, wiersze tylko dla rozwinietych', () => {
    const z = zbudujGrupy(grupy, stan, dane, 'status')
    expect(z[0]).toMatchObject({ licznik: 57, maWiecej: true, zwinieta: false })
    expect(z[0].wiersze).toHaveLength(2)
    expect(z[1]).toMatchObject({ zwinieta: true, maWiecej: false })
    expect(z[1].wiersze).toEqual([])
    expect(z[2]).toMatchObject({ pusta: true, maWiecej: true, wiersze: [] })
  })
  it('wierszeGrup daje klucz grupy nawet dla pustej wartosci i wola akcje', () => {
    const wywolania = []
    const w = wierszeGrup(zbudujGrupy(grupy, stan, dane), (r) => r.map((x) => x.name), {
      przelacz: (k) => wywolania.push(['p', k]),
      wiecej: (k) => wywolania.push(['w', k]),
    })
    expect(w.map((g) => g.group)).toEqual(['g:Lead', 'g:Montaż', 'g:'])
    expect(w[0].rows).toEqual(['a', 'b'])
    expect(w[2].group).toBeTruthy()
    w[0].onToggle()
    w[0].onMore()
    expect(wywolania).toEqual([['p', 'Lead'], ['w', 'Lead']])
  })
  it('podsumowanie', () => {
    expect(podsumowanie(grupy)).toEqual({ razem: 62, liczbaGrup: 3 })
    expect(podsumowanie(null)).toEqual({ razem: 0, liczbaGrup: 0 })
  })
})

describe('inicjaly', () => {
  it('z nazwy i e-maila', () => {
    expect(inicjaly('Marek Sowa')).toBe('MS')
    expect(inicjaly('ewa.lis@proenergy.pro')).toBe('EL')
    expect(inicjaly('')).toBe('?')
  })
})
