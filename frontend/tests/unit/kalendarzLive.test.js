// Kalendarz spotkań na żywo (ops#331): czyste funkcje i composable
// useKalendarzLive z udawanym socketem i zegarem.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createApp, h } from 'vue'
import {
  ODSTEP_ODSWIEZENIA_MS,
  ODSTEP_POLLINGU_MS,
  ODSTEP_SPRAWDZANIA_MS,
  ZDARZENIE_KALENDARZA,
  czasNaPolling,
  dotyczyZakresu,
} from '@/utils/kalendarzLive'
import { useKalendarzLive } from '@/composables/useKalendarzLive'

describe('dotyczyZakresu', () => {
  const od = '2026-11-02'
  const doDaty = '2026-11-08'

  it('bez dat dotyczy zawsze', () => {
    expect(dotyczyZakresu({ daty: [] }, od, doDaty)).toBe(true)
    expect(dotyczyZakresu({}, od, doDaty)).toBe(true)
    expect(dotyczyZakresu(null, od, doDaty)).toBe(true)
  })

  it('data w zakresie, także na granicach', () => {
    expect(dotyczyZakresu({ daty: ['2026-11-02'] }, od, doDaty)).toBe(true)
    expect(dotyczyZakresu({ daty: ['2026-11-08'] }, od, doDaty)).toBe(true)
    expect(dotyczyZakresu({ daty: ['2026-11-05'] }, od, doDaty)).toBe(true)
  })

  it('daty poza zakresem nie dotyczą', () => {
    expect(
      dotyczyZakresu({ daty: ['2026-11-01', '2026-11-09'] }, od, doDaty),
    ).toBe(false)
  })

  it('przesunięcie spoza zakresu do zakresu dotyczy', () => {
    expect(
      dotyczyZakresu({ daty: ['2026-10-20', '2026-11-04'] }, od, doDaty),
    ).toBe(true)
  })

  it('nieczytelna data albo brak zakresu: odśwież', () => {
    expect(dotyczyZakresu({ daty: ['jutro'] }, od, doDaty)).toBe(true)
    expect(dotyczyZakresu({ daty: ['2026-12-01'] }, '', '')).toBe(true)
  })
})

describe('czasNaPolling', () => {
  it('ukryta karta nie odpytuje', () => {
    expect(czasNaPolling({ teraz: 1e9, ostatnie: 0, widoczna: false })).toBe(
      false,
    )
  })

  it('widoczna karta po 60 s ciszy', () => {
    const ostatnie = 1_000_000
    expect(
      czasNaPolling({
        teraz: ostatnie + ODSTEP_POLLINGU_MS - 1,
        ostatnie,
        widoczna: true,
      }),
    ).toBe(false)
    expect(
      czasNaPolling({
        teraz: ostatnie + ODSTEP_POLLINGU_MS,
        ostatnie,
        widoczna: true,
      }),
    ).toBe(true)
  })
})

function udawanySocket() {
  const sluchacze = {}
  return {
    sluchacze,
    on(nazwa, fn) {
      ;(sluchacze[nazwa] ||= []).push(fn)
    },
    off(nazwa, fn) {
      sluchacze[nazwa] = (sluchacze[nazwa] || []).filter((f) => f !== fn)
    },
    emit(nazwa, dane) {
      for (const fn of sluchacze[nazwa] || []) fn(dane)
    },
  }
}

function zamontuj({ socket, okres }) {
  const odswiez = vi.fn()
  const el = document.createElement('div')
  const app = createApp({
    setup() {
      useKalendarzLive({ okres, odswiez, socket })
      return () => h('div')
    },
  })
  app.mount(el)
  return { app, odswiez }
}

function ustawWidocznosc(stan) {
  Object.defineProperty(document, 'visibilityState', {
    configurable: true,
    get: () => stan,
  })
  document.dispatchEvent(new Event('visibilitychange'))
}

