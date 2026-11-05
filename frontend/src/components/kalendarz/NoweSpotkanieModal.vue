<!--
  Nowe spotkanie (kalendarz, ops#318): wybór leada (tylko widoczne dla
  wołającego, zwykłe uprawnienia), data, godzina co 30 min i, dla zakresu
  "wszyscy", handlowiec. Zapis przez crm.api.kalendarz.ustaw_termin.
  Grafik dostępności (b82): dostępni w wybranym terminie na górze listy
  (decyzja 10), termin poza grafikiem daje ostrzeżenie i "Zapisz mimo to"
  (decyzja 6, bez blokady).
  b84 (ops#332): lista leadów z crm.api.kalendarz.leady_do_spotkania (bez
  leadów innego handlowca, przełącznik "Tylko leady z Facebooka") i pole
  "Notatka", zapisywane jako komentarz leada razem z terminem.
-->
<template>
  <Dialog v-model:open="otwarte" :title="__('Nowe spotkanie')" size="md">
    <template #default>
      <div class="flex flex-col gap-4">
        <div>
          <label class="mb-1 block text-xs text-ink-gray-5">{{
            __('Lead')
          }}</label>
          <FormControl
            v-model="tylkoFb"
            type="checkbox"
            class="mb-2"
            :label="__('Wyświetl tylko leady z reklam')"
            data-testid="kalendarz-tylko-fb"
          />
          <Autocomplete
            :model-value="lead"
            :options="opcjeLeadowLista"
            :filterable="false"
            :placeholder="__('Szukaj leada')"
            @update:model-value="zmienLead"
            @update:query="zmienTekst"
          >
            <template #item-label="{ option }">
              <div class="flex flex-col gap-1">
                <div class="flex-1 truncate font-semibold text-ink-gray-7">
                  {{ option.label }}
                </div>
                <div
                  v-if="option.description"
                  class="flex-1 truncate text-sm text-ink-gray-5"
                >
                  {{ option.description }}
                </div>
              </div>
            </template>
          </Autocomplete>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="mb-1 block text-xs text-ink-gray-5">{{
              __('Dzień spotkania')
            }}</label>
            <DatePicker
              v-model="data"
              format="DD.MM.YYYY"
              placeholder="DD.MM.RRRR"
              data-testid="kalendarz-dzien"
            />
          </div>
          <FormControl
            v-model="godzina"
            type="select"
            :label="__('Godzina')"
            :options="opcjeGodzinSelect"
          />
        </div>
        <FormControl
          v-if="zakres === 'wszyscy'"
          v-model="handlowiec"
          type="select"
          :label="__('Handlowiec')"
          :options="opcjeHandlowcow"
        />
        <FormControl
          v-model="notatka"
          type="textarea"
          :rows="3"
          :label="__('Notatka')"
          :placeholder="__('Opcjonalnie, trafi do komentarzy leada')"
          data-testid="kalendarz-notatka"
        />
        <p v-if="podpowiedz" class="text-xs text-ink-amber-8">
          {{ podpowiedz }}
        </p>
        <p
          v-if="ostrzezenie"
          class="text-xs text-ink-amber-8"
          data-testid="kalendarz-poza-grafikiem"
        >
          <span class="font-semibold">{{ __('Uwaga:') }}</span>
          {{ ostrzezenie }}
        </p>
        <ErrorMessage :message="blad" />
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button :label="__('Anuluj')" @click="otwarte = false" />
        <Button
          variant="solid"
          :label="ostrzezenie ? __('Zapisz mimo to') : __('Zapisz')"
          :loading="zapisuje"
          @click="zapisz"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import {
  Button,
  Dialog,
  DatePicker,
  ErrorMessage,
  FormControl,
  call,
  toast,
} from 'frappe-ui'
import Autocomplete from '@/components/frappe-ui/Autocomplete.vue'
import { watchDebounced } from '@vueuse/core'
import { leadDozwolony, opcjeLeadow } from '@/utils/kalendarzLeady'
import {
  opcjeGodzin,
  ostrzezenieGrafiku,
  podpowiedzDnia,
  posortujWgDostepnosci,
  terminDoApi,
} from '@/utils/kalendarz'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // Wstępne wartości: { data, godzina, handlowiec }
  poczatkowe: { type: Object, default: () => ({}) },
  zakres: { type: String, default: 'wszyscy' },
  handlowcy: { type: Array, default: () => [] },
  spotkania: { type: Object, default: () => ({}) },
  // Grafik dostępności { user: { data: okna } | null }; null = wyłączony.
  dostepnosc: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'zapisano'])

const otwarte = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const lead = ref('')
const data = ref('')
const godzina = ref('10:00')
const handlowiec = ref('')
const zapisuje = ref(false)
const blad = ref('')
const notatka = ref('')
const tylkoFb = ref(true)
const tekst = ref('')
const wierszeLeadow = ref([])
// Wybrana opcja (label, lead_owner): pole pokazuje nazwę także wtedy, gdy
// lead wypadnie z bieżącego wyniku wyszukiwania.
const wybranaOpcja = ref(null)
const opcjeLeadowLista = computed(() =>
  opcjeLeadow(wierszeLeadow.value, wybranaOpcja.value),
)

