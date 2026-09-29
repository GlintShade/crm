import { describe, it, expect } from 'vitest'
import {
  DNI_TYGODNIA_SKROT,
  MIESIACE_SKROT,
  formatujTermin,
  terminWzgledny,
  relatywnie,
} from '@/utils/dataPolska'

describe('DNI_TYGODNIA_SKROT / MIESIACE_SKROT', () => {
  it('mają po 7 i 12 wpisów', () => {
    expect(DNI_TYGODNIA_SKROT).toHaveLength(7)
    expect(MIESIACE_SKROT).toHaveLength(12)
  })
})

describe('formatujTermin', () => {
  it('formatuje pełny Datetime z sekundami (piątek)', () => {
    expect(formatujTermin('2026-09-25 17:00:00')).toBe('pt., 25 wrz 2026, 17:00')
  })

  it('formatuje Datetime bez sekund tak samo', () => {
    expect(formatujTermin('2026-09-25 17:00')).toBe('pt., 25 wrz 2026, 17:00')
  })

  it('toleruje separator "T"', () => {
    expect(formatujTermin('2026-09-25T17:00:00')).toBe('pt., 25 wrz 2026, 17:00')
  })

  it('toleruje ułamkowe sekundy zwracane przez Frappe (data_zdarzenia/creation)', () => {
    expect(formatujTermin('2026-09-28 15:19:56.291762')).toBe('pon., 28 wrz 2026, 15:19')
  })

  it('toleruje ułamkowe sekundy z separatorem "T"', () => {
    expect(formatujTermin('2026-09-28T15:19:56.291762')).toBe('pon., 28 wrz 2026, 15:19')
  })

  it('dzień bez zera wiodącego, minuta z zerem (czwartek)', () => {
    // new Date(2026, 0, 1).getDay() === 4 -> czwartek
    expect(formatujTermin('2026-01-01 00:05:00')).toBe('czw., 1 sty 2026, 00:05')
  })

  it('niedziela', () => {
    // new Date(2026, 11, 6).getDay() === 0 -> niedziela
    expect(formatujTermin('2026-12-06 09:30:00')).toBe('niedz., 6 gru 2026, 09:30')
  })

  it('grudzień (skrót "gru")', () => {
    expect(formatujTermin('2026-12-25 12:00:00')).toBe('pt., 25 gru 2026, 12:00')
  })

  it('przyjmuje obiekt Date', () => {
    expect(formatujTermin(new Date(2026, 8, 25, 17, 0))).toBe('pt., 25 wrz 2026, 17:00')
  })

  it('zwraca "" dla pustego/niepoprawnego wejścia', () => {
    expect(formatujTermin('')).toBe('')
    expect(formatujTermin(null)).toBe('')
    expect(formatujTermin(undefined)).toBe('')
    expect(formatujTermin('abc')).toBe('')
  })

  it('zwraca "" dla nieistniejącej daty (31 lutego)', () => {
    expect(formatujTermin('2026-02-31 10:00:00')).toBe('')
  })

  it('zwraca "" dla niepoprawnego miesiąca (13)', () => {
    expect(formatujTermin('2026-13-01 10:00:00')).toBe('')
  })
})

