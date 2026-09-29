import { describe, it, expect } from 'vitest'
import {
  STATUSY_ZADANIA,
  PRIORYTETY_ZADANIA,
  kolorStatusuZadania,
  kolorPriorytetuZadania,
  tloWybranegoStatusu,
  tloWybranegoPriorytetu,
  kropkaStatusu,
} from '@/utils/zadania'

describe('STATUSY_ZADANIA / PRIORYTETY_ZADANIA', () => {
  it('lustrzy crm_task.json (status)', () => {
    expect(STATUSY_ZADANIA).toEqual(['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled'])
  })

  it('lustrzy crm_task.json (priority)', () => {
    expect(PRIORYTETY_ZADANIA).toEqual(['Low', 'Medium', 'High'])
  })
})

describe('kolorStatusuZadania', () => {
  it('Backlog -> gray', () => {
    expect(kolorStatusuZadania('Backlog')).toBe('gray')
  })

  it('Todo -> orange', () => {
    expect(kolorStatusuZadania('Todo')).toBe('orange')
  })

  it('In Progress -> blue (statusy w trakcie sa zawsze niebieskie)', () => {
    expect(kolorStatusuZadania('In Progress')).toBe('blue')
  })

  it('Done -> green', () => {
    expect(kolorStatusuZadania('Done')).toBe('green')
  })

  it('Canceled -> red', () => {
    expect(kolorStatusuZadania('Canceled')).toBe('red')
  })

  it('nieznana wartosc -> gray (fallback)', () => {
    expect(kolorStatusuZadania('Cokolwiek')).toBe('gray')
    expect(kolorStatusuZadania('')).toBe('gray')
    expect(kolorStatusuZadania(undefined)).toBe('gray')
  })
})

describe('kolorPriorytetuZadania', () => {
  it('Low -> gray', () => {
    expect(kolorPriorytetuZadania('Low')).toBe('gray')
  })

  it('Medium -> yellow', () => {
    expect(kolorPriorytetuZadania('Medium')).toBe('yellow')
  })

  it('High -> red', () => {
    expect(kolorPriorytetuZadania('High')).toBe('red')
  })

  it('nieznana wartosc -> gray (fallback)', () => {
    expect(kolorPriorytetuZadania('Cokolwiek')).toBe('gray')
  })
})

describe('tloWybranegoStatusu / tloWybranegoPriorytetu', () => {
  it('zwraca literalne klasy tla+tekstu dla znanego koloru', () => {
    expect(tloWybranegoStatusu('In Progress')).toBe('bg-blue-100 text-blue-800')
    expect(tloWybranegoPriorytetu('High')).toBe('bg-red-100 text-red-800')
  })

  it('nigdy nie zwraca pustego stringa dla nieznanej wartosci', () => {
    expect(tloWybranegoStatusu('Cokolwiek')).toBe('bg-gray-100 text-gray-800')
    expect(tloWybranegoPriorytetu('Cokolwiek')).toBe('bg-gray-100 text-gray-800')
  })

  it('nie uzywa rodzin kolorow spoza presetu (rose/emerald/sky/lime)', () => {
    for (const status of STATUSY_ZADANIA) {
      expect(tloWybranegoStatusu(status)).not.toMatch(/rose|emerald|sky|lime/)
    }
    for (const priority of PRIORYTETY_ZADANIA) {
      expect(tloWybranegoPriorytetu(priority)).not.toMatch(/rose|emerald|sky|lime/)
    }
  })
})

describe('kropkaStatusu', () => {
  it('zwraca klase text-*, nigdy pusta', () => {
    for (const status of STATUSY_ZADANIA) {
      expect(kropkaStatusu(status)).toMatch(/^text-[a-z]+-\d+$/)
    }
  })
})
