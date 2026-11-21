<template>
  <div class="flex h-full flex-col gap-6 p-6 text-ink-gray-8 overflow-y-auto">
    <div class="flex flex-col gap-1 px-2 pt-2">
      <h2 class="text-2xl-semibold leading-none">{{ __('Kategorie handlowców') }}</h2>
      <p class="text-p-sm text-ink-gray-5">
        {{
          __(
            'Kategoria, teren i okręg kampanii FB handlowca decydują, w jakiej kolejności CC dzwoni do leadów. Zmiana zapisuje się od razu.',
          )
        }}
      </p>
    </div>

    <ErrorMessage :message="blad" />

    <div v-if="wczytuje" class="px-2 text-p-sm text-ink-gray-5">{{ __('Wczytywanie...') }}</div>
    <div v-else-if="!wiersze.length" class="rounded-lg border p-3 text-p-sm text-ink-gray-5">
      {{ __('Brak aktywnych handlowców.') }}
    </div>
    <div v-else class="flex flex-col gap-2" data-testid="kategorie-lista">
      <div
        v-for="w in wiersze"
        :key="w.user"
        class="flex flex-wrap items-center gap-3 rounded-lg border p-3"
        :data-testid="'kategoria-wiersz-' + w.user"
      >
        <div class="flex w-48 shrink-0 items-center gap-2">
          <span
            class="inline-block h-3 w-3 shrink-0 rounded-full border"
            :style="stylKropki(w.kategoria)"
          />
          <span class="truncate text-p-base text-ink-gray-8">{{ w.full_name || w.user }}</span>
        </div>
        <div class="w-40">
          <FormControl
            type="select"
            :modelValue="w.kategoria"
            :options="OPCJE_KATEGORII"
            :disabled="Boolean(zapisuje[w.user])"
            @update:modelValue="(v) => zmien(w, { kategoria: v })"
          />
        </div>
        <div class="flex min-w-48 flex-1 items-center gap-2">
          <span class="flex-1 truncate text-p-sm text-ink-gray-6">{{ opisTerenu(w) }}</span>
          <Button
            variant="subtle"
            size="sm"
            :label="__('Ustaw teren')"
            :disabled="Boolean(zapisuje[w.user])"
            @click="otworz(w)"
          />
        </div>
        <div class="w-44">
          <FormControl
            type="select"
            :modelValue="w.okreg"
            :options="OPCJE_OKREGOW"
            :disabled="Boolean(zapisuje[w.user])"
            @update:modelValue="(v) => zmien(w, { okreg: v })"
          />
        </div>
      </div>
    </div>

    <Dialog v-model="dialog.otwarty" :options="{ title: __('Teren handlowca'), size: '3xl' }">
      <template #body-content>
        <div class="flex flex-col gap-3">
          <p class="text-p-sm text-ink-gray-6">{{ dialog.imie }}</p>
          <div class="relative">
            <FormControl
              v-model="dialog.szukaj"
              type="text"
              :label="__('Środek terenu (kod pocztowy albo miejscowość)')"
              placeholder="66-400"
              @update:modelValue="onSzukaj"
            />
            <div
              v-if="kandydaci.length"
              class="absolute z-10 mt-1 max-h-48 w-full overflow-y-auto rounded-md border bg-surface-modal shadow-md"
            >
              <button
                v-for="k in kandydaci"
                :key="k.kod + k.miejscowosc + k.powiat"
                type="button"
                class="block w-full px-3 py-1.5 text-left text-sm text-ink-gray-8 hover:bg-surface-gray-2"
                @click="wybierz(k)"
              >
                {{ etykietaKandydata(k) }}
              </button>
            </div>
          </div>
          <div class="flex items-end gap-3">
            <div class="w-32">
              <FormControl
                v-model="dialog.promien"
                type="number"
                :min="1"
                :max="300"
                :label="__('Promień (km)')"
              />
            </div>
            <p class="flex-1 pb-2 text-xs text-ink-gray-5">
              {{ __('Kliknij w mapę, aby ustawić środek. Odległość w linii prostej.') }}
            </p>
          </div>
          <div class="text-p-sm text-ink-gray-6">{{ opisWyboru }}</div>
          <div class="relative z-0 h-80 w-full overflow-hidden rounded-md border">
            <div ref="mapaEl" class="h-full w-full" data-testid="kategorie-mapa" />
          </div>
          <ErrorMessage :message="dialog.blad" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-between gap-2">
          <Button
            variant="ghost"
            theme="red"
            :label="__('Usuń teren')"
            :disabled="!maSrodek"
            @click="usunTeren"
          />
          <div class="flex gap-2">
            <Button variant="ghost" :label="__('Anuluj')" @click="dialog.otwarty = false" />
            <Button
              variant="solid"
              :label="__('Zapisz teren')"
              :loading="dialog.zapisuje"
              @click="zapiszTeren"
            />
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { createResource, toast, Button, Dialog, ErrorMessage, FormControl } from 'frappe-ui'
import { dodajPodzialke } from '@/utils/mapaPodzialka'
import { etykietaKandydata } from '@/utils/regulyPrzydzialu'
import { KATEGORIE, kolorKategorii } from '@/utils/kategorieHandlowcow'

