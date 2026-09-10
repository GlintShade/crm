<template>
  <Dialog v-model:open="show" :title="__('Lost Reason')" @close="cancel">
    <template #default>
      <div class="-mt-3 mb-4 text-p-base text-ink-gray-7">
        {{
          __('Please provide a reason for marking this {0} as lost', [
            doctype.toLowerCase().replace('crm ', ''),
          ])
        }}
      </div>
      <div class="flex flex-col gap-3">
        <div>
          <div class="mb-2 text-sm text-ink-gray-5">
            {{ __('Lost Reason') }}
            <span class="text-ink-red-5">*</span>
          </div>
          <Link
            ref="linkRef"
            class="form-control flex-1 truncate"
            :value="lostReason"
            doctype="CRM Lost Reason"
            :filters="kontekstFilters"
            :sortComparator="sortComparator"
            :onCreate="onCreate"
            @change="(v) => (lostReason = v)"
          />
        </div>
        <div>
          <div class="mb-2 text-sm text-ink-gray-5">
            {{ __('Lost Notes') }}
            <span v-if="wymagaNotatki" class="text-ink-red-5">*</span>
          </div>
          <FormControl
            class="form-control flex-1 truncate"
            type="textarea"
            :value="lostNotes"
            @change="(e) => (lostNotes = e.target.value)"
          />
        </div>
      </div>
    </template>
    <template #actions>
      <div class="flex justify-between items-center gap-2">
        <div><ErrorMessage :message="error" /></div>
        <div class="flex gap-2">
          <Button :label="__('Cancel')" @click="cancel" />
          <Button variant="solid" :label="__('Save')" @click="save" />
        </div>
      </div>
    </template>
  </Dialog>
</template>
<script setup>
import Link from '@/components/Controls/Link.vue'
import { createDocument } from '@/composables/document'
import { Dialog } from 'frappe-ui'
import { computed, ref } from 'vue'

const props = defineProps({
  doctype: { type: String, default: 'CRM Lead' },
  document: { type: Object, required: true },
})

const show = defineModel({ type: Boolean })

const linkRef = ref(null)
const doc = props.document.doc
const lostReason = ref(doc.lost_reason || '')
const lostNotes = ref(doc.lost_notes || '')
const error = ref('')

// Issue K1 (decyzja właściciela 2026-09-10): CRM Lost Reason niesie teraz
// custom_kontekst ("Lead" / "Szansa" / "Oba"), żeby powody szansy
// (Competition, Zbyt wysoka cena) nie pokazywały się na leadach i odwrotnie.
// props.doctype jest zawsze jawnie przekazywane przez wołające strony
// (Lead.vue/MobileLead.vue/LeadSzybkiPodglad.vue/LeadInlineCell.vue ->
// "CRM Lead"; Deal.vue/MobileDeal.vue -> "CRM Deal"), więc rozstrzygamy
// wprost po nim, bez zgadywania z innych sygnałów.
const jestLeadem = computed(() => props.doctype === 'CRM Lead')
const kontekstFilters = computed(() => ({
  custom_kontekst: ['in', jestLeadem.value ? ['Lead', 'Oba'] : ['Szansa', 'Oba']],
}))

// Kolejność 1..6 z decyzji właściciela 2026-09-10 (ops/crm-leady-
// powody-odrzucenia.py, LEAD_REASONS): search_link nie ma użytecznego pola
// sortowania (patrz komentarz w Link.vue przy sortComparator), więc
// autorytatywna kolejność jest wymuszona tu, po stronie klienta. Dla szansy
// nie ma ustalonej kolejności w decyzji, zostaje sortowanie serwera.
const KOLEJNOSC_LEAD = [
  'Brak zainteresowania',
  'Brak kontaktu',
  'Błędny numer',
  'Ma już instalację',
  'Nie spełnia warunków',
  'Inny',
]

function sortujWgKolejnosciLead(a, b) {
  const ia = KOLEJNOSC_LEAD.indexOf(a.value)
  const ib = KOLEJNOSC_LEAD.indexOf(b.value)
  if (ia === -1 && ib === -1) return a.label.localeCompare(b.label)
  if (ia === -1) return 1
  if (ib === -1) return -1
  return ia - ib
}

const sortComparator = computed(() => (jestLeadem.value ? sortujWgKolejnosciLead : null))

// Issue K1: powód "Other" (angielski, ze stocku) został usunięty razem z
// resztą nieużywanych domyślnych powodów, zastąpiony przez "Inny" na
// leadach. "Other" zostaje tu jako defensywny fallback (dokument utworzony
// przed migracją albo inne środowisko, gdzie usunięcie jeszcze nie zaszło),
// zamiast twardego przełączenia wyłącznie na "Inny".
const WYMAGA_NOTATKI = new Set(['Other', 'Inny'])
const wymagaNotatki = computed(() => WYMAGA_NOTATKI.has(lostReason.value))

function cancel() {
  show.value = false
  error.value = ''
  lostReason.value = ''
  lostNotes.value = ''
  doc.status = props.document.originalDoc.status
}

function save() {
  if (!lostReason.value) {
    error.value = __('Lost Reason is required')
    return
  }
  if (wymagaNotatki.value && !lostNotes.value) {
    error.value = __('Dla powodu "Inny" wymagana jest notatka.')
    return
  }

  error.value = ''
  show.value = false

  doc.lost_reason = lostReason.value
  doc.lost_notes = lostNotes.value
  props.document.save.submit()
}

function onCreate(value, close) {
  let doc = { lost_reason: value }
  createDocument('CRM Lost Reason', doc, close, (doc) => {
    lostReason.value = doc.name
    linkRef.value?.reload('', true)
  })
}
</script>
