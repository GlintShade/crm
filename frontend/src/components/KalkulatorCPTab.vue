<template>
  <div class="flex flex-1 flex-col overflow-y-auto">
    <div class="mx-auto w-full max-w-[1180px] px-4 py-3">
      <div v-if="loading" class="py-8 text-center text-sm text-ink-gray-5">
        {{ __('Ładowanie kalkulatora…') }}
      </div>
      <div
        v-else-if="catalogueError"
        class="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
      >
        {{ catalogueError }}
      </div>

      <div v-else class="kalk-split grid items-start gap-x-5" style="grid-template-columns: minmax(0, 1.6fr) minmax(280px, 1fr)">
        <div>
          <div class="mb-3">
            <div class="mb-1 text-base font-semibold text-ink-gray-9">
              {{ __('Standard docieplenia budynku') }}
            </div>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="standard in STANDARDY"
                :key="standard"
                type="button"
                class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                :class="form.standard === standard
                  ? 'border-gray-900 bg-gray-900 text-white'
                  : 'border-transparent bg-gray-100 text-gray-600 hover:bg-gray-200'"
                @click="setStandard(standard)"
              >{{ standardLabels[standard] }}</button>
            </div>
          </div>

          <div class="mb-3">
            <div class="mb-1 text-base font-semibold text-ink-gray-9">
              {{ __('Poziom dotacji') }}
            </div>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="poziom in dostepnePoziomy(form.standard)"
                :key="poziom"
                type="button"
                class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                :class="form.poziom === poziom
                  ? 'border-gray-900 bg-gray-900 text-white'
                  : 'border-transparent bg-gray-100 text-gray-600 hover:bg-gray-200'"
                @click="form.poziom = poziom"
              >{{ poziomLabels[poziom] }}</button>
            </div>
          </div>

          <div class="mb-3">
            <div class="mb-1 text-base font-semibold text-ink-gray-9">
              {{ __('Źródło ciepła') }}
            </div>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="zrodlo in ZRODLA"
                :key="zrodlo"
                type="button"
                class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60"
                :class="form.zrodlo === zrodlo
                  ? 'border-gray-900 bg-gray-900 text-white'
                  : 'border-transparent bg-gray-100 text-gray-600 hover:bg-gray-200'"
                :disabled="!isActive(zrodlo)"
                :title="isActive(zrodlo) ? '' : __('Pozycja chwilowo niedostępna')"
                @click="setZrodlo(zrodlo)"
              >{{ zrodloLabels[zrodlo] }}</button>
            </div>

            <div v-if="dozwoloneDodatki(form.zrodlo).grzejniki" class="mt-2 grid grid-cols-2 gap-x-3 gap-y-2 kalk-row2">
              <div>
                <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Grzejniki') }}</div>
                <select v-model="form.typGrzejnikow" class="kalk-select">
                  <option :value="null">{{ __('— wybierz —') }}</option>
                  <option value="grzejnik" :disabled="!isActive('grzejnik')">{{ __('Grzejniki') }}</option>
                  <option value="grzejnik_co" :disabled="!isActive('grzejnik_co')">{{ __('Grzejniki + rury CO') }}</option>
                </select>
              </div>
              <div>
                <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Ilość grzejników') }}</div>
                <input v-model="form.iloscGrzejnikow" type="number" min="0" step="1" class="kalk-input" />
              </div>
            </div>
            <label
              v-if="dozwoloneDodatki(form.zrodlo).cwu"
              class="mt-2 inline-flex cursor-pointer items-center gap-2 text-sm text-ink-gray-7"
              :class="{ 'cursor-not-allowed opacity-60': !isActive('cwu') }"
              :title="isActive('cwu') ? '' : __('Pozycja chwilowo niedostępna')"
            >
              <input v-model="form.cwu" type="checkbox" class="h-4 w-4 rounded border-gray-300" :disabled="!isActive('cwu')" />
              <span>{{ __('Pompa ciepła do CWU (dodatek)') }}</span>
            </label>
          </div>

          <div class="mb-3">
            <div class="mb-1 text-base font-semibold text-ink-gray-9">
              {{ __('Powierzchnia użytkowa (parter)') }}
            </div>
            <div class="text-sm text-ink-gray-5">{{ __('m²') }}</div>
            <input v-model="form.powierzchnia" type="number" min="0" step="0.01" class="kalk-input mt-1" />
          </div>

          <div>
            <div class="mb-1 text-base font-semibold text-ink-gray-9">
              {{ __('Prace termomodernizacyjne') }}
            </div>
            <div
              v-for="kod in PRACE_M2"
              :key="kod"
              class="border-t border-gray-100 py-2 first:border-t-0"
            >
              <div class="flex items-center gap-2">
                <span class="w-20 shrink-0 text-sm text-ink-gray-7">{{ workLabels[kod] }}</span>
                <button
                  type="button"
                  class="rounded-md border px-2 py-1 text-xs font-medium transition-colors"
                  :class="form.prace[kod].wybrana
                    ? 'border-gray-900 bg-gray-900 text-white'
                    : 'border-transparent bg-gray-100 text-gray-600 hover:bg-gray-200'"
                  :disabled="!isActive(kod)"
                  :title="isActive(kod) ? '' : __('Pozycja chwilowo niedostępna')"
                  @click="form.prace[kod].wybrana = !form.prace[kod].wybrana"
                >{{ form.prace[kod].wybrana ? __('TAK') : __('NIE') }}</button>
                <input
                  :value="areaValue(kod)"
                  type="number"
                  min="0"
                  step="0.01"
                  class="kalk-input flex-1"
                  :disabled="!form.prace[kod].reczne || !isActive(kod)"
                  @input="form.prace[kod].m2 = $event.target.value"
                />
                <button
                  v-if="!form.prace[kod].reczne"
                  type="button"
                  class="shrink-0 text-xs font-medium text-blue-600 hover:underline disabled:text-gray-400 disabled:no-underline"
                  :disabled="!isActive(kod)"
                  @click="enableManual(kod)"
                >{{ __('wprowadź ręcznie') }}</button>
                <button
                  v-else
                  type="button"
                  class="shrink-0 rounded bg-gray-100 px-1.5 py-1 text-xs text-gray-600 hover:bg-gray-200"
                  @click="disableManual(kod)"
                >{{ __('auto') }}</button>
              </div>
            </div>

            <div class="border-t border-gray-100 py-2">
              <div class="flex items-center gap-2">
                <span class="w-20 shrink-0 text-sm text-ink-gray-7">{{ __('Drzwi') }}</span>
                <button
                  type="button"
                  class="rounded-md border px-2 py-1 text-xs font-medium transition-colors"
                  :class="form.prace.drzwi.wybrana
                    ? 'border-gray-900 bg-gray-900 text-white'
                    : 'border-transparent bg-gray-100 text-gray-600 hover:bg-gray-200'"
                  :disabled="!isActive('drzwi')"
                  :title="isActive('drzwi') ? '' : __('Pozycja chwilowo niedostępna')"
                  @click="form.prace.drzwi.wybrana = !form.prace.drzwi.wybrana"
                >{{ form.prace.drzwi.wybrana ? __('TAK') : __('NIE') }}</button>
                <input
                  v-if="form.prace.drzwi.wybrana"
                  v-model="form.prace.drzwi.ilosc"
                  type="number"
                  min="0"
                  step="1"
                  class="kalk-input flex-1"
                  :placeholder="__('ilość drzwi')"
                  :disabled="!isActive('drzwi')"
                />
                <span v-if="form.prace.drzwi.wybrana && drzwiArea !== null" class="text-xs text-ink-gray-5">= {{ drzwiArea }} {{ __('m²') }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="kalk-output border-l border-gray-200 pl-5">
          <div class="sticky top-3">
            <div v-if="$slots['client-picker']" class="mb-2.5">
              <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Klient') }}</div>
              <slot name="client-picker" />
            </div>

            <div class="mb-2 text-base font-semibold text-ink-gray-9">{{ __('Wycena') }}</div>
            <div v-if="errorMsg" class="mb-2 rounded border border-red-200 bg-red-50 px-2.5 py-2 text-sm text-red-800">
              {{ errorMsg }}
            </div>
            <div v-if="hasResult">
              <div class="mb-2 rounded-lg border border-gray-200 bg-gray-50 p-2.5">
                <div class="flex justify-between py-0.5 text-sm text-ink-gray-7">
                  <span>{{ __('Wkład własny beneficjenta') }}</span>
                  <span class="text-xl font-semibold tabular-nums text-ink-gray-9">{{ plnFmt(result.wklad_wlasny) }}</span>
                </div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                  <span>{{ __('Prowizja handlowa') }}</span><span>{{ plnFmt(result.prowizja_handlowa) }}</span>
                </div>
                <div class="flex justify-between border-t border-gray-200 pt-1.5 text-sm tabular-nums text-ink-gray-7">
                  <span>{{ __('Dotacja łączna') }}</span><span>{{ plnFmt(result.dotacja_laczna) }}</span>
                </div>
              </div>

              <div v-if="restrictionAmount > 0" class="mb-2 text-xs text-ink-gray-5">
                {{ __('Dofinansowanie ograniczone limitem (−{0} zł)', [formatAmount(result.dotacja_ograniczona_o)]) }}
              </div>

              <div v-if="result.linie.length" class="mb-2 overflow-hidden rounded-lg border border-gray-200">
                <div class="border-b border-gray-200 bg-gray-50 px-2.5 py-1.5 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
                  {{ __('Pozycje') }}
                </div>
                <div v-for="(line, index) in result.linie" :key="index" class="border-b border-gray-100 px-2.5 py-2 last:border-b-0">
                  <div class="mb-1 text-sm text-ink-gray-8">{{ lineName(line) }}</div>
                  <div class="flex justify-between gap-2 text-xs tabular-nums text-ink-gray-5">
                    <span>{{ formatQty(line.ilosc) }} {{ line.jednostka || '' }}</span>
                    <span>{{ __('brutto') }}: {{ plnFmt(line.brutto) }}</span>
                    <span>{{ __('dotacja') }}: {{ plnFmt(line.dotacja) }}</span>
                  </div>
                </div>
              </div>

              <div v-if="hasInternal" class="rounded-lg border border-dashed border-amber-300 bg-amber-50 p-2.5">
                <div class="mb-1.5 text-xs font-semibold uppercase tracking-wider text-amber-700">{{ __('Rozbicie kosztów (administrator)') }}</div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>{{ __('Koszt całkowity') }}</span><span>{{ plnFmt(result.wewnetrzne.koszt_calkowity) }}</span></div>
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>{{ __('Marża') }}</span><span>{{ plnFmt(result.wewnetrzne.marza) }}</span></div>
              </div>
            </div>
            <div v-else-if="!errorMsg" class="text-sm text-ink-gray-5">
              {{ __('Uzupełnij konfigurację, aby zobaczyć wycenę.') }}
            </div>

            <!-- Miejsce na przycisk generowania oferty, gdy ścieżka zapisu będzie dostępna. -->
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { call } from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  POZIOMY,
  PRACE_M2,
  STANDARDY,
  ZRODLA,
  autoM2,
  buildWejscie,
  dozwoloneDodatki,
  dostepnePoziomy,
  drzwiM2,
  opisBledu,
  pustyFormularz,
} from '@/utils/cpForm'

