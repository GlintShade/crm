import { describe, it, expect } from 'vitest'
import {
  LIMIT_ZWINIETYCH,
  autorNotatki,
  posortujNotatki,
  wersjaKomentarzy,
  widoczneNotatki,
  zglosZmianeKomentarzy,
} from '@/utils/notatkiLeada'

describe('posortujNotatki / widoczneNotatki', () => {
  const lista = [
    { name: 'a', creation: '2026-11-01 10:00:00.000000' },
    { name: 'c', creation: '2026-11-03 09:00:00.000000' },
    { name: 'b', creation: '2026-11-02 12:00:00.000000' },
    { name: 'd', creation: '2026-11-04 08:00:00.000000' },
  ]
  it('najnowsze na gorze, bez mutacji wejscia', () => {
    const kopia = [...lista]
    expect(posortujNotatki(lista).map((x) => x.name)).toEqual([
      'd',
      'c',
      'b',
      'a',
    ])
    expect(lista).toEqual(kopia)
  })
  it('null daje pusta liste', () => {
    expect(posortujNotatki(null)).toEqual([])
  })
  it('zwiniete pokazuja limit najnowszych, rozwiniete wszystkie', () => {
    const p = posortujNotatki(lista)
    expect(widoczneNotatki(p, false)).toHaveLength(LIMIT_ZWINIETYCH)
    expect(widoczneNotatki(p, false).map((x) => x.name)).toEqual([
      'd',
      'c',
      'b',
    ])
    expect(widoczneNotatki(p, true)).toHaveLength(4)
    expect(widoczneNotatki(p, false, 1).map((x) => x.name)).toEqual(['d'])
    expect(widoczneNotatki(null, false)).toEqual([])
  })
})

describe('autorNotatki', () => {
  it('comment_by przed owner (maska CC przychodzi z backendu w obu)', () => {
    expect(
      autorNotatki({ comment_by: 'Call center', owner: 'Call center' }),
    ).toBe('Call center')
    expect(autorNotatki({ owner: 'jan@x.pl' })).toBe('jan@x.pl')
    expect(autorNotatki(null)).toBe('')
  })
})

describe('sygnal zmian komentarzy', () => {
  it('podbija wersje per doctype+nazwa niezaleznie', () => {
    expect(wersjaKomentarzy('CRM Lead', 'L-1')).toBe(0)
    zglosZmianeKomentarzy('CRM Lead', 'L-1')
    zglosZmianeKomentarzy('CRM Lead', 'L-1')
    zglosZmianeKomentarzy('CRM Lead', 'L-2')
    expect(wersjaKomentarzy('CRM Lead', 'L-1')).toBe(2)
    expect(wersjaKomentarzy('CRM Lead', 'L-2')).toBe(1)
    expect(wersjaKomentarzy('CRM Deal', 'L-1')).toBe(0)
  })
  it('brak doctype albo nazwy to no-op', () => {
    zglosZmianeKomentarzy('', 'L-9')
    zglosZmianeKomentarzy('CRM Lead', '')
    expect(wersjaKomentarzy('', 'L-9')).toBe(0)
    expect(wersjaKomentarzy('CRM Lead', '')).toBe(0)
  })
})
