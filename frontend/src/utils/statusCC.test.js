import { describe, it, expect } from 'vitest'
import {
  leadBezposredniWlasny,
  mozeZmieniacStatusCC,
  sekcjeZeStatusemTylkoDoOdczytu,
} from './statusCC'

describe('mozeZmieniacStatusCC', () => {
  it('czysty handlowiec nie moze', () => {
    expect(mozeZmieniacStatusCC(['Volteo D2D Sales', 'Sales User'])).toBe(false)
  })
  it('handlowiec z CC, backendem, core adminem lub SM moze', () => {
    for (const r of ['Volteo Call Center', 'Volteo Backend', 'Volteo Core Admin', 'System Manager'])
      expect(mozeZmieniacStatusCC(['Volteo D2D Sales', r])).toBe(true)
  })
  it('inne role i puste moga', () => {
    expect(mozeZmieniacStatusCC(['Sales Manager'])).toBe(true)
    expect(mozeZmieniacStatusCC([])).toBe(true)
    expect(mozeZmieniacStatusCC(undefined)).toBe(true)
  })
  it('flaga admina wygrywa', () => {
    expect(mozeZmieniacStatusCC(['Volteo D2D Sales'], true)).toBe(true)
  })
})

describe('mozeZmieniacStatusCC z leadem z reguly bezposredniej (ops#351)', () => {
  const rola = ['Volteo D2D Sales']
  const wlasny = { lead_owner: 'h@x.pl', custom_przydzial_bezposredni: 1 }
  it('wlasny lead z reguly odblokowuje', () => {
    expect(mozeZmieniacStatusCC(rola, false, false, wlasny, 'h@x.pl')).toBe(true)
  })
  it('wlasciciel jako obiekt z wiersza listy', () => {
    const wiersz = { lead_owner: { name: 'h@x.pl' }, custom_przydzial_bezposredni: '1' }
    expect(mozeZmieniacStatusCC(rola, false, false, wiersz, 'h@x.pl')).toBe(true)
  })
  it('cudzy lead z reguly nie odblokowuje', () => {
    expect(mozeZmieniacStatusCC(rola, false, false, wlasny, 'inny@x.pl')).toBe(false)
  })
  it('lead bez znacznika albo bez pola nie odblokowuje', () => {
    expect(
      mozeZmieniacStatusCC(rola, false, false, { lead_owner: 'h@x.pl', custom_przydzial_bezposredni: 0 }, 'h@x.pl'),
    ).toBe(false)
    expect(mozeZmieniacStatusCC(rola, false, false, { lead_owner: 'h@x.pl' }, 'h@x.pl')).toBe(false)
  })
  it('znacznik bez wlasciciela nie odblokowuje', () => {
    expect(mozeZmieniacStatusCC(rola, false, false, { custom_przydzial_bezposredni: 1 }, 'h@x.pl')).toBe(false)
  })
  it('stare wywolanie bez leada dziala jak dotad', () => {
    expect(mozeZmieniacStatusCC(rola)).toBe(false)
    expect(leadBezposredniWlasny(null, 'h@x.pl')).toBe(false)
  })
})

describe('sekcjeZeStatusemTylkoDoOdczytu', () => {
  const sekcje = [
    { label: 'A', columns: [{ fields: [{ fieldname: 'status' }, { fieldname: 'custom_status_handlowy' }] }] },
    { label: 'B' },
  ]
  it('ustawia read_only tylko na status, bez mutacji', () => {
    const wynik = sekcjeZeStatusemTylkoDoOdczytu(sekcje)
    expect(wynik[0].columns[0].fields[0].read_only).toBe(1)
    expect(wynik[0].columns[0].fields[1].read_only).toBeUndefined()
    expect(sekcje[0].columns[0].fields[0].read_only).toBeUndefined()
    expect(wynik[1]).toBe(sekcje[1])
  })
  it('puste wejscie przechodzi', () => {
    expect(sekcjeZeStatusemTylkoDoOdczytu(undefined)).toBeUndefined()
  })
})
