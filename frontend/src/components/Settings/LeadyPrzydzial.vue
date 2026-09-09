<template>
  <div class="flex h-full flex-col gap-8 p-6 text-ink-gray-8 overflow-y-auto">
    <!-- Header -->
    <div class="flex flex-col gap-1 px-2 pt-2">
      <h2 class="flex items-center gap-2 text-2xl-semibold leading-none h-5">
        {{ __('Przydział leadów') }}
      </h2>
      <p class="text-p-base text-ink-gray-6">
        {{
          __(
            'Ręczny przydział paczki nietkniętych leadów D2D jednemu handlowcowi albo osobie CC, opcjonalnie zawężony do województwa, powiatu lub miasta. Liczniki poniżej informują, nie blokują przydziału.',
          )
        }}
      </p>
      <div class="mt-1">
        <span
          class="inline-flex items-center rounded-full px-2.5 py-1 text-xs-medium bg-surface-blue-2 text-ink-blue-3"
        >
          {{ __('Pula nietkniętych: {0}', [state.pula.razem]) }}
        </span>
      </div>
    </div>

    <ErrorMessage class="mx-2" :message="listError" />

    <!-- Mode switch -->
    <div class="px-2">
      <TabButtons v-model="tryb" :options="trybOptions" />
    </div>

    <!-- Assignment form -->
    <div class="flex flex-col gap-4 px-2">
      <div class="text-base-semibold">{{ __('Nowy przydział') }}</div>
      <div class="grid grid-cols-2 gap-4 max-w-2xl">
        <FormControl
          v-if="tryb === 'handlowiec'"
          v-model="form.handlowiec"
          type="select"
          :label="__('Handlowiec')"
          :options="handlowcyOptions"
          :disabled="aktywnyAssignResource.loading"
        />
        <FormControl
          v-else
          v-model="form.cc"
          type="select"
          :label="__('Osoba CC')"
          :options="ccOptions"
          :disabled="aktywnyAssignResource.loading"
        />
        <FormControl
          v-model="form.ilosc"
          type="number"
          :label="__('Ilość')"
          :min="ILOSC_MIN"
          :max="iloscMax"
          :placeholder="String(ILOSC_DOMYSLNA)"
          :disabled="aktywnyAssignResource.loading"
        />
        <FormControl
          v-model="form.wojewodztwo"
          type="select"
          :label="__('Województwo')"
          :options="wojewodztwoOptions"
          :disabled="aktywnyAssignResource.loading"
        />
        <FormControl
          v-model="form.powiat"
          type="select"
          :label="__('Powiat')"
          :description="
            form.wojewodztwo
              ? __('Zawężone do powiatów występujących w wybranym województwie.')
              : __('Wybierz województwo, aby zawęzić listę powiatów.')
          "
          :options="powiatOptions"
          :disabled="aktywnyAssignResource.loading || powiatyResource.loading"
        />
        <FormControl
          v-model="form.miasto"
          type="text"
          :label="__('Miasto')"
          placeholder="Gdańsk"
          :disabled="aktywnyAssignResource.loading"
        />
      </div>
      <ErrorMessage class="max-w-2xl" :message="assignError" />
      <div>
        <Button
          :label="tryb === 'handlowiec' ? __('Przydziel') : __('Przydziel do CC')"
          variant="solid"
          icon-left="user-check"
          :loading="aktywnyAssignResource.loading"
          @click="submitAssign"
        />
      </div>
    </div>

    <div class="border-t mx-2" />

    <!-- Rep table -->
    <div v-if="tryb === 'handlowiec'" class="flex flex-col gap-4 px-2">
      <div class="text-base-semibold">{{ __('Handlowcy') }}</div>

      <div
        v-if="listResource.loading && !state.handlowcy.length"
        class="text-p-sm text-ink-gray-5"
      >
        {{ __('Wczytywanie…') }}
      </div>
      <div
        v-else-if="!state.handlowcy.length"
        class="text-p-sm text-ink-gray-5"
      >
        {{ __('Brak aktywnych handlowców z rolą Volteo D2D Sales.') }}
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full border-collapse text-sm">
          <thead>
            <tr class="bg-surface-gray-2 text-ink-gray-5">
              <th class="px-4 py-2.5 text-left font-medium">{{ __('Handlowiec') }}</th>
              <th class="px-4 py-2.5 text-right font-medium">{{ __('Przydzielone') }}</th>
              <th class="px-4 py-2.5 text-right font-medium">{{ __('Nietknięte') }}</th>
              <th class="px-4 py-2.5 text-right font-medium">{{ __('W toku') }}</th>
              <th class="px-4 py-2.5 text-right font-medium">{{ __('Przerobione') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="rep in state.handlowcy" :key="rep.user" class="border-t border-outline-gray-1">
              <td class="px-4 py-2.5 text-ink-gray-8">{{ rep.full_name || rep.user }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ rep.przydzielone }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ rep.nietkniete }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ rep.w_toku }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ rep.przerobione }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- CC table -->
    <div v-else class="flex flex-col gap-4 px-2">
      <div class="text-base-semibold">{{ __('Osoby CC') }}</div>

      <div
        v-if="listResource.loading && !state.cc.length"
        class="text-p-sm text-ink-gray-5"
      >
        {{ __('Wczytywanie…') }}
      </div>
      <div
        v-else-if="!state.cc.length"
        class="text-p-sm text-ink-gray-5"
      >
        {{ __('Brak aktywnych osób z rolą Volteo Call Center.') }}
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full border-collapse text-sm">
          <thead>
            <tr class="bg-surface-gray-2 text-ink-gray-5">
              <th class="px-4 py-2.5 text-left font-medium">{{ __('CC') }}</th>
              <th class="px-4 py-2.5 text-right font-medium">{{ __('Przydzielone') }}</th>
              <th class="px-4 py-2.5 text-right font-medium">{{ __('Obdzwonione') }}</th>
              <th class="px-4 py-2.5 text-right font-medium">{{ __('Umówione') }}</th>
              <th class="px-4 py-2.5 text-right font-medium">{{ __('Przekazane') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="osoba in state.cc" :key="osoba.user" class="border-t border-outline-gray-1">
              <td class="px-4 py-2.5 text-ink-gray-8">{{ osoba.full_name || osoba.user }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ osoba.przydzielone }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ osoba.obdzwonione }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ osoba.umowione }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ osoba.przekazane }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { createResource, toast, FormControl, Button, ErrorMessage, TabButtons } from 'frappe-ui'

