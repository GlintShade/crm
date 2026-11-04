import { describe, it, expect } from 'vitest'
import {
  formatujDateUtworzenia,
  podpowiedzGgMm,
  podpowiedzCzasuKontaktu,
  czesciPodpowiedzi,
  czyPokazacPodpowiedz,
  MAKS_SEKUND_POLA,
} from '../../src/utils/podpowiedzKontaktu'
import { parsujGgMm } from '../../src/utils/czasKontaktu'

// Konstruktor lokalny: test nie zalezy od strefy czasowej maszyny.
const T = new Date(2026, 10, 4, 12, 0, 0).getTime()
const min = 60000
const godz = 60 * min

describe('formatujDateUtworzenia', () => {
  it('DD.MM.RRRR, GG:MM w 24 h', () =>
    expect(formatujDateUtworzenia(new Date(2026, 10, 2, 14, 5).getTime())).toBe(
      '02.11.2026, 14:05',
    ))
  it('polnoc jako 00:00', () =>
    expect(formatujDateUtworzenia(new Date(2026, 0, 9, 0, 0).getTime())).toBe(
      '09.01.2026, 00:00',
    ))
  it('zle dane daja null', () => {
    expect(formatujDateUtworzenia(undefined)).toBe(null)
    expect(formatujDateUtworzenia(null)).toBe(null)
    expect(formatujDateUtworzenia('')).toBe(null)
    expect(formatujDateUtworzenia('abc')).toBe(null)
  })
})

describe('podpowiedzGgMm', () => {
  it('2 h 40 m', () =>
    expect(podpowiedzGgMm(T - (2 * godz + 40 * min), T)).toBe('02:40'))
  it('sekundy obcinane w dol', () =>
    expect(podpowiedzGgMm(T - (5 * min + 59000), T)).toBe('00:05'))
  it('ponad 24 h dozwolone', () =>
    expect(podpowiedzGgMm(T - (75 * godz + 20 * min), T)).toBe('75:20'))
  it('dokladnie 999:59 jeszcze jest', () =>
    expect(podpowiedzGgMm(T - MAKS_SEKUND_POLA * 1000 - 30000, T)).toBe(
      '999:59',
    ))
  it('1000:00 juz nie', () =>
    expect(podpowiedzGgMm(T - 1000 * godz, T)).toBe(null))
  it('ponizej minuty brak podpowiedzi', () =>
    expect(podpowiedzGgMm(T - 30000, T)).toBe(null))
  it('przyszlosc i zle dane daja null', () => {
    expect(podpowiedzGgMm(T + min, T)).toBe(null)
    expect(podpowiedzGgMm(undefined, T)).toBe(null)
  })
  it('wynik da sie wpisac w pole (parsujGgMm)', () => {
    const ggmm = podpowiedzGgMm(T - (123 * godz + 7 * min), T)
    expect(ggmm).toBe('123:07')
    expect(parsujGgMm(ggmm)).toBe(123 * 3600 + 7 * 60)
  })
})

describe('podpowiedzCzasuKontaktu', () => {
  it('do 48 h: wiek jak na liscie leadow plus gg:mm', () =>
    expect(podpowiedzCzasuKontaktu(T - (2 * godz + 40 * min), T)).toBe(
      'utworzono 02 h 40 m temu (02:40)',
    ))
  it('47 h 59 m', () =>
    expect(podpowiedzCzasuKontaktu(T - (47 * godz + 59 * min), T)).toBe(
      'utworzono 47 h 59 m temu (47:59)',
    ))
  it('starszy lead: data i godzina plus gg:mm', () => {
    const c = new Date(2026, 10, 1, 8, 40).getTime()
    expect(podpowiedzCzasuKontaktu(c, T)).toBe(
      'utworzono 01.11.2026, 08:40 (75:20)',
    )
  })
  it('ponad 999:59: sama data', () => {
    const c = new Date(2026, 7, 1, 9, 15).getTime()
    expect(podpowiedzCzasuKontaktu(c, T)).toBe('utworzono 01.08.2026, 09:15')
  })
  it('swiezy lead (ponizej minuty): bez gg:mm', () =>
    expect(podpowiedzCzasuKontaktu(T - 20000, T)).toBe(
      'utworzono 00 h 00 m temu',
    ))
  it('brak creation daje null', () =>
    expect(podpowiedzCzasuKontaktu(undefined, T)).toBe(null))
})

describe('czesciPodpowiedzi', () => {
  it('opis i gg:mm osobno', () =>
    expect(czesciPodpowiedzi(T - (2 * godz + 40 * min), T)).toEqual({
      opis: 'utworzono 02 h 40 m temu',
      ggmm: '02:40',
      pelny: 'utworzono 02 h 40 m temu (02:40)',
    }))
  it('ponad 999:59: ggmm null', () =>
    expect(czesciPodpowiedzi(new Date(2026, 7, 1, 9, 15).getTime(), T)).toEqual(
      {
        opis: 'utworzono 01.08.2026, 09:15',
        ggmm: null,
        pelny: 'utworzono 01.08.2026, 09:15',
      },
    ))
  it('brak creation daje null', () =>
    expect(czesciPodpowiedzi(null, T)).toBe(null))
})

describe('czyPokazacPodpowiedz', () => {
  it('puste i edytowalne: tak', () => {
    expect(czyPokazacPodpowiedz(0, false)).toBe(true)
    expect(czyPokazacPodpowiedz(null, false)).toBe(true)
    expect(czyPokazacPodpowiedz(undefined, false)).toBe(true)
    expect(czyPokazacPodpowiedz('', false)).toBe(true)
  })
  it('wpisana wartosc: nie', () =>
    expect(czyPokazacPodpowiedz(9600, false)).toBe(false))
  it('tylko do odczytu: nie, nawet puste', () => {
    expect(czyPokazacPodpowiedz(0, true)).toBe(false)
    expect(czyPokazacPodpowiedz(9600, 1)).toBe(false)
  })
})
