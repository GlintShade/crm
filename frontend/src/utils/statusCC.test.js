import { describe, it, expect } from 'vitest'
import {
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