describe('terminWzgledny', () => {
  const teraz = new Date(2026, 8, 29, 12, 0, 0) // 2026-09-29 12:00 (wtorek)

  it('"dziś" dla tego samego dnia kalendarzowego, niezależnie od godziny', () => {
    expect(terminWzgledny('2026-09-29 09:00:00', teraz)).toBe('dziś')
    expect(terminWzgledny('2026-09-29 23:59:00', teraz)).toBe('dziś')
    expect(terminWzgledny('2026-09-29 00:00:00', teraz)).toBe('dziś')
  })

  it('"jutro" dla następnego dnia kalendarzowego', () => {
    expect(terminWzgledny('2026-09-30 08:00:00', teraz)).toBe('jutro')
  })

  it('"za {0} dni" dla terminów dalej w przyszłości', () => {
    expect(terminWzgledny('2026-10-04 08:00:00', teraz)).toBe('za 5 dni')
    expect(terminWzgledny('2026-10-02 08:00:00', teraz)).toBe('za 3 dni')
  })

  it('"Termin minął {0} dni temu" dla terminów w przeszłości', () => {
    expect(terminWzgledny('2026-09-28 08:00:00', teraz)).toBe('Termin minął 1 dni temu')
    expect(terminWzgledny('2026-09-24 08:00:00', teraz)).toBe('Termin minął 5 dni temu')
  })

  it('porównuje wyłącznie dzień kalendarzowy, nie 24h od "teraz"', () => {
    // "teraz" to 29.09 12:00 - termin jutro o 01:00 jest tylko 13h w przodzie,
    // ale to inny dzień kalendarzowy, więc ma być "jutro", nie "dziś".
    expect(terminWzgledny('2026-09-30 01:00:00', teraz)).toBe('jutro')
    // I odwrotnie: termin dziś o 23:00 to "dziś", mimo że to prawie 11h stąd.
    expect(terminWzgledny('2026-09-29 23:00:00', teraz)).toBe('dziś')
  })

  it('przyjmuje obiekt Date jako dataCzas', () => {
    expect(terminWzgledny(new Date(2026, 8, 30, 8, 0), teraz)).toBe('jutro')
  })

  it('domyślny "teraz" to new Date() (nie rzuca, zwraca string)', () => {
    expect(typeof terminWzgledny('2026-09-29 09:00:00')).toBe('string')
  })

  it('zwraca "" dla pustego/niepoprawnego dataCzas', () => {
    expect(terminWzgledny('', teraz)).toBe('')
    expect(terminWzgledny(null, teraz)).toBe('')
    expect(terminWzgledny(undefined, teraz)).toBe('')
    expect(terminWzgledny('abc', teraz)).toBe('')
  })

  it('zwraca "" dla niepoprawnego "teraz"', () => {
    expect(terminWzgledny('2026-09-29 09:00:00', new Date('abc'))).toBe('')
    expect(terminWzgledny('2026-09-29 09:00:00', 'nie-data')).toBe('')
  })
})

describe('relatywnie', () => {
  const teraz = new Date(2026, 8, 29, 12, 0, 0) // 2026-09-29 12:00 (wtorek)

  it('"dziś HH:MM" dla różnicy 0 minut (dokładnie "teraz")', () => {
    expect(relatywnie('2026-09-29 12:00:00', teraz)).toBe('dziś 12:00')
  })

  it('"dziś HH:MM" dla innej godziny tego samego dnia kalendarzowego', () => {
    expect(relatywnie('2026-09-29 00:00:00', teraz)).toBe('dziś 00:00')
    expect(relatywnie('2026-09-29 23:59:00', teraz)).toBe('dziś 23:59')
  })

  it('"wczoraj" dla 23:59 dnia poprzedzającego "teraz" (mniej niż godzina różnicy)', () => {
    expect(relatywnie('2026-09-28 23:59:00', teraz)).toBe('wczoraj')
  })

  it('"wczoraj" dla dowolnej godziny dnia poprzedzającego', () => {
    expect(relatywnie('2026-09-28 00:00:00', teraz)).toBe('wczoraj')
    expect(relatywnie('2026-09-28 08:30:00', teraz)).toBe('wczoraj')
  })

  it('"N dni temu" w zakresie 2-30 dni', () => {
    expect(relatywnie('2026-09-27 10:00:00', teraz)).toBe('2 dni temu')
    expect(relatywnie('2026-09-20 10:00:00', teraz)).toBe('9 dni temu')
  })

  it('dokładnie 30 dni: jeszcze "N dni temu"', () => {
    expect(relatywnie('2026-08-30 10:00:00', teraz)).toBe('30 dni temu')
  })

  it('31 dni: już pełna data DD.MM.RRRR', () => {
    expect(relatywnie('2026-08-29 10:00:00', teraz)).toBe('29.08.2026')
  })

  it('data znacznie starsza: pełna data DD.MM.RRRR', () => {
    expect(relatywnie('2026-01-05 10:00:00', teraz)).toBe('05.01.2026')
  })

  it('zwraca "" dla pustego/niepoprawnego wejścia', () => {
    expect(relatywnie('', teraz)).toBe('')
    expect(relatywnie(null, teraz)).toBe('')
    expect(relatywnie(undefined, teraz)).toBe('')
    expect(relatywnie('abc', teraz)).toBe('')
  })

  it('domyślny "teraz" to new Date() (nie rzuca, zwraca string)', () => {
    expect(typeof relatywnie('2026-09-29 09:00:00')).toBe('string')
  })

  it('przyjmuje obiekt Date jako wejście', () => {
    expect(relatywnie(new Date(2026, 8, 28, 23, 59), teraz)).toBe('wczoraj')
  })
})
