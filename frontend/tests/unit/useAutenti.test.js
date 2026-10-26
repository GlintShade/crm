// Regression test for ops#163: the Kredyt tab fires
// crm.integrations.autenti.api.autenti_kredyt_status with no `kredyt` key
// on every mount/switch before the selected record resolves, which used to
// 500 (TypeError: missing 1 required positional argument) on the backend.
// See crm/integrations/autenti/api.py::autenti_kredyt_status for the
// matching backend-side hardening.
//
// `frappe-ui` and `@/utils` are mocked because useAutenti.js pulls in
// frappe-ui's resource layer and the `@/utils` barrel (which in turn pulls
// in Vue SFCs and `~icons/*` aliases) that only resolve inside the full
// app's Vite config, not the bare vitest config this project runs
// (vitest.config.js has no vue()/Icons() plugins), mocking both is what
// keeps this test importable at all.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createApp, nextTick } from 'vue'

const { callMock } = vi.hoisted(() => ({ callMock: vi.fn() }))

vi.mock('frappe-ui', () => ({
  call: (...args) => callMock(...args),
  toast: { success: vi.fn(), error: vi.fn() },
}))
vi.mock('@/utils', () => ({
  formatDate: vi.fn(() => ''),
}))

import { useAutenti } from '@/composables/useAutenti'

// useAutenti() calls onMounted()/onUnmounted(), which only register inside
// an active component instance, mount it for real via a throwaway Vue app
// (no @vue/test-utils in this project's devDependencies) so the composable
// is exercised exactly the way KredytTab.vue/UmowaTab.vue exercise it.
function mountComposable(options) {
  let exposed
  const app = createApp({
    setup() {
      exposed = useAutenti(options)
      return () => null
    },
  })
  app.mount(document.createElement('div'))
  return { exposed, unmount: () => app.unmount() }
}

const BASE_OPTIONS = {
  docParam: 'kredyt',
  statusMethod: 'crm.integrations.autenti.api.autenti_kredyt_status',
  sendMethod: 'crm.integrations.autenti.api.autenti_send_kredyt',
  sentToastLabel: 'wysłano',
}

describe('useAutenti, pusty docId nie woła statusMethod (ops#163)', () => {
  beforeEach(() => {
    callMock.mockReset()
  })

  it('nie woła call() przy montowaniu, gdy docId (getter) jest jeszcze null', async () => {
    const { exposed, unmount } = mountComposable({ ...BASE_OPTIONS, docId: () => null })
    await nextTick()
    await nextTick()
    expect(callMock).not.toHaveBeenCalled()
    expect(exposed.autenti.value).toBeNull()
    unmount()
  })

  it('nie woła call() przy montowaniu, gdy docId (getter) jest jeszcze undefined', async () => {
    const { exposed, unmount } = mountComposable({ ...BASE_OPTIONS, docId: () => undefined })
    await nextTick()
    await nextTick()
    expect(callMock).not.toHaveBeenCalled()
    expect(exposed.autenti.value).toBeNull()
    unmount()
  })

  it('woła call() z realną nazwą rekordu, gdy docId już się rozwiązał', async () => {
    callMock.mockResolvedValue({ enabled: false })
    const { unmount } = mountComposable({ ...BASE_OPTIONS, docId: () => 'fuf2kkt1tg' })
    await nextTick()
    await nextTick()
    expect(callMock).toHaveBeenCalledTimes(1)
    expect(callMock).toHaveBeenCalledWith(
      'crm.integrations.autenti.api.autenti_kredyt_status',
      { kredyt: 'fuf2kkt1tg' },
    )
    unmount()
  })

  it('restart() jest no-op (bez wywołania call()) dopóki docId zostaje puste', async () => {
    const { exposed, unmount } = mountComposable({ ...BASE_OPTIONS, docId: () => '' })
    await nextTick()
    callMock.mockClear()
    await exposed.restart()
    expect(callMock).not.toHaveBeenCalled()
    expect(exposed.autenti.value).toBeNull()
    unmount()
  })

  it('restart() woła call() dopiero po tym, jak docId (picker w KredytTab.vue) się rozwiąże', async () => {
    callMock.mockResolvedValue({ enabled: false })
    let current = null
    const { exposed, unmount } = mountComposable({ ...BASE_OPTIONS, docId: () => current })
    await nextTick()
    expect(callMock).not.toHaveBeenCalled()

    current = 'g23juvd3v1'
    await exposed.restart()
    expect(callMock).toHaveBeenCalledWith(
      'crm.integrations.autenti.api.autenti_kredyt_status',
      { kredyt: 'g23juvd3v1' },
    )
    unmount()
  })

  it('confirmSendAutenti() nie woła sendMethod, gdy docId jest puste', async () => {
    const { exposed, unmount } = mountComposable({ ...BASE_OPTIONS, docId: () => null })
    await nextTick()
    callMock.mockClear()
    await exposed.confirmSendAutenti()
    expect(callMock).not.toHaveBeenCalled()
    unmount()
  })

  it('UmowaTab.vue-style dealId (docParam domyślny "deal") nadal woła normalnie', async () => {
    callMock.mockResolvedValue({ enabled: false })
    const { unmount } = mountComposable({
      dealId: () => 'PRO/PVME/26/1006',
      statusMethod: 'crm.integrations.autenti.api.autenti_umowa_status',
      sendMethod: 'crm.integrations.autenti.api.autenti_send_umowa',
      sentToastLabel: 'wysłano',
    })
    await nextTick()
    await nextTick()
    expect(callMock).toHaveBeenCalledWith(
      'crm.integrations.autenti.api.autenti_umowa_status',
      { deal: 'PRO/PVME/26/1006' },
    )
    unmount()
  })
})

