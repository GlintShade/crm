<!--
  Siatka tygodnia (kalendarz spotkań, ops#318): kolumny dni, wiersze godzin,
  bloki spotkań. Dla jednego handlowca. Nagłówek dni (32 px) leży POZA
  kontenerem skali godzin: pierwsza linia 08:00 zaczyna się tuż pod nim, a
  etykieta każdej godziny jest wyśrodkowana na swojej linii (top: Ypx,
  translateY(-50%)), razem z ostatnią. Bloki mają ten sam układ współrzędnych.
  Prop `kompakt` = mniejsza skala (karta w tablicy), `naglowek` = karta z
  nagłówkiem handlowca (NaglowekKarty).
-->
<template>
  <div
    ref="korzen"
    class="rounded-xl border border-outline-gray-2 bg-surface-base p-3.5"
    :class="kompakt ? '' : 'overflow-x-auto'"
  >
    <NaglowekKarty
      v-if="naglowek"
      ref="naglowekKarty"
      class="mb-3"
      :handlowiec="handlowiec"
      :kolor="kolor"
      :etykieta-zakresu="etykietaZakresu"
      :chip="chip"
      @przesun="(k) => $emit('przesun', k)"
    />
    <div :class="kompakt ? '' : 'min-w-[640px]'">
      <!-- Nagłówek dni: osobny wiersz, nie jest częścią skali godzin -->
      <div
        class="flex items-stretch"
        :style="{ height: WYSOKOSC_NAGLOWKA_DNI_PX + 'px' }"
      >
        <div class="shrink-0" :class="kolumnaGodzin"></div>
        <div
          v-for="dzien in dni"
          :key="dzien"
          class="flex min-w-0 flex-1 items-center justify-center truncate whitespace-nowrap text-center"
          :class="[
            'text-xs',
            czyDzis(dzien, teraz)
              ? 'font-semibold text-ink-blue-8'
              : czyWeekend(dzien)
                ? 'text-ink-gray-4'
                : 'text-ink-gray-7',
          ]"
        >
          <span class="min-w-0 truncate">{{
            kompakt ? etykietaDniaKrotka(dzien) : etykietaDniaZMiesiacem(dzien)
          }}</span>
        </div>
      </div>

      <!-- Skala godzin: kontener relative, współrzędne w px od pierwszej linii -->
      <div class="flex pb-2">
        <div
          class="relative shrink-0"
          :class="kolumnaGodzin"
          :style="{ height: wysokosc + 'px' }"
        >
          <span
            v-for="g in etykietyGodzin"
            :key="g"
            class="absolute right-2 text-xs tabular-nums text-ink-gray-5"
            :style="{
              top: (g - os.od) * pxNaH + 'px',
              transform: 'translateY(-50%)',
            }"
          >
            {{ String(g).padStart(2, '0') }}:00
          </span>
        </div>
        <div
          v-for="dzien in dni"
          :key="dzien"
          class="relative min-w-0 flex-1 cursor-pointer border-l border-outline-gray-1"
          :class="[
            czyWeekend(dzien) ? 'bg-surface-gray-1' : '',
            czyDzis(dzien, teraz) ? 'bg-surface-blue-1' : '',
          ]"
          :style="{ height: wysokosc + 'px' }"
          :data-dzien="dzien"
          @click="klikPuste($event, dzien)"
        >
          <span
            v-for="g in godziny"
            :key="g"
            class="pointer-events-none absolute left-0 right-0 border-t border-outline-gray-2"
            :style="{ top: (g - os.od) * pxNaH + 'px' }"
          ></span>
          <DymekSpotkania
            v-for="s in poDniach[dzien] || []"
            :key="s.name"
            :spotkanie="s"
          >
            <button
              type="button"
              class="absolute z-[2] overflow-hidden rounded-md text-left text-xs leading-[1.15] text-white"
              :class="[
                kompakt
                  ? 'left-0.5 right-0.5 px-1 py-px'
                  : 'left-1 right-1 px-1.5 py-0.5',
                kolor.pelny,
                czyUmowiony(s.status) ? '' : 'opacity-[0.7]',
              ]"
              :style="stylBloku(s)"
              :data-lead="s.name"
              @click.stop="$emit('otworz', s.name)"
            >
              <template v-if="jednaLinia">
                <span class="block truncate font-semibold">{{
                  godzinaTekst(s.termin) + ' ' + nazwisko(s.lead_name)
                }}</span>
              </template>
              <template v-else>
                <span class="block truncate font-semibold">{{
                  kompakt
                    ? godzinaTekst(s.termin)
                    : godzinaTekst(s.termin) + ' ' + s.lead_name
                }}</span>
                <span class="block truncate">{{
                  kompakt ? nazwisko(s.lead_name) : s.miasto
                }}</span>
              </template>
            </button>
          </DymekSpotkania>
          <span
            v-if="znacznikTeraz(dzien) !== null"
            class="pointer-events-none absolute left-0 right-0 z-[3] h-0.5 bg-surface-red-5"
            :style="{ top: znacznikTeraz(dzien) + 'px' }"
            data-testid="kalendarz-teraz"
          >
            <span
              class="absolute -left-1 -top-[3px] h-2 w-2 rounded-full bg-surface-red-5"
            ></span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import NaglowekKarty from '@/components/kalendarz/NaglowekKarty.vue'
