<template>
  <div class="flex flex-col gap-4 px-2" data-testid="reguly-panel">
    <div class="flex items-center gap-3">
      <div class="min-w-0 flex-1">
        <div class="text-base-semibold">{{ __('Reguły dla nowych leadów z Facebooka') }}</div>
        <p class="text-p-sm text-ink-gray-6">
          {{
            __(
              'Lead, którego kod pocztowy leży w obszarze, trafia od razu do handlowca. Pozostałe leady obsługuje CC.',
            )
          }}
        </p>
      </div>
      <Button
        variant="solid"
        icon-left="plus"
        :label="__('Dodaj regułę')"
        data-testid="regula-dodaj"
        @click="otworzDialog(null)"
      />
    </div>

    <ErrorMessage :message="blad" />

    <div
      v-if="!stan.smsWlaczony && stan.reguly.some((r) => r.aktywna)"
      class="rounded-lg border border-outline-amber-3 bg-surface-amber-2 px-3 py-2 text-p-sm text-ink-amber-8"
      data-testid="reguly-sms-wylaczony"
    >
      {{
        __(
          'SMS do handlowca o nowym leadzie jest wyłączony. Handlowcy dostaną leady bez SMS-a. Włącz go w Ustawieniach, w panelu SMS do handlowców.',
        )
      }}
    </div>

    <div v-if="listResource.loading && !stan.reguly.length" class="text-p-sm text-ink-gray-5">
      {{ __('Wczytywanie…') }}
    </div>
    <div v-else-if="!stan.reguly.length" class="text-p-sm text-ink-gray-5">
      {{ __('Brak reguł. Wszystkie leady z Facebooka obsługuje CC.') }}
    </div>
    <div v-else class="overflow-x-auto">
      <table class="w-full border-collapse text-sm">
        <thead>
          <tr class="bg-surface-gray-2 text-ink-gray-5">
            <th class="w-14 px-3 py-2.5 text-left font-medium">{{ __('Kolej.') }}</th>
            <th class="px-3 py-2.5 text-left font-medium">{{ __('Handlowiec') }}</th>
            <th class="px-3 py-2.5 text-left font-medium">{{ __('Obszar') }}</th>
            <th class="px-3 py-2.5 text-right font-medium">{{ __('Leady (30 dni)') }}</th>
            <th class="px-3 py-2.5 text-left font-medium">{{ __('Aktywna') }}</th>
            <th class="w-40 px-3 py-2.5"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(r, i) in stan.reguly"
            :key="r.name"
            class="border-t border-outline-gray-1"
            :class="{ 'opacity-60': !r.aktywna }"
            data-testid="regula-wiersz"
          >
            <td class="px-3 py-2.5">
              <span
                class="inline-flex h-6 w-6 items-center justify-center rounded-full text-xs-medium text-white"
                :style="{ backgroundColor: kolorReguly(i) }"
                >{{ r.kolejnosc }}</span
              >
            </td>
            <td class="px-3 py-2.5 text-ink-gray-8">
              <div class="font-medium">{{ r.handlowiec_nazwa }}</div>
              <div v-for="o in r.ostrzezenia" :key="o" class="text-xs text-ink-amber-8">{{ o }}</div>
            </td>
            <td class="px-3 py-2.5 text-ink-gray-8">{{ opisObszaru(r) }}</td>
            <td class="px-3 py-2.5 text-right text-ink-gray-8">{{ r.leady_30_dni }}</td>
            <td class="px-3 py-2.5">
              <Switch
                :modelValue="Boolean(r.aktywna)"
                :disabled="zapisuje"
                data-testid="regula-aktywna"
                @update:modelValue="(v) => przelacz(r, v)"
              />
            </td>
            <td class="whitespace-nowrap px-3 py-2.5 text-right">
              <Button
                variant="ghost"
                size="sm"
                icon="chevron-up"
                :aria-label="__('Wyżej')"
                :disabled="zapisuje || i === 0"
                data-testid="regula-wyzej"
                @click="przesun(i, 'wyzej')"
              />
              <Button
                variant="ghost"
                size="sm"
                icon="chevron-down"
                :aria-label="__('Niżej')"
                :disabled="zapisuje || i === stan.reguly.length - 1"
                data-testid="regula-nizej"
                @click="przesun(i, 'nizej')"
              />
              <Button
                variant="ghost"
                size="sm"
                icon="edit"
                :aria-label="__('Edytuj')"
                data-testid="regula-edytuj"
                @click="otworzDialog(r)"
              />
              <Button
                variant="ghost"
                size="sm"
                theme="red"
                icon="trash-2"
                :aria-label="__('Usuń')"
                data-testid="regula-usun"
                @click="doUsuniecia = r"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="flex flex-col gap-4 lg:flex-row">
      <div class="relative isolate min-w-0 flex-1" style="min-height: 320px">
        <div ref="mapaEl" class="h-80 w-full rounded-lg border" data-testid="reguly-mapa"></div>
      </div>
      <div class="flex w-full flex-col gap-2 rounded-lg border p-3 lg:w-64 lg:flex-none">
        <div class="text-base-semibold">{{ __('Sprawdź kod pocztowy') }}</div>
        <div class="flex gap-2">
          <div class="min-w-0 flex-1" data-testid="sprawdz-kod-pole">
            <FormControl
              v-model="kodDoSprawdzenia"
              type="text"
              placeholder="66-200"
              :aria-label="__('Kod pocztowy')"
              @keydown.enter="sprawdz"
            />
          </div>
          <Button
            :label="__('Sprawdź')"
            :loading="sprawdzResource.loading"
            data-testid="sprawdz-kod-przycisk"
            @click="sprawdz"
          />
        </div>
        <ErrorMessage :message="bladSprawdzenia" />
        <div
          v-if="wynik"
          class="flex flex-col gap-1 rounded-md border p-2 text-sm"
          :class="wynik.wariant === 'regula' ? 'border-outline-green-2' : 'border-outline-gray-3'"
          :data-wariant="wynik.wariant"
          data-testid="sprawdz-kod-wynik"
        >
          <span v-if="wynik.lokalizacja" class="text-xs text-ink-gray-5">{{ wynik.lokalizacja }}</span>
          <span class="font-semibold text-ink-gray-9">{{ wynik.tytul }}</span>
          <span v-for="s in wynik.szczegoly" :key="s" class="text-xs text-ink-gray-6">{{ s }}</span>
        </div>
      </div>
    </div>

    <p class="text-p-sm text-ink-gray-5">
      {{
        __(
          'Leady spoza obszarów i leady bez znanego położenia kodu obsługuje CC. SMS dostaje wtedy osoba na dyżurze.',
        )
      }}
    </p>

    <!-- Okno reguły -->
    <Dialog v-model="dialog.otwarty" :options="{ title: __('Reguła bezpośrednia') }">
      <template #body-content>
        <div class="flex flex-col gap-4">
          <div data-testid="regula-pole-handlowiec">
            <FormControl
              v-model="dialog.handlowiec"
              type="select"
              :label="__('Handlowiec')"
              :options="opcjeHandlowcow"
            />
          </div>
          <div
            v-if="kontrola.length"
            class="flex flex-col gap-0.5 rounded-md border p-2 text-xs"
            data-testid="regula-kontrola"
          >
            <span
              v-for="k in kontrola"
              :key="k.tekst"
              :class="k.ok ? 'text-ink-green-8' : 'text-ink-amber-8'"
              >{{ k.ok ? '✓' : '!' }} {{ k.tekst }}</span
            >
          </div>

          <div class="relative" data-testid="regula-pole-srodek">
            <FormControl
              v-model="dialog.szukaj"
              type="text"
              :label="__('Środek obszaru (kod pocztowy albo miejscowość)')"
              placeholder="66-400"
              @update:modelValue="onSzukaj"
            />
            <div
              v-if="kandydaci.length"
              class="absolute z-10 mt-1 max-h-48 w-full overflow-y-auto rounded-md border bg-surface-modal shadow-md"
              data-testid="regula-kandydaci"
            >
              <button
                v-for="k in kandydaci"
                :key="k.kod + k.miejscowosc + k.powiat"
                type="button"
                class="block w-full px-3 py-1.5 text-left text-sm text-ink-gray-8 hover:bg-surface-gray-2"
                @click="wybierzKandydata(k)"
              >
                {{ etykietaKandydata(k) }}
              </button>
            </div>
            <p class="mt-1 text-xs text-ink-gray-5">
              {{ __('Jeśli miejscowości nie ma na liście, wpisz jej kod pocztowy.') }}
            </p>
            <p v-if="dialog.srodekKod" class="mt-1 text-xs text-ink-gray-6">
              {{ __('Wybrany kod: {0}', [dialog.srodekKod]) }}
            </p>
          </div>

          <div data-testid="regula-pole-nazwa">
            <FormControl
              v-model="dialog.srodekNazwa"
              type="text"
              :label="__('Nazwa obszaru')"
              placeholder="Gorzów Wielkopolski"
            />
          </div>

          <div class="flex items-end gap-3">
            <div class="w-32" data-testid="regula-pole-promien">
              <FormControl
                v-model="dialog.promien"
                type="number"
                :min="1"
                :label="__('Promień (km)')"
                @update:modelValue="odswiezPodglad"
              />
            </div>
            <p class="flex-1 pb-2 text-xs text-ink-gray-5">
              {{ __('Odległość w linii prostej, nie drogowa.') }}
            </p>
          </div>

          <div
            v-if="podglad !== null"
            class="rounded-md border p-2 text-xs text-ink-gray-7"
            data-testid="regula-podglad"
          >
            {{ __('W ostatnich 30 dniach w tym obszarze było {0} leadów z Facebooka.', [podglad]) }}
          </div>

          <div data-testid="regula-pole-aktywna">
            <FormControl v-model="dialog.aktywna" type="checkbox" :label="__('Aktywna')" />
          </div>
          <ErrorMessage :message="dialog.blad" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button variant="ghost" :label="__('Anuluj')" @click="dialog.otwarty = false" />
          <Button
            variant="solid"
            :label="__('Zapisz regułę')"
            :loading="zapisuje"
            data-testid="regula-zapisz"
            @click="zapiszRegule"
          />
        </div>
      </template>
    </Dialog>

    <!-- Potwierdzenie usunięcia -->
    <Dialog v-model="potwierdzenieOtwarte" :options="{ title: __('Usunąć regułę?') }">
      <template #body-content>
        <p class="text-p-base text-ink-gray-7">
          {{
            __('Reguła dla {0} ({1}) zostanie usunięta. Nowe leady z tego obszaru obsłuży CC.', [
              doUsuniecia?.handlowiec_nazwa,
              doUsuniecia ? opisObszaru(doUsuniecia) : '',
            ])
          }}
        </p>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button variant="ghost" :label="__('Anuluj')" @click="doUsuniecia = null" />
          <Button
            variant="solid"
            theme="red"
            :label="__('Usuń')"
            :loading="zapisuje"
            data-testid="regula-usun-potwierdz"
            @click="usun"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { dodajPodzialke } from '@/utils/mapaPodzialka'
