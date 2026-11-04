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

  b83 (prosba wlasciciela): siedem kolejnych kolumn, ten sam wzorzec zapisu.
  - lead_owner ("Przypisany handlowiec"): Link do User z tym samym zakresem
    co panel boczny (znacznik volteo_scope_handlowcy -> crm.api.volteo_leady.
    handlowcy, userScope -> crm.api.volteo_uzytkownicy.widoczni_uzytkownicy).
    Handlowiec D2D widzi sama nazwe, bez edycji (utils/leadyInline.js::
    mozePrzypisywacHandlowca). Zapis to zwykly set_value, czyli ta sama
    sciezka co panel boczny (document.save.submit w frappe-ui tez wola
    frappe.client.set_value ze slownikiem zmienionych pol), wiec hooki
    CRMLead.validate/on_update (ToDo, DocShare, mail o przydziale, odebranie
    widocznosci poprzedniemu handlowcowi) odpalaja sie tak samo.
  - custom_voivodeship: select 16 wojewodztw.
  - pola tekstowe (KOLUMNY_TEKSTOWE_INLINE): klik w komorke otwiera pole,
    Enter albo opuszczenie pola zatwierdza, Escape anuluje. Kod pocztowy
    przechodzi walidacje NN-NNN przed zapisem. Powiat ma podpowiedzi z
    crm.api.volteo_leady.powiaty_filtra dla wojewodztwa z tego wiersza
    (datalist), ale przyjmuje dowolny tekst.
  - "Rewert" przy bledzie: kontrolki natywne (select, input) trzymaja wlasny
    stan DOM, wiec po bledzie podbijamy `wersjaKontrolki` (klucz), co
    przerysowuje kontrolke z wartoscia sprzed edycji.
