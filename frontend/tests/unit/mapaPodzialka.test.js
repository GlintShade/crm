import { describe, it, expect } from 'vitest'
import { dodajPodzialke, OPCJE_PODZIALKI } from '@/utils/mapaPodzialka'

function fakeL() {
  const zapis = { opcje: null, mapa: null }
  const kontrolka = {
    addTo(m) {
      zapis.mapa = m
      return kontrolka
    },
  }
  const L = {
    control: {
      scale(o) {
        zapis.opcje = o
        return kontrolka
      },
    },
  }
  return { L, zapis, kontrolka }
}

describe('dodajPodzialke', () => {
  it('dodaje metryczna podzialke w lewym dolnym rogu', () => {
    const { L, zapis, kontrolka } = fakeL()
    const mapa = { id: 'm' }
    const wynik = dodajPodzialke(L, mapa)
    expect(zapis.opcje).toEqual({
      position: 'bottomleft',
      metric: true,
      imperial: false,
      maxWidth: 150,
    })
    expect(zapis.mapa).toBe(mapa)
    expect(wynik).toBe(kontrolka)
  })

  it('nie modyfikuje zamrozonych opcji', () => {
    const { L, zapis } = fakeL()
    dodajPodzialke(L, {})
    expect(zapis.opcje).not.toBe(OPCJE_PODZIALKI)
    expect(Object.isFrozen(OPCJE_PODZIALKI)).toBe(true)
  })

  it('zwraca null bez L, bez control.scale lub bez mapy', () => {
    expect(dodajPodzialke(null, {})).toBeNull()
    expect(dodajPodzialke({}, {})).toBeNull()
    expect(dodajPodzialke({ control: {} }, {})).toBeNull()
    expect(dodajPodzialke(fakeL().L, null)).toBeNull()
  })
})
