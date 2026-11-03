<!--
  Karta handlowca (kalendarz spotkań, ops#318): nagłówek, oś godzin i osobna
  zaokrąglona ścieżka na każdy dzień z paskami spotkań. Czysta prezentacja:
  pozycje i daty liczy utils/kalendarz.js, dane i zapis żyją w Kalendarz.vue.
  Prop `duzy` = karta na całą szerokość (ścieżki 36 px), domyślnie kompakt
  tablicy (ścieżki 24 px). Prop `os` = wspólna oś godzin całej tablicy.
  Grafik dostępności (b82): prop `dostepnosc` (mapa dzień -> okna, null = brak
  grafiku, undefined = funkcja wyłączona) daje ciemne odcinki w paski,
  czerwoną obwódkę spotkań poza grafikiem i chip "brak grafiku"; prop
  `edycja` pokazuje przycisk "Grafik" (emit `grafik`).
-->
<template>
  <div
    class="rounded-xl border border-outline-gray-2 bg-surface-base p-3.5 text-xs"
  >
    <NaglowekKarty
      :handlowiec="handlowiec"
      :kolor="kolor"
      :etykieta-zakresu="etykietaZakresu"
      :chip="chip"
      :brak-grafiku="grafikWlaczony && dostepnosc === null"
      @przesun="(k) => $emit('przesun', k)"
    >
      <template v-if="edycja" #akcje>
        <Button
          size="sm"
          variant="outline"
          data-testid="kalendarz-grafik"
          @click="$emit('grafik')"
        >
          <template #prefix
            ><FeatherIcon name="edit-2" class="h-3.5 w-3.5"
          /></template>
          {{ __('Grafik') }}
        </Button>
      </template>
    </NaglowekKarty>

    <div class="mt-3 flex items-end border-b border-outline-gray-2 pb-1.5">
      <div
        class="shrink-0 text-xs uppercase tracking-wide text-ink-gray-5"
        :style="{ width: wymiary.kolumnaDniPx + 'px' }"
      >
        {{ __('Dzień') }}
      </div>
      <div class="relative h-4 flex-1">
        <span
          v-for="g in etykietyGodzin"
          :key="g"
          class="absolute top-0 -translate-x-1/2 text-xs tabular-nums text-ink-gray-5"
          :style="{ left: pozycjaGodzinyPct(g, os.od, os.do) + '%' }"
        >
          {{ String(g).padStart(2, '0') }}
        </span>
      </div>
    </div>

    <div
      class="relative mt-2 flex flex-col"
      :style="{ gap: wymiary.odstepPx + 'px' }"
    >
      <div
        v-for="dzien in dni"
        :key="dzien"
        class="flex items-center"
        :style="{ height: wymiary.sciezkaPx + 'px' }"
      >
        <div
          class="flex shrink-0 items-center gap-1"
          :style="{ width: wymiary.kolumnaDniPx + 'px' }"
        >
          <span
            class="font-semibold"
            :class="[
              'text-xs',
              czyDzis(dzien, teraz)
                ? 'text-ink-blue-8'
                : czyWeekend(dzien)
                  ? 'text-ink-gray-4'
                  : 'text-ink-gray-8',
            ]"
          >
            {{ skrotDnia(dzien) }}
          </span>
          <span
            v-if="czyDzis(dzien, teraz)"
            class="flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-surface-blue-6 px-1 text-[11px] font-semibold text-white"
          >
            {{ numerDnia(dzien) }}
          </span>
          <span v-else class="text-ink-gray-5">{{ numerDnia(dzien) }}</span>
        </div>
        <div
          class="relative h-full min-w-0 flex-1 cursor-pointer"
          :data-dzien="dzien"
          @click="klikPuste($event, dzien)"
        >
          <div
            class="absolute inset-0 rounded-md"
            :class="[
              czyDzis(dzien, teraz) ? 'bg-surface-blue-1' : 'bg-surface-gray-1',
              czyWeekend(dzien) ? 'opacity-50' : '',
            ]"
          ></div>
          <div
            v-if="niedostepne[dzien]?.length"
            class="pointer-events-none absolute inset-0 z-[1]"
            data-testid="kalendarz-niedostepny"
          >
            <span
              v-for="[a, b] in niedostepne[dzien]"
              :key="a"
              class="kalendarz-niedostepny absolute bottom-0 top-0 rounded-md"
              :style="stylOdcinkaPoziomo(a, b, os.od, os.do)"
            ></span>
          </div>
          <DymekSpotkania
            v-for="s in poDniach[dzien] || []"
            :key="s.name"
            :spotkanie="s"
          >
            <button
              type="button"
              class="absolute bottom-0.5 top-0.5 z-[2] overflow-hidden whitespace-nowrap rounded-[5px] border border-surface-base px-2 text-left text-xs font-medium text-white"
              :class="[
                kolor.pelny,
                czyUmowiony(s.status) ? '' : 'opacity-[0.7]',
                pozaGrafikiem(s) ? 'kalendarz-poza-grafikiem' : '',
              ]"
              :style="stylPaskaPoziomo(s.termin, os.od, os.do)"
              :data-lead="s.name"
              @click.stop="$emit('otworz', s.name)"
            >
              <span class="block truncate">{{ nazwisko(s.lead_name) }}</span>
            </button>
          </DymekSpotkania>
          <span
            v-if="znacznikTeraz(dzien) !== null"
            class="pointer-events-none absolute bottom-0 top-0 z-[3] w-0.5 -translate-x-1/2 rounded bg-surface-red-5"
            :style="{ left: znacznikTeraz(dzien) + '%' }"
            data-testid="kalendarz-teraz"
          ></span>
        </div>
      </div>
      <div
        class="pointer-events-none absolute inset-y-0 right-0 z-0"
        :style="{ left: wymiary.kolumnaDniPx + 'px' }"
      >
        <span
          v-for="g in liniePionowe(os.od, os.do)"
          :key="g"
          class="absolute bottom-0 top-0 border-l border-dashed border-outline-gray-2"
          :style="{ left: pozycjaGodzinyPct(g, os.od, os.do) + '%' }"
        ></span>
      </div>
    </div>

    <div
      class="mt-2.5 flex items-center justify-between gap-3 whitespace-nowrap border-t border-outline-gray-2 pt-2.5 text-xs text-ink-gray-6"
    >
      <div class="flex items-center gap-3">
        <span class="flex items-center gap-1.5">
          <span class="h-2 w-2 rounded-full" :class="kolor.pelny"></span
          >{{ __('Umówiony') }}
        </span>
        <span class="flex items-center gap-1.5">
          <span
            class="h-2 w-2 rounded-full opacity-[0.7]"
            :class="kolor.pelny"
          ></span
          >{{ __('Do potwierdzenia') }}
        </span>
        <span class="flex items-center gap-1.5">
          <span class="h-2 w-2 rounded-full bg-surface-red-5"></span
          >{{ __('Teraz') }}
        </span>
        <span v-if="grafikWlaczony" class="flex items-center gap-1.5">
          <span class="kalendarz-niedostepny h-2.5 w-4 rounded-sm"></span
          >{{ __('Niedostępny') }}
        </span>
        <span v-if="maPozaGrafikiem" class="flex items-center gap-1.5">
          <span class="kalendarz-poza-grafikiem h-2 w-3 rounded-sm"></span
          >{{ __('Poza grafikiem') }}
        </span>
      </div>
      <span class="hidden sm:inline">
        {{ String(os.od).padStart(2, '0') }}:00 {{ __('do') }}
        {{ String(os.do).padStart(2, '0') }}:00
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Button, FeatherIcon } from 'frappe-ui'
import NaglowekKarty from '@/components/kalendarz/NaglowekKarty.vue'
import DymekSpotkania from '@/components/kalendarz/DymekSpotkania.vue'
import {
  czyDzis,
  czyPozaGrafikiem,
  czyUmowiony,
  czyWeekend,
  etykietaChipa,
  etykietaZakresu as zbudujEtykieteZakresu,
  godzinaZKlikniecia,
  godzinyEtykiet,
  kolorHandlowca,
  liniePionowe,
  nazwisko,
  numerDnia,
  odcinkiNiedostepne,
  oknaDnia,
  osGodzin,
  pogrupujPoDniach,
  pozycjaGodzinyPct,
  pozycjaTeraz,
  skrotDnia,
  stylOdcinkaPoziomo,
  stylPaskaPoziomo,
  wymiaryTorow,
} from '@/utils/kalendarz'

