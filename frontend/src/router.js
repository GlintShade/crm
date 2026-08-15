import { createRouter, createWebHistory } from 'vue-router'
import { call } from 'frappe-ui'
import { usersStore } from '@/stores/users'
import { sessionStore } from '@/stores/session'
import { viewsStore } from '@/stores/views'
import { isStaleChunkError, shouldReload } from '@/utils/chunkReload'

let personaChecked = false
export const PERSONA_DONE_KEY = 'crm_persona_captured'

async function shouldCapturePersona() {
  // Client-side flag guards against re-prompting if the server persist failed.
  if (localStorage.getItem(PERSONA_DONE_KEY)) return false
  const captured = await call('frappe.client.get_single_value', {
    doctype: 'FCRM Settings',
    field: 'persona_captured',
  })
  if (captured) return false
  // The wizard only feeds telemetry; skip it entirely if the user opted out.
  // This backend has no frappe.utils.telemetry.pulse.client.boot_config endpoint, so the
  // call is expected to fail (417); guard it so that failure degrades to "not enabled"
  // instead of rejecting and breaking routing.
  const { enabled } =
    (await call('frappe.utils.telemetry.pulse.client.boot_config').catch(() => null)) || {}
  return !!enabled
}

const routes = [
  {
    path: '/',
    name: 'Home',
  },
  {
    path: '/notifications',
    name: 'Notifications',
    component: () => import('@/pages/MobileNotification.vue'),
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/pages/Dashboard.vue'),
  },
  {
    path: '/kalkulator',
    name: 'Kalkulator',
    component: () => import('@/pages/Kalkulator.vue'),
  },
  {
    path: '/kalkulator-czyste-powietrze',
    name: 'KalkulatorCzystePowietrze',
    component: () => import('@/pages/KalkulatorCzystePowietrze.vue'),
  },
  {
    alias: '/leads',
    path: '/leads/view/:viewType?',
    name: 'Leads',
    component: () => import('@/pages/Leads.vue'),
  },
  {
    path: '/leads/:leadId',
    name: 'Lead',
    component: () => import(`@/pages/${handleMobileView('Lead')}.vue`),
    props: true,
  },
  {
    alias: '/deals',
    path: '/deals/view/:viewType?',
    name: 'Deals',
    component: () => import('@/pages/Deals.vue'),
  },
  {
    // VOLTEO: deal names carry slashes since b38 (PRO/KOD/RR/NNNN, crm/volteo_naming.py).
    // The default single-segment param can't match them on a cold load (refresh/deep-link
    // → silently empty view); (.+) lets the param span slashes.
    path: '/deals/:dealId(.+)',
    name: 'Deal',
    component: () => import(`@/pages/${handleMobileView('Deal')}.vue`),
    props: true,
  },
  {
    alias: '/notes',
    path: '/notes/view/:viewType?',
    name: 'Notes',
    component: () => import('@/pages/Notes.vue'),
  },
  {
    alias: '/tasks',
    path: '/tasks/view/:viewType?',
    name: 'Tasks',
    component: () => import('@/pages/Tasks.vue'),
  },
  {
    alias: '/contacts',
    path: '/contacts/view/:viewType?',
    name: 'Contacts',
    component: () => import('@/pages/Contacts.vue'),
  },
  {
    path: '/contacts/:contactId',
    name: 'Contact',
    component: () => import(`@/pages/${handleMobileView('Contact')}.vue`),
    props: true,
  },
  {
    alias: '/organizations',
    path: '/organizations/view/:viewType?',
    name: 'Organizations',
    component: () => import('@/pages/Organizations.vue'),
  },
  {
    path: '/organizations/:organizationId',
    name: 'Organization',
    component: () => import(`@/pages/${handleMobileView('Organization')}.vue`),
    props: true,
  },
  {
    alias: '/call-logs',
    path: '/call-logs/view/:viewType?',
    name: 'Call Logs',
    component: () => import('@/pages/CallLogs.vue'),
  },
  {
    path: '/data-import',
    name: 'DataImportList',
    component: () => import('@/pages/DataImport.vue'),
  },
  {
    path: '/data-import/doctype/:doctype',
    name: 'NewDataImport',
    component: () => import('@/pages/DataImport.vue'),
    props: true,
  },
  {
    path: '/data-import/:importName',
    name: 'DataImport',
    component: () => import('@/pages/DataImport.vue'),
    props: true,
  },
  {
    path: '/welcome',
    name: 'Welcome',
    component: () => import('@/pages/Welcome.vue'),
  },
  {
    path: '/onboarding',
    name: 'Onboarding',
    component: () => import('@/pages/PersonaForm.vue'),
  },
  {
    path: '/:invalidpath',
    name: 'Invalid Page',
    component: () => import('@/pages/InvalidPage.vue'),
  },
  {
    path: '/not-permitted',
    name: 'Not Permitted',
    component: () => import('@/pages/NotPermitted.vue'),
  },
]