const API = 'crm.api.kategorie_handlowcow.'
const OKREGI = ['Wrocław', 'Gorzów', 'Szczecin', 'Trójmiasto']
const OPCJE_KATEGORII = [
  { label: __('Bez kategorii'), value: '' },
  ...KATEGORIE.map((k) => ({ label: k, value: k })),
]
const OPCJE_OKREGOW = [
  { label: __('Bez okręgu'), value: '' },
  ...OKREGI.map((o) => ({ label: o, value: o })),
]
const NAZWA_PUNKTU = 'Punkt na mapie'

const wiersze = ref([])
const wczytuje = ref(true)
const blad = ref('')
const zapisuje = reactive({})
const kandydaci = ref([])
const dialog = reactive({
  otwarty: false,
  user: '',
  imie: '',
  szukaj: '',
  nazwa: '',
  lat: 0,
  lng: 0,
  promien: '',
  blad: '',
  zapisuje: false,
})

const maSrodek = computed(() => Boolean(dialog.lat || dialog.lng))
const opisWyboru = computed(() =>
  maSrodek.value
    ? `${dialog.nazwa || NAZWA_PUNKTU} (${Number(dialog.lat).toFixed(4)}, ${Number(dialog.lng).toFixed(4)})`
    : __('Teren nie jest ustawiony.'),
)

function stylKropki(kategoria) {
  const k = kolorKategorii(kategoria)
  return k
    ? { backgroundColor: k.wypelnienie, borderColor: k.obwodka }
    : { backgroundColor: 'transparent' }
}

function opisTerenu(w) {
  if (!(w.teren_lat || w.teren_lng)) return __('Brak terenu')
  return `${w.teren_nazwa || NAZWA_PUNKTU}, ${w.promien_km} km`
}

function komunikat(err, domyslny) {
  return err?.messages?.[0] || domyslny
}

async function wczytaj() {
  try {
    const res = createResource({ url: API + 'lista' })
    wiersze.value = (await res.submit()) || []
    blad.value = ''
  } catch (err) {
    blad.value = komunikat(err, __('Nie udało się wczytać kategorii handlowców'))
  } finally {
    wczytuje.value = false
  }
}

// Serwer zapisuje wszystkie sześć wartości naraz, więc zawsze wysyłamy cały wiersz.
async function zapiszWiersz(w, zmiany) {
  const nowy = { ...w, ...zmiany }
  const res = createResource({
    url: API + 'zapisz',
    makeParams: () => ({
      uzytkownik: nowy.user,
      kategoria: nowy.kategoria,
      teren_nazwa: nowy.teren_nazwa,
      teren_lat: nowy.teren_lat,
      teren_lng: nowy.teren_lng,
      promien_km: nowy.promien_km,
      okreg: nowy.okreg,
    }),
  })
  await res.submit()
  wiersze.value = wiersze.value.map((x) => (x.user === w.user ? nowy : x))
}

async function zmien(w, zmiany) {
  zapisuje[w.user] = true
  try {
    await zapiszWiersz(w, zmiany)
  } catch (err) {
    toast.error(komunikat(err, __('Nie udało się zapisać')))
    await wczytaj()
  } finally {
    zapisuje[w.user] = false
  }
}

// --- Dialog terenu ---
function otworz(w) {
  dialog.user = w.user
  dialog.imie = w.full_name || w.user
  dialog.szukaj = ''
  dialog.nazwa = w.teren_nazwa || ''
  dialog.lat = w.teren_lat || 0
  dialog.lng = w.teren_lng || 0
  dialog.promien = w.promien_km || ''
  dialog.blad = ''
  kandydaci.value = []
  dialog.otwarty = true
}