import { createResource, toast, Button, Dialog, ErrorMessage, FormControl, Switch } from 'frappe-ui'
import {
  kolorReguly,
  opisObszaru,
  etykietaKandydata,
  przesunNazwy,
  opisWynikuKodu,
  kontrolaHandlowca,
  walidujFormularzReguly,
  punktKodu,
  MIN_ZNAKOW_SZUKANIA,
  PROMIEN_DOMYSLNY_KM,
} from '@/utils/regulyPrzydzialu'

const API = 'crm.api.reguly_przydzialu.'

// Pełny kształt stanu od początku, zawsze podmieniany na świeżą wartość.
const stan = reactive({ reguly: [], handlowcy: [], smsWlaczony: true })
const blad = ref('')
const zapisuje = ref(false)

function zastosuj(dane) {
  stan.reguly = dane?.reguly || []
  stan.handlowcy = dane?.handlowcy || []
  // Brak klucza (stary backend) znaczy: nie ostrzegaj.
  stan.smsWlaczony = dane?.sms_wlaczony !== false
  rysujMape()
}

const listResource = createResource({
  url: API + 'lista',
  auto: true,
  onSuccess: (d) => {
    blad.value = ''
    zastosuj(d)
  },
  onError: (err) => {
    blad.value = err?.messages?.[0] || __('Nie udało się wczytać reguł')
  },
})

