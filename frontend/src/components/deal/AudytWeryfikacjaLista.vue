<!--
  Lista pol audytu na etapie Weryfikacja: jeden wiersz na pole, trzy kolumny
  (etykieta | wartosc | decyzja). Wartosc to zwykly tekst; edycja w miejscu
  (tylko gdy `readOnly` jest false) otwiera pole formularza dla jednego
  wiersza naraz i zapisuje przez te same obserwatory autozapisu, co reszta
  AudytTab (komponent zmienia `form` w miejscu). Decyzje emituje jako
  `set-verdict`, nie wola API.
-->
<template>
  <div class="flex flex-col gap-4">
    <section v-for="sec in widoczneSekcje" :key="sec.label">
      <div class="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
        {{ sec.label }}
      </div>
      <div class="flex flex-col overflow-hidden rounded-lg border border-outline-gray-2">
        <template v-for="f in sec.fields" :key="f.fieldname">
          <div
            :id="'audyt-el-' + fieldKey(f.fieldname)"
            :class="[
              'grid grid-cols-2 items-start gap-x-3 gap-y-1.5 border-b border-outline-gray-2 px-3 py-2 last:border-b-0 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_auto]',
              tloWiersza(f),
            ]"
          >
            <div
              :class="[
                'text-sm',
                status(f) === 'accepted' ? 'text-ink-gray-5' : 'font-medium text-ink-gray-8',
              ]"
            >
              {{ f.label }}
            </div>

            <div class="min-w-0 text-sm text-ink-gray-8">
              <template v-if="edytowany === f.fieldname">
                <div class="flex flex-col gap-1.5">
                  <FormControl
                    :type="f.type"
                    :options="f.options"
                    :step="f.step"
                    :disabled="readOnly"
                    v-model="form[f.fieldname]"
                  />
                  <div class="flex flex-wrap items-center gap-2">
                    <Button size="sm" variant="subtle" :label="__('Gotowe')" @click="edytowany = null" />
                    <span class="text-xs text-ink-gray-5">
                      {{ __('Zapis zmiany cofa akceptację tego elementu.') }}
                    </span>
                  </div>
                </div>
              </template>
              <div v-else class="flex items-start gap-1.5">
                <span
                  v-if="jestPuste(f)"
                  class="text-ink-gray-4"
                >
                  {{ __('brak') }}
                </span>
                <span
                  v-else
                  :class="f.type === 'textarea' ? 'line-clamp-2 whitespace-pre-wrap' : 'break-words'"
                >
                  {{ form[f.fieldname] }}
                </span>
                <button
                  v-if="!readOnly"
                  type="button"
                  class="shrink-0 rounded p-0.5 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8"
                  :title="__('Edytuj')"
                  :aria-label="__('Edytuj')"
                  @click="edytowany = f.fieldname"
                >
                  <span class="lucide-pencil size-3.5" aria-hidden="true" />
                </button>
              </div>
            </div>

            <div class="col-span-2 sm:col-span-1">
              <AudytVerdictControls
                uklad="wiersz"
                :verdict="verdictFor(weryfikacja, fieldKey(f.fieldname))"
                :can-review="canReview"
                :busy="!!busy[fieldKey(f.fieldname)]"
                :show-controls="true"
                @set-verdict="(st, note) => $emit('set-verdict', fieldKey(f.fieldname), st, note)"
              />
            </div>
          </div>

          <div
            v-if="canReview && f.fieldname === 'istniejaca_pv_moc_kw' && podpowiedzPv"
            class="border-b border-outline-gray-2 bg-surface-amber-2 px-3 py-1.5 text-xs text-ink-amber-8 last:border-b-0"
          >
            {{
              __(
                '{0} kW przy {1} modułach daje {2} W na moduł. Typowy moduł ma 350 do 500 W.',
                [form.istniejaca_pv_moc_kw, form.istniejaca_pv_moduly, podpowiedzPv.watNaModul],
              )
            }}
          </div>
        </template>
      </div>
    </section>
  </div>
</template>

<script setup>
import AudytVerdictControls from '@/components/deal/AudytVerdictControls.vue'
import { fieldKey, spojnoscPv, verdictFor } from '@/utils/audytWeryfikacja'
import { Button, FormControl } from 'frappe-ui'
import { computed, ref } from 'vue'

const props = defineProps({
  // [{ label, fields }], pola juz przefiltrowane do widocznych (depends_on)
  sekcje: { type: Array, default: () => [] },
  // reaktywny obiekt z AudytTab, zmieniany w miejscu (v-model)
  form: { type: Object, required: true },
  weryfikacja: { type: Object, default: () => ({}) },
  canReview: { type: Boolean, default: false },
  readOnly: { type: Boolean, default: false },
  // mapa zajetosci per klucz elementu (verdictBusy)
  busy: { type: Object, default: () => ({}) },
  // 'wszystkie' | 'otwarte' | 'bledy'
  filtr: { type: String, default: 'wszystkie' },
})

defineEmits(['set-verdict'])

// Tylko jeden wiersz w trybie edycji naraz.
const edytowany = ref(null)

function status(f) {
  return verdictFor(props.weryfikacja, fieldKey(f.fieldname)).status
}

const widoczneSekcje = computed(() =>
  props.sekcje
    .map((sec) => ({
      label: sec.label,
      fields: (sec.fields || []).filter((f) => {
        if (props.filtr === 'otwarte') return status(f) === 'waiting'
        if (props.filtr === 'bledy') return status(f) === 'error'
        return true
      }),
    }))
    .filter((sec) => sec.fields.length),
)

function jestPuste(f) {
  const v = props.form[f.fieldname]
  return v === undefined || v === null || String(v).trim() === ''
}

function tloWiersza(f) {
  const st = status(f)
  if (st === 'error') return 'bg-surface-red-2'
  if (st === 'waiting' && props.canReview) return 'bg-surface-blue-2'
  return ''
}

const podpowiedzPv = computed(() => {
  const r = spojnoscPv(props.form.istniejaca_pv_moc_kw, props.form.istniejaca_pv_moduly)
  return r && r.nietypowe ? r : null
})
</script>