const handleMobileView = (componentName) => {
  return window.innerWidth < 768 ? `Mobile${componentName}` : componentName
}

let router = createRouter({
  history: createWebHistory('/crm'),
  routes,
})

// --- Stale-chunk recovery -----------------------------------------------
//
// Every production deploy deletes the old hashed chunk files from the
// server. A browser that still holds the OLD document — an open tab, or
// the service worker's precached index.html (vite-plugin-pwa, autoUpdate)
// — then lazy-loads a route chunk that no longer exists, the dynamic
// import() rejects, and the user is stuck on a blank page. The fix is a
// single reload to pick up the current document and chunk manifest.
// `autoUpdate` only updates the service worker in the background; it does
// not rescue a page that already failed to load a chunk.
//
// Loop protection is a time-based cooldown (60s), not a per-navigation
// flag. A flag cleared on router.afterEach was tried and rejected: because
// 'vite:preloadError' fires independently of navigation, a successful
// navigation to an already-cached route can re-arm the guard while a
// *different* lazy chunk (or the same one, offline) keeps failing in the
// background — each clear immediately allows another reload, producing an
// infinite loop. A sessionStorage timestamp cannot be shortened by any
// sequence of navigations, so that loop is structurally impossible here:
// at most one reload per STALE_CHUNK_RELOAD_COOLDOWN_MS, ever, in this
// tab — while a later, unrelated deploy hours into a long session is
// still repaired once the cooldown has long since elapsed.
const STALE_CHUNK_RELOAD_KEY = 'crm_stale_chunk_reload'
const STALE_CHUNK_RELOAD_COOLDOWN_MS = 60 * 1000

function recoverFromStaleChunk(error) {
  if (!isStaleChunkError(error)) return

  // sessionStorage can throw in private browsing / restricted contexts;
  // degrade to "never reload" rather than letting that break routing.
  let storedValue
  try {
    storedValue = sessionStorage.getItem(STALE_CHUNK_RELOAD_KEY)
  } catch {
    return
  }

  if (!shouldReload(storedValue, Date.now(), STALE_CHUNK_RELOAD_COOLDOWN_MS)) return

  try {
    sessionStorage.setItem(STALE_CHUNK_RELOAD_KEY, String(Date.now()))
  } catch {
    // Couldn't record the timestamp — skip the reload rather than risk an
    // unthrottled loop where every failure looks like "no recent reload".
    return
  }

  window.location.reload()
}

router.onError(recoverFromStaleChunk)
window.addEventListener('vite:preloadError', (event) => recoverFromStaleChunk(event.payload))