describe('useKalendarzLive', () => {
  const okres = () => ({ od: '2026-11-02', do: '2026-11-08' })
  let socket

  beforeEach(() => {
    vi.useFakeTimers()
    socket = udawanySocket()
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'visible',
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('seria sygnałów w zakresie daje jedno odświeżenie po ~1 s', () => {
    const { app, odswiez } = zamontuj({ socket, okres })
    socket.emit(ZDARZENIE_KALENDARZA, { daty: ['2026-11-03'] })
    socket.emit(ZDARZENIE_KALENDARZA, { daty: ['2026-11-04'] })
    socket.emit(ZDARZENIE_KALENDARZA, { daty: [] })
    expect(odswiez).not.toHaveBeenCalled()
    vi.advanceTimersByTime(ODSTEP_ODSWIEZENIA_MS)
    expect(odswiez).toHaveBeenCalledTimes(1)
    app.unmount()
  })

  it('sygnał spoza widocznego zakresu nie odświeża', () => {
    const { app, odswiez } = zamontuj({ socket, okres })
    socket.emit(ZDARZENIE_KALENDARZA, { daty: ['2026-12-24'] })
    vi.advanceTimersByTime(ODSTEP_ODSWIEZENIA_MS * 3)
    expect(odswiez).not.toHaveBeenCalled()
    app.unmount()
  })

  it('ukryta karta ignoruje sygnały i nadrabia po powrocie', () => {
    const { app, odswiez } = zamontuj({ socket, okres })
    ustawWidocznosc('hidden')
    socket.emit(ZDARZENIE_KALENDARZA, { daty: ['2026-11-03'] })
    vi.advanceTimersByTime(ODSTEP_ODSWIEZENIA_MS * 2)
    expect(odswiez).not.toHaveBeenCalled()
    ustawWidocznosc('visible')
    vi.advanceTimersByTime(ODSTEP_ODSWIEZENIA_MS)
    expect(odswiez).toHaveBeenCalledTimes(1)
    app.unmount()
  })

  it('ponowne połączenie socketu odświeża', () => {
    const { app, odswiez } = zamontuj({ socket, okres })
    socket.emit('connect')
    vi.advanceTimersByTime(ODSTEP_ODSWIEZENIA_MS)
    expect(odswiez).toHaveBeenCalledTimes(1)
    app.unmount()
  })

  it('polling po 60 s ciszy, także bez socketu', () => {
    const { app, odswiez } = zamontuj({ socket: null, okres })
    vi.advanceTimersByTime(ODSTEP_POLLINGU_MS - ODSTEP_SPRAWDZANIA_MS)
    expect(odswiez).not.toHaveBeenCalled()
    vi.advanceTimersByTime(ODSTEP_SPRAWDZANIA_MS + ODSTEP_ODSWIEZENIA_MS)
    expect(odswiez).toHaveBeenCalledTimes(1)
    app.unmount()
  })

  it('odświeżenie z sygnału przesuwa polling', () => {
    const { app, odswiez } = zamontuj({ socket, okres })
    vi.advanceTimersByTime(ODSTEP_POLLINGU_MS - ODSTEP_SPRAWDZANIA_MS)
    socket.emit(ZDARZENIE_KALENDARZA, { daty: [] })
    vi.advanceTimersByTime(ODSTEP_ODSWIEZENIA_MS)
    expect(odswiez).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(ODSTEP_SPRAWDZANIA_MS * 2)
    expect(odswiez).toHaveBeenCalledTimes(1)
    app.unmount()
  })

  it('odmontowanie zdejmuje słuchaczy i timery', () => {
    const { app, odswiez } = zamontuj({ socket, okres })
    app.unmount()
    expect(socket.sluchacze[ZDARZENIE_KALENDARZA]).toEqual([])
    expect(socket.sluchacze.connect).toEqual([])
    socket.emit(ZDARZENIE_KALENDARZA, { daty: [] })
    vi.advanceTimersByTime(ODSTEP_POLLINGU_MS * 2)
    expect(odswiez).not.toHaveBeenCalled()
  })
})
