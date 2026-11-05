// Zadanie J: "Czas do pierwszego kontaktu" na zywo po notatce -- composable
// usePrzeladujPoNotatce odpala `reload` ~1 s po sygnale `wersjaKomentarzy`
// (notatkiLeada.js), z debounce dla serii notatek i sprzataniem przy
// odmontowaniu.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createApp, h } from 'vue'
import {
  OPOZNIENIE_PRZELADOWANIA_MS,
  usePrzeladujPoNotatce,
} from '@/composables/usePrzeladujPoNotatce'
import { zglosZmianeKomentarzy } from '@/utils/notatkiLeada'

function zamontuj(opcje) {
  const reload = vi.fn()
  const el = document.createElement('div')
  const app = createApp({
    setup() {
      usePrzeladujPoNotatce({ reload, ...opcje })
      return () => h('div')
    },
  })
  app.mount(el)
  return { app, reload }
}

describe('usePrzeladujPoNotatce', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('odswieza ~1 s po dodaniu notatki', () => {
    const docname = 'CRM-LEAD-1'
    const { app, reload } = zamontuj({ docname: () => docname })
    zglosZmianeKomentarzy('CRM Lead', docname)
    expect(reload).not.toHaveBeenCalled()
    vi.advanceTimersByTime(OPOZNIENIE_PRZELADOWANIA_MS - 1)
    expect(reload).not.toHaveBeenCalled()
    vi.advanceTimersByTime(1)
    expect(reload).toHaveBeenCalledTimes(1)
    app.unmount()
  })

  it('seria notatek pod rzad daje jedno odswiezenie', () => {
    const docname = 'CRM-LEAD-2'
    const { app, reload } = zamontuj({ docname: () => docname })
    zglosZmianeKomentarzy('CRM Lead', docname)
    vi.advanceTimersByTime(OPOZNIENIE_PRZELADOWANIA_MS / 2)
    zglosZmianeKomentarzy('CRM Lead', docname)
    vi.advanceTimersByTime(OPOZNIENIE_PRZELADOWANIA_MS / 2)
    expect(reload).not.toHaveBeenCalled()
    vi.advanceTimersByTime(OPOZNIENIE_PRZELADOWANIA_MS / 2)
    expect(reload).toHaveBeenCalledTimes(1)
    app.unmount()
  })

  it('notatka na innym leadzie nie odswieza tego dokumentu', () => {
    const docname = 'CRM-LEAD-3'
    const { app, reload } = zamontuj({ docname: () => docname })
    zglosZmianeKomentarzy('CRM Lead', 'CRM-LEAD-INNY')
    vi.advanceTimersByTime(OPOZNIENIE_PRZELADOWANIA_MS * 2)
    expect(reload).not.toHaveBeenCalled()
    app.unmount()
  })

  it('respektuje wlasne opoznienie', () => {
    const docname = 'CRM-LEAD-4'
    const { app, reload } = zamontuj({ docname: () => docname, opoznienieMs: 300 })
    zglosZmianeKomentarzy('CRM Lead', docname)
    vi.advanceTimersByTime(299)
    expect(reload).not.toHaveBeenCalled()
    vi.advanceTimersByTime(1)
    expect(reload).toHaveBeenCalledTimes(1)
    app.unmount()
  })

  it('odmontowanie przed uplywem opoznienia nie odswieza', () => {
    const docname = 'CRM-LEAD-5'
    const { app, reload } = zamontuj({ docname: () => docname })
    zglosZmianeKomentarzy('CRM Lead', docname)
    app.unmount()
    vi.advanceTimersByTime(OPOZNIENIE_PRZELADOWANIA_MS * 2)
    expect(reload).not.toHaveBeenCalled()
  })
})
