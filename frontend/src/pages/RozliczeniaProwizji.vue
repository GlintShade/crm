<!--
  Rozliczenia prowizji (ops#283): rejestr wszystkich wierszy `Volteo Rozliczenie`,
  grupowany per osoba lub per szansa, z wyborem okresu, filtrami i akcjami
  masowymi. TYLKO dla administracji (isVolteoAdmin); trase pilnuje router.js,
  prawdziwe uprawnienia egzekwuje serwer (crm.api.rozliczenia).
-->
<template>
  <div class="flex h-full flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <span class="text-lg font-semibold text-ink-gray-9">{{ __('Rozliczenia prowizji') }}</span>
          <span
            class="inline-flex items-center gap-1 rounded-full border border-outline-amber-3 bg-surface-amber-2 px-2 py-0.5 text-xs text-ink-amber-8"
          >
            <FeatherIcon name="lock" class="h-3 w-3" />
            {{ __('Tylko admin i core admin') }}
          </span>
        </div>
      </template>
      <template #right-header>
        <div class="flex items-center gap-2">
          <div class="flex rounded border border-outline-gray-2 p-0.5 text-sm">
            <button
              v-for="g in GRUPOWANIA"
              :key="g.klucz"
              type="button"
              class="rounded px-3 py-0.5"
              :class="
                grupowanie === g.klucz
                  ? 'bg-surface-gray-3 text-ink-gray-9'
                  : 'text-ink-gray-6 hover:bg-surface-gray-2'
              "
              @click="grupowanie = g.klucz"
            >
              {{ __(g.etykieta) }}
            </button>
          </div>
          <Button :label="__('Eksport CSV')" :loading="eksportuje" @click="eksportuj">
            <template #prefix><FeatherIcon name="download" class="h-4 w-4" /></template>
          </Button>
        </div>
      </template>
    </LayoutHeader>

    <div class="flex-1 overflow-y-auto p-5 pb-24">
      <!-- Filtry -->
      <div class="flex flex-wrap items-end gap-3">
        <div class="w-52">
          <label class="mb-1 block text-xs text-ink-gray-5">{{ __('Osoba') }}</label>
          <Link
            doctype="User"
            :model-value="filtry.osoba"
            :placeholder="__('Szukaj osoby')"
            @update:model-value="(v) => (filtry = { ...filtry, osoba: v || '' })"
          />
        </div>
        <div class="w-40">
          <label class="mb-1 block text-xs text-ink-gray-5">{{ __('Rola') }}</label>
          <select
            class="h-8 w-full rounded border border-outline-gray-2 bg-surface-base px-2 py-0 text-sm leading-normal text-ink-gray-8"
            :value="filtry.rola"
            @change="filtry = { ...filtry, rola: $event.target.value }"
          >
            <option value="">{{ __('Wszystkie') }}</option>
            <option v-for="r in ROLE" :key="r" :value="r">{{ __(r) }}</option>
          </select>
        </div>
        <MultiWyborProsty
          v-model="filtry.status"
          :label="__('Status')"
          :options="OPCJE_STATUSU"
          :pusty="__('Wszystkie')"
        />
        <MultiWyborProsty
          v-model="filtry.rodzaj_umowy"
          :label="__('Rodzaj umowy')"
          :options="OPCJE_RODZAJU"
          :pusty="__('Wszystkie')"
        />
        <OkresPicker v-model="wybor" />
      </div>
      <div v-if="filtry.szansa" class="mt-3 flex items-center gap-2 text-sm">
        <span class="inline-flex items-center gap-1.5 rounded-full border border-outline-blue-2 bg-surface-blue-2 px-3 py-1 text-ink-blue-8">
          {{ __('Szansa') }}: {{ filtry.szansa }}
          <button type="button" @click="wyczyscSzanse"><FeatherIcon name="x" class="h-3.5 w-3.5" /></button>
        </span>
      </div>

      <ErrorMessage class="mt-3" :message="blad" />

      <!-- Kafelki -->
      <div class="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div v-for="k in kafelkiWidok" :key="k.etykieta" class="rounded-lg border border-outline-gray-2 p-3">
          <div class="text-xs text-ink-gray-5">{{ k.etykieta }}</div>
          <div class="mt-1 text-xl font-semibold text-ink-gray-9">{{ k.wartosc }}</div>
        </div>
      </div>

      <div class="mt-3 flex items-center gap-2 rounded-lg bg-surface-gray-2 px-3 py-2 text-sm text-ink-gray-6">
        <FeatherIcon name="info" class="h-4 w-4 shrink-0" />
        {{
          __(
            'Te same dane co w zakładce Rozliczenia każdej szansy. Oznaczenie tutaj jest od razu widoczne na szansie, i odwrotnie.',
          )
        }}
      </div>

      <div v-if="ladowanie && !grupy.length" class="py-10 text-center text-sm text-ink-gray-5">
        {{ __('Wczytywanie…') }}
      </div>
      <div v-else-if="!grupy.length" class="py-10 text-center text-sm text-ink-gray-5">
        {{ __('Brak pozycji dla wybranych filtrów i okresu.') }}
      </div>

      <!-- Grupy -->
      <div class="mt-4 flex flex-col gap-4">
        <section v-for="g in grupy" :key="g.klucz" class="overflow-hidden rounded-lg border border-outline-gray-2">
          <div class="flex flex-wrap items-center gap-3 bg-surface-gray-1 px-3 py-2">
            <input
              type="checkbox"
              class="rounded border-outline-gray-3"
              :checked="grupaZaznaczona(g)"
              :disabled="!wierszeWybieralne(g).length"
              @change="przelaczGrupe(g, $event.target.checked)"
            />
            <span
              v-if="grupowanie === 'osoba'"
              class="flex h-8 w-8 items-center justify-center rounded-full bg-surface-gray-3 text-xs font-medium text-ink-gray-7"
            >
              {{ inicjaly(g.etykieta) }}
            </span>
            <div class="min-w-0">
              <div class="truncate font-medium text-ink-gray-9">{{ g.etykieta }}</div>
              <div class="truncate text-xs text-ink-gray-5">{{ g.podtytul }}</div>
            </div>
            <div class="ml-auto text-sm text-ink-gray-6">
              {{ __('Do wypłaty') }}: <b class="text-ink-gray-9">{{ zl(g.suma_do_wyplaty) }}</b>
              {{ __('w') }} {{ g.liczba_szans }} {{ odmianaSzans(g.liczba_szans) }}
            </div>
            <Button
              size="sm"
              :label="__('Oznacz grupę jako wypłaconą')"
              :disabled="!wierszeDoWyplaty(g).length"
              @click="otworzGrupowo(g)"
            />
          </div>
          <table class="w-full table-fixed text-sm">
            <thead>
              <tr class="border-b border-outline-gray-2 text-left text-xs text-ink-gray-5">
                <th class="w-9 px-3 py-1.5"></th>
                <th class="w-44 py-1.5">{{ __(grupowanie === 'osoba' ? 'Szansa' : 'Odbiorca') }}</th>
                <th class="py-1.5">{{ __('Klient') }}</th>
                <th class="w-36 py-1.5">{{ __('Rodzaj') }}</th>
                <th class="w-40 py-1.5">{{ __('Etap procesu') }}</th>
                <th class="w-28 py-1.5 text-right">{{ __('Kwota') }}</th>
                <th class="w-28 py-1.5 pl-4">{{ __('Status') }}</th>
                <th class="w-28 py-1.5">{{ __('Data wypłaty') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="w in g.wiersze"
                :key="w.nazwa"
                class="border-b border-outline-gray-1 last:border-0"
                :class="w.status === 'Wypłacone' ? 'text-ink-gray-4' : 'text-ink-gray-8'"
              >
                <td class="px-3 py-1.5">
                  <input
                    type="checkbox"
                    class="rounded border-outline-gray-3"
                    :checked="zaznaczone.has(w.nazwa)"
                    :disabled="!czyWybieralny(w)"
                    @change="przelaczWiersz(w.nazwa, $event.target.checked)"
                  />
                </td>
                <td class="py-1.5">
                  <template v-if="grupowanie === 'osoba'">
                    <router-link
                      :to="{ name: 'Deal', params: { dealId: w.deal } }"
                      class="inline-flex items-center gap-1 text-ink-blue-3 hover:underline"
                      :title="__('Otwiera zakładkę Rozliczenia tej szansy')"
                    >
                      {{ w.deal }}
                      <FeatherIcon name="external-link" class="h-3 w-3" />
                    </router-link>
                  </template>
                  <template v-else>
                    {{ w.odbiorca_nazwa || '' }}
                    <span class="text-xs text-ink-gray-5">({{ w.rola }})</span>
                  </template>
                </td>
                <td class="truncate py-1.5">{{ w.klient }}</td>
                <td class="truncate py-1.5">{{ w.rodzaj }}</td>
                <td class="truncate py-1.5">{{ w.etap }}</td>
                <td class="py-1.5 text-right tabular-nums">{{ zl(w.kwota) }}</td>
                <td class="py-1.5 pl-4">
                  <Badge :label="w.status" :theme="motywStatusu(w.status)" variant="subtle" />
                </td>
                <td class="py-1.5">{{ w.data_wyplaty || '' }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
    </div>

    <!-- Plywajacy pasek akcji -->
    <div
      v-if="zaznaczone.size"
      class="fixed bottom-4 left-1/2 z-30 flex -translate-x-1/2 items-center gap-3 rounded-lg border border-outline-gray-2 bg-surface-base px-4 py-2 shadow-xl"
      data-testid="pasek-masowy"
    >
      <b class="text-sm text-ink-gray-9">
        {{ __('Zaznaczono') }} {{ zaznaczone.size }} {{ odmianaPozycji(zaznaczone.size) }},
        {{ zl(sumaZaznaczonych) }}
      </b>
      <Button :label="__('Wyczyść')" @click="zaznaczone = new Set()" />
      <Button variant="solid" :label="__('Oznacz jako wypłacone')" @click="otworzDialog([...zaznaczone])" />
    </div>

    <!-- Okno masowe -->
    <Dialog v-model:open="pokazDialog" :title="tytulDialogu" size="md">
      <template #default>
        <div class="flex flex-col gap-4">
          <FormControl v-model="dataWyplaty" type="date" :label="__('Data wypłaty')" />
          <FormControl
            v-model="uwaga"
            type="textarea"
            :label="__('Uwaga')"
            :placeholder="__('Np. przelew zbiorczy za wrzesień')"
          />
          <label class="flex items-center gap-2 text-sm text-ink-gray-7">
            <input type="checkbox" checked disabled class="rounded border-outline-gray-3" />
            {{ __('Dodaj wpis do Aktywności każdej szansy') }}
          </label>
          <ErrorMessage :message="bladDialogu" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button :label="__('Anuluj')" @click="pokazDialog = false" />
          <Button variant="solid" :label="__('Zapisz')" :loading="zapisuje" @click="zapisz" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Badge, Button, Dialog, ErrorMessage, FeatherIcon, FormControl, call, toast, usePageMeta } from 'frappe-ui'
import LayoutHeader from '@/components/LayoutHeader.vue'
import OkresPicker from '@/components/OkresPicker.vue'
import MultiWyborProsty from '@/components/rozliczenia/MultiWyborProsty.vue'
import Link from '@/components/Controls/Link.vue'
import { KODY_RODZAJU_UMOWY } from '@/utils/rodzajUmowy'
import { formatujDate, odczytajWybor, okresDlaApi, zapiszWybor } from '@/utils/okres'

usePageMeta(() => ({ title: __('Rozliczenia prowizji') }))

const API = 'crm.api.rozliczenia'
const GRUPOWANIA = [
  { klucz: 'osoba', etykieta: 'Per osoba' },
  { klucz: 'szansa', etykieta: 'Per szansa' },
]
const ROLE = ['Handlowiec', 'Manager', 'Partner']
const STATUSY = ['Do wypłaty', 'Wypłacone', 'Wstrzymane', 'Nie dotyczy']
const OPCJE_STATUSU = STATUSY.map((s) => ({ value: s, label: __(s) }))
const OPCJE_RODZAJU = Object.keys(KODY_RODZAJU_UMOWY).map((r) => ({ value: r, label: r }))

const route = useRoute()
const router = useRouter()

// Kształt deklarowany z góry (reaktywność, bez hasOwnProperty).
const filtry = ref({ osoba: '', rola: '', status: ['Do wypłaty'], rodzaj_umowy: [], szansa: '' })
const wybor = ref(odczytajWybor())
const grupowanie = ref('osoba')
const grupy = ref([])
const kafelki = ref({
  do_wyplaty_w_okresie: '0.00',
  wyplacono_w_okresie: '0.00',
  szans_z_otwartym: 0,
  odbiorcow_do_rozliczenia: 0,
})
const ladowanie = ref(false)
const blad = ref('')
const eksportuje = ref(false)
const zaznaczone = ref(new Set())

const pokazDialog = ref(false)
const dialogNazwy = ref([])
const dataWyplaty = ref(formatujDate(new Date()))
const uwaga = ref('')
const bladDialogu = ref('')
const zapisuje = ref(false)

const okresApi = computed(() => okresDlaApi(wybor.value))

function filtryApi() {
  const f = filtry.value
  const wynik = {}
  if (f.osoba) wynik.osoba = f.osoba
  if (f.rola) wynik.rola = f.rola
  if (f.status.length) wynik.status = f.status
  if (f.rodzaj_umowy.length) wynik.rodzaj_umowy = f.rodzaj_umowy
  if (f.szansa) wynik.szansa = f.szansa
  return wynik
}

let numerZapytania = 0
async function wczytaj() {
  if (!okresApi.value) return
  const moj = ++numerZapytania
  ladowanie.value = true
  blad.value = ''
  try {
    const odp = await call(`${API}.rejestr`, {
      filtry: filtryApi(),
      grupowanie: grupowanie.value,
      okres: okresApi.value,
    })
    if (moj !== numerZapytania) return
    // Serwer (ops#281) nie filtruje po `szansa`; zawężamy po stronie klienta,
    // żeby wejście z zakładki szansy pokazywało tylko tę szansę.
    const szansa = filtry.value.szansa
    grupy.value = (odp.grupy || [])
      .map((g) => (szansa ? { ...g, wiersze: g.wiersze.filter((w) => w.deal === szansa) } : g))
      .filter((g) => g.wiersze.length)
    kafelki.value = odp.kafelki
    const istniejace = new Set(grupy.value.flatMap((g) => g.wiersze.map((w) => w.nazwa)))
    zaznaczone.value = new Set([...zaznaczone.value].filter((n) => istniejace.has(n)))
  } catch (e) {
    if (moj !== numerZapytania) return
    blad.value = e?.messages?.[0] || e?.message || __('Nie udało się wczytać rejestru.')
  } finally {
    if (moj === numerZapytania) ladowanie.value = false
  }
}

watch([filtry, wybor, grupowanie], () => wczytaj(), { deep: true })
watch(wybor, (w) => zapiszWybor(w), { deep: true })

onMounted(() => {
  const s = route.query.szansa
  if (typeof s === 'string' && s) {
    filtry.value = { ...filtry.value, szansa: s, status: [] }
    grupowanie.value = 'szansa'
  } else {
    wczytaj()
  }
})

function wyczyscSzanse() {
  filtry.value = { ...filtry.value, szansa: '' }
  if (route.query.szansa) router.replace({ query: {} })
}

const kafelkiWidok = computed(() => [
  { etykieta: __('Do wypłaty w okresie'), wartosc: zl(kafelki.value.do_wyplaty_w_okresie) },
  { etykieta: __('Wypłacono w okresie'), wartosc: zl(kafelki.value.wyplacono_w_okresie) },
  { etykieta: __('Szans z otwartym rozliczeniem'), wartosc: String(kafelki.value.szans_z_otwartym) },
  { etykieta: __('Odbiorców do rozliczenia'), wartosc: String(kafelki.value.odbiorcow_do_rozliczenia) },
])

// --- formatowanie --------------------------------------------------------------
const formatKwoty = new Intl.NumberFormat('pl-PL', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
function zl(v) {
  const n = Number(v ?? 0)
  return `${formatKwoty.format(Number.isFinite(n) ? n : 0)} zł`
}
function inicjaly(nazwa) {
  const lit = String(nazwa || '')
    .split(/\s+/)
    .map((s) => s[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
  return lit.toUpperCase() || 'XX'
}
function odmianaSzans(n) {
  if (n === 1) return __('szansie')
  return __('szansach')
}
function odmianaPozycji(n) {
  if (n === 1) return __('pozycję')
  if (n % 10 >= 2 && n % 10 <= 4 && !(n % 100 >= 12 && n % 100 <= 14)) return __('pozycje')
  return __('pozycji')
}
function motywStatusu(status) {
  return (
    { 'Do wypłaty': 'blue', Wypłacone: 'green', Wstrzymane: 'orange', 'Nie dotyczy': 'gray' }[status] || 'gray'
  )
}

// --- zaznaczanie ---------------------------------------------------------------
const wszystkieWiersze = computed(() => new Map(grupy.value.flatMap((g) => g.wiersze).map((w) => [w.nazwa, w])))
const sumaZaznaczonych = computed(() =>
  [...zaznaczone.value].reduce((s, n) => s + Number(wszystkieWiersze.value.get(n)?.kwota || 0), 0),
)
const czyWybieralny = (w) => w.status !== 'Wypłacone' && w.status !== 'Nie dotyczy'
const wierszeWybieralne = (g) => g.wiersze.filter(czyWybieralny)
const wierszeDoWyplaty = (g) => g.wiersze.filter((w) => w.status === 'Do wypłaty')
function grupaZaznaczona(g) {
  const w = wierszeWybieralne(g)
  return w.length > 0 && w.every((x) => zaznaczone.value.has(x.nazwa))
}
function przelaczWiersz(nazwa, on) {
  const nowy = new Set(zaznaczone.value)
  if (on) nowy.add(nazwa)
  else nowy.delete(nazwa)
  zaznaczone.value = nowy
}
function przelaczGrupe(g, on) {
  const nowy = new Set(zaznaczone.value)
  for (const w of wierszeWybieralne(g)) {
    if (on) nowy.add(w.nazwa)
    else nowy.delete(w.nazwa)
  }
  zaznaczone.value = nowy
}

// --- okno masowe ---------------------------------------------------------------
const tytulDialogu = computed(() => {
  const n = dialogNazwy.value.length
  const suma = dialogNazwy.value.reduce((s, x) => s + Number(wszystkieWiersze.value.get(x)?.kwota || 0), 0)
  return `${__('Oznacz jako wypłacone')} (${n} ${odmianaPozycji(n)}, ${zl(suma)})`
})
function otworzDialog(nazwy) {
  dialogNazwy.value = nazwy
  dataWyplaty.value = formatujDate(new Date())
  uwaga.value = ''
  bladDialogu.value = ''
  pokazDialog.value = true
}
function otworzGrupowo(g) {
  otworzDialog(wierszeDoWyplaty(g).map((w) => w.nazwa))
}
async function zapisz() {
  if (!dataWyplaty.value) {
    bladDialogu.value = __('Podaj datę wypłaty.')
    return
  }
  zapisuje.value = true
  bladDialogu.value = ''
  try {
    const odp = await call(`${API}.oznacz_wyplacone`, {
      nazwy: dialogNazwy.value,
      data_wyplaty: dataWyplaty.value,
      uwaga: uwaga.value,
    })
    pokazDialog.value = false
    zaznaczone.value = new Set()
    toast.success(`${__('Oznaczono jako wypłacone')}: ${odp?.oznaczono ?? 0}`)
    await wczytaj()
  } catch (e) {
    bladDialogu.value = e?.messages?.[0] || e?.message || __('Nie udało się zapisać.')
  } finally {
    zapisuje.value = false
  }
}

// --- eksport CSV ---------------------------------------------------------------
async function eksportuj() {
  if (!okresApi.value) return
  eksportuje.value = true
  try {
    const tresc = await call(`${API}.eksport_csv`, { filtry: filtryApi(), okres: okresApi.value })
    const blob = new Blob([tresc], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `rozliczenia-prowizji-${okresApi.value.od}-${okresApi.value.do}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Nie udało się wyeksportować.'))
  } finally {
    eksportuje.value = false
  }
}
</script>
