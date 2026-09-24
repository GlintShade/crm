import { describe, it, expect } from 'vitest'
import { opcjeWskaznikaZapisu, WSKAZNIK_ZAPISU_MS } from './wskaznikZapisu'

describe('opcjeWskaznikaZapisu', () => {
  it('czas zycia rowny WSKAZNIK_ZAPISU_MS i nie dluzszy niz 1000 ms', () => {
    const opcje = opcjeWskaznikaZapisu()
    expect(opcje.duration).toBe(WSKAZNIK_ZAPISU_MS)
    expect(opcje.duration).toBeLessThanOrEqual(1000)
  })

  it('wylacza przycisk zamkniecia i przeciagniecie', () => {
    const opcje = opcjeWskaznikaZapisu()
    expect(opcje.closeButton).toBe(false)
    expect(opcje.dismissible).toBe(false)
  })

  it('pointer-events: none, zeby klik przechodzil na element pod spodem', () => {
    const opcje = opcjeWskaznikaZapisu()
    expect(opcje.style.pointerEvents).toBe('none')
  })

  it('kazde wywolanie zwraca nowy obiekt o rownej tresci, bez wspoldzielenia stanu', () => {
    const a = opcjeWskaznikaZapisu()
    const b = opcjeWskaznikaZapisu()
    expect(a).not.toBe(b)
    expect(a).toEqual(b)

    a.style.width = 'zmienione'
    expect(b.style.width).toBe('auto')
  })
})
