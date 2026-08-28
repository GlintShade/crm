<!--
  Mapa leadów D2D (b52, ops#26) — piny geokodowanych leadów na OSM/Leaflet.

  Dane: `crm.api.volteo_leady.mapa` (frappe.get_list, więc scoping ról robi
  serwer przez crm/permissions/org_hierarchy.py — rep dostaje tylko swoje
  leady, admin/backend wszystkie; ta strona nie implementuje żadnej logiki
  uprawnień). Endpoint zwraca WYŁĄCZNIE leady z ustawionym geokodem
  (custom_lat != 0) — licznik "N leadów bez współrzędnych" jest tu celowo
  pominięty: policzenie go wymagałoby albo osobnego wywołania statystyk,
  albo zmiany API, a ten issue miał wyraźny zakaz dotykania mapa() (konflikt
  plików z issue #24). Z tego samego powodu brak tu filtra województwa —
  mapa() nie zwraca custom_voivodeship.

  Leaflet ładowany leniwie (wzorzec: Controls/GeolocationControl.vue
  L203-272) — tylko warstwa OSM, `preferCanvas: true` bo ~11 tys. pinów.
  Piny to L.circleMarker (wektor na canvasie), więc — inaczej niż w
  GeolocationControl — nie trzeba łatać ikon markerów przez ?url.

  Kolory pinów: hex są w porządku na canvasie Leafleta (to rysowanie na
  mapie, nie UI motywu) — CLAUDE.md pozwala na to wyraźnie. Reszta interfejsu
  wokół mapy (filtry, stopka, spinner) trzyma się wyłącznie tokenów
  ink-*/surface-*/outline-* jak wszędzie indziej.
-->
<template>
  <div class="flex h-full flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <ViewBreadcrumbs routeName="MapaLeadow" />
      </template>
    </LayoutHeader>

    <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
      <ErrorMessage class="mx-4 mt-3" :message="blad" />

      <!-- Filtry -->
      <div
        class="flex flex-wrap items-center gap-3 border-b border-outline-gray-2 px-4 py-3"
      >
        <div class="flex flex-wrap items-center gap-1.5">
          <button
            v-for="s in statusyZListy"
            :key="s.status"
            type="button"
            class="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm transition-colors"
            :class="
              aktywneStatusy.has(s.status)
                ? 'border-outline-gray-3 bg-surface-gray-3 text-ink-gray-8'
                : 'border-outline-gray-2 text-ink-gray-5 hover:bg-surface-gray-1'
            "
            @click="toggleStatus(s.status)"
          >
            <span
              class="h-2 w-2 shrink-0 rounded-full"
              :style="{ backgroundColor: kolorStatusu(s.status) }"
            />
            <span>{{ s.status }}</span>
            <span class="text-ink-gray-4">({{ s.liczba }})</span>
          </button>
        </div>

        <FormControl
          v-if="pokazSelectHandlowca"
          v-model="filtrHandlowiec"
          type="select"
          variant="outline"
          class="w-52"
          :options="opcjeHandlowcow"
        />

        <FormControl
          v-model="filtrMiasto"
          type="text"
          variant="outline"
          class="w-52"
          :placeholder="__('Szukaj miasta…')"
        />

        <div class="ml-auto shrink-0 text-sm text-ink-gray-5">
          {{ __('{0} z {1} leadów z lokalizacją', [leadyPrzefiltrowane.length, stan.leady.length]) }}
        </div>
      </div>

      <!-- Mapa -->
      <div class="relative min-h-0 flex-1">
        <div
          v-if="initialLoading"
          class="absolute inset-0 z-[1000] flex items-center justify-center bg-surface-white/70 dark:bg-surface-gray-1/70"
        >
          <LoadingIndicator class="size-8" />
        </div>
        <div :id="mapId" class="h-full w-full" />
      </div>

      <!-- Atrybucje (wymóg licencyjny OSM + GeoNames) -->
      <div
        class="border-t border-outline-gray-2 px-4 py-1.5 text-xs text-ink-gray-4"
      >
        {{ __('© OpenStreetMap contributors') }}
        ·
        {{ __('kody pocztowe: GeoNames, CC-BY 4.0') }}
      </div>
    </div>
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import { usersStore } from '@/stores/users'
import { sessionStore } from '@/stores/session'
import { statusesStore } from '@/stores/statuses'
import { colorNameFromParsed } from '@/utils/statusColors'
import router from '@/router'
import {
  ErrorMessage,
  FormControl,
  LoadingIndicator,
  createResource,
  usePageMeta,
} from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

usePageMeta(() => {
  return { title: __('Mapa leadów') }
})

const mapId = `mapa-leadow-${Math.random().toString(36).slice(2)}`

const { user: currentUser } = sessionStore()
const { getUser } = usersStore()
const { getLeadStatus } = statusesStore()

// --- Dane z API --------------------------------------------------------------

const stan = reactive({ leady: [] })
const blad = ref('')

const listResource = createResource({
  url: 'crm.api.volteo_leady.mapa',
  auto: true,
  onSuccess: (data) => {
    stan.leady = data || []
    blad.value = ''
    aktywneStatusy.value = new Set(stan.leady.map((lead) => lead.status || BRAK_STATUSU))
  },
  onError: (err) => {
    blad.value = extractErrorMessage(err) || __('Nie udało się wczytać leadów z mapy')
  },
})

const initialLoading = computed(() => listResource.loading && !listResource.data)

// Precedent: DokumentyLista.vue's extractErrorMessage() — call()/createResource
// throw an error whose Polish server message lives in err.messages[0], not
// under _server_messages/exception.
function extractErrorMessage(err) {
  try {
    if (err?.messages?.length && err.messages[0]) return err.messages[0]
    if (err && err._server_messages) {
      const msgs = JSON.parse(err._server_messages)
      if (msgs && msgs.length) {
        const first = JSON.parse(msgs[0])
        return first.message || ''
      }
    }
    if (err && err.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || ''
    }
    if (err && err.message) return err.message
  } catch (e) {
    /* fall through */
  }
  return ''
}

// --- Kolory statusów -----------------------------------------------------------

const BRAK_STATUSU = __('(brak)')

// Leaflet rysuje na <canvas> — potrzebuje realnego koloru CSS, nie klasy
// Tailwind. Mapa nazwa->hex odpowiada w przybliżeniu odcieniowi, jaki
// parseColor() (utils/index.js) generuje dla statusów w reszcie CRM (-600,
// poza gray/green -700 i black -> ink-gray-9) — piny są więc spójne
// kolorystycznie z badge'ami/przyciskami statusów gdzie indziej w appce.
const HEX_PO_NAZWIE_KOLORU = {
  black: '#18181b',
  gray: '#374151',
  blue: '#2563eb',
  green: '#15803d',
  red: '#dc2626',
  pink: '#db2777',
  orange: '#ea580c',
  amber: '#d97706',
  yellow: '#ca8a04',
  cyan: '#0891b2',
  teal: '#0d9488',
  violet: '#7c3aed',
  purple: '#9333ea',
}

function kolorStatusu(status) {
  const parsed = getLeadStatus(status)?.color
  const nazwa = colorNameFromParsed(parsed)
  return HEX_PO_NAZWIE_KOLORU[nazwa] || HEX_PO_NAZWIE_KOLORU.gray
}

// --- Filtry --------------------------------------------------------------------

const statusyZListy = computed(() => {
  const liczniki = new Map()
  for (const lead of stan.leady) {
    const status = lead.status || BRAK_STATUSU
    liczniki.set(status, (liczniki.get(status) || 0) + 1)
  }
  return [...liczniki.entries()]
    .map(([status, liczba]) => ({ status, liczba }))
    .sort((a, b) => b.liczba - a.liczba)
})

const aktywneStatusy = ref(new Set())

function toggleStatus(status) {
  const next = new Set(aktywneStatusy.value)
  if (next.has(status)) {
    next.delete(status)
  } else {
    next.add(status)
  }
  aktywneStatusy.value = next
}

const unikalniWlasciciele = computed(() =>
  [...new Set(stan.leady.map((lead) => lead.lead_owner).filter(Boolean))],
)

// Select handlowca pokazuje się tylko gdy zwrócone dane zawierają cudzego
// lead_owner — czyli de facto tylko dla admina/backoffice'u. Serwerowy
// scoping (org_hierarchy.py) i tak ogranicza szeregowego repa do jego
// własnych leadów, więc dla niego ta gałąź nigdy nie jest prawdziwa.
const pokazSelectHandlowca = computed(() => {
  const wlasciciele = unikalniWlasciciele.value
  if (wlasciciele.length > 1) return true
  return wlasciciele.length === 1 && wlasciciele[0] !== currentUser.value
})

const opcjeHandlowcow = computed(() => [
  { label: __('Wszyscy handlowcy'), value: '' },
  ...unikalniWlasciciele.value.map((email) => ({
    label: getUser(email).full_name || email,
    value: email,
  })),
])

const filtrHandlowiec = ref('')
const filtrMiasto = ref('')

// Lekki debounce (200ms) na wyszukiwarce miasta — bez niego każde
// naciśnięcie klawisza czyściłoby i przerysowywało do 11 tys. circleMarkerów.
const filtrMiastoDebounced = ref('')
let miastoTimer = null
watch(filtrMiasto, (val) => {
  clearTimeout(miastoTimer)
  miastoTimer = setTimeout(() => {
    filtrMiastoDebounced.value = val
  }, 200)
})

const leadyPrzefiltrowane = computed(() => {
  const miasto = filtrMiastoDebounced.value.trim().toLowerCase()
  return stan.leady.filter((lead) => {
    const status = lead.status || BRAK_STATUSU
    if (!aktywneStatusy.value.has(status)) return false
    if (filtrHandlowiec.value && lead.lead_owner !== filtrHandlowiec.value) return false
    if (miasto && !(lead.custom_install_city || '').toLowerCase().includes(miasto)) return false
    return true
  })
})

watch(leadyPrzefiltrowane, () => rysujMarkery())

// --- Mikro-jitter deterministyczny ---------------------------------------------

// Piny z tego samego kodu pocztowego geokodują się na (prawie) identyczne
// współrzędne i inaczej stałyby jeden na drugim. Hash nazwy leada (stabilny
// identyfikator, np. CRM-LEAD-2026-00123) daje deterministyczne przesunięcie:
// ten sam lead zawsze ląduje w tym samym miejscu między przeładowaniami.
function hashString(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i)
    hash |= 0
  }
  return hash
}

