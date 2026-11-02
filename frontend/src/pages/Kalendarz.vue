<!--
  Kalendarz spotkań handlowców (ops#318). Zakres "wszyscy" (CC, backoffice,
  administracja): Tablica kart handlowców albo Jeden handlowiec (poziomo lub
  pionowo). Zakres "wlasny" (handlowiec): od razu własny kalendarz. O zakresie
  decyduje odpowiedź serwera (crm.api.kalendarz.spotkania), front tylko ukrywa
  kontrolki. Daty i pozycje liczy utils/kalendarz.js, zero logiki dat tutaj.
-->
<template>
  <div class="flex h-full flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <span class="text-lg font-semibold text-ink-gray-9">{{
            __('Kalendarz')
          }}</span>
          <div class="flex items-center">
            <Button
              variant="ghost"
              :tooltip="__('Poprzedni')"
              @click="przesun(-1)"
            >
              <template #icon
                ><FeatherIcon name="chevron-left" class="h-4 w-4"
              /></template>
            </Button>
            <Button variant="ghost" :label="__('Dziś')" @click="dzis" />
            <Button
              variant="ghost"
              :tooltip="__('Następny')"
              @click="przesun(1)"
            >
              <template #icon
                ><FeatherIcon name="chevron-right" class="h-4 w-4"
              /></template>
            </Button>
          </div>
          <span
            class="hidden text-sm text-ink-gray-7 sm:inline"
            data-testid="kalendarz-etykieta"
            >{{ etykieta }}</span
          >
        </div>
      </template>
      <template #right-header>
        <div class="flex items-center gap-2">
          <PrzelacznikSegmentowy
            v-model="stan.widok"
            :options="OPCJE_WIDOKU"
            class="hidden sm:flex"
          />
          <Button
            variant="solid"
            :title="__('Nowe spotkanie')"
            @click="otworzModal({})"
          >
            <template #prefix
              ><FeatherIcon name="plus" class="h-4 w-4"
            /></template>
            <span class="hidden sm:inline">{{ __('Nowe spotkanie') }}</span>
          </Button>
        </div>
      </template>
    </LayoutHeader>

    <div class="flex-1 overflow-y-auto p-4">
      <div class="mb-2 flex items-center justify-between gap-2 sm:hidden">
        <span class="text-sm text-ink-gray-7">{{ etykieta }}</span>
        <PrzelacznikSegmentowy v-model="stan.widok" :options="OPCJE_WIDOKU" />
      </div>
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
      </div>

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
            <KartaHandlowca
              v-if="stan.orientacja === 'poziomo'"
              :handlowiec="h"
              :kolor-index="indeksKoloru(h.user)"
              :spotkania="spotkania[h.user] || []"
              :dni="dni"
              :teraz="teraz"
              :os-zewnetrzna="osTablicy"
              @otworz="otworzLeada"
              @nowe="otworzModal"
              @przesun="przesun"
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
              @otworz="otworzLeada"
              @nowe="otworzModal"
              @przesun="przesun"
            />
          </template>
        </div>

        <!-- Jeden handlowiec / własny -->
        <template v-else>
          <KartaHandlowca
            v-if="stan.orientacja === 'poziomo'"
            :handlowiec="widoczni[0]"
            :kolor-index="indeksKoloru(widoczni[0].user)"
            :spotkania="spotkania[widoczni[0].user] || []"
            :dni="dni"
            :teraz="teraz"
            duzy
            data-testid="kalendarz-jeden-poziomo"
            @otworz="otworzLeada"
            @nowe="otworzModal"
            @przesun="przesun"
          />
          <KalendarzPionowy
            v-else
            :handlowiec="widoczni[0]"
            :kolor-index="indeksKoloru(widoczni[0].user)"
            :spotkania="spotkania[widoczni[0].user] || []"
            :dni="dni"
            :teraz="teraz"
            data-testid="kalendarz-jeden-pionowo"
            @otworz="otworzLeada"
            @nowe="otworzModal"
          />
        </template>
      </template>
    </div>

    <NoweSpotkanieModal
      v-model="modalOtwarty"
      :poczatkowe="modalDane"
      :zakres="zakres || 'wszyscy'"
      :handlowcy="handlowcy"
      :spotkania="spotkania"
      @zapisano="wczytaj"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  Button,
  ErrorMessage,
  FeatherIcon,
  FormControl,
  call,
  usePageMeta,
} from 'frappe-ui'
import LayoutHeader from '@/components/LayoutHeader.vue'
import MultiWyborProsty from '@/components/rozliczenia/MultiWyborProsty.vue'
import KartaHandlowca from '@/components/kalendarz/KartaHandlowca.vue'
import KalendarzPionowy from '@/components/kalendarz/KalendarzPionowy.vue'
import NoweSpotkanieModal from '@/components/kalendarz/NoweSpotkanieModal.vue'
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

usePageMeta(() => ({ title: __('Kalendarz') }))

const API = 'crm.api.kalendarz'
const OPCJE_WIDOKU = [
  { value: 'tydzien', label: __('Tydzień') },
  { value: 'dzien', label: __('Dzień') },
]
const OPCJE_TRYBU = [
  { value: 'tablica', label: __('Tablica') },
  { value: 'jeden', label: __('Jeden handlowiec') },
]
const OPCJE_ORIENTACJI = [
  { value: 'poziomo', label: __('Poziomo') },
  { value: 'pionowo', label: __('Pionowo') },
]

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

watch([() => okres.value.od, () => okres.value.do], wczytaj)

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
</script>
