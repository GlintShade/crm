<!--
  Jedna notatka w strumieniu notatek szansy (issue #200, "W2 notatki na
  szansie"; wygląd przebudowany na "wariant C" w issue ops#206). Wspólny
  komponent dla wszystkich ośmiu zakładek (Zestaw, Umowa, Kredyt, Faktury,
  Montaż, OSD, Dotacja, Trify) ORAZ dla wspólnego feedu "Notatki"
  (`NotatkiTab.vue`, gdzie dochodzi też Audyt/AudytCP) - bezstanowy co do
  zakładki, dostaje gotowy wpis jako prop.

  Decyzja właściciela: BEZ edycji i BEZ kosza - pomyłka to nowa notatka pod
  spodem, nie poprawka istniejącej. Ten komponent więc celowo nie ma żadnego
  przycisku edytuj/usuń, niezależnie od `can_delete` w odpowiedzi API (to
  pole istnieje dla przyszłego użycia gdzie indziej, nie tutaj).

  WARIANT C (ops#206): etykieta zakładki źródłowej (ikona + tekst, tło/tekst
  w kolorze źródła) i lewa krawędź karty w tym samym kolorze renderują się
  ZAWSZE, niezależnie od `pokazZakladke` - to jest zmiana względem
  poprzedniego wyglądu, gdzie chip zakładki (wtedy zawsze pomarańczowy,
  Badge `theme="orange"`) pokazywał się WYŁĄCZNIE we wspólnym feedzie.
  Jeden kolor na źródło (`kolorZrodla()`, `utils/notatki.js`) na trzech
  miejscach naraz (panel źródeł, chip mobilny, ta karta) było wprost
  wymaganiem issue - karta na zakładce źródłowej (np. Zestaw) dziś też
  pokazuje bursztynową etykietę "Zestaw" i bursztynową krawędź, nie tylko
  gdy wpis przychodzi z feedu.

  `pokazZakladke` (domyślnie false) steruje TERAZ wyłącznie stopką "Otwórz w
  zakładce {X}" - widoczną jedynie we wspólnym feedzie (`NotatkiTab.vue`),
  bo tylko tam ma sens nawigacja "wróć do źródła"; żadne z ośmiu wywołań na
  samych zakładkach źródłowych (`NotatkiStrumien.vue`) tego nie ustawia, i
  nie musi - stopka jest WEWNĄTRZ karty (nie osobnym przyciskiem pod nią,
  jak poprzednio), emitowana przez `otworz-zakladke` do rodzica, który zna
  router (`wpis.zakladka_hash` jest już gotowym, małym literami hashem bez
  "#", policzonym serwerowo).

  `ikonaZakladki` i `etykietaZakladkiOverride` pozostają jako opcjonalne
  nadpisania (feed ich używa, bo backend już policzył `zrodlo_etykieta` dla
  źródeł spoza ośmiu zakładek `Volteo Notatka`, czyli Audyt/AudytCP) - bez
  nadpisania komponent sam wylicza ikonę (`IKONY_ZRODEL`, przeniesione tu z
  `NotatkiTab.vue` na wprost polecenie briefu issue) i etykietę
  (`ETYKIETY_ZRODEL`, już istniejące w `utils/notatki.js`, komplet
  dziesięciu kluczy łącznie z Audyt/AudytCP) z `wpis.zakladka`.

  `tylkoGodzina` (domyślnie false) pokazuje w prawym górnym rogu wyłącznie
  godzinę 24h (np. "17:00") zamiast pełnej daty z `formatujTermin` - feed
  włącza to, bo dzień jest tam już pokazany raz, w nagłówku grupy dnia
  (`grupujPoDniu` w utils/notatki.js); pokazywanie pełnej daty na KAŻDEJ
  karcie pod nagłówkiem "Dziś" byłoby zwykłą powtórką.

  Załączniki: siatka kafelków 96×96 (`h-24 w-24`) zamiast dawnej listy
  przycisków `AttachmentItem`/siatki miniatur `grid-cols-3` - PDF (i każde
  inne rozszerzenie niebędące rozpoznanym obrazem) dostaje kafelek z ikoną w
  kolorowym kwadraciku (czerwony tylko dla PDF, `ikonaDla()` z
  `utils/pliki.js` już odróżnia PDF od "inny" po rozszerzeniu nazwy pliku,
  nie po `file_type`), nazwą pliku (dwie linie, `line-clamp-2`) i rozmiarem
  (`formatujRozmiar()`); klik otwiera plik w nowej karcie, ten sam wzorzec
  co `PlikiTab.vue`'s `otworz()`. Obraz zostaje miniaturą `object-cover`
  otwierającą `AudytPodgladZdjec` - niezmienione względem poprzedniego
  wyglądu.
-->
<template>
  <div
    class="flex flex-col gap-3 rounded-xl border border-outline-gray-2 border-l-[5px] p-3.5 sm:p-4"
    :class="kolor.krawedz"
  >
    <div class="flex items-start justify-between gap-2">
      <div class="flex items-start gap-2.5">
        <UserAvatar :user="wpis.owner" size="lg" />
        <div class="flex flex-col gap-1">
          <span class="text-[13px] font-semibold leading-tight text-ink-gray-9">{{ autor }}</span>
          <div class="flex flex-wrap items-center gap-1.5">
            <span
              class="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-semibold leading-none"
              :class="[kolor.tlo, kolor.tekst]"
            >
              <component :is="ikonaChipu" class="h-3 w-3 shrink-0" />
              {{ etykietaChipu }}
            </span>
            <Badge variant="subtle" theme="gray" size="sm" :label="wpis.typ || __('Notatka')" />
          </div>
        </div>
      </div>
      <span class="shrink-0 whitespace-nowrap text-xs tabular-nums text-ink-gray-5">{{ dataTekst }}</span>
    </div>

    <div class="prose-f max-w-[64ch] text-[15px] text-ink-gray-9" v-html="sanitizeHTML(wpis.tekst)" />

    <div v-if="dokumenty.length || obrazy.length" class="flex flex-wrap gap-2">
      <button
        v-for="p in dokumenty"
        :key="p.name"
        type="button"
        class="flex h-24 w-24 shrink-0 flex-col items-start gap-1 overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-2 text-left"
        @click="otworzDokument(p)"
      >
        <span
          class="flex h-6 w-7 shrink-0 items-center justify-center rounded"
          :class="jestPdf(p) ? 'bg-red-600 text-white' : 'bg-ink-gray-5 text-white'"
        >
          <component :is="ikonaDokumentu(p)" class="h-3.5 w-3.5" />
        </span>
        <span class="line-clamp-2 w-full min-w-0 flex-1 break-all text-[11px] leading-tight text-ink-gray-8">{{ p.file_name }}</span>
        <span class="text-[10px] text-ink-gray-4">{{ formatujRozmiar(p.file_size) }}</span>
      </button>

      <img
        v-for="o in obrazy"
        :key="o.name"
        :src="o.file_url"
        :alt="o.file_name"
        loading="lazy"
        class="h-24 w-24 shrink-0 cursor-pointer rounded-lg border border-outline-gray-2 object-cover"
        @click="otworzPodglad(o.name)"
      />
    </div>

    <Button
      v-if="pokazZakladke && wpis.zakladka_hash"
      variant="ghost"
      size="sm"
      class="self-start !px-0 !text-xs !text-ink-gray-5 hover:!text-ink-gray-7"
      iconRight="arrow-up-right"
      :label="__('Otwórz w zakładce {0}', [etykietaChipu])"
      @click="$emit('otworz-zakladke', wpis.zakladka_hash)"
    />

    <AudytPodgladZdjec v-model="podgladOtwarty" :zdjecia="podgladLista" v-model:indeks="podgladIndeks" />
  </div>
</template>

<script setup>
import AudytIcon from '@/components/Icons/AudytIcon.vue'
import DotacjaIcon from '@/components/Icons/DotacjaIcon.vue'
import FakturyIcon from '@/components/Icons/FakturyIcon.vue'
import FileIcon from '@/components/Icons/FileIcon.vue'
import FilePdfIcon from '@/components/Icons/FilePdfIcon.vue'
import FileTextIcon from '@/components/Icons/FileTextIcon.vue'
import FileVideoIcon from '@/components/Icons/FileVideoIcon.vue'
import KredytIcon from '@/components/Icons/KredytIcon.vue'
import MontazIcon from '@/components/Icons/MontazIcon.vue'
import NoteIcon from '@/components/Icons/NoteIcon.vue'
import OsdIcon from '@/components/Icons/OsdIcon.vue'
import TrifyIcon from '@/components/Icons/TrifyIcon.vue'
import UmowaIcon from '@/components/Icons/UmowaIcon.vue'
import ZestawIcon from '@/components/Icons/ZestawIcon.vue'
import AudytPodgladZdjec from '@/components/deal/AudytPodgladZdjec.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { usersStore } from '@/stores/users'
import { sanitizeHTML } from '@/utils'
import { indeksDlaKlucza } from '@/utils/audytPodglad'
import { formatujTermin } from '@/utils/dataPolska'
import {
  ETYKIETY_ZRODEL,
  etykietaZakladki,
  godzinaZTekstu,
  kolorZrodla,
  nazwaAutora,
  plikiDoPodgladu,
  podzielPliki,
} from '@/utils/notatki'
import { IKONA_PDF, formatujRozmiar, ikonaDla } from '@/utils/pliki'
import { Badge, Button } from 'frappe-ui'
import { computed, ref } from 'vue'

const props = defineProps({
  // Jeden wpis w kształcie zwracanym przez crm.api.notatki.lista: { name,
  // zakladka, typ, data_zdarzenia, tekst, kredyt, owner, creation,
  // autor_nazwa, pliki: [{name, file_name, file_url, file_type, file_size}] }
  // (feed `NotatkiTab.vue` mapuje swój własny kształt na ten sam, patrz
  // `jakoKartaWpis()` tam).
  wpis: { type: Object, required: true },
  // Pokazuje stopkę "Otwórz w zakładce {X}" - WYŁĄCZNIE feed (patrz komentarz
  // nagłówka pliku). Etykieta/krawędź/ikona renderują się zawsze, niezależnie
  // od tego propa.
  pokazZakladke: { type: Boolean, default: false },
  ikonaZakladki: { type: [Object, Function], default: null },
  etykietaZakladkiOverride: { type: String, default: '' },
  tylkoGodzina: { type: Boolean, default: false },
})

defineEmits(['otworz-zakladke'])

const { getUser } = usersStore()

const autor = computed(() => nazwaAutora(props.wpis, getUser))

const kolor = computed(() => kolorZrodla(props.wpis.zakladka))

// Ikona domyślna resolwowana z `wpis.zakladka` - OSD/Dotacja mają już
// własne ikony (`OsdIcon`/`DotacjaIcon`, dodane w równoległym issue tej
// paczki), więc żadne źródło nie musi już spadać na `NoteIcon` poza
// naprawdę nieznanym kluczem.
const IKONY_ZRODEL = {
  Zestaw: ZestawIcon,
  Umowa: UmowaIcon,
  Kredyt: KredytIcon,
  Faktury: FakturyIcon,
  Montaz: MontazIcon,
  OSD: OsdIcon,
  Dotacja: DotacjaIcon,
  Trify: TrifyIcon,
  Audyt: AudytIcon,
  AudytCP: AudytIcon,
}

const ikonaChipu = computed(
  () => props.ikonaZakladki || IKONY_ZRODEL[props.wpis.zakladka] || NoteIcon,
)

// Etykieta: nadpisanie wywołującego (feed, `zrodlo_etykieta` policzone
// serwerowo) ma pierwszeństwo, potem `ETYKIETY_ZRODEL` (komplet dziesięciu
// kluczy, łącznie z Audyt/AudytCP, które `etykietaZakladki()`/`ZAKLADKI` nie
// znają), na końcu `etykietaZakladki()` jako ostatnia deska ratunku (zwraca
// sam klucz dla czegoś naprawdę nieznanego, nigdy pusty string).
const etykietaChipu = computed(
  () =>
    props.etykietaZakladkiOverride ||
    ETYKIETY_ZRODEL[props.wpis.zakladka] ||
    etykietaZakladki(props.wpis.zakladka),
)

const dataTekst = computed(() => {
  const surowa = props.wpis.data_zdarzenia || props.wpis.creation
  return props.tylkoGodzina ? godzinaZTekstu(surowa) : formatujTermin(surowa)
})

const podzial = computed(() => podzielPliki(props.wpis.pliki))
const dokumenty = computed(() => podzial.value.dokumenty)
const obrazy = computed(() => podzial.value.obrazy)

const podgladLista = computed(() => plikiDoPodgladu(obrazy.value))
const podgladOtwarty = ref(false)
const podgladIndeks = ref(0)

function otworzPodglad(nazwa) {
  const idx = indeksDlaKlucza(podgladLista.value, nazwa)
  if (idx === -1) return
  podgladIndeks.value = idx
  podgladOtwarty.value = true
}

function jestPdf(plik) {
  return ikonaDla(plik) === IKONA_PDF
}

const KOMPONENTY_IKON_DOKUMENTU = {
  pdf: FilePdfIcon,
  wideo: FileVideoIcon,
  dokument: FileTextIcon,
  inny: FileIcon,
}

function ikonaDokumentu(plik) {
  return KOMPONENTY_IKON_DOKUMENTU[ikonaDla(plik)] || FileIcon
}

function otworzDokument(plik) {
  if (!plik?.file_url) return
  window.open(plik.file_url, '_blank', 'noopener')
}
</script>