defineProps({
  contact: { type: Object, default: () => ({}) },
})

const form = reactive(pustyFormularz())
const loading = ref(true)
const catalogueError = ref('')
const pozycje = ref({})
const mnozniki = ref({})
const m2NaDrzwi = ref(null)
const errorMsg = ref('')
const resultReady = ref(false)
const result = reactive({
  wklad_wlasny: '',
  prowizja_handlowa: '',
  dotacja_laczna: '',
  dotacja_ograniczona_o: '',
  linie: [],
})

const standardLabels = {
  do80: __('do 80 kWh/m²·rok'),
  od80do140: __('80–140 kWh/m²·rok'),
  powyzej140: __('powyżej 140 kWh/m²·rok'),
}
const poziomLabels = {
  [POZIOMY[0]]: __('Podstawowy'),
  [POZIOMY[1]]: __('Podwyższony'),
  [POZIOMY[2]]: __('Najwyższy'),
}
const zrodloLabels = {
  pompa_ciepla: __('Pompa ciepła'),
  pellet: __('Piec na pellet'),
  zgazowujacy: __('Piec zgazowujący drewno'),
}
const workLabels = {
  elewacja: __('Elewacja'),
  strop: __('Strop'),
  dach: __('Dach'),
  okna: __('Okna'),
}