// Jedno miejsce na wywołania zapisujące: zwraca świeże `lista()`.
async function wywolaj(metoda, params, bladDomyslny) {
  zapisuje.value = true
  try {
    const res = createResource({ url: API + metoda, makeParams: () => params })
    const dane = await res.submit()
    zastosuj(dane)
    blad.value = ''
    return true
  } catch (err) {
    const komunikat = err?.messages?.[0] || bladDomyslny
    toast.error(komunikat)
    return komunikat
  } finally {
    zapisuje.value = false
  }
}

async function przelacz(r, wartosc) {
  const wynik = await wywolaj('przelacz', { name: r.name, aktywna: wartosc ? 1 : 0 }, __('Nie udało się zmienić reguły'))
  // Błąd: lista nie została podmieniona, więc przełącznik wraca do stanu z `stan`,
  // ale wymuszamy odświeżenie renderu.
  if (wynik !== true) stan.reguly = [...stan.reguly]
}

async function przesun(i, kierunek) {
  const nowe = przesunNazwy(
    stan.reguly.map((r) => r.name),
    i,
    kierunek,
  )
  if (!nowe) return
  await wywolaj('ustaw_kolejnosc', { nazwy: JSON.stringify(nowe) }, __('Nie udało się zmienić kolejności'))
}

