<!--
  Pasek etapów pipeline'u (Szansa) — pełnoszerokościowy pasek między
  nagłówkiem strony a wierszem zakładek. Klikanie WĘZŁÓW nic nie robi —
  jedynym ręcznym sterowaniem statusem pozostaje dropdown w nagłówku strony
  (Deal.vue / MobileDeal.vue, triggerStatusChange). Węzły CP, które mają
  podzadania (katalog `payload.subtasks`, patrz niżej), dostają dodatkowo
  chevron rozwijający pas mini-zadań POD paskiem — to jedyna interaktywna
  część tego komponentu (b49 F2).

  Cała logika stanu (tryb paska, stan węzła, numer węzła, odznaka poza
  pipeline'em) żyje w `utils/dealPipeline.js` — ten komponent tylko renderuje
  wynik na podstawie payloadu SERWERA (KSZTAŁT rurociągu: `steps`/`notes`, z
  `crm.api.pipeline.volteo_pipeline_get`, WOŁANY PO PEŁNEJ KROPKOWANEJ
  ŚCIEŻCE — gołe nazwy dają HTTP 417 w runtime dla API forka) i `props.status`
  (prawda kliencka — patrz komentarz w <script>). Notatka "następny krok" NIE
  renderuje się tu — korzysta z tego samego payloadu i tej samej pochodnej
  logiki co reszta tego pliku, ale mieszka w panelu bocznym, patrz
  `DealNextStepNote.vue`.

  Logika STANU podzadań (parse/walidacja/dozwolone przejścia) żyje w
  `utils/dealPodzadania.js`, lustrzana 1:1 wobec `crm/volteo_pipeline.py`.
  Ten komponent renderuje ją nad KATALOGIEM podzadań, który już jedzie w tym
  samym payloadzie (`payload.subtasks`, dodane w B1) — więc rozwinięcie
  pasa NIE odpytuje serwera ponownie, zgodnie z regułą "jedno pobranie per
  rodzaj" wyjaśnioną niżej. Sam STAN podzadań (kto co zaznaczył) jest na razie
  mockiem lokalnym w tym komponencie — patrz `// F3: zastąpić
  volteo_podzadania_get/set` przy `mapaZadan` niżej.
-->
<template>
  <div
    v-if="!resource.loading && mode !== 'hidden'"
    class="w-full border-b px-5 py-3"
    :class="mode === 'lost' ? 'bg-surface-red-2' : 'bg-surface-base'"
  >
    <!-- Zawartość ograniczona do ~80% szerokości kontenera i wyśrodkowana
         TYLKO gdy rurociąg ma niewiele węzłów (OZE, 5 kroków) — przy 12
         węzłach CP ograniczenie do 80% zostawiłoby za mało miejsca, więc tam
         zawartość zajmuje pełną szerokość i polega na overflow-x-auto niżej. -->
    <div
      class="mx-auto flex w-full max-w-full flex-wrap items-center gap-4"
      :class="capWidth ? 'sm:max-w-[80%]' : ''"
    >
      <!-- Stepper: węzły równo rozłożone na pełną szerokość, połączone linią -->
      <div class="flex flex-1 items-start overflow-x-auto">
        <template v-for="(step, i) in payload.steps" :key="i">
          <!-- Segment łącznika PRZED węzłem (pomijamy dla pierwszego węzła) -->
          <div
            v-if="i > 0"
            class="mt-3.5 h-0.5 flex-1 shrink-0"
            :class="connectorClass(i)"
          />
          <div
            class="flex shrink-0 flex-col items-center px-1"
            :class="capWidth ? 'gap-1.5' : 'gap-1'"
          >
            <div
              class="flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-medium"
              :class="nodeCircleClass(i)"
            >
              <span
                v-if="nodeStateForMode(mode, i, currentIndex) === 'done'"
                class="lucide-check size-3.5"
                aria-hidden="true"
              />
              <span v-else>{{ stepNumber(i) }}</span>
            </div>
            <div
              class="whitespace-normal break-words text-center leading-tight"
              :class="[nodeLabelClass(i), capWidth ? 'w-24 text-xs' : 'w-20 text-[11px]']"
            >
              {{ __(step.status) }}
            </div>
            <!-- Chevron podzadań — tylko dla etapów obecnych w katalogu
                 `payload.subtasks` (na razie wyłącznie CP; OZE ma pusty
                 katalog, więc tu nic się nie renderuje i wygląd paska OZE
                 zostaje bez zmian). Hit area >=40px przez padding wokół
                 14px ikony (13px * 2 + 14px = 40px), bez zmiany widocznego
                 rozmiaru strzałki. -->
            <button
              v-if="payload.subtasks?.[step.status]?.length"
              type="button"
              class="flex items-center justify-center rounded p-[13px] text-ink-gray-4 transition-colors hover:bg-surface-gray-2 hover:text-ink-gray-7"
              :aria-expanded="rozwinietyEtap === step.status"
              :aria-label="__('Pokaż zadania etapu')"
              @click="toggleEtap(step.status)"
            >
              <span
                class="lucide-chevron-down block size-3.5 transition-transform duration-150"
                :class="{ 'rotate-180': rozwinietyEtap === step.status }"
                aria-hidden="true"
              />
            </button>
          </div>
        </template>
      </div>

      <!-- Odznaka poza pipeline'em (Przegrana / Wygrana / inny status) -->
      <Badge
        v-if="badgeLabel"
        :label="__(badgeLabel)"
        :theme="badgeTheme"
        variant="subtle"
        class="shrink-0"
      />
    </div>

    <!-- Pas mini-zadań etapu — celowo POZA divem overflow-x-auto steppera
         wyżej: pełna szerokość, nie scrolluje się razem z paskiem etapów. -->
    <div v-if="rozwinietyEtap" class="mx-auto mt-3 w-full max-w-full border-t pt-3">
      <div class="mb-2 flex items-center gap-2">
        <span class="text-sm font-medium text-ink-gray-8">{{ __(rozwinietyEtap) }}</span>
        <span class="text-xs text-ink-gray-5">
          {{ etapPodsumowanie.zrobione }}/{{ etapPodsumowanie.wszystkie }}
        </span>
      </div>
      <div class="flex flex-wrap gap-2">
        <template v-for="def in etapZadania" :key="def.klucz">
          <!-- Rep: prostokąt tylko do odczytu, bez popovera (nie widzi/nie
               zmienia stanu podzadań — jak reszta tego paska). -->
          <div v-if="isRep" :class="pillClass(stanFor(mapaZadan, def.klucz))">
            <span
              v-if="def.z_data && mapaZadan[def.klucz]?.data"
              class="lucide-calendar size-3 shrink-0"
              aria-hidden="true"
            />
            <span>{{ __(def.label) }}</span>
            <span
              v-if="def.z_data && mapaZadan[def.klucz]?.data"
              class="text-[11px] tabular-nums opacity-80"
            >
              {{ getFormat(mapaZadan[def.klucz].data, '', true, false, true) }}
            </span>
            <span
              v-if="mapaZadan[def.klucz]?.note"
              class="size-1.5 shrink-0 rounded-full bg-current"
              :title="mapaZadan[def.klucz].note"
              aria-hidden="true"
            />
          </div>

          <!-- Admin/backoffice: prostokąt otwiera popover ze stanami i notatką. -->
          <Popover v-else placement="bottom-start">
            <template #target="{ togglePopover }">
              <button
                type="button"
                :class="pillClass(stanFor(mapaZadan, def.klucz))"
                @click="togglePopover"
              >
                <span
                  v-if="def.z_data && mapaZadan[def.klucz]?.data"
                  class="lucide-calendar size-3 shrink-0"
                  aria-hidden="true"
                />
                <span>{{ __(def.label) }}</span>
                <span
                  v-if="def.z_data && mapaZadan[def.klucz]?.data"
                  class="text-[11px] tabular-nums opacity-80"
                >
                  {{ getFormat(mapaZadan[def.klucz].data, '', true, false, true) }}
                </span>
                <span
                  v-if="mapaZadan[def.klucz]?.note"
                  class="size-1.5 shrink-0 rounded-full bg-current"
                  :title="mapaZadan[def.klucz].note"
                  aria-hidden="true"
                />
              </button>
            </template>
            <template #body>
              <div
                class="my-2 flex w-64 flex-col gap-2.5 rounded-lg bg-surface-elevation-2 p-3 shadow-2xl ring-1 ring-black ring-opacity-5 focus:outline-none"
              >
                <div class="flex items-start justify-between gap-2">
                  <span class="text-sm font-medium text-ink-gray-8">{{ __(def.label) }}</span>
                  <Badge
                    :theme="STAN_META[stanFor(mapaZadan, def.klucz)].theme"
                    variant="subtle"
                    size="sm"
                    :label="__(STAN_META[stanFor(mapaZadan, def.klucz)].label)"
                  />
                </div>
                <div class="flex flex-wrap gap-1.5">
                  <Button
                    v-for="stan in dozwoloneStany(def).filter((s) => s !== 'brak')"
                    :key="stan"
                    size="sm"
                    variant="subtle"
                    :theme="STAN_META[stan].theme"
                    :label="__(STAN_META[stan].label)"
                    @click="ustawStan(def.klucz, stan)"
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    :label="__('Wyczyść')"
                    @click="ustawStan(def.klucz, 'brak')"
                  />
                </div>
                <FormControl
                  v-if="def.z_data"
                  type="date"
                  :label="__('Data')"
                  :modelValue="mapaZadan[def.klucz]?.data || ''"
                  @update:modelValue="(v) => ustawData(def.klucz, v)"
                />
                <FormControl
                  type="textarea"
                  :label="__('Notatka')"
                  :maxlength="500"
                  :modelValue="mapaZadan[def.klucz]?.note || ''"
                  @update:modelValue="(v) => ustawNotatka(def.klucz, v)"
                />
              </div>
            </template>
          </Popover>
        </template>
      </div>
    </div>
  </div>
</template>
<script setup>
// Dlaczego pasek NIGDY nie odświeża payloadu po zmianie `props.status`:
// wcześniejsza wersja miała `watch(() => props.status, () => resource.reload())`
// i to właśnie ono powodowało błąd „pasek o jeden krok za późno” — reload
// odpytuje serwer, ale zapis TEJ SAMEJ zmiany statusu (SAVE wywołany z
// dropdownu w nagłówku) jest wtedy jeszcze w locie; serwer potrafił oddać
// STARY status i pasek renderował poprzedni krok aż do kolejnej zmiany.
// Rozwiązanie: serwer (`volteo_pipeline_get`) dostarcza tylko KSZTAŁT
// rurociągu (`steps`, `notes`, `subtasks`) dla `rodzaj` — payload odświeżamy
// WYŁĄCZNIE, gdy `rodzaj` się zmienia. Bieżący krok/tryb/notatkę/odznakę
// liczymy tu, w komponencie, synchronicznie z `props.status` (jedyna prawda
// kliencka — ustawiana przez dropdown natychmiast, bez czekania na
// round-trip) i z `statusType` ze store'u statusów (już załadowanego przez
// inny widok tej strony). Migawkowe pola payloadu (`current_index`,
// `off_pipeline*`, `note`, `status`) zostają w odpowiedzi API dla sond, ale
// ten komponent ich nie czyta. Rozwijanie pasa mini-zadań (poniżej) czyta
// TEN SAM `payload.subtasks` bez żadnego dodatkowego fetcha.
import { Badge, Button, FormControl, Popover, createResource } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'
import { getFormat } from '@/utils'
import { statusesStore } from '@/stores/statuses'
import {
  bandMode,
  currentIndexFor,
  nodeStateForMode,
  stepNumber,
  offPipelineBadge,
} from '@/utils/dealPipeline'
import {
  STAN_META,
  parsePodzadania,
  stanFor,
  dozwoloneStany,
  tasksForStage,
  stageSummary,
} from '@/utils/dealPodzadania'

const props = defineProps({
  dealId: { type: String, required: true },
  status: { type: String, default: '' },
  rodzaj: { type: String, default: '' },
})

const { getDealStatus } = statusesStore()

const resource = createResource({
  url: 'crm.api.pipeline.volteo_pipeline_get',
  params: { deal: props.dealId },
  auto: true,
  cache: ['volteo-pipeline', props.dealId],
})

// Kształt rurociągu zależy tylko od `rodzaj` — to jedyna zmiana, po której
// warto odpytać serwer ponownie (np. zmiana linii produktowej na szansie).
watch(() => props.rodzaj, () => resource.reload())

const payload = computed(() => resource.data || null)

// Null-safe na dwa sposoby: nieznany `props.status` (getDealStatus zwraca
// undefined) i store statusów jeszcze niezaładowany (to samo zimne-wejście
// zjawisko, które wywalało render w Deal.vue — patrz commit 46397328;
// tu żaden odczyt nie rzuca, bo `?.type` na undefined daje po prostu undefined,
// a bandMode/offPipelineBadge (i notatka "następny krok" w panelu bocznym,
// zasilana tym samym payloadem) traktują undefined statusType jako 'unknown').
const statusType = computed(() => getDealStatus?.(props.status)?.type)

const currentIndex = computed(() => currentIndexFor(payload.value?.steps, props.status))
const mode = computed(() => bandMode(payload.value, props.status, statusType.value))
const badgeLabel = computed(() => offPipelineBadge(payload.value, props.status, statusType.value))

// Cap `sm:max-w-[80%]` (i etykiety w pełnym rozmiarze) tylko dla rurociągów
// z niewieloma krokami (OZE, 5) — przy 12 węzłach CP zostawiałby za mało
// miejsca w wąskim oknie, więc tam etykiety są węższe/mniejsze (patrz użycia
// niżej w template). Warunkowanie na `steps.length` (nie na `rodzaj`) trzyma
// tę logikę spójną z resztą pliku, który też nigdy nie czyta `props.rodzaj`
// poza triggerem refetcha — i gwarantuje zero zmian wizualnych na OZE (5
// kroków, zawsze `capWidth === true`, więc etykiety/gap/cap zostają dokładnie
// takie jak przed tym issue).
const capWidth = computed(() => (payload.value?.steps?.length ?? 0) <= 6)

const badgeTheme = computed(() => {
  if (mode.value === 'lost') return 'red'
  if (mode.value === 'won') return 'green'
  return 'gray'
})

function connectorClass(index) {
  // Segment "ukończony" (zielony), jeśli węzeł PRZED nim jest już done.
  const prevState = nodeStateForMode(mode.value, index - 1, currentIndex.value)
  return prevState === 'done' || mode.value === 'won'
    ? 'bg-green-500'
    : 'bg-surface-gray-3'
}

function nodeCircleClass(index) {
  const state = nodeStateForMode(mode.value, index, currentIndex.value)
  if (state === 'done') return 'bg-green-500 text-white'
  if (state === 'current') return 'bg-blue-500 text-white'
  if (state === 'future') return 'bg-surface-gray-3 text-ink-gray-6'
  // 'muted' (lost / unknown)
  return 'bg-surface-gray-2 text-ink-gray-4'
}

function nodeLabelClass(index) {
  const state = nodeStateForMode(mode.value, index, currentIndex.value)
  if (state === 'current') return 'font-medium text-ink-blue-link'
  if (state === 'done') return 'text-ink-gray-7'
  if (state === 'muted') return 'text-ink-gray-3'
  return 'text-ink-gray-5'
}

// -----------------------------------------------------------------------
// Pas mini-zadań (b49 F2) — rozwijanie, katalog i STAN (mock).
// -----------------------------------------------------------------------

// Nazwa statusu (step.status) aktualnie rozwiniętego etapu, albo `null`, gdy
// pas jest zwinięty. Jawny stan `null`/string zamiast obecności klucza —
// patrz pułapka projektu: hasOwnProperty na reactive() nie rejestruje
// zależności i zamraża computed (KalkulatorCPTab.vue miało ten błąd).
const rozwinietyEtap = ref(null)

function toggleEtap(status) {
  rozwinietyEtap.value = rozwinietyEtap.value === status ? null : status
}

// Katalog podzadań rozwiniętego etapu, prosto z payloadu serwera (kształt —
// patrz nagłówek pliku). `[]`, gdy pas jest zwinięty albo etap nie ma
// podzadań (tasksForStage jest null-safe względem obu argumentów).
const etapZadania = computed(() => tasksForStage(payload.value?.subtasks, rozwinietyEtap.value))
const etapPodsumowanie = computed(() => stageSummary(etapZadania.value, mapaZadan))

// Restricted D2D rep: widzi pas (postęp), ale nie zmienia stanu podzadań —
// ten sam flag, ten sam wzorzec co w Deal.vue/MobileDeal.vue.
const isRep = Boolean(window.volteo_is_rep)

// F3: zastąpić volteo_podzadania_get/set. Do tego czasu STAN podzadań
// (kto co zaznaczył/zaakceptował/oznaczył jako nd) żyje wyłącznie w tej
// lokalnej mapie reactive — nic tu się nie zapisuje na serwer i znika przy
// odświeżeniu strony. Seed pokazuje demonstracyjnie wszystkie pięć wyglądów
// (brak/waiting/accepted/error/nd) plus oba chipy (data, notatka) na jednym
// etapie „Dokumentacja”, a „Umowa na realizację” zostaje celowo bez seeda,
// żeby był widoczny etap całkiem szary (wszystko „brak”).
//
// Klucz notatki w każdym wpisie to `note` (nie `notatka`) — dopasowanie do
// kształtu, który zwraca/zapisuje już scalony `volteo_podzadania_set`
// (`crm.api.pipeline`, B3): `{stan, by, at, data?, note?}`. Gdy F3 podepnie
// tę mapę pod prawdziwy endpoint, klucz musi się zgadzać, inaczej odczyt
// notatki po cichu przestanie działać.
const SEED_PODZADAN = {
  'dok:umowa_obsluga_dotacji': { stan: 'accepted' },
  'dok:gops_zaswiadczenie': { stan: 'accepted' },
  'dok:pelnomocnictwo_notarialne': { stan: 'waiting' },
  'dok:zgoda_wspolwlascicieli': { stan: 'nd' },
  'dok:ankieta_cp': { stan: 'error', note: 'Brakuje podpisu na drugiej stronie ankiety.' },
  'audyt:umowiony': { stan: 'waiting', data: '2026-08-25' },
}

const mapaZadan = reactive(parsePodzadania(SEED_PODZADAN))

function ustawStan(klucz, stan) {
  const istniejacy = mapaZadan[klucz] || {}
  mapaZadan[klucz] = { ...istniejacy, stan }
}

function ustawData(klucz, data) {
  const istniejacy = mapaZadan[klucz] || {}
  mapaZadan[klucz] = { ...istniejacy, data }
}

function ustawNotatka(klucz, note) {
  const istniejacy = mapaZadan[klucz] || {}
  mapaZadan[klucz] = { ...istniejacy, note }
}

// Klasy pigułki per stan — te same tokeny co warianty subtle+outline w
// frappe-ui Badge.vue (bg/border/text per motyw), żeby paleta pozostała
// spójna z resztą aplikacji i poprawnie flipowała się w ciemnym motywie
// (tokeny semantyczne, zero surowych hexów).
const PILL_THEME_CLASSES = {
  gray: 'border-outline-gray-2 bg-surface-gray-2 text-ink-gray-6',
  blue: 'border-outline-blue-3 bg-surface-blue-2 text-ink-blue-8',
  green: 'border-outline-green-3 bg-surface-green-2 text-ink-green-8',
  red: 'border-outline-red-3 bg-surface-red-2 text-ink-red-8',
}

function pillClass(stan) {
  const meta = STAN_META[stan] || STAN_META.brak
  const theme = PILL_THEME_CLASSES[meta.theme] || PILL_THEME_CLASSES.gray
  const border = meta.muted ? 'border-dashed opacity-70' : 'border-solid'
  return `inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs ${theme} ${border}`
}
</script>