const drzwiArea = computed(() => drzwiM2(form.prace.drzwi.ilosc, m2NaDrzwi.value))
const restrictionAmount = computed(() => Number(result.dotacja_ograniczona_o) || 0)
const hasResult = computed(() => resultReady.value)
const hasInternal = computed(() => Object.prototype.hasOwnProperty.call(result, 'wewnetrzne'))

function setStandard(standard) {
  form.standard = standard
  if (!dostepnePoziomy(standard).includes(form.poziom)) form.poziom = null
}

function setZrodlo(zrodlo) {
  form.zrodlo = zrodlo
  const dodatki = dozwoloneDodatki(zrodlo)
  if (!dodatki.grzejniki) {
    form.typGrzejnikow = null
    form.iloscGrzejnikow = 0
  }
  if (!dodatki.cwu) form.cwu = false
}

function isActive(kod) {
  return pozycje.value[kod]?.aktywny !== false
}

function areaValue(kod) {
  const work = form.prace[kod]
  return work.reczne ? work.m2 : (autoM2(kod, form.powierzchnia, mnozniki.value) ?? '')
}

function enableManual(kod) {
  form.prace[kod].reczne = true
  form.prace[kod].m2 = autoM2(kod, form.powierzchnia, mnozniki.value) ?? ''
}

