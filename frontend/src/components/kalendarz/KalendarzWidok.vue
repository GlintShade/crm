<!--
  Treść kalendarza spotkań handlowców (ops#318), wspólna dla strony /kalendarz
  (pages/Kalendarz.vue, pasek w LayoutHeader) i widoku "Kalendarz" w Leadach
  (pages/Leads.vue, prop `pasek` = własny pasek nawigacji, bez drugiego
  LayoutHeader). Zakres "wszyscy" (CC, backoffice, administracja): Tablica
  kart handlowców albo Jeden handlowiec (poziomo lub pionowo). Zakres
  "wlasny" (handlowiec): od razu własny kalendarz. O zakresie decyduje
  odpowiedź serwera (crm.api.kalendarz.spotkania), front tylko ukrywa
  kontrolki. Kalendarz nie używa filtrów listy leadów. Daty i pozycje liczy
  utils/kalendarz.js, zero logiki dat tutaj. Grafik dostępności (b82): ciemne
  odcinki na kartach z `dostepnosc` z serwera, przycisk "Grafik" (backoffice,
  widok tygodnia) zamienia kartę w EdycjaGrafiku, "Grafik zespołu" pokazuje
  podgląd całego zespołu.
-->
<template>
  <div>
    <KalendarzPasek
      v-if="pasek"
      class="mb-3"
      czesc="calosc"
      :etykieta="etykieta"
      :widok="stan.widok"
      @update:widok="(v) => (stan.widok = v)"
      @przesun="przesun"
      @dzis="dzis"
      @nowe="otworzModal({})"
    />
    <KalendarzPasek
      v-if="!pasek"
      class="mb-2 sm:hidden"
      czesc="mobilna"
      :etykieta="etykieta"
      :widok="stan.widok"
      @update:widok="(v) => (stan.widok = v)"
    />
    <div v-if="zakres" class="mb-4 flex flex-wrap items-center gap-2">
      <PrzelacznikSegmentowy
        v-if="zakres === 'wszyscy'"
        v-model="stan.tryb"
        :options="OPCJE_TRYBU"
      />
      <PrzelacznikSegmentowy
        v-model="stan.orientacja"
        :options="OPCJE_ORIENTACJI"
      />
      <div
        v-if="zakres === 'wszyscy' && stan.tryb === 'jeden'"
        class="w-52 text-xs"
      >
        <FormControl
          type="select"
          :model-value="wybranyHandlowiec"
          :options="opcjeHandlowcow"
          @update:model-value="(v) => (stan.handlowiec = v)"
        />
      </div>
      <MultiWyborProsty
        v-if="zakres === 'wszyscy' && stan.tryb === 'tablica'"
        v-model="stan.filtr"
        :options="opcjeHandlowcow"
        :pusty="__('Wszyscy handlowcy')"
        class="w-52 text-xs"
      />
      <Button
        v-if="zakres === 'wszyscy' && grafikWlaczony"
        size="sm"
        :variant="zespolOtwarty ? 'subtle' : 'outline'"
        data-testid="kalendarz-zespol"
        @click="zespolOtwarty = !zespolOtwarty"
      >
        <template #prefix
          ><FeatherIcon name="users" class="h-3.5 w-3.5"
        /></template>
        {{ __('Grafik zespołu') }}
      </Button>
    </div>

    <GrafikZespolu
      v-if="zespolOtwarty && zakres === 'wszyscy' && grafikWlaczony"
      class="mb-4"
      :handlowcy="widoczni"
      :dostepnosc="dostepnosc"
      :dni="dni"
      :teraz="teraz"
      :moze-edytowac="mozeEdytowac"
      :indeks-koloru="(u) => indeksKoloru(u)"
      @zamknij="zespolOtwarty = false"
    />

    <ErrorMessage v-if="blad" :message="blad" class="mb-3" />
    <div
      v-if="ladowanie && !zakres"
      class="py-10 text-center text-sm text-ink-gray-5"
    >
      {{ __('Ładowanie...') }}
    </div>

    <template v-else-if="zakres">
      <div
        v-if="!widoczni.length"
        class="py-10 text-center text-sm text-ink-gray-5"
      >
        {{ __('Brak handlowców do wyświetlenia.') }}
      </div>

      <!-- Tablica: siatka kart -->
      <div
        v-else-if="zakres === 'wszyscy' && stan.tryb === 'tablica'"
        class="grid grid-cols-1 items-start gap-4 lg:grid-cols-2"
        data-testid="kalendarz-tablica"
      >
        <template v-for="h in widoczni" :key="h.user">
          <EdycjaGrafiku
            v-if="edytowany === h.user"
            class="lg:col-span-2"
            :handlowiec="h"
            :kolor-index="indeksKoloru(h.user)"
            :dni="dni"
            :dostepnosc="dostepnoscDla(h.user) || null"
            :zmiany="zmianyGrafiku[h.user] || []"
            @anuluj="edytowany = ''"
            @zapisano="poZapisieGrafiku"
          />
          <KartaHandlowca
            v-else-if="stan.orientacja === 'poziomo'"
            :handlowiec="h"
            :kolor-index="indeksKoloru(h.user)"
            :spotkania="spotkania[h.user] || []"
            :dni="dni"
            :teraz="teraz"
            :os-zewnetrzna="osTablicy"
            :dostepnosc="dostepnoscDla(h.user)"
            :edycja="edycjaMozliwa"
            @otworz="otworzLeada"
            @nowe="otworzModal"
            @przesun="przesun"
            @grafik="edytowany = h.user"
          />
          <KalendarzPionowy
            v-else
            :handlowiec="h"
            :kolor-index="indeksKoloru(h.user)"
            :spotkania="spotkania[h.user] || []"
            :dni="dni"
            :teraz="teraz"
            kompakt
            naglowek
            :os-zewnetrzna="osTablicy"
            :dostepnosc="dostepnoscDla(h.user)"
            :edycja="edycjaMozliwa"
            @otworz="otworzLeada"
            @nowe="otworzModal"
            @przesun="przesun"
            @grafik="edytowany = h.user"
          />
        </template>
      </div>

      <!-- Jeden handlowiec / własny -->
      <template v-else>
        <EdycjaGrafiku
          v-if="edytowany === widoczni[0].user"
          :handlowiec="widoczni[0]"
          :kolor-index="indeksKoloru(widoczni[0].user)"
          :dni="dni"
          :dostepnosc="dostepnoscDla(widoczni[0].user) || null"
          :zmiany="zmianyGrafiku[widoczni[0].user] || []"
          @anuluj="edytowany = ''"
          @zapisano="poZapisieGrafiku"
        />
        <KartaHandlowca
          v-else-if="stan.orientacja === 'poziomo'"
          :handlowiec="widoczni[0]"
          :kolor-index="indeksKoloru(widoczni[0].user)"
          :spotkania="spotkania[widoczni[0].user] || []"
          :dni="dni"
          :teraz="teraz"
          duzy
          :dostepnosc="dostepnoscDla(widoczni[0].user)"
          :edycja="edycjaMozliwa && zakres === 'wszyscy'"
          data-testid="kalendarz-jeden-poziomo"
          @otworz="otworzLeada"
          @nowe="otworzModal"
          @przesun="przesun"
          @grafik="edytowany = widoczni[0].user"
        />
        <KalendarzPionowy
          v-else
          :handlowiec="widoczni[0]"
          :kolor-index="indeksKoloru(widoczni[0].user)"
          :spotkania="spotkania[widoczni[0].user] || []"
          :dni="dni"
          :teraz="teraz"
          :dostepnosc="dostepnoscDla(widoczni[0].user)"
          data-testid="kalendarz-jeden-pionowo"
          @otworz="otworzLeada"
          @nowe="otworzModal"
        />
      </template>
    </template>

    <NoweSpotkanieModal
      v-model="modalOtwarty"
      :poczatkowe="modalDane"
      :zakres="zakres || 'wszyscy'"
      :handlowcy="handlowcy"
      :spotkania="spotkania"
      :dostepnosc="dostepnosc"
      @zapisano="wczytaj"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, ErrorMessage, FeatherIcon, FormControl, call } from 'frappe-ui'
