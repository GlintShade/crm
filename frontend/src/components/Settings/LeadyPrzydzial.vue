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
            'Ręczny przydział paczki nietkniętych leadów D2D jednemu handlowcowi, opcjonalnie zawężony do województwa, powiatu lub miasta. Liczniki poniżej informują — nie blokują przydziału.',
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

    <!-- Assignment form -->
    <div class="flex flex-col gap-4 px-2">
      <div class="text-base-semibold">{{ __('Nowy przydział') }}</div>
      <div class="grid grid-cols-2 gap-4 max-w-2xl">
        <FormControl
          v-model="form.handlowiec"
          type="select"
          :label="__('Handlowiec')"
          :options="handlowcyOptions"
          :disabled="assignResource.loading"
        />
        <FormControl
          v-model="form.ilosc"
          type="number"
          :label="__('Ilość')"
          :min="ILOSC_MIN"
          :max="ILOSC_MAX"
          :placeholder="String(ILOSC_DOMYSLNA)"
          :disabled="assignResource.loading"
        />
        <FormControl
          v-model="form.wojewodztwo"
          type="select"
          :label="__('Województwo')"
          :options="wojewodztwoOptions"
          :disabled="assignResource.loading"
        />
        <FormControl
          v-model="form.powiat"
          type="select"
          :label="__('Powiat')"
          :description="__('Filtr niezależny od województwa (pula jest agregowana globalnie).')"
          :options="powiatOptions"
          :disabled="assignResource.loading"
        />
        <FormControl
          v-model="form.miasto"
          type="text"
          :label="__('Miasto')"
          placeholder="Gdańsk"
          :disabled="assignResource.loading"
        />
      </div>
      <ErrorMessage class="max-w-2xl" :message="assignError" />
      <div>
        <Button
          :label="__('Przydziel')"
          variant="solid"
          icon-left="user-check"
          :loading="assignResource.loading"
          @click="submitAssign"
        />
      </div>
    </div>

    <div class="border-t mx-2" />

    <!-- Rep table -->
    <div class="flex flex-col gap-4 px-2">
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
              <th class="px-4 py-2.5 text-right font-medium">{{ __('Skonwertowane') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="rep in state.handlowcy" :key="rep.user" class="border-t border-outline-gray-1">
              <td class="px-4 py-2.5 text-ink-gray-8">{{ rep.full_name || rep.user }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ rep.przydzielone }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ rep.nietkniete }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ rep.w_toku }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ rep.przerobione }}</td>
              <td class="px-4 py-2.5 text-right text-ink-gray-8">{{ rep.skonwertowane }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { createResource, toast, FormControl, Button, ErrorMessage } from 'frappe-ui'

// Reactive state declares every key up front and is always replaced with a
// fresh value on update — never gated on key presence (see CLAUDE.md:
// hasOwnProperty on a reactive() object breaks Vue's dependency tracking
// and froze the CP admin panel for its entire lifetime).
const state = reactive({
  handlowcy: [],
  pula: { razem: 0, wojewodztwa: {}, powiaty: {} },
})
const listError = ref('')

const listResource = createResource({
  url: 'crm.api.volteo_leady.statystyki',
  auto: true,
  onSuccess: (data) => {
    state.handlowcy = data?.handlowcy || []
    state.pula = data?.pula || { razem: 0, wojewodztwa: {}, powiaty: {} }
    listError.value = ''
  },
  onError: (err) => {
    listError.value = err?.messages?.[0] || __('Nie udało się wczytać statystyk leadów')
  },
})

// Mirrors crm.api.volteo_leady.ILOSC_MIN/MAX/DOMYSLNA — kept in sync by hand,
// the server is still the source of truth and clamps independently.
const ILOSC_MIN = 1
const ILOSC_MAX = 100
const ILOSC_DOMYSLNA = 20

function emptyForm() {
  return {
    handlowiec: '',
    wojewodztwo: '',
    powiat: '',
    miasto: '',
    ilosc: ILOSC_DOMYSLNA,
  }
}

const form = reactive(emptyForm())
const assignError = ref('')

const handlowcyOptions = computed(() => [
  { label: __('Wybierz handlowca'), value: '' },
  ...state.handlowcy.map((rep) => ({ label: rep.full_name || rep.user, value: rep.user })),
])

// Powiaty are aggregated globally without a voivodeship pairing (known API
// limitation, see ops#24/#25) — this select is a plain independent filter,
// not cascaded from the voivodeship select above. Names can repeat across
// voivodeships; the server-side filter still ANDs both fields when both are
// set, so the combination is still meaningful even without cascading.
function liczbaOpcji(dict) {
  return Object.entries(dict || {})
    .sort((a, b) => b[1] - a[1])
    .map(([klucz, ile]) => ({ label: `${klucz} (${ile})`, value: klucz }))
}

const wojewodztwoOptions = computed(() => [
  { label: __('Wszystkie województwa'), value: '' },
  ...liczbaOpcji(state.pula.wojewodztwa),
])

const powiatOptions = computed(() => [
  { label: __('Wszystkie powiaty'), value: '' },
  ...liczbaOpcji(state.pula.powiaty),
])

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
    // Re-fetch so per-rep counters and the pool pill reflect the new state —
    // the server owns the truth, nothing here is computed optimistically.
    listResource.reload()
  },
  onError: (err) => {
    assignError.value = err?.messages?.[0] || __('Nie udało się przydzielić leadów')
  },
})

function submitAssign() {
  assignError.value = ''

  if (!form.handlowiec) {
    assignError.value = __('Wybierz handlowca')
    return
  }

  // Deliberately no client-side block on pool size vs. requested ilość
  // (owner decision, issue #25): the button stays active and the counters
  // above are informational only — the server just returns fewer leads than
  // requested if the filtered pool is smaller.
  assignResource.submit()
}
</script>
