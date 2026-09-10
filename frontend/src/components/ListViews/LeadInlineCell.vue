<!--
  VOLTEO (issue #99, K3): edycja inline czterech kolumn listy leadow (Status
  CC, Status handlowy, Kolejny kontakt, Termin spotkania), bez otwierania
  leada. LeadsListView.vue renderuje ten komponent dla kolumn z
  utils/leadyInline.js::KOLUMNY_INLINE, PRZED generyczna galazia etykiety.

  Wrapper ma `@click.stop.prevent @dblclick.stop` (poprawka po klik-tescie
  wlasciciela, issue #99 follow-up): caly wiersz to `<router-link>`
  (frappe-ui ListRow.vue), ktore renderuje sie jako prawdziwy `<a href>`.
  Samo `.stop` NIE WYSTARCZA: stopPropagation() blokuje wylacznie to, zeby
  zdarzenie dotarlo do WLASNEGO listenera RouterLink na tym `<a>` (ten,
  ktory normalnie wywoluje preventDefault() i robi SPA router.push), ale
  natywna akcja domyslna przegladarki dla klikniecia w `<a href>`
  (pelna nawigacja) i tak sie wykonuje, bo o niej decyduje WYLACZNIE flaga
  `event.defaultPrevented` w momencie zakonczenia dispatchu, niezaleznie od
  tego, czy event zdazyl dotrzec do listenera na samym `<a>`. Bez `.prevent`
  klik w komorke Kolejny kontakt / Termin spotkania powodowal wiec PELNE
  przeladowanie strony na widok leada zamiast otwarcia pickera (potwierdzone
  Playwright: elementFromPoint trafial poprawnie w input, ale bubble-fazowy
  listener na document nigdy nie zobaczyl zdarzenia 'click', bo
  stopPropagation przerwal bubblowanie wczesniej -- mimo to nawigacja i tak
  zaszla, bo nic nie wywolalo preventDefault). `.prevent` na tym wrapperze
  (przodku kontrolek) jest bezpieczny mimo ze kontrolki sa NIZEJ w drzewie:
  wlasne handlery inputu/przycisku/selecta (target zdarzenia) i tak
  odpalaja sie PRZED naszym, bo listener na targecie zawsze biegnie przed
  listenerami na przodkach w fazie bubble -- `.prevent` na przodku tylko
  dopisuje defaultPrevented=true PO fakcie, co i tak wystarczy, zeby
  zablokowac natywna nawigacje `<a>`. Ten sam wzorzec `.stop.prevent` juz
  dziala w tym pliku obok (galezie "Szczegoly" i "Komentarze" w
  LeadsListView.vue). frappe-ui `Dropdown` (status) renderuje liste opcji w
  portalu (reka-ui) poza drzewem wiersza, wiec klik w sama opcje i tak nie
  dociera do wrappera ponizej -- `.stop.prevent` tutaj dotyczy tylko
  klikniecia OTWIERAJACEGO dropdown/picker/select.

  Zapis idzie zawsze przez `frappe.client.set_value` (serwer robi
  doc.save -> validate), NIGDY optymistycznie: pickery/select sa bound do
  `wartosc` (computed z props.item, wiec zmienia sie dopiero po odswiezeniu
  listy przez rodzica), wiec przy bledzie po prostu nic sie nie zmienia w
  komorce -- to jest caly "rewert": bez sukcesu widget nigdy nie pokazuje
  nowej wartosci.

  Status typu Lost ("Odrzucony") wymaga powodu: kopia wzorca z
  LeadSzybkiPodglad.vue (triggerStatusChange / LostReasonModal) --
  `useDocument('CRM Lead', name)`, `await document.get.promise`, ustawienie
  `document.doc.status`, otwarcie wspolnego LostReasonModal. Modal zapisuje
  caly dokument sam (status + lost_reason + lost_notes) przez
  `document.save.submit()` -- ten komponent tylko obserwuje zamkniecie
  modala i porownuje `document.doc.status` z aktualna wartoscia komorki: gdy
  sie rozjezdzaja, modal faktycznie zapisal (inaczej doc.status zostal
  cofniety przez LostReasonModal.cancel() do originalDoc.status, czyli
  wartosci sprzed edycji, rownej biezacej komorce -- brak emitu).
-->
<template>
  <div class="flex items-center" @click.stop.prevent @dblclick.stop>
    <Dropdown
      v-if="column.key === 'status'"
      :options="opcjeStatusu"
      placement="bottom-start"
    >
      <template #default="{ open }">
        <Button
          variant="ghost"
          size="sm"
          class="!h-7 max-w-full justify-start truncate"
          :label="wartosc ? statusLabel(wartosc) : ''"
          :iconRight="open ? 'chevron-up' : 'chevron-down'"
          :disabled="zapisywanie"
        >
          <template #prefix>
            <IndicatorIcon v-if="wartosc" :class="getLeadStatus(wartosc)?.color" />
          </template>
        </Button>
      </template>
    </Dropdown>

    <FormControl
      v-else-if="column.key === 'custom_status_handlowy'"
      type="select"
      size="sm"
      variant="outline"
      class="w-full"
      :options="opcjeStatusuHandlowego"
      :modelValue="wartosc"
      :disabled="zapisywanie"
      @update:modelValue="(v) => zapiszWartosc(column.key, v)"
    />

    <DatePicker
      v-else-if="column.key === 'custom_kolejny_kontakt'"
      :value="wartosc"
      :format="formatDaty"
      variant="outline"
      input-class="border-none text-sm text-ink-gray-8"
      :disabled="zapisywanie"
      @change="(v) => zapiszWartosc(column.key, v)"
    />

    <DateTimePicker
      v-else-if="column.key === 'custom_termin_spotkania'"
      :value="wartosc"
      :format="formatDatyCzasu"
      variant="outline"
      input-class="border-none text-sm text-ink-gray-8"
      :disabled="zapisywanie"
      @change="(v) => zapiszWartosc(column.key, v)"
    />
  </div>

  <LostReasonModal
    v-if="showLostReason && dokumentOdrzucenia"
    v-model="showLostReason"
    doctype="CRM Lead"
    :document="dokumentOdrzucenia"
  />
</template>

<script setup>
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import LostReasonModal from '@/components/Modals/LostReasonModal.vue'
import { useDocument } from '@/data/document'
import { getMeta } from '@/stores/meta'
import { statusesStore } from '@/stores/statuses'
import { surowaWartoscKomorki } from '@/utils/leadyInline'
import { isTranslatable, getFormat } from '@/utils'
import {
  Button,
  DatePicker,
  DateTimePicker,
  Dropdown,
  FormControl,
  call,
  toast,
} from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const props = defineProps({
  row: { type: Object, required: true },
  column: { type: Object, required: true },
  item: { type: [String, Number, Object], default: '' },
})

const emit = defineEmits(['saved'])

const { getLeadStatus, statusOptions } = statusesStore()
const meta = getMeta('CRM Lead')

function statusLabel(status) {
  return isTranslatable('CRM Lead Status') ? __(status) : status
}

// Format jawnie liczony przez getFormat('', '', ..., ..., false) (piaty
// argument withDate=false zwraca sam wzorzec, nie sformatowana date) --
// dokladnie ten sam wzorzec co SidePanelLayout.vue. Bez tego DatePicker
// pokazuje surowa wartosc bez formatowania, a DateTimePicker doklada
// sekundy: window.sysdefaults.time_format (System Settings.time_format,
// teraz "HH:mm") jest czytany dopiero wewnatrz getFormat, wiec pomijajac
// ten prop traci sie kontrole nad formatem systemowym.
const formatDaty = computed(() => getFormat('', '', true, false, false))
const formatDatyCzasu = computed(() => getFormat('', '', true, true, false))

const wartosc = computed(() => surowaWartoscKomorki(props.column, props.item))

const opcjeStatusuHandlowego = computed(() => {
  const pole = meta
    .getFields()
    .find((f) => f.fieldname === 'custom_status_handlowy')
  return pole?.options || []
})

const zapisywanie = ref(false)

async function zapiszWartosc(fieldname, wartoscDoZapisu) {
  zapisywanie.value = true
  try {
    await call('frappe.client.set_value', {
      doctype: 'CRM Lead',
      name: props.row.name,
      fieldname,
      value: wartoscDoZapisu ?? '',
    })
    emit('saved', { fieldname, value: wartoscDoZapisu ?? '' })
    toast.success(__('Zapisano'))
  } catch (err) {
    toast.error(err.messages?.[0] || __('Nie udalo sie zapisac'))
  } finally {
    zapisywanie.value = false
  }
}

// --- Status: "Odrzucony" wymaga powodu (kopia wzorca LeadSzybkiPodglad.vue) ---

const showLostReason = ref(false)
const dokumentOdrzucenia = ref(null)

const opcjeStatusu = computed(() =>
  statusOptions('lead', [], triggerStatusChange),
)

async function triggerStatusChange(nowyStatus) {
  if (nowyStatus === wartosc.value || zapisywanie.value) return

  if (getLeadStatus(nowyStatus)?.type === 'Lost') {
    const { document } = useDocument('CRM Lead', props.row.name)
    await document.get.promise
    document.doc.status = nowyStatus
    dokumentOdrzucenia.value = document
    showLostReason.value = true
    return
  }

  zapiszWartosc('status', nowyStatus)
}

// LostReasonModal zapisuje caly dokument sam (poza tym komponentem), wiec
// nowa wartosc statusu trafia do listy dopiero tutaj, po zamknieciu modala.
watch(showLostReason, (otwarty, byloOtwarte) => {
  if (!byloOtwarte || otwarty) return
  const doc = dokumentOdrzucenia.value?.doc
  dokumentOdrzucenia.value = null
  if (!doc) return
  if (doc.status && doc.status !== wartosc.value) {
    emit('saved', { fieldname: 'status', value: doc.status })
  }
})
</script>
