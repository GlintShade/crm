import { describe, it, expect, beforeEach, vi } from 'vitest'

// Uzytkownik sesji podmieniany w testach (logowanie innego uzytkownika).
const sesja = vi.hoisted(() => ({ user: 'jan@x.pl' }))
vi.mock('@/stores/session', () => ({ sessionStore: () => sesja }))

import { useStanSekcjiPanelu } from '@/composables/useStanSekcjiPanelu'
import { kluczStanuSekcji } from '@/utils/stanSekcjiPanelu'

// Kazdy test na innym doctype: pamiec composable zyje w zasiegu modulu.
let nr = 0
let doctype
beforeEach(() => {
  localStorage.clear()
  sesja.user = 'jan@x.pl'
  doctype = `Test Doctype ${++nr}`
})

describe('useStanSekcjiPanelu', () => {
  it('bez zapisu daje stan domyslny', () => {
    const s = useStanSekcjiPanelu(doctype)
    expect(s.czyOtwarta('handlowe', true)).toBe(true)
    expect(s.czyOtwarta('handlowe', false)).toBe(false)
  })

  it('ustaw zapisuje do localStorage pod kluczem uzytkownika', () => {
    useStanSekcjiPanelu(doctype).ustaw('handlowe', false)
    expect(JSON.parse(localStorage.getItem(kluczStanuSekcji('jan@x.pl', doctype)))).toEqual({
      handlowe: false,
    })
  })

  it('stan wspolny dla wszystkich paneli tego doctype (lead, szczegoly, mapa)', () => {
    const prawyPanel = useStanSekcjiPanelu(doctype)
    const podgladMapy = useStanSekcjiPanelu(() => doctype)
    prawyPanel.ustaw('zrodlo', true)
    expect(podgladMapy.czyOtwarta('zrodlo', false)).toBe(true)
  })

  it('inny uzytkownik na tej samej przegladarce ma wlasny stan', () => {
    useStanSekcjiPanelu(doctype).ustaw('zrodlo', false)
    sesja.user = 'ola@x.pl'
    expect(useStanSekcjiPanelu(doctype).czyOtwarta('zrodlo', true)).toBe(true)
  })

  it('kazdy doctype osobno (szansa, kontakt, organizacja)', () => {
    const inny = `${doctype} B`
    useStanSekcjiPanelu(doctype).ustaw('dane', false)
    expect(useStanSekcjiPanelu(inny).czyOtwarta('dane', true)).toBe(true)
  })

  it('stan przetrwa odswiezenie (odczyt z localStorage)', () => {
    localStorage.setItem(
      kluczStanuSekcji('jan@x.pl', doctype),
      JSON.stringify({ handlowe: true }),
    )
    expect(useStanSekcjiPanelu(doctype).czyOtwarta('handlowe', false)).toBe(true)
  })

  it('ustaw bez nazwy sekcji nic nie zapisuje', () => {
    useStanSekcjiPanelu(doctype).ustaw('', true)
    expect(localStorage.getItem(kluczStanuSekcji('jan@x.pl', doctype))).toBeNull()
  })
})