-->
<template>
  <div
    class="flex items-center"
    :class="{ 'w-full min-w-0': wypelnijKomorke }"
    @click.stop.prevent
    @dblclick.stop
  >
    <Button
      v-if="column.key === 'status' && !mozeZmieniacStatusCC()"
      data-testid="status-cc-readonly"
      variant="ghost"
      size="sm"
      class="pointer-events-none !h-7 max-w-full justify-start truncate"
      :label="wartosc ? statusLabel(wartosc) : ''"
    >
      <template #prefix>
        <IndicatorIcon v-if="wartosc" :class="getLeadStatus(wartosc)?.color" />
      </template>
    </Button>

    <Dropdown
      v-else-if="column.key === 'status'"
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
      :placeholder="__('Wybierz opcję')"
      @update:modelValue="(v) => zapiszWartosc(column.key, v)"
    />

    <CzasGgMmInput
      v-else-if="column.key === 'custom_czas_do_kontaktu'"
      class="w-full [&_input]:text-center"
      :value="wartosc"
      :disabled="zapisywanie"
      @change="(v) => zapiszWartosc(column.key, v)"
    />

    <FormControl
      v-else-if="column.key === 'custom_proby_kontaktu'"
      type="select"
      size="sm"
      variant="outline"
      class="w-full"
      :options="opcjeProbKontaktu"
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
      :placeholder="__('Wybierz datę')"
      @change="(v) => zapiszWartosc(column.key, v)"
    />

    <DateTimePickerSiatka
      v-else-if="column.key === 'custom_termin_spotkania'"
      :value="wartosc"
      :format="formatDatyCzasu"
      variant="outline"
      input-class="border-none text-sm text-ink-gray-8"
      :disabled="zapisywanie"
      :placeholder="__('Wybierz datę i godzinę')"
      @change="(v) => zapiszWartosc(column.key, v)"
    />

    <div
      v-else-if="column.key === 'lead_owner' && !mozeEdytowacHandlowca"
      data-testid="handlowiec-readonly"
      class="flex min-w-0 items-center gap-1.5 truncate text-base"
    >
      <Avatar
        v-if="wartosc"
        :image="item?.user_image"
        :label="item?.full_name || wartosc"
        size="sm"
      />
      <span v-if="wartosc" class="truncate">{{ item?.full_name || wartosc }}</span>
    </div>

    <Link
      v-else-if="column.key === 'lead_owner'"
      :key="`handlowiec-${wersjaKontrolki}`"
      class="w-full"
      doctype="User"
      variant="outline"
      :value="wartosc"
      :filters="filtryHandlowca"
      :userScope="true"
      :hideMe="true"
      :disabled="zapisywanie"
      :placeholder="__('Wybierz handlowca')"
      @change="zapiszHandlowca"
    >
      <template v-if="wartosc" #prefix>
        <UserAvatar class="mr-1.5" :user="wartosc" size="sm" />
      </template>
      <template #item-prefix="{ option }">
        <UserAvatar class="mr-1.5" :user="option.value" size="sm" />
      </template>
    </Link>

    <FormControl
      v-else-if="column.key === 'custom_voivodeship'"
      :key="`wojewodztwo-${wersjaKontrolki}`"
      type="select"
      size="sm"
      variant="outline"
      class="w-full"
      :options="opcjeWojewodztw"
      :modelValue="wartosc"
      :disabled="zapisywanie"
      @update:modelValue="(v) => zapiszJesliZmiana(column.key, v)"
    />

    <template v-else-if="KOLUMNY_TEKSTOWE_INLINE.has(column.key)">
      <TextInput
        v-if="edytujeTekst"
        ref="poleTekstoweRef"
        :key="`tekst-${wersjaKontrolki}`"
        size="sm"
        variant="outline"
        class="w-full"
        :value="szkic"
        :placeholder="placeholderTekstu"
        :list="column.key === 'custom_powiat' ? idListyPowiatow : undefined"
        :maxlength="column.key === 'custom_install_postal_code' ? 8 : undefined"
        @input="(e) => (szkic = e.target.value)"
        @keydown="onKeydownTekstu"
        @blur="zatwierdzTekst"
      />
      <datalist
        v-if="edytujeTekst && column.key === 'custom_powiat'"
        :id="idListyPowiatow"
      >
        <option v-for="p in podpowiedziPowiatow" :key="p" :value="p" />
      </datalist>
      <div
        v-if="!edytujeTekst"
        data-testid="komorka-tekst"
        class="flex h-7 w-full min-w-0 cursor-text items-center truncate rounded px-1 text-base hover:bg-surface-gray-2"
        :class="{ 'opacity-60': zapisywanie }"
        :title="wyswietlanyTekst || __('Kliknij, aby edytować')"
        @click="rozpocznijEdycjeTekstu"
      >
        <span class="truncate">{{ wyswietlanyTekst }}</span>
      </div>
    </template>
  </div>

  <LostReasonModal
    v-if="showLostReason && dokumentOdrzucenia"
    v-model="showLostReason"
    doctype="CRM Lead"
    :document="dokumentOdrzucenia"
  />
</template>

<script>
// Wspolny dla wszystkich instancji komorki (patrz pobierzPodpowiedziPowiatow).
const cachePowiatow = new Map()
</script>

<script setup>
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import LostReasonModal from '@/components/Modals/LostReasonModal.vue'
import { useDocument } from '@/data/document'
import { getMeta } from '@/stores/meta'
import { statusesStore } from '@/stores/statuses'
import { usersStore } from '@/stores/users'
import {
  KOLUMNY_TEKSTOWE_INLINE,
  WOJEWODZTWA,
  czyWartoscSieZmienila,
  mozePrzypisywacHandlowca,
  surowaWartoscKomorki,
  wartoscTekstuDoZapisu,
} from '@/utils/leadyInline'
import { parseLinkFilters } from '@/utils/fieldTransforms'
import { isTranslatable, getFormat } from '@/utils'
import {
  Avatar,
  Button,
  DatePicker,
  Dropdown,
  FormControl,
  TextInput,
  call,
  toast,
} from 'frappe-ui'
import CzasGgMmInput from '@/components/Controls/CzasGgMmInput.vue'
import DateTimePickerSiatka from '@/components/Controls/DateTimePickerSiatka.vue'
import Link from '@/components/Controls/Link.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  row: { type: Object, required: true },
  column: { type: Object, required: true },
  item: { type: [String, Number, Object], default: '' },
})