let licznikSzukania = 0
let timerSzukania = null
function onSzukaj(tekst) {
  clearTimeout(timerSzukania)
  const fraza = (tekst || '').trim()
  if (fraza.length < 2) {
    kandydaci.value = []
    return
  }
  timerSzukania = setTimeout(async () => {
    const numer = ++licznikSzukania
    try {
      const res = createResource({
        url: 'crm.api.reguly_przydzialu.szukaj_srodka',
        makeParams: () => ({ q: fraza }),
      })
      const dane = await res.submit()
      if (numer === licznikSzukania) kandydaci.value = dane || []
    } catch (err) {
      if (numer === licznikSzukania)
        dialog.blad = komunikat(err, __('Nie udało się wyszukać miejscowości'))
    }
  }, 300)
}

function wybierz(k) {
  dialog.lat = Number(k.lat)
  dialog.lng = Number(k.lng)
  dialog.nazwa = k.miejscowosc || etykietaKandydata(k)
  dialog.szukaj = etykietaKandydata(k)
  kandydaci.value = []
  rysuj(true)
}

function usunTeren() {
  dialog.lat = 0
  dialog.lng = 0
  dialog.nazwa = ''
  dialog.promien = ''
  rysuj()
}

async function zapiszTeren() {
  const w = wiersze.value.find((x) => x.user === dialog.user)
  if (!w) return
  const promien = Number(dialog.promien)
  if (maSrodek.value && !(Number.isInteger(promien) && promien >= 1 && promien <= 300)) {
    dialog.blad = __('Promień musi być liczbą całkowitą od 1 do 300 km.')
    return
  }
  dialog.blad = ''
  dialog.zapisuje = true
  try {
    await zapiszWiersz(w, {
      teren_nazwa: maSrodek.value ? dialog.nazwa || NAZWA_PUNKTU : '',
      teren_lat: maSrodek.value ? dialog.lat : 0,
      teren_lng: maSrodek.value ? dialog.lng : 0,
      promien_km: maSrodek.value ? promien : 0,
    })
    dialog.otwarty = false
  } catch (err) {
    dialog.blad = komunikat(err, __('Nie udało się zapisać terenu'))
  } finally {
    dialog.zapisuje = false
  }
}

// --- Mapa (Leaflet ładowany leniwie, tworzona przy otwarciu dialogu, niszczona przy zamknięciu) ---
const mapaEl = ref(null)
let L = null
let mapa = null
let warstwa = null

async function startMapy() {
  await nextTick()
  const el = mapaEl.value
  if (!el) return
  await import('leaflet/dist/leaflet.css')
  const modul = await import('leaflet')
  L = modul.default ?? modul
  if (!dialog.otwarty || !mapaEl.value) return
  zniszczMape()
  mapa = L.map(mapaEl.value).setView([52.0, 19.3], 6)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution:
      '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(mapa)
  dodajPodzialke(L, mapa)
  warstwa = L.featureGroup().addTo(mapa)
  mapa.on('click', (e) => {
    dialog.lat = e.latlng.lat
    dialog.lng = e.latlng.lng
    dialog.nazwa = NAZWA_PUNKTU
    dialog.szukaj = ''
    rysuj()
  })
  // Dialog animuje się przy otwarciu, więc rozmiar kontenera zmienia się po inicjalizacji.
  setTimeout(() => {
    if (!mapa) return
    mapa.invalidateSize()
    rysuj(true)
  }, 200)
}

function rysuj(przesun = false) {
  if (!mapa || !L || !warstwa) return
  warstwa.clearLayers()
  if (!maSrodek.value) return
  const kolor = kolorKategorii(wiersze.value.find((x) => x.user === dialog.user)?.kategoria)
  const barwa = kolor ? kolor.obwodka : '#2563eb'
  const promien = Number(dialog.promien)
  L.marker([dialog.lat, dialog.lng]).addTo(warstwa)
  if (Number.isFinite(promien) && promien > 0) {
    L.circle([dialog.lat, dialog.lng], {
      radius: promien * 1000,
      color: barwa,
      weight: 2,
      fillColor: kolor ? kolor.wypelnienie : barwa,
      fillOpacity: 0.15,
    }).addTo(warstwa)
  }
  if (przesun) {
    const granice = warstwa.getBounds()
    if (granice.isValid()) mapa.fitBounds(granice, { padding: [20, 20], maxZoom: 10 })
  }
}

function zniszczMape() {
  if (mapa) {
    mapa.remove()
    mapa = null
    warstwa = null
  }
}

watch(
  () => dialog.otwarty,
  (otwarty) => {
    if (otwarty) startMapy()
    else {
      zniszczMape()
      kandydaci.value = []
    }
  },
)
watch(
  () => dialog.promien,
  () => rysuj(true),
)

onMounted(wczytaj)
onBeforeUnmount(() => {
  clearTimeout(timerSzukania)
  zniszczMape()
})
</script>
