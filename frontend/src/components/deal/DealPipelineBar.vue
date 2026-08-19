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
  rodzaj" wyjaśnioną niżej. Sam STAN podzadań (kto co zaznaczył/zaakceptował)
  jedzie osobnym pobraniem, `crm.api.pipeline.volteo_podzadania_get`
  (`mapaZadan` niżej), i zapisuje się przez `volteo_podzadania_set` z zapisem
  optymistycznym (b49 F3) — wzorzec `setVerdict()` z `AudytTab.vue`: snapshot
  mapy → optymistyczna podmiana wpisu → po odpowiedzi CAŁA mapa zastępowana
  autorytatywnym `res.stan_mapa` → rollback do snapshotu + toast na błędzie.
  NIGDY `resource.reload()` po zapisie (patrz uzasadnienie tej zasady dla
  `volteo_pipeline_get` powyżej — ten sam race jest tu równie realny).
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
          <!-- "Tab" wokół węzła rozwiniętego etapu: tło (ten sam token
               `bg-surface-gray-2` co panel pasa niżej) + zaokrąglenie TYLKO
               górnych rogów (`rounded-t-md`, bez `rounded-b`) — kolumna
               wygląda jak zakładka teczki, która na dole przechodzi prosto w
               pełnoszerokościowy panel. `self-stretch` każe jej wypełnić
               PEŁNĄ wysokość wiersza steppera (nie tylko wysokość własnej
               treści) — w praktyce i tak jest już najwyższą kolumną w
               wierszu (tylko kolumny z chevronem, czyli z podzadaniami, mogą
               być rozwinięte, a to one ustawiają wysokość wiersza), ale bez
               `self-stretch` zerowa przerwa do panelu niżej zależałaby od
               przypadku, nie była gwarantowana. Zero marginesu/paddingu
               między tą kolumną a panelem (patrz `mt-2` USUNIĘTE z panelu
               niżej) — inaczej "zakładka" wisiałaby w powietrzu nad panelem
               zamiast się w niego wtapiać. Poziome dopasowanie tabu do
               panelu jest przybliżone: ten div żyje w scrollowanym
               kontenerze steppera, panel POZA scrollem na pełną szerokość —
               przy nieprzewiniętym stepperze wygląda jak jedno spójne tło,
               po przewinięciu tab się przesuwa (tab jedzie ze scrollem, górna
               krawędź panelu może wtedy przebiegać "pod" tabem) — świadomy,
               zaakceptowany kompromis (bez mierzenia offsetów JS-em).
               Subtelna ramka 1px (`border-outline-gray-3` — widoczna na tle
               `bg-surface-gray-2`, ale niekrzykliwa) z góry i po bokach, BEZ
               dołu (wtapia się w panel). `border-x border-t` jest OBECNE w
               obu gałęziach (aktywnej i nieaktywnej), zmienia się tylko
               kolor (`border-transparent` gdy nieaktywna) — inaczej 1px
               ramki pojawiającej się/znikającej przy rozwijaniu przesuwałby
               sąsiednie węzły w wierszu o te same 1-2px. -->
          <div
            class="flex shrink-0 flex-col items-center border-x border-t px-1"
            :class="
              rozwinietyEtap === step.status
                ? 'self-stretch rounded-t-md border-outline-gray-3 bg-surface-gray-2'
                : 'border-transparent'
            "
          >
            <div
              class="flex flex-col items-center py-1"
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
                   rozmiaru strzałki. Stan aktywny (etap rozwinięty) dostaje
                   wypełnione tło — `bg-surface-gray-4`, nie `-3`, żeby mieć
                   kontrast NA TLE taba (`bg-surface-gray-2` wyżej), nie na
                   gołym tle paska. -->
              <button
                v-if="payload.subtasks?.[step.status]?.length"
                type="button"
                class="flex items-center justify-center rounded p-[13px] transition-colors"
                :class="
                  rozwinietyEtap === step.status
                    ? 'bg-surface-gray-4 text-ink-gray-8'
                    : 'text-ink-gray-4 hover:bg-surface-gray-2 hover:text-ink-gray-7'
                "
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

    <!-- Panel mini-zadań etapu — celowo POZA divem overflow-x-auto steppera
         wyżej: pełna szerokość, nie scrolluje się razem z paskiem etapów.
         BEZ marginesu/paddingu nad tym divem (patrz `self-stretch` na tabie
         kolumny węzła wyżej) — panel i tab dzielą ten sam token tła
         (`bg-surface-gray-2`) i tę samą ramkę (`border-outline-gray-3`), więc
         przy nieprzewiniętym stepperze wyglądają jak jedna spójna
         "obwoluta": tab wokół aktywnego węzła + panel pod spodem, bez
         przerwy między nimi. Pełna ramka (wszystkie 4 boki) — w
         przeciwieństwie do tabu wyżej ten div montuje/odmontowuje się cały
         przez `v-if`, więc dodanie ramki nie powoduje osobnego "skoku"
         layoutu poza tym, który już wynika z pojawienia/zniknięcia panelu. -->
    <div
      v-if="rozwinietyEtap"
      class="w-full max-w-full rounded-md border border-outline-gray-3 bg-surface-gray-2 p-3"
    >
      <div class="mb-2 flex items-center justify-center gap-2">
        <span class="text-sm font-medium text-ink-gray-8">{{ __(rozwinietyEtap) }}</span>
        <span class="text-xs text-ink-gray-5">
          {{ etapPodsumowanie.zrobione }}/{{ etapPodsumowanie.wszystkie }}
        </span>
      </div>
      <div class="flex flex-wrap justify-center gap-2">
        <template v-for="def in etapZadania" :key="def.klucz">
          <!-- Rep (albo dowolny użytkownik bez roli backoffice/core-admin —
               `editable` jest prawdą SERWERA po załadowaniu, patrz komentarz
               przy `stanResource` w <script>): prostokąt tylko do odczytu,
               bez popovera. -->
          <div v-if="!editable" :class="pillClass(stanFor(mapaZadan, def.klucz))">
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
              <!-- frappe-ui's Popover already sits on reka-ui's PopperContent
                   with `avoidCollisions: true` (default `shift` + `flip`
                   middleware, `collisionPadding: 10`), so bottom-start
                   auto-repositions near a screen edge without any placement
                   logic here. `max-w-[calc(100vw-2rem)]` is only a safety net
                   under the fixed `w-64` (256px) for viewports narrower than
                   ~288px — b49 F4; at every width this app actually ships to
                   (375px+) it is a no-op, so nothing here changes on desktop
                   or on the 375px/768px probe widths. -->
              <div
                class="my-2 flex w-64 max-w-[calc(100vw-2rem)] flex-col gap-2.5 rounded-lg bg-surface-elevation-2 p-3 shadow-2xl ring-1 ring-black ring-opacity-5 focus:outline-none"
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
                    :disabled="busyZadania[def.klucz]"
                    @click="ustawStan(def.klucz, stan)"
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    :label="__('Wyczyść')"
                    :disabled="busyZadania[def.klucz]"
                    @click="ustawStan(def.klucz, 'brak')"
                  />
                </div>
                <!-- `label` celowo BEZ __() — msgid "Data" trafia w pl.po
                     na zupełnie inny, niepowiązany łańcuch UI ("Dane" na
                     `Activities/DataFields.vue` i kilku innych miejscach) i
                     katalog .mo zwróciłby to samo tłumaczenie tutaj. Krótkie
                     "Data" nie potrzebuje tłumaczenia — zostaje gołym
                     stringiem, żeby nie kolidować z tym cudzym msgid. -->
                <FormControl
                  v-if="def.z_data"
                  type="date"
                  label="Data"
                  placeholder="Wybierz datę"
                  :modelValue="formData(def.klucz)"
                  @update:modelValue="(v) => ustawData(def.klucz, v)"
                />
                <FormControl
                  type="textarea"
                  :label="__('Notatka')"
                  :maxlength="500"
                  :modelValue="formNote(def.klucz)"
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
import { Badge, Button, FormControl, Popover, call, createResource, toast } from 'frappe-ui'
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
  buildPodzadaniePayload,
  entryFromPayload,
  applyOptimistic,
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
// Pas mini-zadań (b49 F2) — rozwijanie i katalog.
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