// --- Usuwanie ---
const doUsuniecia = ref(null)
const potwierdzenieOtwarte = computed({
  get: () => doUsuniecia.value !== null,
  set: (v) => {
    if (!v) doUsuniecia.value = null
  },
})

async function usun() {
  if (!doUsuniecia.value) return
  const wynik = await wywolaj('usun', { name: doUsuniecia.value.name }, __('Nie udało się usunąć reguły'))
  if (wynik === true) doUsuniecia.value = null
}

// --- Okno reguły ---
const dialog = reactive({
  otwarty: false,
  name: null,
  handlowiec: '',
  szukaj: '',
  srodekKod: '',
  srodekNazwa: '',
  promien: PROMIEN_DOMYSLNY_KM,
  aktywna: true,
  blad: '',
})
const kandydaci = ref([])
const podglad = ref(null)

const opcjeHandlowcow = computed(() => [
  { label: __('Wybierz handlowca'), value: '' },
  ...stan.handlowcy.map((h) => ({ label: h.full_name || h.user, value: h.user })),
])
const kontrola = computed(() =>
  kontrolaHandlowca(stan.handlowcy.find((h) => h.user === dialog.handlowiec)),
)

function otworzDialog(r) {
  dialog.name = r?.name || null
  dialog.handlowiec = r?.handlowiec || ''
  dialog.szukaj = r ? r.srodek_kod || r.srodek_nazwa || '' : ''
  dialog.srodekKod = r?.srodek_kod || ''
  dialog.srodekNazwa = r?.srodek_nazwa || ''
  dialog.promien = r ? r.promien_km : PROMIEN_DOMYSLNY_KM
  dialog.aktywna = r ? Boolean(r.aktywna) : true
  dialog.blad = ''
  kandydaci.value = []
  podglad.value = null
  dialog.otwarty = true
  if (dialog.srodekKod) odswiezPodglad()
}

let licznikSzukania = 0
let timerSzukania = null
function onSzukaj(tekst) {
  // Ręczna zmiana pola unieważnia wcześniej wybrany kod.
  dialog.srodekKod = ''
  podglad.value = null
  clearTimeout(timerSzukania)
  const fraza = (tekst || '').trim()
  if (fraza.length < MIN_ZNAKOW_SZUKANIA) {
    kandydaci.value = []
    return
  }
  timerSzukania = setTimeout(async () => {
    const numer = ++licznikSzukania
    try {
      const res = createResource({ url: API + 'szukaj_srodka', makeParams: () => ({ q: fraza }) })
      const dane = await res.submit()
      if (numer !== licznikSzukania) return
      kandydaci.value = dane || []
      // Wpisany pełny kod pocztowy działa bez klikania w listę.
      if (/^\d{2}-?\d{3}$/.test(fraza) && kandydaci.value.length) {
        dialog.srodekKod = kandydaci.value[0].kod
        if (!dialog.srodekNazwa) dialog.srodekNazwa = kandydaci.value[0].miejscowosc || ''
        odswiezPodglad()
      }
    } catch (err) {
      if (numer !== licznikSzukania) return
      dialog.blad = err?.messages?.[0] || __('Nie udało się wyszukać miejscowości')
    }
  }, 300)
}

function wybierzKandydata(k) {
  dialog.srodekKod = k.kod
  dialog.srodekNazwa = k.miejscowosc || ''
  dialog.szukaj = etykietaKandydata(k)
  kandydaci.value = []
  odswiezPodglad()
}

let licznikPodgladu = 0
let timerPodgladu = null
function odswiezPodglad() {
  clearTimeout(timerPodgladu)
  const promien = Number(dialog.promien)
  if (!dialog.srodekKod || !Number.isFinite(promien) || promien < 1) {
    podglad.value = null
    return
  }
  timerPodgladu = setTimeout(async () => {
    const numer = ++licznikPodgladu
    try {
      const res = createResource({
        url: API + 'podglad_obszaru',
        makeParams: () => ({ srodek_kod: dialog.srodekKod, promien_km: promien }),
      })
      const dane = await res.submit()
      if (numer !== licznikPodgladu) return
      podglad.value = dane?.leady_30_dni ?? null
    } catch (err) {
      if (numer !== licznikPodgladu) return
      podglad.value = null
    }
  }, 300)
}

