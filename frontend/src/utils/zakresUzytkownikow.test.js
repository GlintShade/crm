import { describe, expect, it } from 'vitest'
import { dolozOpcjeMoje, filtrZakresuUzytkownikow } from './zakresUzytkownikow'

describe('filtrZakresuUzytkownikow', () => {
  it('lista null/undefined → filtryBazowe bez zmian ("bez ograniczenia")', () => {
    expect(filtrZakresuUzytkownikow({ enabled: 1 }, null)).toEqual({ enabled: 1 })
    expect(filtrZakresuUzytkownikow({ enabled: 1 }, undefined)).toEqual({ enabled: 1 })
  })

  it('lista niepusta → name: ["in", lista] dołączone do filtrów bazowych', () => {
    expect(filtrZakresuUzytkownikow({}, ['jan@x.pl', 'ewa@x.pl'])).toEqual({
      name: ['in', ['jan@x.pl', 'ewa@x.pl']],
    })
  })

  it('lista pusta → wartownik ["in", [""]] (nie dopasowuje nic)', () => {
    expect(filtrZakresuUzytkownikow({}, [])).toEqual({ name: ['in', ['']] })
  })

  it('brak filtrów bazowych (undefined/null/tablica) → start od pustego obiektu', () => {
    expect(filtrZakresuUzytkownikow(undefined, ['jan@x.pl'])).toEqual({
      name: ['in', ['jan@x.pl']],
    })
    expect(filtrZakresuUzytkownikow(null, ['jan@x.pl'])).toEqual({
      name: ['in', ['jan@x.pl']],
    })
    expect(filtrZakresuUzytkownikow([], ['jan@x.pl'])).toEqual({
      name: ['in', ['jan@x.pl']],
    })
  })

  it('wartość inna niż tablica/null/undefined → traktowana jak "bez ograniczenia"', () => {
    expect(filtrZakresuUzytkownikow({ enabled: 1 }, {})).toEqual({ enabled: 1 })
  })

  it('nie mutuje filtryBazowe (immutability)', () => {
    const baza = { enabled: 1 }
    filtrZakresuUzytkownikow(baza, ['jan@x.pl'])
    expect(baza).toEqual({ enabled: 1 })
  })

  it('zwraca zawsze nowy obiekt', () => {
    const baza = { enabled: 1 }
    expect(filtrZakresuUzytkownikow(baza, null)).not.toBe(baza)
  })
})

describe('dolozOpcjeMoje', () => {
  const opcje = [{ label: 'Jan Kowalski', value: 'jan@x.pl' }]

  it('dokleja "@me" jako pierwszą pozycję, z podaną etykietą', () => {
    expect(dolozOpcjeMoje(opcje, 'Moje szanse')).toEqual([
      { label: 'Moje szanse', value: '@me' },
      ...opcje,
    ])
  })

  it('pomin=true → opcja "@me" nie jest dokładana', () => {
    expect(dolozOpcjeMoje(opcje, 'Moje szanse', true)).toEqual(opcje)
  })

  it('brak opcji (jeszcze nie pobrane) → sama opcja "@me"', () => {
    expect(dolozOpcjeMoje([], 'Moje leady')).toEqual([{ label: 'Moje leady', value: '@me' }])
    expect(dolozOpcjeMoje(null, 'Moje leady')).toEqual([{ label: 'Moje leady', value: '@me' }])
  })

  it('nie mutuje opcje (immutability)', () => {
    dolozOpcjeMoje(opcje, 'Moje szanse')
    expect(opcje).toEqual([{ label: 'Jan Kowalski', value: 'jan@x.pl' }])
  })
})