// -----------------------------------------------------------------------
// Stan podzadań (b49 F3) — pobranie, edytowalność, zapis optymistyczny.
// -----------------------------------------------------------------------

// Osobne pobranie od `resource` (KSZTAŁT rurociągu) powyżej — ten payload
// jest per-SZANSA (STAN, nie katalog), więc cache klucz niesie `dealId`, nie
// `rodzaj`. Pełna kropkowana ścieżka: gołe nazwy metod dają HTTP 417 w
// runtime dla API forka (patrz nagłówek pliku / `crm.api.umowa`).
const stanResource = createResource({
  url: 'crm.api.pipeline.volteo_podzadania_get',
  params: { deal: props.dealId },
  auto: true,
  cache: ['volteo-podzadania', props.dealId],
})

// Mapa stanu jest w `ref`, nie `reactive()`, żeby zapis/rollback mógł
// zamienić CAŁĄ mapę na nowy obiekt jednym przypisaniem (`applyOptimistic`
// i rekoncyliacja z `res.stan_mapa` zwracają zawsze NOWY obiekt, nigdy nie
// mutują — patrz `utils/dealPodzadania.js`) zamiast ręcznie kasować/dopisywać
// klucze na istniejącym reactive obiekcie. Template czyta `mapaZadan` bez
// `.value` — Vue odwija top-level ref automatycznie w wyrażeniach szablonu.
const mapaZadan = ref(parsePodzadania(stanResource.data?.stan))
watch(
  () => stanResource.data,
  (data) => {
    mapaZadan.value = parsePodzadania(data?.stan)
  },
)