// Reactive state declares every key up front and is always replaced with a
// fresh value on update, never gated on key presence (see CLAUDE.md:
// hasOwnProperty on a reactive() object breaks Vue's dependency tracking
// and froze the CP admin panel for its entire lifetime).
const state = reactive({
  handlowcy: [],
  cc: [],
  pula: { razem: 0, wojewodztwa: {}, powiaty: {} },
})
const listError = ref('')

const listResource = createResource({
  url: 'crm.api.volteo_leady.statystyki',
  auto: true,
  onSuccess: (data) => {
    state.handlowcy = data?.handlowcy || []
    state.cc = data?.cc || []
    state.pula = data?.pula || { razem: 0, wojewodztwa: {}, powiaty: {} }
    listError.value = ''
  },
  onError: (err) => {
    listError.value = err?.messages?.[0] || __('Nie udało się wczytać statystyk leadów')
  },
})

// Mirrors crm.api.volteo_leady.ILOSC_MIN/MAX/DOMYSLNA (tryb handlowiec) i
// LIMIT_PRZYDZIAL_CC (tryb CC) - kept in sync by hand, the server is still
// the source of truth and clamps independently.
const ILOSC_MIN = 1
const ILOSC_MAX = 100
const ILOSC_DOMYSLNA = 20
const LIMIT_PRZYDZIAL_CC = 2000

// Tryb przełącznika "Handlowiec / CC" u góry panelu (issue #104). Oba tryby
// dzielą to samo `form` (wojewodztwo/powiat/miasto/ilosc) - tylko pole osoby
// docelowej (handlowiec vs cc) i wywoływany endpoint się różnią.
const tryb = ref('handlowiec')
const trybOptions = [
  { label: __('Handlowiec'), value: 'handlowiec' },
  { label: __('CC'), value: 'cc' },
]

function emptyForm() {
  return {
    handlowiec: '',
    cc: '',
    wojewodztwo: '',
    powiat: '',
    miasto: '',
    ilosc: ILOSC_DOMYSLNA,
  }
}

const form = reactive(emptyForm())
const assignError = ref('')

const iloscMax = computed(() => (tryb.value === 'cc' ? LIMIT_PRZYDZIAL_CC : ILOSC_MAX))

const handlowcyOptions = computed(() => [
  { label: __('Wybierz handlowca'), value: '' },
  ...state.handlowcy.map((rep) => ({ label: rep.full_name || rep.user, value: rep.user })),
])

const ccOptions = computed(() => [
  { label: __('Wybierz osobę CC'), value: '' },
  ...state.cc.map((osoba) => ({ label: osoba.full_name || osoba.user, value: osoba.user })),
])

function liczbaOpcji(dict) {
  return Object.entries(dict || {})
    .sort((a, b) => b[1] - a[1])
    .map(([klucz, ile]) => ({ label: `${klucz} (${ile})`, value: klucz }))
}

const wojewodztwoOptions = computed(() => [
  { label: __('Wszystkie województwa'), value: '' },
  ...liczbaOpcji(state.pula.wojewodztwa),
])