const emit = defineEmits(['saved'])

const { getLeadStatus, statusOptions } = statusesStore()
const { mozeZmieniacStatusCC, users, getUser, isVolteoAdmin } = usersStore()
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

const opcjeProbKontaktu = computed(() => {
  const pole = meta.getFields().find((f) => f.fieldname === 'custom_proby_kontaktu')
  const opcje = pole?.options || []
  const lista = typeof opcje === 'string' ? opcje.split('\n') : opcje
  // Bez pustego wyboru: puste pole to "0" (patrz probyKontaktuDoWyswietlenia).
  return lista.filter((o) => (typeof o === 'object' ? o?.value !== '' : Boolean(o)))
})

const wypelnijKomorke = computed(
  () =>
    props.column.key === 'custom_czas_do_kontaktu' ||
    props.column.key === 'custom_proby_kontaktu' ||
    props.column.key === 'lead_owner' ||
    props.column.key === 'custom_voivodeship' ||
    KOLUMNY_TEKSTOWE_INLINE.has(props.column.key),
)

const zapisywanie = ref(false)

// b83: podbijane po bledzie zapisu, zeby kontrolki z wlasnym stanem DOM
// (select, input, Link) przerysowaly sie z wartoscia sprzed edycji.
const wersjaKontrolki = ref(0)

async function zapiszWartosc(fieldname, wartoscDoZapisu) {
  if (zapisywanie.value) return false
  zapisywanie.value = true
  try {
    // Pulapka Frappe: frappe/client.py::set_value robi `if not value`, wiec
    // 0 lub '' wyslane pozycyjnie zamieniaja sie w {pole: ""}, co dla pola
    // Duration/liczbowego daje DataError 1366. Dict w `fieldname` omija te galaz.
    await call('frappe.client.set_value', {
      doctype: 'CRM Lead',
      name: props.row.name,
      fieldname: { [fieldname]: wartoscDoZapisu ?? '' },
    })
    emit('saved', { fieldname, value: wartoscDoZapisu ?? '' })
    toast.success(__('Zapisano'))
    return true
  } catch (err) {
    toast.error(err.messages?.[0] || __('Nie udało się zapisać'))
    wersjaKontrolki.value += 1
    return false
  } finally {
    zapisywanie.value = false
  }
}

function zapiszJesliZmiana(fieldname, nowa) {
  if (!czyWartoscSieZmienila(wartosc.value, nowa)) return
  return zapiszWartosc(fieldname, nowa)
}

// --- b83: Przypisany handlowiec (lead_owner) ---

const mozeEdytowacHandlowca = computed(() =>
  mozePrzypisywacHandlowca(getUser().roles, isVolteoAdmin()),
)

// Te same filtry co SidePanelLayout.vue::parsedField dla Linku do User:
// lista crmUsers + ignore_user_type + link_filters pola z meta (Property
// Setter z ops/crm-leady-call-center.py niesie tam volteo_scope_handlowcy).
// Znacznik dokladamy tez jawnie, zeby lista na liscie nie rozjechala sie z
// panelem, gdyby meta przyszla bez link_filters. Link.vue sam usuwa
// znacznik przed wyslaniem do search_link i po cichu spada do bazowych
// filtrow, gdy wolajacy nie ma prawa do crm.api.volteo_leady.handlowcy.
const filtryHandlowca = computed(() => {
  const pole = meta.getFields().find((f) => f.fieldname === 'lead_owner')
  return {
    name: ['in', users.data?.crmUsers?.map((u) => u.name) || []],
    ignore_user_type: 1,
    volteo_scope_handlowcy: true,
    ...(parseLinkFilters(pole?.link_filters) || {}),
  }
})