router.beforeEach(async (to, from, next) => {
  router.previousRoute = from

  const { isLoggedIn, user } = sessionStore()
  const { users, isCrmUser, isAdmin } = usersStore()

  if (isLoggedIn && !users.fetched) {
    try {
      // VOLTEO: a prior attempt in this SPA session may have failed (e.g. backend
      // restart window) and left users.promise settled/rejected forever — awaiting
      // it again would resolve to the same failure without ever retrying. Reload
      // instead so the store self-heals on the next navigation once the backend
      // is back, without requiring a manual page refresh.
      if (users.error) {
        await users.reload()
      } else {
        await users.promise
      }
    } catch (error) {
      console.error('Error loading users', error)
    }
  }

  const isAdminUser = isAdmin() || user === 'Administrator'

  // Only admins who haven't finished may reach the wizard, even via direct URL.
  if (isLoggedIn && to.name === 'Onboarding') {
    try {
      if (!isAdminUser || !(await shouldCapturePersona())) {
        return next({ name: 'Home' })
      }
    } catch {
      return next({ name: 'Home' })
    }
  }

  if (
    isLoggedIn &&
    isCrmUser() &&
    !personaChecked &&
    to.name !== 'Onboarding' &&
    isAdminUser
  ) {
    personaChecked = true
    try {
      if (await shouldCapturePersona()) {
        return next({ name: 'Onboarding' })
      }
    } catch (error) {
      // fail open
    }
  }

  // VOLTEO: only redirect on a confirmed load of the users list. isCrmUser() reads
  // users.data.crmUsers, which is indistinguishable between "genuinely not a CRM
  // user" and "the users fetch failed" (e.g. backend restart window) — without the
  // fetched guard a transient outage reads as a permission denial. If the fetch
  // failed, fail open here: real authorization is enforced server-side, this guard
  // is client-side convenience only.
  if (isLoggedIn && to.name !== 'Not Permitted' && users.fetched && !isCrmUser()) {
    next({ name: 'Not Permitted' })
  } else if (to.name === 'Home' && isLoggedIn) {
    const { views, getDefaultView } = viewsStore()
    try {
      await views.promise
    } catch (e) {
      console.error('[router] views fetch failed; proceeding with defaults', e)
    }

    let defaultView = getDefaultView()
    if (!defaultView) {
      next({ name: window.hide_leads ? 'Deals' : 'Leads' }) // VOLTEO
      return
    }

    let { route_name, type, name, is_standard } = defaultView
    route_name = route_name || (window.hide_leads ? 'Deals' : 'Leads') // VOLTEO

    if (name && !is_standard) {
      next({
        name: route_name,
        params: { viewType: type },
        query: { view: name },
      })
    } else {
      next({ name: route_name, params: { viewType: type } })
    }
  } else if (!isLoggedIn) {
    window.location.href = '/login?redirect-to=/crm'
  } else if (to.matched.length === 0) {
    next({ name: 'Invalid Page' })
  } else if (['Deal', 'Lead'].includes(to.name) && !to.hash) {
    let storageKey = to.name === 'Deal' ? 'lastDealTab' : 'lastLeadTab'
    const activeTab = localStorage.getItem(storageKey) || 'activity'
    const hash = '#' + activeTab
    next({ ...to, hash })
  } else if (
    [
      'Leads',
      'Deals',
      'Contacts',
      'Organizations',
      'Notes',
      'Tasks',
      'Call Logs',
    ].includes(to.name) &&
    !to.query?.view
  ) {
    const { views, standardViews, getDefaultView } = viewsStore()
    try {
      await views.promise
    } catch (e) {
      console.error('[router] views fetch failed; proceeding with defaults', e)
    }

    const viewType = to.params?.viewType ?? ''
    const standardViewTypes = ['list', 'kanban', 'group_by']

    if (!viewType) {
      const doctypeMap = {
        Leads: 'CRM Lead',
        Deals: 'CRM Deal',
        Contacts: 'Contact',
        Organizations: 'CRM Organization',
        Notes: 'FCRM Note',
        Tasks: 'CRM Task',
        'Call Logs': 'CRM Call Log',
      }

      const doctype = doctypeMap[to.name]
      let defaultViewType = 'list'

      let globalDefault = getDefaultView()
      if (globalDefault && globalDefault.route_name === to.name) {
        defaultViewType = globalDefault.type || 'list'
        if (globalDefault.name && !globalDefault.is_standard) {
          next({
            name: to.name,
            params: { viewType: defaultViewType },
            query: { ...to.query, view: globalDefault.name },
          })
          return
        }
      }

      for (const viewType of standardViewTypes) {
        const standardView = standardViews.value?.[doctype + ' ' + viewType]
        if (standardView?.is_default) {
          defaultViewType = viewType
          break
        }
      }

      next({
        name: to.name,
        params: { viewType: defaultViewType },
        query: to.query,
      })
    } else if (!standardViewTypes.includes(viewType)) {
      const viewNameOrLabel = viewType

      let view = views.data?.find(
        (v) => v.name == viewNameOrLabel || v.label === viewNameOrLabel,
      )

      if (view) {
        next({
          name: to.name,
          params: { viewType: view.type || 'list' },
          query: { ...to.query, view: view.name },
        })
      } else {
        next({
          name: to.name,
          params: { viewType: 'list' },
          query: to.query,
        })
      }
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