// Licznik zrobione/wszystkie obok chevronu/nagłówka pasa — musi być
// zdefiniowany PO `mapaZadan`, bo czyta jej `.value` synchronicznie w ciele
// (nie w callbacku, więc kolejność deklaracji ma tu znaczenie, w
// przeciwieństwie do funkcji niżej wołanych dopiero z handlerów).
const etapPodsumowanie = computed(() => stageSummary(etapZadania.value, mapaZadan.value))

// Edytowalność: serwer jest prawdą PO załadowaniu (`stanResource.data.editable`,
// wyliczone z ról wywołującego — `BYPASS_ROLES`, ten sam zestaw co backoffice/
// core-admin gdzie indziej w apce). `!window.volteo_is_rep` to WYŁĄCZNIE
// boot-flaga na pierwszy paint (zanim `stanResource` się załaduje) — ten sam
// flag co w Deal.vue/MobileDeal.vue, ale tu nigdy nie jest ostatnim słowem:
// gdy odpowiedź serwera nadejdzie, `stanResource.data?.editable` przejmuje
// gating, więc popover nie renderuje się dla nikogo bez roli backoffice/
// core-admin nawet gdyby boot-flaga była (błędnie) `false` dla repa.
const editable = computed(() => stanResource.data?.editable ?? !window.volteo_is_rep)

// Formularz (data/notatka) w otwartym popoverze czyta z lokalnego draftu
// zamiast wprost z `mapaZadan`, bo "brak" (żaden wpis jeszcze) nie ma
// odpowiednika po stronie serwera do którego przypiąć datę/notatkę —
// `volteo_podzadania_set` w gałęzi `stan == "brak"` tylko usuwa wpis z mapy,
// nigdy nie czyta `data`/`note` (patrz `crm/api/pipeline.py`). Wpisana przed
// wybraniem stanu wartość więc NIE jedzie do serwera od razu — czeka w
// `draftZadan` i jest wysyłana razem z PIERWSZYM ustawieniem stanu
// (`ustawStan` niżej czyta `formData`/`formNote`, które sięgają do draftu).
// Gdy wpis na serwerze już istnieje, draft nadpisuje wyświetlaną wartość
// (jest "świeższy" niż to, co ostatnio potwierdził serwer) — ale pigułka i
// widok tylko-do-odczytu poza formularzem ZAWSZE czytają `mapaZadan` wprost
// (autorytatywny stan potwierdzony), nigdy draft, żeby nie pokazywać
// niewysłanych zmian jako gdyby były zapisane.
const draftZadan = reactive({})

