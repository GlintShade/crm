<!--
  VOLTEO (issue #97, L08): panel boczny "Szybki podglad" leada na mapie
  leadow. Klik w pinezke (MapaLeadow.vue) otwiera ten panel zamiast
  nawigowac na strone /leads/<id> -- CC ogladajacy 11 tys. pinezek nie moze
  tracic pozycji/zoomu mapy przy kazdym kliknieciu. Panel pozycjonuje sie
  sam (absolute inset-y-0 right-0 z-[1000] na korzeniu ponizej) zamiast
  przyjmowac `class` od rodzica -- ma wiecej niz jeden korzen (panel +
  LostReasonModal + KomentarzeLeadaModal), a Vue cicho gubi attrs
  przekazane do multi-root komponentu.

  Reuzywane komponenty, nie duplikowane:
  - SidePanelLayout.vue (ta sama zakladka "Szczegoly" co Lead.vue) --
    :docname="lead.name" jest wystarczajace, bo useDocument() cache'uje
    zasob per doctype+docname (frontend/src/data/document.js); ten
    komponent wolany jest z rodzica z :key="lead.name" (patrz
    MapaLeadow.vue), wiec przy zmianie zaznaczonego leada caly panel
    (wlacznie z ponizszym useDocument) montuje sie od nowa zamiast
    trzymac stary dokument.
  - PrzekazHandlowcowi.vue (issue #96) -- ten sam przycisk + wlasny Dialog
    co w Lead.vue, widoczny dla isCallCenter() || isVolteoAdmin().
  - KomentarzeLeadaModal.vue (ops#94) -- ten sam modal co pseudo-kolumna
    "Komentarze" na liscie leadow.

  Status i "Odrzucony wymaga powodu": kopia logiki Lead.vue (triggerStatusChange
  / setLostReason / beforeStatusChange) -- musi zostac skopiowana, nie
  wyciagnieta do wspolnego helpera w tym batchu (poza zakresem #97), bo oba
  miejsca subtelnie rozjezdzaja sie w tym, co robia PO zapisie (Lead.vue
  odswieza zakladke Aktywnosci i sekcje strony; ten panel emituje 'zaktualizowano'
  do mapy, zeby przebarwic pinezke bez przeladowania calej listy leadow).

  Esc zamyka panel, ale NIE gdy jakikolwiek Dialog frappe-ui jest otwarty
  (LostReasonModal / KomentarzeLeadaModal / wewnetrzny Dialog
  PrzekazHandlowcowi) -- inaczej Escape zamykalby modal i panel na raz.
  DialogOverlay frappe-ui renderuje atrybut `data-dialog` na kazdym otwartym
  oknie, wiec sprawdzenie jego obecnosci w DOM jest tanim i wystarczajacym
  sygnalem "jakis Dialog jest teraz otwarty".
-->
<template>
  <div
    class="absolute inset-y-0 right-0 z-[1000] flex w-[340px] shrink-0 flex-col overflow-hidden border-l border-outline-gray-2 bg-surface-elevation-1 shadow-lg"
  >
    <div
      class="flex items-start justify-between gap-2 border-b border-outline-gray-2 px-3 py-2.5"
    >
      <div class="min-w-0">
        <div class="truncate text-base font-medium text-ink-gray-9">
          {{ tytul }}
        </div>
        <div
          v-if="doc.mobile_no"
          class="mt-0.5 flex items-center gap-1 text-sm text-ink-gray-6"
        >
          <Button
            v-if="callEnabled"
            variant="ghost"
            class="-ml-1.5 size-6"
            :icon="PhoneIcon"
            @click="zadzwon"
          />
          <span>{{ doc.mobile_no }}</span>
        </div>
      </div>
      <Button
        variant="ghost"
        icon="lucide-x"
        class="shrink-0"
        @click="emit('zamknij')"
      />
    </div>

    <div
      class="flex flex-wrap items-center gap-1.5 border-b border-outline-gray-2 px-3 py-2"
    >
      <span v-if="doc.status" class="text-sm text-ink-gray-5">{{
        __('Status CC')
      }}</span>
      <Dropdown v-if="doc.status" :options="statuses" placement="bottom-start">
        <template #default="{ open }">
          <Button
            :label="statusLabel(doc.status)"
            :iconRight="open ? 'chevron-up' : 'chevron-down'"
          >
            <template #prefix>
              <IndicatorIcon :class="getLeadStatus(doc.status).color" />
            </template>
          </Button>
        </template>
      </Dropdown>
      <PrzekazHandlowcowi
        v-if="isCallCenter() || isVolteoAdmin()"
        :docname="lead.name"
        @przekazano="onPrzekazano"
      />
      <Button
        :label="__('Otwórz leada')"
        icon-left="lucide-external-link"
        @click="otworzLeada"
      />
    </div>

    <div
      v-if="dymek.length"
      class="flex flex-col gap-1 border-b border-outline-gray-2 px-3 py-2 text-sm"
    >
      <div v-for="wiersz in dymek" :key="wiersz.label" class="flex gap-2">
        <span class="w-2/5 shrink-0 truncate text-ink-gray-5">{{
          wiersz.label
        }}</span>
        <span class="min-w-0 flex-1 truncate text-ink-gray-8">{{
          wiersz.value
        }}</span>
      </div>
    </div>

    <!-- VOLTEO (ops#112 followup): panel jest waski (w-[340px], patrz korzen
         wyzej), wiec te same pola co na Lead.vue zajmuja tu wiecej pionowej
         przestrzeni (mniej miejsca na wartosc = czestszy zawijanie). Sekcje
         z wieloma polami (np. "Kwalifikacja", 12 pol) przekraczaly wtedy
         wewnetrzny limit SidePanelLayout.vue (.column max-height: 300px) i
         FadedScrollableDiv rysowal blaknace gradientowe "wieko" (mask-image)
         na ostatnim widocznym polu -- to byla prawdziwa "winieta" z klik-testu,
         nie przeswitujaca mapa (to bylo osobne, juz naprawione). Zdejmujemy
         limit WYLACZNIE w tym panelu przez zmienna CSS
         --sidepanel-column-max-height (patrz SidePanelLayout.vue), zeby
         Lead.vue/Deal.vue/Contact.vue i inni konsumenci tego komponentu
         zachowali dotychczasowy wyglad. Caly panel ma wlasny scroll (klasa
         ponizej), wiec brak limitu per-sekcja nie psuje ogolnej wysokosci --
         przybywa tylko jeden spojny scroll zamiast zagniezdzonego. -->
    <div
      class="min-h-0 flex-1 overflow-y-auto"
      style="--sidepanel-column-max-height: none"
    >
      <SidePanelLayout
        v-if="sections.data"
        :sections="sections.data"
        doctype="CRM Lead"
        :docname="lead.name"
        @reload="sections.reload"
        @beforeFieldChange="beforeFieldChange"
      />
    </div>

    <div class="border-t border-outline-gray-2 px-3 py-2">
      <Button
        class="w-full"
        :label="komentarzeLabel"
        icon-left="lucide-message-square"
        @click="showKomentarze = true"
      />
    </div>
  </div>

  <LostReasonModal
    v-if="showLostReasonModal"
    v-model="showLostReasonModal"
    doctype="CRM Lead"
    :document="document"
  />
  <KomentarzeLeadaModal
    v-model="showKomentarze"
    :docname="lead.name"
    doctype="CRM Lead"
    @commentAdded="onCommentAdded"
  />
</template>

<script setup>
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import SidePanelLayout from '@/components/SidePanelLayout.vue'
import PrzekazHandlowcowi from '@/components/PrzekazHandlowcowi.vue'
import KomentarzeLeadaModal from '@/components/Modals/KomentarzeLeadaModal.vue'
import LostReasonModal from '@/components/Modals/LostReasonModal.vue'
import { useDocument } from '@/data/document'
import { globalStore } from '@/stores/global'
import { usersStore } from '@/stores/users'
import { statusesStore } from '@/stores/statuses'
import { callEnabled } from '@/composables/telephony'
import { isTranslatable } from '@/utils'
import router from '@/router'
import { Button, Dropdown, createResource } from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  lead: { type: Object, required: true },
})

const emit = defineEmits(['zamknij', 'zaktualizowano'])

const { makeCall } = globalStore()
const { isCallCenter, isVolteoAdmin } = usersStore()
const { statusOptions, getLeadStatus } = statusesStore()

const { document, triggerOnChange } = useDocument('CRM Lead', props.lead.name)

const doc = computed(() => document.doc || {})

const tytul = computed(() => doc.value.lead_name || props.lead.name)

// --- Sekcja "Szczegoly" (ten sam layout co Lead.vue) --------------------

const sections = createResource({
  url: 'crm.fcrm.doctype.crm_fields_layout.crm_fields_layout.get_sidepanel_sections',
  cache: ['sidePanelSections', 'CRM Lead'],
  params: { doctype: 'CRM Lead' },
  auto: true,
})

// --- Status + "Odrzucony wymaga powodu" (kopia Lead.vue) ----------------

const showLostReasonModal = ref(false)

const statuses = computed(() => statusOptions('lead', [], triggerStatusChange))

function statusLabel(status) {
  return isTranslatable('CRM Lead Status') ? __(status) : status
}

async function triggerStatusChange(value) {
  await triggerOnChange('status', value)
  setLostReason({ status: value })
}

function setLostReason(patch) {
  if (
    getLeadStatus(document.doc.status).type !== 'Lost' ||
    (document.doc.lost_reason && document.doc.lost_reason !== 'Other') ||
    (document.doc.lost_reason === 'Other' && document.doc.lost_notes)
  ) {
    document.save.submit(null, {
      onSuccess: () => powiadomOZmianie(patch || { status: document.doc.status }),
    })
    return
  }
  oczekujacaZmiana.value = patch || { status: document.doc.status }
  showLostReasonModal.value = true
}

// LostReasonModal zapisuje (albo cofa) dokument samodzielnie, bez callbacku
// onSuccess -- czekamy az sie zamknie i wtedy powiadamiamy mape aktualnym
// stanem doc.status (zapisanym po "Zapisz" albo przywroconym po "Anuluj",
// oba przypadki sa poprawne do przebarwienia pinezki).
const oczekujacaZmiana = ref(null)
watch(showLostReasonModal, (open, wasOpen) => {
  if (wasOpen && !open) {
    powiadomOZmianie(oczekujacaZmiana.value || { status: document.doc.status })
    oczekujacaZmiana.value = null
  }
})

function beforeFieldChange(data) {
  if (
    Object.hasOwn(data ?? {}, 'status') &&
    getLeadStatus(data.status).type == 'Lost'
  ) {
    setLostReason({ status: data.status })
  } else {
    document.save.submit(null, {
      onSuccess: () => powiadomOZmianie(data),
    })
  }
}

function powiadomOZmianie(patch) {
  emit('zaktualizowano', { name: props.lead.name, ...patch })
}

// --- "Otworz leada" w nowej karcie ---------------------------------------

function otworzLeada() {
  const href = router.resolve({
    name: 'Lead',
    params: { leadId: props.lead.name },
  }).href
  window.open(href, '_blank', 'noopener')
}

// --- Telefon --------------------------------------------------------------

function zadzwon() {
  if (!doc.value.mobile_no) return
  makeCall(doc.value.mobile_no)
}

// --- Przekaz handlowcowi ---------------------------------------------------

function onPrzekazano({ handlowiec }) {
  document.reload()
  powiadomOZmianie({ lead_owner: handlowiec })
}

// --- Komentarze -------------------------------------------------------------

const showKomentarze = ref(false)
const liczbaKomentarzy = ref(null)

const komentarzeLabel = computed(() =>
  liczbaKomentarzy.value === null
    ? __('Komentarze')
    : __('Komentarze ({0})', [liczbaKomentarzy.value]),
)

function onCommentAdded({ count }) {
  liczbaKomentarzy.value = count
}

// --- Dymek: skrot zrodla/produktow/statusu zrodla (te same pola co dymek pinezki) ---

const dymek = computed(() => {
  const wiersze = [
    [__('Źródło'), props.lead.custom_import_source],
    [__('Obecne produkty'), props.lead.custom_posiadane_produkty],
    [__('Status źródła'), props.lead.custom_status_zrodla],
  ]
  return wiersze
    .filter(([, value]) => Boolean(value))
    .map(([label, value]) => ({ label, value }))
})

// --- Esc zamyka panel (ale nie gdy otwarty jest jakis Dialog) --------------

// Uwaga: `document` w tym pliku to zasob z useDocument() (patrz wyzej), nie
// globalny DOM document -- stad `window.document` ponizej, zeby faktycznie
// zapytac o otwarte okna Dialog (frappe-ui renderuje atrybut `data-dialog`
// na kazdym otwartym DialogOverlay).
function onKeydown(e) {
  if (e.key !== 'Escape') return
  if (window.document.querySelector('[data-dialog]')) return
  emit('zamknij')
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>