// Kaskada powiatu od województwa (issue #104): gdy województwo jest wybrane,
// lista powiatów pochodzi z `crm.api.volteo_leady.powiaty` (zawężona do tego
// województwa, bez liczników). Bez wybranego województwa wraca stara,
// niezawężona pula agregowana globalnie (`state.pula.powiaty`, z licznikami)
// - poprzedni jedyny widok tego selecta.
const powiatyDlaWojewodztwa = ref([])
const powiatyResource = createResource({
  url: 'crm.api.volteo_leady.powiaty',
  auto: false,
  onSuccess: (data) => {
    powiatyDlaWojewodztwa.value = data || []
  },
})

watch(
  () => form.wojewodztwo,
  (wojewodztwo) => {
    // Poprzednio wybrany powiat może nie istnieć w nowym województwie -
    // reset, żeby przydział nigdy nie poszedł z cichym, niepasującym filtrem.
    form.powiat = ''
    powiatyDlaWojewodztwa.value = []
    if (wojewodztwo) {
      powiatyResource.submit({ wojewodztwo })
    }
  },
)

const powiatOptions = computed(() => {
  if (form.wojewodztwo) {
    return [
      { label: __('Wszystkie powiaty'), value: '' },
      ...powiatyDlaWojewodztwa.value.map((powiat) => ({ label: powiat, value: powiat })),
    ]
  }
  return [
    { label: __('Wszystkie powiaty'), value: '' },
    ...liczbaOpcji(state.pula.powiaty),
  ]
})

const assignResource = createResource({
  url: 'crm.api.volteo_leady.przydziel',
  makeParams: () => ({
    handlowiec: form.handlowiec,
    ilosc: form.ilosc || ILOSC_DOMYSLNA,
    wojewodztwo: form.wojewodztwo,
    powiat: form.powiat,
    miasto: form.miasto.trim(),
  }),
  onSuccess: (data) => {
    assignError.value = ''
    toast.success(
      __('Przydzielono {0} leadów. Pozostało {1} w puli wg wybranych filtrów.', [
        data.przydzielono,
        data.pozostalo_w_puli,
      ]),
    )
    // Re-fetch so per-rep counters and the pool pill reflect the new state,
    // the server owns the truth, nothing here is computed optimistically.
    listResource.reload()
  },
  onError: (err) => {
    assignError.value = err?.messages?.[0] || __('Nie udało się przydzielić leadów')
  },
})

// Filtry budowane dokładnie jak `przydziel` buduje swoje warunki SQL (patrz
// crm.api.volteo_leady.przydziel), tylko jako filters dict dla przydziel_cc:
// status literalnie "Nowy" (jedyny status typu Open w słowniku CC, patrz
// ops/crm-leady-call-center.py) i custom_cc puste (operator "is"/"not set",
// ten sam wzorzec co gdzie indziej w forku, np. crm/api/contact.py), żeby nie
// przydzielać CC leadów już obsłużonych albo już przypisanych innej osobie.
function zbudujFiltryCc() {
  const filters = {
    status: 'Nowy',
    custom_cc: ['is', 'not set'],
  }
  if (form.wojewodztwo) filters.custom_voivodeship = form.wojewodztwo
  if (form.powiat) filters.custom_powiat = form.powiat
  if (form.miasto.trim()) filters.custom_install_city = form.miasto.trim()
  return filters
}

const assignCcResource = createResource({
  url: 'crm.api.volteo_leady.przydziel_cc',
  makeParams: () => ({
    cc: form.cc,
    filters: JSON.stringify(zbudujFiltryCc()),
    ilosc: form.ilosc || ILOSC_DOMYSLNA,
  }),
  onSuccess: (data) => {
    assignError.value = ''
    const czesci = [__('Przydzielono: {0}', [data.przydzielono])]
    if (data.pominieto) {
      czesci.push(__('Pominięto (już przypisane): {0}', [data.pominieto]))
    }
    if (data.nieznane) {
      czesci.push(__('Nieznane: {0}', [data.nieznane]))
    }
    toast.success(czesci.join(', '))
    listResource.reload()
  },
  onError: (err) => {
    assignError.value = err?.messages?.[0] || __('Nie udało się przydzielić leadów do CC')
  },
})

// Resource aktywny w bieżącym trybie - jedyne miejsce, które decyduje, który
// z dwóch createResource ma :loading/:disabled na formularzu i przycisku.
const aktywnyAssignResource = computed(() =>
  tryb.value === 'handlowiec' ? assignResource : assignCcResource,
)

function submitAssign() {
  assignError.value = ''

  if (tryb.value === 'handlowiec') {
    if (!form.handlowiec) {
      assignError.value = __('Wybierz handlowca')
      return
    }
    // Deliberately no client-side block on pool size vs. requested ilość
    // (owner decision, issue #25): the button stays active and the counters
    // above are informational only, the server just returns fewer leads
    // than requested if the filtered pool is smaller. Tryb handlowca:
    // semantyka bez zmian (issue #104).
    assignResource.submit()
    return
  }

  if (!form.cc) {
    assignError.value = __('Wybierz osobę CC')
    return
  }
  assignCcResource.submit()
}
</script>
