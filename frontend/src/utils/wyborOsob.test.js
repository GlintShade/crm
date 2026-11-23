import { describe, it, expect } from 'vitest'
import { chipyOsob, loginyZWierszy, opcjeOsob, przelaczOsobe } from './wyborOsob'

describe('przelaczOsobe', () => {
  it('dodaje i usuwa bez mutowania', () => {
    const start = [{ user: 'a@x' }]
    const dodane = przelaczOsobe(start, 'b@x')
    expect(dodane).toEqual([{ user: 'a@x' }, { user: 'b@x' }])
    expect(start).toEqual([{ user: 'a@x' }])
    expect(przelaczOsobe(dodane, 'a@x')).toEqual([{ user: 'b@x' }])
  })
  it('obsluguje undefined i pusty login', () => {
    expect(przelaczOsobe(undefined, 'a@x')).toEqual([{ user: 'a@x' }])
    expect(przelaczOsobe(undefined, '')).toEqual([])
  })
})

describe('opcjeOsob', () => {
  const u = [
    { name: 'z@x', full_name: 'Zofia' },
    { name: 'a@x', full_name: 'Adam' },
    { name: 'w@x', full_name: 'Wykonawca' },
  ]
  it('pomija wykonawce i sortuje', () => {
    expect(opcjeOsob(u, 'w@x').map((o) => o.name)).toEqual(['a@x', 'z@x'])
  })
  it('filtruje po nazwie i loginie', () => {
    expect(opcjeOsob(u, null, 'zof').map((o) => o.name)).toEqual(['z@x'])
    expect(opcjeOsob(u, null, 'A@X').map((o) => o.name)).toEqual(['a@x'])
    expect(opcjeOsob(null, null)).toEqual([])
  })
})

describe('chipyOsob', () => {
  it('nazwa pelna, a bez niej login', () => {
    const get = (l) => (l === 'a@x' ? { full_name: 'Adam' } : {})
    expect(chipyOsob([{ user: 'a@x' }, { user: 'b@x' }], get)).toEqual([
      { login: 'a@x', nazwa: 'Adam' },
      { login: 'b@x', nazwa: 'b@x' },
    ])
    expect(loginyZWierszy([{ user: '' }, null])).toEqual([])
  })
})
