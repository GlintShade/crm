<!--
  Nowe spotkanie (kalendarz, ops#318): wybór leada (tylko widoczne dla
  wołającego, zwykłe uprawnienia), data, godzina co 30 min i, dla zakresu
  "wszyscy", handlowiec. Zapis przez crm.api.kalendarz.ustaw_termin.
  Grafik dostępności (b82): dostępni w wybranym terminie na górze listy
  (decyzja 10), termin poza grafikiem daje ostrzeżenie i "Zapisz mimo to"
  (decyzja 6, bez blokady).
-->
<template>
  <Dialog v-model:open="otwarte" :title="__('Nowe spotkanie')" size="md">
    <template #default>
      <div class="flex flex-col gap-4">
        <div>
          <label class="mb-1 block text-xs text-ink-gray-5">{{
            __('Lead')
          }}</label>
          <Link
            doctype="CRM Lead"
            :model-value="lead"
            :placeholder="__('Szukaj leada')"
            @update:model-value="zmienLead"
          />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <FormControl
            v-model="data"
            type="date"
            :label="__('Dzień spotkania')"
          />
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
  ErrorMessage,
  FormControl,
  call,
  toast,
} from 'frappe-ui'
import Link from '@/components/Controls/Link.vue'
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
  },
)

const podpowiedz = computed(() => {
  const h = props.handlowcy.find((x) => x.user === handlowiec.value)
  if (!h || !data.value) return ''
  return podpowiedzDnia(h.full_name, props.spotkania[h.user], data.value)
})

async function zmienLead(wartosc) {
  lead.value = wartosc || ''
  if (!lead.value || handlowiec.value || props.zakres !== 'wszyscy') return
  try {
    const odp = await call('frappe.client.get_value', {
      doctype: 'CRM Lead',
      filters: { name: lead.value },
      fieldname: 'lead_owner',
    })
    const wlasciciel = odp?.lead_owner
    if (
      wlasciciel &&
      props.handlowcy.some((h) => h.user === wlasciciel) &&
      !handlowiec.value
    ) {
      handlowiec.value = wlasciciel
    }
  } catch (e) {
    // Podpowiedź właściciela jest opcjonalna, błąd odczytu nie blokuje formularza.
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