const JITTER_DEG = 0.005

function jitterOffset(name, sol) {
  const h = hashString(`${name}:${sol}`)
  // h jest 32-bit signed; % 2000 daje -1999..1999, normalizacja do [-1, 1).
  return ((h % 2000) / 2000) * JITTER_DEG
}

// --- Leaflet ---------------------------------------------------------------------

let L = null
let mapInstance = null
let markerLayer = null
let dopasowanoWidok = false

async function initMap() {
  if (!L) {
    await import('leaflet/dist/leaflet.css')
    const leafletModule = await import('leaflet')
    L = leafletModule.default ?? leafletModule
  }

  mapInstance = L.map(mapId, { preferCanvas: true }).setView([52.0, 19.3], 6)

  // TYLKO warstwa OSM (Stadia wymaga klucza na niedev domenach — nie używać).
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution:
      '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(mapInstance)

  markerLayer = L.featureGroup().addTo(mapInstance)

  rysujMarkery()
}

function rysujMarkery() {
  if (!L || !mapInstance || !markerLayer) return

  markerLayer.clearLayers()

  for (const lead of leadyPrzefiltrowane.value) {
    const lat = Number(lead.custom_lat) + jitterOffset(lead.name, 'lat')
    const lng = Number(lead.custom_lng) + jitterOffset(lead.name, 'lng')
    if (!isFinite(lat) || !isFinite(lng)) continue

    const kolor = kolorStatusu(lead.status)
    const marker = L.circleMarker([lat, lng], {
      radius: 6,
      color: kolor,
      weight: 1,
      fillColor: kolor,
      fillOpacity: 0.75,
    })
    marker.bindPopup(() => budujPopup(lead))
    marker.addTo(markerLayer)
  }

  if (!dopasowanoWidok && leadyPrzefiltrowane.value.length) {
    const bounds = markerLayer.getBounds()
    if (bounds.isValid()) {
      mapInstance.fitBounds(bounds, { padding: [20, 20] })
    }
    dopasowanoWidok = true
  }
}