function formData(klucz) {
  return draftZadan[klucz]?.data ?? mapaZadan.value[klucz]?.data ?? ''
}

function formNote(klucz) {
  return draftZadan[klucz]?.note ?? mapaZadan.value[klucz]?.note ?? ''
}

// Zapis w locie per klucz zadania — osobna flaga per zadanie, nie jedna
// globalna, żeby zapis jednego podzadania nie blokował przycisków innego w
// tym samym (albo innym otwartym) popoverze.
const busyZadania = reactive({})

// Debounce notatki (500ms) — ten sam odstęp i ten sam wzorzec
// (per-pole `setTimeout`, czyszczony przy kolejnym wejściu) co autosave pól
// audytu w AudytTab.vue. Klucz = nazwa zadania, bo więcej niż jeden popover
// może być otwarty naraz (każdy Popover zarządza swoim stanem niezależnie).
const noteSaveTimers = {}

function cancelNoteTimer(klucz) {
  if (noteSaveTimers[klucz]) {
    clearTimeout(noteSaveTimers[klucz])
    delete noteSaveTimers[klucz]
  }
}

// Jedyne miejsce, które faktycznie woła `volteo_podzadania_set` — zapis
// optymistyczny z rollbackiem, wzorzec `setVerdict()` z `AudytTab.vue`
// (~l.892): snapshot mapy PRZED optymistyczną podmianą (żeby błąd cofał do
// dokładnie tego, co było na ekranie, nie do tego, czym stała się mapa po
// optymistycznej zmianie), po odpowiedzi CAŁA mapa zastąpiona autorytatywnym
// `res.stan_mapa` (serwer nadpisuje cały wpis, nie łata go — stąd
// `buildPodzadaniePayload` zawsze wysyła KOMPLET bieżącej daty/notatki, nie
// tylko zmienione pole). Nigdy `resource.reload()` — ten sam race co przy
// statusie rurociągu (patrz nagłówek pliku).
async function persist(klucz, { stan, data, note, zData }) {
  if (!editable.value || busyZadania[klucz]) return

  const payload = buildPodzadaniePayload({ zadanie: klucz, stan, data, note, zData })
  busyZadania[klucz] = true
  const before = mapaZadan.value
  mapaZadan.value = applyOptimistic(before, klucz, entryFromPayload(payload))

  try {
    const res = await call('crm.api.pipeline.volteo_podzadania_set', {
      deal: props.dealId,
      ...payload,
    })
    mapaZadan.value = parsePodzadania(res?.stan_mapa)
  } catch (err) {
    mapaZadan.value = before
    toast.error(extractErrorMessage(err))
  } finally {
    busyZadania[klucz] = false
  }
}

// Przycisk stanu (albo "Wyczyść", `stan === 'brak'`) — zapis NATYCHMIAST,
// zawsze z bieżącą datą/notatką z formularza (draft, jeśli edytowany, inaczej
// to, co już potwierdził serwer), bo zapis nadpisuje cały wpis. "Wyczyść"
// dodatkowo czyści draft i ewentualny debounce notatki w locie — po
// wyczyszczeniu wpisu po stronie serwera nie ma sensu wysłać za chwilę
// spóźnioną notatkę, która odtworzyłaby wpis.
function ustawStan(klucz, stan) {
  const def = etapZadania.value.find((d) => d.klucz === klucz)
  if (!def) return
  if (stan === 'brak') {
    delete draftZadan[klucz]
    cancelNoteTimer(klucz)
  }
  persist(klucz, { stan, data: formData(klucz), note: formNote(klucz), zData: def.z_data })
}