const props = defineProps({
  handlowiec: { type: Object, required: true },
  kolorIndex: { type: Number, default: 0 },
  spotkania: { type: Array, default: () => [] },
  dni: { type: Array, required: true },
  teraz: { type: Date, default: () => new Date() },
  duzy: { type: Boolean, default: false },
  // Wspólna oś godzin tablicy ({ od, do }); bez niej oś liczona z własnych spotkań.
  osZewnetrzna: { type: Object, default: null },
  // Grafik dostępności: { 'RRRR-MM-DD': [[od, do]] }, null = brak grafiku,
  // undefined = grafik wyłączony (brak doctype na serwerze).
  dostepnosc: { type: Object, default: undefined },
  // Przycisk "Grafik" (backoffice, widok tygodnia).
  edycja: { type: Boolean, default: false },
})

const emit = defineEmits(['otworz', 'nowe', 'przesun', 'grafik'])

const grafikWlaczony = computed(() => props.dostepnosc !== undefined)
const niedostepne = computed(() => {
  const wynik = {}
  if (!grafikWlaczony.value) return wynik
  for (const dzien of props.dni) {
    wynik[dzien] = odcinkiNiedostepne(
      oknaDnia(props.dostepnosc, dzien),
      os.value.od,
      os.value.do,
    )
  }
  return wynik
})
const maPozaGrafikiem = computed(() =>
  props.spotkania.some((s) => pozaGrafikiem(s)),
)

function pozaGrafikiem(s) {
  return grafikWlaczony.value && czyPozaGrafikiem(s, props.dostepnosc)
}

const kolor = computed(() => kolorHandlowca(props.kolorIndex))
const os = computed(() => props.osZewnetrzna || osGodzin(props.spotkania))
const wymiary = computed(() => wymiaryTorow(props.duzy))
const etykietyGodzin = computed(() =>
  godzinyEtykiet(os.value.od, os.value.do, props.duzy ? 1 : 2),
)
const poDniach = computed(() => pogrupujPoDniach(props.spotkania))
const chip = computed(() =>
  etykietaChipa(props.spotkania, props.dni.length === 1 ? 'dzien' : 'tydzien'),
)
const etykietaZakresu = computed(() =>
  props.dni.length
    ? zbudujEtykieteZakresu(props.dni[0], props.dni[props.dni.length - 1])
    : '',
)

function znacznikTeraz(dzien) {
  if (!czyDzis(dzien, props.teraz)) return null
  return pozycjaTeraz(props.teraz, os.value.od, os.value.do)
}

function klikPuste(event, dzien) {
  const prostokat = event.currentTarget.getBoundingClientRect()
  if (!prostokat.width) return
  const xPct = ((event.clientX - prostokat.left) / prostokat.width) * 100
  emit('nowe', {
    data: dzien,
    godzina: godzinaZKlikniecia(xPct, os.value.od, os.value.do),
    handlowiec: props.handlowiec.user,
  })
}
</script>