import DymekSpotkania from '@/components/kalendarz/DymekSpotkania.vue'
import {
  WYSOKOSC_NAGLOWKA_DNI_PX,
  czyDzis,
  czyUmowiony,
  czyWeekend,
  etykietaChipa,
  etykietaDniaKrotka,
  etykietaDniaZMiesiacem,
  etykietaZakresu as zbudujEtykieteZakresu,
  godzinaTekst,
  godzinaZKliknieciaPion,
  czyJednaLinia,
  godzinyEtykietPion,
  godzinyOsi,
  pxNaGodzineZSzerokosci,
  kolorHandlowca,
  nazwisko,
  osGodzin,
  pogrupujPoDniach,
  pozycjaBlokuPx,
  pozycjaTeraz,
  skalaPionowa,
  wysokoscSiatkiPion,
} from '@/utils/kalendarz'

const props = defineProps({
  handlowiec: { type: Object, required: true },
  kolorIndex: { type: Number, default: 0 },
  spotkania: { type: Array, default: () => [] },
  dni: { type: Array, required: true },
  teraz: { type: Date, default: () => new Date() },
  kompakt: { type: Boolean, default: false },
  naglowek: { type: Boolean, default: false },
  // Wspólna oś godzin tablicy ({ od, do }); bez niej oś liczona z własnych spotkań.
  osZewnetrzna: { type: Object, default: null },
})

const emit = defineEmits(['otworz', 'nowe', 'przesun'])

const kolor = computed(() => kolorHandlowca(props.kolorIndex))
const os = computed(() => props.osZewnetrzna || osGodzin(props.spotkania))
const godziny = computed(() => godzinyOsi(os.value.od, os.value.do))
// Skala px/h z SZEROKOŚCI karty (proporcje ok. 16:9): ResizeObserver mierzy
// szerokość i wysokość nagłówka karty; przed pierwszym pomiarem skala stała.
const korzen = ref(null)
const naglowekKarty = ref(null)
const szerokosc = ref(0)
const wysokoscNaglowka = ref(0)
let obserwator = null

function zmierz() {
  if (!korzen.value) return
  szerokosc.value = korzen.value.offsetWidth
  const el = naglowekKarty.value && naglowekKarty.value.$el
  wysokoscNaglowka.value = el ? el.offsetHeight : 0
}

onMounted(() => {
  zmierz()
  if (typeof ResizeObserver !== 'undefined' && korzen.value) {
    obserwator = new ResizeObserver(zmierz)
    obserwator.observe(korzen.value)
  }
})

onBeforeUnmount(() => {
  if (obserwator) obserwator.disconnect()
})

const pxNaH = computed(() =>
  szerokosc.value > 0
    ? pxNaGodzineZSzerokosci(szerokosc.value, os.value.do - os.value.od, {
        // nagłówek karty + jego dolny margines mb-3 (12 px)
        naglowekKarty:
          wysokoscNaglowka.value > 0 ? wysokoscNaglowka.value + 12 : 0,
      })
    : skalaPionowa(props.kompakt),
)
const jednaLinia = computed(() => czyJednaLinia(pxNaH.value))
const etykietyGodzin = computed(() =>
  godzinyEtykietPion(os.value.od, os.value.do, pxNaH.value),
)
const wysokosc = computed(() =>
  wysokoscSiatkiPion(os.value.od, os.value.do, pxNaH.value),
)
const kolumnaGodzin = computed(() => (props.kompakt ? 'w-12' : 'w-14'))
const poDniach = computed(() => pogrupujPoDniach(props.spotkania))
const chip = computed(() =>
  etykietaChipa(props.spotkania, props.dni.length === 1 ? 'dzien' : 'tydzien'),
)
const etykietaZakresu = computed(() =>
  props.dni.length
    ? zbudujEtykieteZakresu(props.dni[0], props.dni[props.dni.length - 1])
    : '',
)

function stylBloku(s) {
  const p = pozycjaBlokuPx(s.termin, os.value.od, pxNaH.value)
  return { top: p.topPx + 1 + 'px', height: p.heightPx - 2 + 'px' }
}

function znacznikTeraz(dzien) {
  if (!czyDzis(dzien, props.teraz)) return null
  const pct = pozycjaTeraz(props.teraz, os.value.od, os.value.do)
  if (pct === null) return null
  return (pct / 100) * wysokosc.value
}

function klikPuste(event, dzien) {
  const prostokat = event.currentTarget.getBoundingClientRect()
  emit('nowe', {
    data: dzien,
    godzina: godzinaZKliknieciaPion(
      event.clientY - prostokat.top,
      os.value.od,
      os.value.do,
      pxNaH.value,
    ),
    handlowiec: props.handlowiec.user,
  })
}
</script>