// ops#303: push z serwera zamiast odpytywania co 30 s.
function mountZSocketem(options) {
  const socket = { on: vi.fn(), off: vi.fn(), emit: vi.fn() }
  let exposed
  const app = createApp({
    setup() {
      exposed = useAutenti(options)
      return () => null
    },
  })
  app.config.globalProperties.$socket = socket
  app.mount(document.createElement('div'))
  return { exposed, socket, unmount: () => app.unmount() }
}

const UMOWA_OPTIONS = {
  dealId: () => 'PRO/PVME/26/1006',
  statusMethod: 'crm.integrations.autenti.api.autenti_umowa_status',
  sendMethod: 'crm.integrations.autenti.api.autenti_send_umowa',
  sentToastLabel: 'wysłano',
}

function handler(socket, event) {
  const wpis = socket.on.mock.calls.find((c) => c[0] === event)
  return wpis && wpis[1]
}

describe('useAutenti, status wypychany z serwera (ops#303)', () => {
  beforeEach(() => {
    callMock.mockReset()
    callMock.mockResolvedValue({ enabled: true, autenti_status: 'Wysłana' })
    vi.useRealTimers()
  })

  it('nie tworzy żadnego setInterval', async () => {
    const spy = vi.spyOn(globalThis, 'setInterval')
    const { unmount } = mountZSocketem(UMOWA_OPTIONS)
    await nextTick()
    await nextTick()
    expect(spy).not.toHaveBeenCalled()
    unmount()
    spy.mockRestore()
  })

  it('subskrybuje pokój szansy przy montowaniu i zdejmuje wszystko przy odmontowaniu', async () => {
    const { socket, unmount } = mountZSocketem(UMOWA_OPTIONS)
    await nextTick()
    expect(socket.emit).toHaveBeenCalledWith('doc_subscribe', 'CRM Deal', 'PRO/PVME/26/1006')
    const h = handler(socket, 'volteo_autenti_status')
    expect(typeof h).toBe('function')
    unmount()
    expect(socket.off).toHaveBeenCalledWith('volteo_autenti_status', h)
    expect(socket.emit).toHaveBeenCalledWith('doc_unsubscribe', 'CRM Deal', 'PRO/PVME/26/1006')
  })

  it('zdarzenie dla innej szansy nie woła call(), dla bieżącej woła', async () => {
    const { socket, unmount } = mountZSocketem(UMOWA_OPTIONS)
    await nextTick()
    await nextTick()
    callMock.mockClear()
    const h = handler(socket, 'volteo_autenti_status')
    h({ deal: 'INNA' })
    expect(callMock).not.toHaveBeenCalled()
    h({ deal: 'PRO/PVME/26/1006' })
    expect(callMock).toHaveBeenCalledTimes(1)
    unmount()
  })

  it('odmontowanie przed rozwiązaniem pierwszego call() nic dalej nie robi', async () => {
    let rozwiaz
    callMock.mockReturnValue(new Promise((r) => (rozwiaz = r)))
    const { exposed, socket, unmount } = mountZSocketem(UMOWA_OPTIONS)
    unmount()
    const emitPo = socket.emit.mock.calls.length
    const callPo = callMock.mock.calls.length
    rozwiaz({ enabled: true, autenti_status: 'Wysłana' })
    await nextTick()
    await nextTick()
    expect(callMock.mock.calls.length).toBe(callPo)
    expect(socket.emit.mock.calls.length).toBe(emitPo)
    expect(exposed.autenti.value).toBeNull()
  })

  it('visibilitychange (visible) i connect odświeżają status', async () => {
    const { socket, unmount } = mountZSocketem(UMOWA_OPTIONS)
    await nextTick()
    await nextTick()
    callMock.mockClear()
    document.dispatchEvent(new Event('visibilitychange'))
    expect(callMock).toHaveBeenCalledTimes(1)
    handler(socket, 'connect')()
    expect(callMock).toHaveBeenCalledTimes(2)
    expect(socket.emit.mock.calls.filter((c) => c[0] === 'doc_subscribe').length).toBe(2)
    unmount()
    callMock.mockClear()
    document.dispatchEvent(new Event('visibilitychange'))
    expect(callMock).not.toHaveBeenCalled()
  })

  it('po confirmSendAutenti() jedno dodatkowe call() po 10 s, po odmontowaniu żadnego', async () => {
    vi.useFakeTimers()
    const { exposed, unmount } = mountZSocketem(UMOWA_OPTIONS)
    await vi.advanceTimersByTimeAsync(0)
    exposed.autenti.value = {
      enabled: true,
      dokument_exists: true,
      pdf_exists: true,
      proposed_signer: { full_name: 'A B', email: 'a@b.pl' },
    }
    callMock.mockResolvedValue({ autenti_status: 'Wysyłanie' })
    await exposed.confirmSendAutenti()
    callMock.mockClear()
    callMock.mockResolvedValue({ enabled: true, autenti_status: 'Wysłana' })
    await vi.advanceTimersByTimeAsync(9000)
    expect(callMock).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1500)
    expect(callMock).toHaveBeenCalledTimes(1)

    await exposed.confirmSendAutenti()
    callMock.mockClear()
    unmount()
    await vi.advanceTimersByTimeAsync(20000)
    expect(callMock).not.toHaveBeenCalled()
    vi.useRealTimers()
  })
})