async function zapiszRegule() {
  const komunikat = walidujFormularzReguly({
    handlowiec: dialog.handlowiec,
    srodek_kod: dialog.srodekKod,
    promien_km: dialog.promien,
  })
  if (komunikat) {
    dialog.blad = komunikat
    return
  }
  dialog.blad = ''
  const params = {
    handlowiec: dialog.handlowiec,
    srodek_kod: dialog.srodekKod,
    srodek_nazwa: dialog.srodekNazwa.trim(),
    promien_km: Number(dialog.promien),
    aktywna: dialog.aktywna ? 1 : 0,
  }
  if (dialog.name) params.name = dialog.name
  const wynik = await wywolaj('zapisz', params, __('Nie udało się zapisać reguły'))
  if (wynik === true) dialog.otwarty = false
  else dialog.blad = wynik
}

// --- Sprawdzanie kodu ---
const kodDoSprawdzenia = ref('')
const wynik = ref(null)
const surowyWynik = ref(null)
const bladSprawdzenia = ref('')
const sprawdzResource = createResource({
  url: API + 'sprawdz_kod',
  makeParams: () => ({ kod: kodDoSprawdzenia.value.trim() }),
  onSuccess: (d) => {
    bladSprawdzenia.value = ''
    wynik.value = opisWynikuKodu(d)
    surowyWynik.value = d
    rysujMape()
  },
  onError: (err) => {
    wynik.value = null
    surowyWynik.value = null
    rysujMape()
    bladSprawdzenia.value = err?.messages?.[0] || __('Nie udało się sprawdzić kodu')
  },
})

function sprawdz() {
  if (!kodDoSprawdzenia.value.trim()) {
    bladSprawdzenia.value = __('Wpisz kod pocztowy.')
    return
  }
  bladSprawdzenia.value = ''
  sprawdzResource.submit().catch(() => {})
}

// --- Mapa ---
const mapaEl = ref(null)
let L = null
let mapa = null
let warstwa = null

async function inicjujMape() {
  if (!mapaEl.value) return
  await import('leaflet/dist/leaflet.css')
  const modul = await import('leaflet')
  L = modul.default ?? modul
  if (!mapaEl.value) return
  mapa = L.map(mapaEl.value).setView([52.0, 19.3], 6)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution:
      '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(mapa)
  dodajPodzialke(L, mapa)
  warstwa = L.featureGroup().addTo(mapa)
  rysujMape()
}

function rysujMape() {
  if (!mapa || !L || !warstwa) return
  warstwa.clearLayers()
  stan.reguly.forEach((r, i) => {
    const lat = Number(r.srodek_lat)
    const lng = Number(r.srodek_lng)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return
    const kolor = kolorReguly(i)
    L.circle([lat, lng], {
      radius: (Number(r.promien_km) || 0) * 1000,
      color: kolor,
      weight: 2,
      fillColor: kolor,
      fillOpacity: r.aktywna ? 0.12 : 0.03,
      dashArray: r.aktywna ? null : '6 6',
    }).addTo(warstwa)
    L.circleMarker([lat, lng], { radius: 5, color: kolor, fillColor: kolor, fillOpacity: 1 })
      .bindTooltip(`${r.kolejnosc}. ${r.handlowiec_nazwa}`)
      .addTo(warstwa)
  })
  // Punkt sprawdzanego kodu: rysowany w tej samej warstwie, więc nie ginie ani nie dubluje się.
  const punkt = punktKodu(surowyWynik.value)
  if (punkt) {
    L.circleMarker([punkt.lat, punkt.lng], {
      radius: 7,
      color: '#ffffff',
      weight: 2,
      fillColor: '#111827',
      fillOpacity: 1,
    })
      .bindTooltip(punkt.kod)
      .addTo(warstwa)
  }
  const granice = warstwa.getBounds()
  if (granice.isValid()) mapa.fitBounds(granice, { padding: [20, 20], maxZoom: 9 })
}

onMounted(async () => {
  await nextTick()
  inicjujMape()
})
onBeforeUnmount(() => {
  clearTimeout(timerSzukania)
  clearTimeout(timerPodgladu)
  if (mapa) {
    mapa.remove()
    mapa = null
    warstwa = null
  }
})

watch(
  () => dialog.otwarty,
  (otwarty) => {
    if (!otwarty) kandydaci.value = []
  },
)
</script>