const opcjeGodzinSelect = opcjeGodzin().map((g) => ({ label: g, value: g }))
const opcjeHandlowcow = computed(() => [
  { label: __('Bez zmiany handlowca'), value: '' },
  ...posortujWgDostepnosci(
    props.handlowcy,
    props.dostepnosc,
    data.value,
    godzina.value,
  ).map((h) => ({
    label: h.dostepny
      ? h.full_name
      : `${h.full_name} (${__('poza grafikiem')})`,
    value: h.user,
  })),
])

// Handlowiec, którego dotyczy termin: wybrany, a handlowiec na własnym
// kalendarzu (zakres "wlasny") to zawsze on sam.
const handlowiecTerminu = computed(() => {
  if (handlowiec.value)
    return props.handlowcy.find((x) => x.user === handlowiec.value)
  return props.zakres === 'wlasny' ? props.handlowcy[0] : null
})

const ostrzezenie = computed(() => {
  const h = handlowiecTerminu.value
  if (!h || !props.dostepnosc) return ''
  return ostrzezenieGrafiku(
    h.full_name,
    props.dostepnosc[h.user],
    data.value,
    godzina.value,
  )
})

watch(
  () => props.modelValue,
  (otwarty) => {
    if (!otwarty) return
    lead.value = ''
    blad.value = ''
    data.value = props.poczatkowe.data || ''
    godzina.value = props.poczatkowe.godzina || '10:00'
    handlowiec.value = props.poczatkowe.handlowiec || ''
    notatka.value = ''
    tylkoFb.value = true
    tekst.value = ''
    wybranaOpcja.value = null
    wierszeLeadow.value = []
    zaladujLeady()
  },
)

// Handlowiec, po którym serwer filtruje listę (zakres "wlasny": serwer sam
// bierze zalogowanego).
const handlowiecFiltra = computed(() =>
  props.zakres === 'wszyscy' ? handlowiec.value : '',
)

let numerZapytania = 0
async function zaladujLeady() {
  const numer = ++numerZapytania
  try {
    const wynik = await call('crm.api.kalendarz.leady_do_spotkania', {
      tekst: tekst.value,
      handlowiec: handlowiecFiltra.value || null,
      tylko_fb: tylkoFb.value ? 1 : 0,
    })
    if (numer === numerZapytania) wierszeLeadow.value = wynik || []
  } catch {
    if (numer === numerZapytania) wierszeLeadow.value = []
  }
}

function zmienTekst(wartosc) {
  tekst.value = wartosc || ''
}

watchDebounced(tekst, () => props.modelValue && zaladujLeady(), {
  debounce: 300,
})

// Zmiana handlowca lub przełącznika: odśwież listę; wybrany lead innego
// handlowca przestaje być dozwolony, więc wybór jest czyszczony.
watch([handlowiecFiltra, tylkoFb], () => {
  if (!props.modelValue) return
  if (
    wybranaOpcja.value &&
    !leadDozwolony(wybranaOpcja.value.lead_owner, handlowiecFiltra.value)
  ) {
    lead.value = ''
    wybranaOpcja.value = null
  }
  zaladujLeady()
})

const podpowiedz = computed(() => {
  const h = props.handlowcy.find((x) => x.user === handlowiec.value)
  if (!h || !data.value) return ''
  return podpowiedzDnia(h.full_name, props.spotkania[h.user], data.value)
})

function zmienLead(wartosc) {
  // Autocomplete oddaje całą opcję albo null (przycisk czyszczenia).
  const nazwa = typeof wartosc === 'string' ? wartosc : wartosc?.value || ''
  lead.value = nazwa
  wybranaOpcja.value = !nazwa
    ? null
    : typeof wartosc === 'object'
      ? wartosc
      : opcjeLeadowLista.value.find((o) => o.value === nazwa) || null
  if (!lead.value || handlowiec.value || props.zakres !== 'wszyscy') return
  const wlasciciel = wybranaOpcja.value?.lead_owner
  if (wlasciciel && props.handlowcy.some((h) => h.user === wlasciciel)) {
    handlowiec.value = wlasciciel
  }
}

async function zapisz() {
  blad.value = ''
  const termin = terminDoApi(data.value, godzina.value)
  if (!lead.value) {
    blad.value = __('Wybierz leada.')
    return
  }
  if (!termin) {
    blad.value = __('Podaj datę i godzinę.')
    return
  }
  zapisuje.value = true
  try {
    await call('crm.api.kalendarz.ustaw_termin', {
      lead: lead.value,
      termin,
      handlowiec:
        props.zakres === 'wszyscy' && handlowiec.value
          ? handlowiec.value
          : null,
      notatka: notatka.value.trim() ? notatka.value : null,
    })
    toast.success(__('Spotkanie zapisane'))
    otwarte.value = false
    emit('zapisano')
  } catch (e) {
    blad.value =
      e?.messages?.[0] || e?.message || __('Nie udało się zapisać spotkania.')
  } finally {
    zapisuje.value = false
  }
}
</script>