import KalendarzPasek from '@/components/kalendarz/KalendarzPasek.vue'
import MultiWyborProsty from '@/components/rozliczenia/MultiWyborProsty.vue'
import KartaHandlowca from '@/components/kalendarz/KartaHandlowca.vue'
import KalendarzPionowy from '@/components/kalendarz/KalendarzPionowy.vue'
import NoweSpotkanieModal from '@/components/kalendarz/NoweSpotkanieModal.vue'
import EdycjaGrafiku from '@/components/kalendarz/EdycjaGrafiku.vue'
import GrafikZespolu from '@/components/kalendarz/GrafikZespolu.vue'
import PrzelacznikSegmentowy from '@/components/kalendarz/PrzelacznikSegmentowy.vue'
import { sessionStore } from '@/stores/session'
import {
  dniTygodnia,
  dzisIso,
  etykietaDnia,
  etykietaZakresu,
  kluczStanu,
  osWspolna,
  przesunKotwice,
  wczytajStan,
  zakresWidoku,
} from '@/utils/kalendarz'

const API = 'crm.api.kalendarz'
const OPCJE_TRYBU = [
  { value: 'tablica', label: __('Tablica') },
  { value: 'jeden', label: __('Jeden handlowiec') },
]
const OPCJE_ORIENTACJI = [
  { value: 'poziomo', label: __('Poziomo') },
  { value: 'pionowo', label: __('Pionowo') },
]