function disableManual(kod) {
  form.prace[kod].reczne = false
  form.prace[kod].m2 = ''
}

function clearResult() {
  resultReady.value = false
  result.wklad_wlasny = ''
  result.prowizja_handlowa = ''
  result.dotacja_laczna = ''
  result.dotacja_ograniczona_o = ''
  result.linie = []
  if (hasInternal.value) delete result.wewnetrzne
}

function formatQty(value) {
  const number = Number(value)
  return Number.isFinite(number) ? String(number) : String(value || '')
}

function formatAmount(value) {
  const number = Math.round(Number(value) || 0)
  return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

function plnFmt(value) {
  return `${formatAmount(value)} zł`
}

function lineName(line) {
  return pozycje.value[line.kod]?.nazwa || line.nazwa_kategorii || line.kod
}

let calcTimer = null
let calcRequest = 0
watch(
  form,
  () => {
    errorMsg.value = ''
    if (calcTimer) clearTimeout(calcTimer)
    calcTimer = setTimeout(runCalc, 350)
  },
  { deep: true },
)

async function runCalc() {
  const request = ++calcRequest
  const hasWork = Object.values(form.prace).some((work) => work.wybrana)
  if (!form.poziom || !form.standard || !(form.zrodlo || form.cwu || hasWork)) {
    clearResult()
    return
  }

  try {
    const data = await call('crm.api.czyste_powietrze.volteo_cp_calc', {
      wejscie: buildWejscie(form),
    })
    if (request !== calcRequest) return
    result.wklad_wlasny = data.wklad_wlasny
    result.prowizja_handlowa = data.prowizja_handlowa
    result.dotacja_laczna = data.dotacja_laczna
    result.dotacja_ograniczona_o = data.dotacja_ograniczona_o
    result.linie = data.linie || []
    resultReady.value = true
    if (Object.prototype.hasOwnProperty.call(data, 'wewnetrzne')) result.wewnetrzne = data.wewnetrzne
    else if (hasInternal.value) delete result.wewnetrzne
  } catch (error) {
    if (request !== calcRequest) return
    clearResult()
    errorMsg.value = opisBledu(error)
  }
}

onMounted(async () => {
  try {
    const data = await call('crm.api.czyste_powietrze.volteo_cp_pozycje')
    pozycje.value = Object.fromEntries((data.pozycje || []).map((pozycja) => [pozycja.kod, pozycja]))
    mnozniki.value = data.mnozniki || {}
    m2NaDrzwi.value = data.m2_na_drzwi
    for (const kod of PRACE_M2) {
      if (mnozniki.value[kod] === null) form.prace[kod].reczne = true
    }
  } catch (error) {
    catalogueError.value = opisBledu(error)
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  if (calcTimer) clearTimeout(calcTimer)
})
</script>

<style scoped>
.kalk-input,
.kalk-select {
  height: 28px;
  width: 100%;
  border-radius: 0.25rem;
  border: 1px solid #e5e5e5;
  background: #f5f5f5;
  padding: 0 8px;
  font-size: 14px;
  color: #383838;
  outline: none;
  transition: background-color 0.15s, border-color 0.15s;
  cursor: pointer;
}
.kalk-input { cursor: text; }
.kalk-input:hover,
.kalk-select:hover {
  background: #ededed;
}
.kalk-input:focus,
.kalk-select:focus {
  border-color: #a3a3a3;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.kalk-input:disabled,
.kalk-select:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
@media (max-width: 880px) {
  .kalk-split { grid-template-columns: 1fr !important; }
  .kalk-row2 { grid-template-columns: 1fr !important; }
  .kalk-output { border-left: 0 !important; padding-left: 0 !important; margin-top: 0.75rem; }
  .sticky { position: static; }
}
</style>
