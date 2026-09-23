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