// Zmiana daty: jeśli zadanie ma już stan inny niż "brak", zapis natychmiast
// (z bieżącą notatką — kompletny wpis, jak wyżej). Jeśli stan to "brak", nie
// ma po stronie serwera czego nadpisać datą — patrz komentarz przy
// `draftZadan` powyżej — więc data zostaje wyłącznie lokalnie i pojedzie
// razem z pierwszym ustawieniem stanu.
function ustawData(klucz, data) {
  draftZadan[klucz] = { ...draftZadan[klucz], data }

  const aktualny = stanFor(mapaZadan.value, klucz)
  if (aktualny === 'brak') return

  const def = etapZadania.value.find((d) => d.klucz === klucz)
  if (!def) return
  persist(klucz, { stan: aktualny, data, note: formNote(klucz), zData: def.z_data })
}

// Notatka: debounce 500ms zamiast zapisu na każde naciśnięcie klawisza (ta
// sama logika "brak = tylko draft" co dla daty). Stan jest odczytywany
// PONOWNIE wewnątrz timera (nie zamykany przez `aktualny` z momentu wpisu),
// bo w ciągu tych 500ms użytkownik mógł już nacisnąć przycisk stanu — ten
// zapis idzie osobno i natychmiast, więc odroczony zapis notatki musi widzieć
// stan, jaki jest FAKTYCZNIE w chwili odpalenia, nie w chwili wpisania znaku.
function ustawNotatka(klucz, note) {
  const truncated = typeof note === 'string' ? note.slice(0, 500) : ''
  draftZadan[klucz] = { ...draftZadan[klucz], note: truncated }

  if (stanFor(mapaZadan.value, klucz) === 'brak') return

  const def = etapZadania.value.find((d) => d.klucz === klucz)
  if (!def) return

  cancelNoteTimer(klucz)
  noteSaveTimers[klucz] = setTimeout(() => {
    delete noteSaveTimers[klucz]
    const aktualny = stanFor(mapaZadan.value, klucz)
    if (aktualny === 'brak') return // wyczyszczone w międzyczasie — nic do zapisania
    persist(klucz, { stan: aktualny, data: formData(klucz), note: truncated, zData: def.z_data })
  }, 500)
}

function extractErrorMessage(err) {
  try {
    if (err && err._server_messages) {
      const msgs = JSON.parse(err._server_messages)
      if (msgs && msgs.length) {
        const first = JSON.parse(msgs[0])
        return first.message || __('Wystąpił błąd - spróbuj ponownie')
      }
    }
    if (err && err.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || __('Wystąpił błąd - spróbuj ponownie')
    }
    if (err && err.message) return err.message
  } catch (e) {
    /* fall through */
  }
  return __('Wystąpił błąd - spróbuj ponownie')
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

// `min-h-10` (2.5rem = 40px) + bumped `px-3 py-2 gap-2` on mobile give the
// pill (both the read-only div and the popover-trigger button below) a
// >=40px touch target regardless of label length — b49 F4. `sm:` reverts
// every one of those to the ORIGINAL desktop values (`min-h-0`/`px-2.5`/
// `py-1.5`/`gap-1.5`), so desktop stays pixel-identical to pre-F4: this is
// the padding-only approach the issue asks for, not an icon/text resize.
function pillClass(stan) {
  const meta = STAN_META[stan] || STAN_META.brak
  const theme = PILL_THEME_CLASSES[meta.theme] || PILL_THEME_CLASSES.gray
  const border = meta.muted ? 'border-dashed opacity-70' : 'border-solid'
  return `inline-flex min-h-10 items-center gap-2 rounded-md border px-3 py-2 text-xs sm:min-h-0 sm:gap-1.5 sm:px-2.5 sm:py-1.5 ${theme} ${border}`
}
</script>