// Pasek nawigacji (strzałki, Dziś, etykieta zakresu, Tydzień/Dzień, Nowe
// spotkanie) rysuje ten komponent tylko z propem `pasek` (widok w Leadach);
// strona /kalendarz trzyma go w swoim LayoutHeader i czyta stan przez expose.
defineProps({
  pasek: { type: Boolean, default: false },
})

const router = useRouter()
const { user } = sessionStore()

function odczytajZPamieci() {
  try {
    return window.localStorage.getItem(kluczStanu(user)) || null
  } catch (e) {
    return null
  }
}

const surowyStan = odczytajZPamieci()
const stan = reactive(wczytajStan(surowyStan, 'wszyscy'))
const kotwica = ref(dzisIso())
const teraz = ref(new Date())
const zakres = ref('')
const handlowcy = ref([])
const spotkania = ref({})
const ladowanie = ref(false)
const blad = ref('')
const modalOtwarty = ref(false)
const modalDane = ref({})
// Grafik dostępności (b82): null = doctype jeszcze nie istnieje na serwerze.
const dostepnosc = ref(null)
const zmianyGrafiku = ref({})
const mozeEdytowac = ref(false)
const edytowany = ref('')
const zespolOtwarty = ref(false)
let numerZapytania = 0
let zegar = null

const okres = computed(() => zakresWidoku(kotwica.value, stan.widok))
const dni = computed(() =>
  stan.widok === 'dzien' ? [kotwica.value] : dniTygodnia(okres.value.od),
)
const etykieta = computed(() =>
  stan.widok === 'dzien'
    ? etykietaDnia(kotwica.value)
    : etykietaZakresu(okres.value.od, okres.value.do),
)

const opcjeHandlowcow = computed(() =>
  handlowcy.value.map((h) => ({ value: h.user, label: h.full_name })),
)
const wybranyHandlowiec = computed(() => {
  const jest = handlowcy.value.some((h) => h.user === stan.handlowiec)
  return jest ? stan.handlowiec : handlowcy.value[0]?.user || ''
})
const widoczni = computed(() => {
  if (zakres.value === 'wlasny') return handlowcy.value.slice(0, 1)
  if (stan.tryb === 'jeden')
    return handlowcy.value.filter((h) => h.user === wybranyHandlowiec.value)
  if (!stan.filtr.length) return handlowcy.value
  return handlowcy.value.filter((h) => stan.filtr.includes(h.user))
})