function zapiszHandlowca(v) {
  zapiszJesliZmiana('lead_owner', v || '')
}

// --- b83: Wojewodztwo ---

const opcjeWojewodztw = computed(() => {
  const pole = meta.getFields().find((f) => f.fieldname === 'custom_voivodeship')
  const surowe = pole?.options
  const lista = (typeof surowe === 'string' ? surowe.split('\n') : surowe || [])
    .map((o) => (typeof o === 'object' ? o?.value : o))
    .filter(Boolean)
  const wartosci = lista.length ? lista : WOJEWODZTWA
  return [
    { label: '', value: '' },
    ...wartosci.map((w) => ({ label: w, value: w })),
  ]
})

// --- b83: pola tekstowe adresu ---

const edytujeTekst = ref(false)
const szkic = ref('')
// Wartosc w trakcie zapisu: komorka pokazuje ja od razu, a po bledzie
// wraca do `wartosc` (props.item), czyli do stanu sprzed edycji.
const zapisywanyTekst = ref(null)
const poleTekstoweRef = ref(null)

const wyswietlanyTekst = computed(() =>
  zapisywanyTekst.value !== null ? zapisywanyTekst.value : wartosc.value,
)

const placeholderTekstu = computed(() =>
  props.column.key === 'custom_install_postal_code' ? 'NN-NNN' : '',
)

async function rozpocznijEdycjeTekstu() {
  if (zapisywanie.value) return
  szkic.value = wartosc.value ?? ''
  edytujeTekst.value = true
  if (props.column.key === 'custom_powiat') pobierzPodpowiedziPowiatow()
  await nextTick()
  const el = poleTekstoweRef.value?.el
  el?.focus()
  el?.select?.()
}

async function zatwierdzTekst() {
  if (!edytujeTekst.value) return
  edytujeTekst.value = false
  const wynik = wartoscTekstuDoZapisu(props.column.key, szkic.value)
  if (!wynik.ok) {
    toast.error(__(wynik.blad))
    return
  }
  if (!czyWartoscSieZmienila(wartosc.value, wynik.wartosc)) return
  zapisywanyTekst.value = wynik.wartosc
  try {
    await zapiszWartosc(props.column.key, wynik.wartosc)
  } finally {
    zapisywanyTekst.value = null
  }
}

function anulujTekst() {
  edytujeTekst.value = false
  szkic.value = wartosc.value ?? ''
}

function onKeydownTekstu(e) {
  if (e.key === 'Enter') {
    e.preventDefault()
    zatwierdzTekst()
  } else if (e.key === 'Escape') {
    e.preventDefault()
    anulujTekst()
  }
}

// Podpowiedzi powiatu: powiaty_filtra zwraca powiaty leadow widocznych
// wolajacemu, zawezone do wojewodztwa z tego wiersza (puste wojewodztwo =
// wszystkie widoczne). Cache na poziomie modulu, wspolny dla wszystkich
// komorek, jedno zapytanie na wojewodztwo. Blad = brak podpowiedzi, pole
// dalej przyjmuje dowolny tekst.
const idListyPowiatow = computed(() => `powiaty-${props.row.name}`)
const podpowiedziPowiatow = ref([])

async function pobierzPodpowiedziPowiatow() {
  const wojewodztwo = String(props.row.custom_voivodeship || '')
  if (!cachePowiatow.has(wojewodztwo)) {
    cachePowiatow.set(
      wojewodztwo,
      call('crm.api.volteo_leady.powiaty_filtra', {
        wojewodztwa: wojewodztwo || null,
      }).catch(() => {
        cachePowiatow.delete(wojewodztwo)
        return []
      }),
    )
  }
  const lista = await cachePowiatow.get(wojewodztwo)
  podpowiedziPowiatow.value = Array.isArray(lista) ? lista : []
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