// Budowane przez DOM (nie string HTML) — bezpieczne wobec lead_name z
// dowolną treścią i nie wymaga v-html.
function budujPopup(lead) {
  const container = document.createElement('div')
  container.className = 'flex flex-col gap-1'

  const title = document.createElement('div')
  title.className = 'text-sm font-medium text-ink-gray-9'
  title.textContent = lead.lead_name || lead.name
  container.appendChild(title)

  const city = document.createElement('div')
  city.className = 'text-sm text-ink-gray-6'
  city.textContent = lead.custom_install_city || '—'
  container.appendChild(city)

  const status = document.createElement('div')
  status.className = 'text-sm text-ink-gray-6'
  status.textContent = lead.status || BRAK_STATUSU
  container.appendChild(status)

  const link = document.createElement('button')
  link.type = 'button'
  link.className = 'mt-1 self-start text-sm text-ink-blue-3 underline'
  link.textContent = __('Otwórz leada')
  link.addEventListener('click', () => {
    router.push({ name: 'Lead', params: { leadId: lead.name } })
  })
  container.appendChild(link)

  return container
}

function destroyMap() {
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
    markerLayer = null
  }
}

onMounted(() => initMap())
onBeforeUnmount(() => {
  clearTimeout(miastoTimer)
  destroyMap()
})
</script>
