<!--
  Karta ręcznego statusu na zakładkach OSD/Dotacja (ops#202), wzorowana 1:1
  na dropdownzie statusu finansowania formularza kredytowego (KredytTab.vue,
  ops#197): kolorowy Dropdown dla backoffice/adminów (`isVolteoAdmin() ||
  isBackend()`), kolorowa plakietka (bez dropdownu, bez hover) dla
  handlowca i każdej innej roli. Zmianę statusu zapisuje wyłącznie
  `crm.api.osd_dotacja.ustaw_status` - ten komponent nigdy nie pisze
  bezpośrednio na `custom_status_osd`/`custom_status_dotacja`.

  Bez optymistycznej aktualizacji (kontrakt issue): po sukcesie tylko
  `dealDoc.reload()`, przycisk/plakietka pokazuje starą wartość aż serwer
  potwierdzi nową.

  Renderuje null, gdy szansa nie jest OZE - defensywna, redundantna kopia
  bramki, którą `Deal.vue`/`MobileDeal.vue` już stosują na poziomie
  warunku zakładki (`condition: () => OZE_RODZAJE.has(...)`), dokładnie tak
  jak `NotatkiStrumien.vue` sam się broni mimo że jego zakładki-gospodarze
  bywają gated inaczej. `czyOze` importowane z `@/utils/notatki` (issue W1/
  W2, ta sama paczka) - to samo źródło prawdy co `NotatkiStrumien.vue` już
  używa, nie osobna kopia predykatu.
-->
<template>
  <div v-if="ozeWidoczne" class="flex items-center justify-between gap-2 border-b px-4 py-3">
    <span class="text-base font-medium text-ink-gray-9">{{ __(etykietaKarty) }}</span>
    <Dropdown v-if="mozeEdytowac" :options="opcjeStatusu" placement="bottom-end">
      <template #default="{ open }">
        <Button
          :label="__(etykietaPrzycisku)"
          :iconRight="open ? 'chevron-up' : 'chevron-down'"
          :class="statusButtonClass(kolorObecny)"
          :disabled="ustawiajac"
        >
          <template #prefix>
            <IndicatorIcon :class="kolorObecny" />
          </template>
        </Button>
      </template>
    </Dropdown>
    <span
      v-else
      class="inline-flex items-center gap-1.5 rounded px-2 py-1 text-sm"
      :class="klasyPlakietki"
    >
      <IndicatorIcon :class="kolorObecny" />
      {{ __(etykietaPrzycisku) }}
    </span>
  </div>
</template>

<script setup>
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import { usersStore } from '@/stores/users'
import { parseColor } from '@/utils'
import { czyOze } from '@/utils/notatki'
import { statusButtonClass } from '@/utils/statusColors'
import { ETYKIETY, STATUSY, etykietaStatusu, kolorStatusu } from '@/utils/osdDotacja'
import { Button, Dropdown, call, getCachedDocumentResource, toast } from 'frappe-ui'
import { computed, h, ref } from 'vue'

const props = defineProps({
  dealId: { type: String, required: true },
  // "OSD" albo "Dotacja" - klucz stały per instancja, patrz
  // crm.volteo_osd_dotacja.ZAKLADKI.
  zakladka: { type: String, required: true },
})

// Lustro crm/volteo_osd_dotacja.py::POLE (fieldname pola Select na
// CRM Deal per zakladka) - `osdDotacja.js` celowo nie eksportuje tej
// mapy (patrz jej własny nagłówek), więc żyje lokalnie tutaj, jak
// `Deal.vue`'s own OZE_RODZAJE mirror.
const POLE = { OSD: 'custom_status_osd', Dotacja: 'custom_status_dotacja' }

const { isVolteoAdmin, isBackend } = usersStore()
const mozeEdytowac = computed(() => isVolteoAdmin() || isBackend())

const dealDoc = computed(() => getCachedDocumentResource('CRM Deal', props.dealId))
const ozeWidoczne = computed(() => czyOze(dealDoc.value?.doc?.custom_rodzaj_umowy))

const fieldname = computed(() => POLE[props.zakladka])
const wartoscObecna = computed(() => dealDoc.value?.doc?.[fieldname.value])

const etykietaKarty = computed(() => ETYKIETY[props.zakladka] || '')
const etykietaPrzycisku = computed(() => etykietaStatusu(props.zakladka, wartoscObecna.value))
const kolorObecny = computed(() => parseColor(kolorStatusu(props.zakladka, wartoscObecna.value)))

const klasyPlakietki = computed(() =>
  statusButtonClass(kolorObecny.value)
    .split(' ')
    .filter((klasa) => !klasa.startsWith('hover:'))
    .join(' '),
)

const ustawiajac = ref(false)

const opcjeStatusu = computed(() =>
  (STATUSY[props.zakladka] || []).map((s) => ({
    label: __(s),
    value: s,
    icon: () => h(IndicatorIcon, { class: parseColor(kolorStatusu(props.zakladka, s)) }),
    onClick: () => ustawStatus(s),
  })),
)

async function ustawStatus(s) {
  if (!props.dealId || ustawiajac.value) return
  if (s === wartoscObecna.value) return
  ustawiajac.value = true
  try {
    await call('crm.api.osd_dotacja.ustaw_status', {
      deal: props.dealId,
      zakladka: props.zakladka,
      status: s,
    })
    await dealDoc.value?.reload()
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    ustawiajac.value = false
  }
}

// Kopiowane 1:1 z tego samego wzorca w KredytTab.vue/UmowaTab.vue/inne -
// call() z frappe-ui zwraca błąd, którego `messages` niesie już
// sparsowany polski tekst serwera (patrz komentarz przy oryginale).
function extractErrorMessage(err) {
  try {
    if (err?.messages?.length && err.messages[0]) return err.messages[0]
    if (err && err._server_messages) {
      const msgs = JSON.parse(err._server_messages)
      if (msgs && msgs.length) {
        const first = JSON.parse(msgs[0])
        return first.message || __('Wystąpił błąd, spróbuj ponownie')
      }
    }
    if (err && err.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || __('Wystąpił błąd, spróbuj ponownie')
    }
    if (err && err.message) return err.message
  } catch (e) {
    /* fall through */
  }
  return __('Wystąpił błąd, spróbuj ponownie')
}
</script>