// Wspólna oś godzin kart tablicy (spotkania wszystkich widocznych handlowców),
// żeby karty obok siebie miały te same kolumny godzin.
const osTablicy = computed(() =>
  osWspolna(
    spotkania.value,
    widoczni.value.map((h) => h.user),
  ),
)

const grafikWlaczony = computed(() => dostepnosc.value !== null)
// Edycja grafiku tylko w widoku tygodnia (zapis dotyczy całego tygodnia).
const edycjaMozliwa = computed(
  () => mozeEdytowac.value && grafikWlaczony.value && stan.widok === 'tydzien',
)

/** Mapa dostępności handlowca; undefined, gdy grafik wyłączony. */
function dostepnoscDla(userName) {
  if (!grafikWlaczony.value) return undefined
  return dostepnosc.value[userName] ?? null
}

function poZapisieGrafiku() {
  edytowany.value = ''
  wczytaj()
}

function indeksKoloru(userName) {
  return Math.max(
    0,
    handlowcy.value.findIndex((h) => h.user === userName),
  )
}

async function wczytaj() {
  const numer = ++numerZapytania
  ladowanie.value = true
  blad.value = ''
  try {
    const odp = await call(`${API}.spotkania`, {
      od: okres.value.od,
      do: okres.value.do,
    })
    if (numer !== numerZapytania) return
    const pierwszy = !zakres.value
    zakres.value = odp.zakres
    handlowcy.value = odp.handlowcy || []
    spotkania.value = odp.spotkania || {}
    dostepnosc.value = odp.dostepnosc ?? null
    zmianyGrafiku.value = odp.zmiany_grafiku || {}
    mozeEdytowac.value = !!odp.moze_edytowac_grafik
    if (pierwszy && odp.zakres === 'wlasny' && !surowyStan)
      stan.orientacja = 'pionowo'
  } catch (e) {
    if (numer !== numerZapytania) return
    blad.value =
      e?.messages?.[0] || e?.message || __('Nie udało się wczytać kalendarza.')
  } finally {
    if (numer === numerZapytania) ladowanie.value = false
  }
}

function przesun(kierunek) {
  kotwica.value = przesunKotwice(kotwica.value, stan.widok, kierunek)
}

function dzis() {
  kotwica.value = dzisIso()
}

function otworzLeada(leadId) {
  router.push({ name: 'Lead', params: { leadId } })
}

function otworzModal(dane) {
  modalDane.value = {
    data: dane.data || (stan.widok === 'dzien' ? kotwica.value : dzisIso()),
    godzina: dane.godzina || '10:00',
    handlowiec:
      dane.handlowiec ||
      (zakres.value === 'wszyscy' && stan.tryb === 'jeden'
        ? wybranyHandlowiec.value
        : ''),
  }
  modalOtwarty.value = true
}

watch([() => okres.value.od, () => okres.value.do], () => {
  // Edytor dotyczy jednego tygodnia; zmiana tygodnia albo widoku go zamyka.
  edytowany.value = ''
  wczytaj()
})

watch(
  stan,
  (nowy) => {
    try {
      window.localStorage.setItem(kluczStanu(user), JSON.stringify(nowy))
    } catch (e) {
      // Pamięć przeglądarki bywa niedostępna (tryb prywatny); widok działa bez niej.
    }
  },
  { deep: true },
)

onMounted(() => {
  wczytaj()
  zegar = window.setInterval(() => (teraz.value = new Date()), 60000)
})

onBeforeUnmount(() => {
  if (zegar) window.clearInterval(zegar)
})

defineExpose({ stan, etykieta, przesun, dzis, otworzModal })
</script>
