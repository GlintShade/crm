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
                <!-- Prowizja/Zysk czytają z `podzial.razem`, NIE z `result.wewnetrzne`:
                     to samo źródło co tabela niżej, żeby administrator nigdy nie
                     zobaczył dwóch różnych liczb pod etykietą „Zysk" na raz — ten
                     przyklejony blok jest live'owym streszczeniem, serwer liczy
                     `wewnetrzne.prowizja_handlowa`/`wewnetrzne.zysk` tylko stawkami
                     katalogowymi, więc po edycji stawki przez administratora byłyby
                     nieaktualne. -->
                <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>{{ __('Prowizja') }}</span><span>{{ plnFmt(podzial.razem.prowizja) }}</span></div>
                <div
                  class="flex justify-between border-t border-amber-200 pt-1 text-sm font-semibold tabular-nums"
                  :class="podzial.razem.zysk < 0 ? 'text-red-600' : 'text-amber-800'"
                ><span>{{ __('Zysk') }}</span><span>{{ plnFmt(podzial.razem.zysk) }}</span></div>
              </div>
            </div>
            <div v-else-if="!errorMsg" class="text-sm text-ink-gray-5">
              {{ __('Uzupełnij konfigurację, aby zobaczyć wycenę.') }}
            </div>

            <Button
              class="mt-2 w-full"
              variant="solid"
              :disabled="!canCreateDeal || creatingDeal"
              @click="runCreateDeal"
            >
              {{ creatingDeal ? __('Tworzę szansę…') : __('Utwórz szansę') }}
            </Button>
            <div v-if="hasResult && !contactSelected" class="mt-1 text-center text-xs text-red-600">
              {{ __('Wybierz klienta, aby utworzyć szansę.') }}
            </div>
          </div>
        </div>
      </div>

      <!-- Piaskownica: podział puli między prowizję struktury a zysk ProEnergy.
           Widoczna wyłącznie dla administratora (hasInternal), bo tylko on
           dostaje `wewnetrzne` z serwera — przeglądarka niczego tu nie ukrywa,
           po prostu nie ma czego pokazać nie-administratorowi. Pełna
           szerokość (poza wąską kolumną kalk-output), bo tabela ma 9 kolumn. -->
      <div v-if="hasInternal && hasResult" class="mt-4 border-t border-gray-200 pt-4">
        <div class="mb-2 flex flex-wrap items-start justify-between gap-2">
          <div>
            <div class="text-base font-semibold text-ink-gray-9">
              {{ __('Modelowanie prowizji dla struktur sprzedażowych (administrator)') }}
            </div>
            <div class="text-xs text-ink-gray-5">
              {{ __('Zmiany poniżej są wyłącznie poglądowe — nic tutaj nie jest zapisywane ani nie trafia do oferty klienta.') }}
            </div>
          </div>
          <button
            type="button"
            class="shrink-0 rounded-md border border-transparent bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200"
            @click="sekcjaProwizjiRozwinieta = !sekcjaProwizjiRozwinieta"
          >{{ sekcjaProwizjiRozwinieta ? __('Zwiń') : __('Rozwiń') }}</button>
        </div>

        <div v-show="sekcjaProwizjiRozwinieta">
          <div class="kalk-marza-scroll">
            <table class="kalk-marza-table w-full border-collapse text-sm">
              <thead>
                <tr class="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-ink-gray-5">
                  <th class="py-1.5 pr-2">{{ __('Pozycja') }}</th>
                  <th class="py-1.5 pr-2 text-right">{{ __('Ilość') }}</th>
                  <th class="py-1.5 pr-2 text-right">{{ __('Netto') }}</th>
                  <th class="py-1.5 pr-2 text-right">{{ __('Koszt') }}</th>
                  <th class="py-1.5 pr-2 text-right">{{ __('Pula') }}</th>
                  <th class="py-1.5 pr-2 text-right">{{ __('Stawka') }}</th>
                  <th class="py-1.5 pr-2 text-right">{{ __('Prowizja') }}</th>
                  <th class="py-1.5 pr-2 text-right">{{ __('Zysk') }}</th>
                  <th class="py-1.5 text-right">{{ __('%') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="linia in podzial.linie" :key="linia.kod" class="border-b border-gray-100 tabular-nums">
                  <td class="py-1.5 pr-2 text-ink-gray-8">{{ nazwaPozycji(linia.kod) }}</td>
                  <td class="py-1.5 pr-2 text-right text-ink-gray-6">
                    {{ formatQty(linia.iloscRozliczeniowa) }} {{ linia.jednostkaRozliczeniowa === 'szt' ? __('szt') : __('m²') }}
                  </td>
                  <td class="py-1.5 pr-2 text-right text-ink-gray-7">{{ plnFmt(linia.netto) }}</td>
                  <td class="py-1.5 pr-2 text-right">
                    <div class="flex flex-col items-end gap-1">
                      <input
                        :value="koszty[linia.kod]?.jednostkowy"
                        type="text"
                        inputmode="decimal"
                        class="kalk-input kalk-input-koszt text-right"
                        :class="{ 'kalk-input-nadpisany': linia.kosztJednostkowy !== linia.kosztJednostkowyKatalogowy }"
                        :title="tytulNadpisania(linia.kosztJednostkowy, linia.kosztJednostkowyKatalogowy)"
                        @input="koszty[linia.kod] = { ...koszty[linia.kod], jednostkowy: $event.target.value }"
                      />
                      <!-- Koszt stały renderujemy WYŁĄCZNIE dla pozycji, dla których katalog
                           przewiduje niezerowy koszt stały (dziś: elewacja) — inaczej tabela
                           zapełnia się dziesięcioma polami zer bez znaczenia. Dopisek pod polem
                           jest widoczny na stałe, nie tylko w `title`, żeby było jasne bez
                           najeżdżania myszą, że ta liczba dolicza się raz, nie razy ilość. -->
                      <template v-if="linia.kosztStalyKatalogowy > 0">
                        <input
                          :value="koszty[linia.kod]?.staly"
                          type="text"
                          inputmode="decimal"
                          class="kalk-input kalk-input-koszt-staly text-right"
                          :class="{ 'kalk-input-nadpisany': linia.kosztStaly !== linia.kosztStalyKatalogowy }"
                          :title="tytulNadpisania(linia.kosztStaly, linia.kosztStalyKatalogowy)"
                          @input="koszty[linia.kod] = { ...koszty[linia.kod], staly: $event.target.value }"
                        />
                        <span class="text-[10px] leading-none text-ink-gray-5">{{ __('koszt stały — raz na ofertę') }}</span>
                      </template>
                      <div class="text-xs text-ink-gray-5">
                        {{ formatAmount(linia.kosztJednostkowy) }} × {{ formatQty(linia.iloscRozliczeniowa) }}<template v-if="linia.kosztStalyKatalogowy > 0"> + {{ formatAmount(linia.kosztStaly) }}</template> = {{ plnFmt(linia.koszt) }}
                      </div>
                    </div>
                  </td>
                  <td class="py-1.5 pr-2 text-right text-ink-gray-7">{{ plnFmt(linia.pula) }}</td>
                  <td class="py-1.5 pr-2 text-right">
                    <input
                      :value="stawki[linia.kod]"
                      type="text"
                      inputmode="decimal"
                      class="kalk-input kalk-input-stawka text-right"
                      :class="{ 'kalk-input-nadpisany': linia.stawka !== linia.stawkaKatalogowa }"
                      :title="tytulNadpisania(linia.stawka, linia.stawkaKatalogowa)"
                      @input="stawki[linia.kod] = $event.target.value"
                    />
                  </td>
                  <td class="py-1.5 pr-2 text-right text-ink-gray-7">{{ plnFmt(linia.prowizja) }}</td>
                  <td class="py-1.5 pr-2 text-right font-medium" :class="linia.zysk < 0 ? 'text-red-600' : 'text-ink-gray-8'">
                    {{ plnFmt(linia.zysk) }}
                  </td>
                  <td class="py-1.5 text-right text-ink-gray-6">{{ formatPercent(linia.zyskProc) }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr class="border-t-2 border-gray-300 font-semibold tabular-nums">
                  <td class="py-1.5 pr-2 text-ink-gray-9">{{ __('RAZEM') }}</td>
                  <td class="py-1.5 pr-2"></td>
                  <td class="py-1.5 pr-2 text-right">{{ plnFmt(podzial.razem.netto) }}</td>
                  <td class="py-1.5 pr-2 text-right">{{ plnFmt(podzial.razem.koszt) }}</td>
                  <td class="py-1.5 pr-2 text-right">{{ plnFmt(podzial.razem.pula) }}</td>
                  <td class="py-1.5 pr-2"></td>
                  <td class="py-1.5 pr-2 text-right">{{ plnFmt(podzial.razem.prowizja) }}</td>
                  <td class="py-1.5 pr-2 text-right" :class="podzial.razem.zysk < 0 ? 'text-red-600' : ''">
                    {{ plnFmt(podzial.razem.zysk) }}
                  </td>
                  <td class="py-1.5 text-right">{{ formatPercent(podzial.razem.zyskProc) }}</td>
                </tr>
              </tfoot>
            </table>
          </div>

          <div class="mt-3 max-w-xs rounded-lg border border-gray-200 bg-gray-50 p-2.5 text-sm tabular-nums">
            <div class="flex justify-between py-0.5 text-ink-gray-7">
              <span>{{ __('Przychód netto') }}</span><span>{{ plnFmt(podzial.razem.netto) }}</span>
            </div>
            <div class="flex justify-between py-0.5 text-ink-gray-7">
              <span>{{ __('− Koszt ProEnergy') }}</span><span>{{ plnFmt(podzial.razem.koszt) }}</span>
            </div>
            <div class="flex justify-between border-t border-gray-200 py-0.5 pt-1 font-medium text-ink-gray-8">
              <span>{{ __('= Marża brutto') }}</span>
              <span>{{ plnFmt(podzial.razem.pula) }} <span class="font-normal text-ink-gray-5">({{ formatPercent(podzial.razem.marzaProc) }} {{ __('netto') }})</span></span>
            </div>
            <div class="flex justify-between py-0.5 text-ink-gray-7">
              <span>{{ __('− Prowizja struktury') }}</span><span>{{ plnFmt(podzial.razem.prowizja) }}</span>
            </div>
            <div
              class="flex justify-between border-t border-gray-200 py-0.5 pt-1 font-semibold"
              :class="podzial.razem.zysk < 0 ? 'text-red-600' : 'text-ink-gray-9'"
            >
              <span>{{ __('= ZYSK ProEnergy') }}</span>
              <span>
                {{ plnFmt(podzial.razem.zysk) }}
                <span class="font-normal" :class="podzial.razem.zysk < 0 ? 'text-red-600' : 'text-ink-gray-5'">
                  ({{ formatPercent(podzial.razem.zyskProc) }} {{ __('netto') }})
                </span>
              </span>
            </div>
          </div>

          <button
            type="button"
            class="mt-2 rounded-md border border-transparent bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200"
            @click="resetWartosci"
          >{{ __('Przywróć wartości katalogowe') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button, call, toast } from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
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
import {
  przeliczPodzial,
  scalStawki,
  stawkiPoczatkowe,
  scalKoszty,
  kosztyPoczatkowe,
} from '@/utils/cpMarza'

const props = defineProps({
  contact: { type: Object, default: () => ({}) },
})

const router = useRouter()

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
  // Klucz istnieje od startu (wartość `null`, nigdy `delete`) celowo — patrz
  // komentarz przy `hasInternal` niżej: usuwanie i doczytywanie klucza przez
  // `hasOwnProperty` na obiekcie `reactive` po cichu psuje reaktywność.
  wewnetrzne: null,
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
// NIE używać tu `Object.prototype.hasOwnProperty.call(result, 'wewnetrzne')`.
// `result` jest obiektem `reactive` (Proxy) — Vue śledzi zależności wyłącznie
// przez pułapki `get`/`has`/`ownKeys`/`deleteProperty`; `hasOwnProperty`
// wywołuje `[[GetOwnProperty]]` (pułapka `getOwnPropertyDescriptor`), której
// `MutableReactiveHandler` NIE definiuje. Taki odczyt nie rejestruje żadnej
// zależności, więc `computed` zostaje policzony raz i zamrożony na starcie —
// dokładnie to się stało: pierwsze wywołanie (zawsze przy niekompletnym
// formularzu, przez `clearResult()`) betonowało `false` na całą sesję, mimo
// że serwer poprawnie zwracał `wewnetrzne`. Zwykły odczyt właściwości
// (`result.wewnetrzne`) przechodzi przez pułapkę `get`, która JEST śledzona.
const hasInternal = computed(() => Boolean(result.wewnetrzne))

// --- Modelowanie prowizji dla struktur sprzedażowych (administrator) --------
// `stawki` i `koszty` PRZEŻYWAJĄ kolejne przeliczenia (scalStawki/scalKoszty
// w runCalc scalają je z nowym cennikiem zamiast nadpisywać katalogowymi
// wartościami) — główny scenariusz użycia to porównanie kilku konfiguracji
// formularza przy TYM SAMYM cenniku partnerskim, więc reset na każdą zmianę
// formularza unieważniałby narzędzie. Jedyny sposób na powrót do wartości
// katalogowych to przycisk „Przywróć wartości katalogowe" (resetWartosci
// niżej). To piaskownica: nic stąd nie trafia do zapisu ani do dokumentu
// klienta.
const stawki = ref({})
// `koszty[kod]` to `{ jednostkowy, staly }` — koszt stały jest edytowalny
// tylko tam, gdzie katalog przewiduje go niezerowym (dziś: `elewacja`), ale
// stan trzyma oba pola dla każdego kodu jednolicie; przeliczPodzial i tak
// bierze katalogowe 0 dla pól, których administrator nigdy nie dotknął.
const koszty = ref({})
const sekcjaProwizjiRozwinieta = ref(true)
// `razem.marzaProc` and `razem.zyskProc` are computed inside przeliczPodzial
// itself (both as % of netto) so the component never re-derives the same
// ratio by hand — see cpMarza.js.
const podzial = computed(() =>
  przeliczPodzial(result.wewnetrzne?.linie ?? [], stawki.value, koszty.value),
)

function resetWartosci() {
  if (!hasInternal.value) return
  stawki.value = stawkiPoczatkowe(result.wewnetrzne.linie)
  koszty.value = kosztyPoczatkowe(result.wewnetrzne.linie)
}

function nazwaPozycji(kod) {
  return pozycje.value[kod]?.nazwa || kod
}

// Wskaźnik nadpisania: porównujemy WYLICZONE (sparsowane) wartości z
// `podzial.linie`, nie surowy tekst inputa — administrator może wpisać
// "3000" gdy katalog trzyma "3000.00" i to wciąż jest ta sama liczba, więc
// nie ma czego podświetlać. Tytuł inputa pokazuje wartość katalogową, żeby
// dało się wrócić do niej myślą bez klikania „Przywróć wartości katalogowe".
function tytulNadpisania(aktualna, katalogowa) {
  return aktualna !== katalogowa
    ? __('Katalogowo: {0}', [plnFmt(katalogowa)])
    : undefined
}

// --- Tworzenie szansy --------------------------------------------------------
// `hasResult` już odzwierciedla kompletność formularza: staje się prawdziwe
// dopiero, gdy serwer zaakceptuje wycenę (patrz runCalc niżej), więc nie
// duplikujemy tu logiki walidacji formularza.
const c = computed(() => props.contact || {})
const contactSelected = computed(() => Boolean(c.value.name))
const canCreateDeal = computed(() => hasResult.value && contactSelected.value)
const creatingDeal = ref(false)

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
  // `= null`, never `delete` — see the comment above `hasInternal`. Deleting
  // the key would put us right back in a state where `hasOwnProperty` (if
  // anyone reintroduces it) can no longer see the property at all.
  result.wewnetrzne = null
  // `stawki`/`koszty` are deliberately NOT reset here — `podzial` is a
  // computed that reads `hasInternal`, so it collapses to an empty split on
  // its own once `wewnetrzne` is gone. Wiping them too would defeat the
  // "compare configurations against the same rate card" workflow the moment
  // the form passes through a momentarily invalid state.
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

// formatAmount rounds to whole złoty, which flattens the profit-margin
// percentages in the commission-modeling section to e.g. "17%" vs "16,6%" —
// not precise enough to tell "sustainable" from "barely positive" apart.
function formatPercent(value) {
  const number = Number(value)
  const safe = Number.isFinite(number) ? number : 0
  return `${safe.toFixed(1).replace('.', ',')}%`
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
    // `data` is a plain object freshly parsed from the server response, not
    // the `reactive` `result` — `hasOwnProperty` is safe here (see the
    // comment above `hasInternal` for why it is NOT safe on `result`).
    if (Object.prototype.hasOwnProperty.call(data, 'wewnetrzne')) {
      result.wewnetrzne = data.wewnetrzne
      // Merge, never overwrite — see the comment above `stawki` declaration.
      stawki.value = scalStawki(stawki.value, data.wewnetrzne.linie)
      koszty.value = scalKoszty(koszty.value, data.wewnetrzne.linie)
    } else if (hasInternal.value) {
      result.wewnetrzne = null
    }
  } catch (error) {
    if (request !== calcRequest) return
    clearResult()
    errorMsg.value = opisBledu(error)
  }
}

async function runCreateDeal() {
  if (!canCreateDeal.value || creatingDeal.value) return
  creatingDeal.value = true
  try {
    const data = await call('crm.api.czyste_powietrze.volteo_cp_create_deal', {
      wejscie: buildWejscie(form),
      contact: c.value.name,
    })
    router.push({ name: 'Deal', params: { dealId: data.deal } })
  } catch (error) {
    toast.error(opisBledu(error))
  } finally {
    creatingDeal.value = false
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
.kalk-input-stawka {
  width: 84px;
  margin-left: auto;
}
.kalk-input-koszt {
  width: 92px;
  margin-left: auto;
}
.kalk-input-koszt-staly {
  width: 92px;
  margin-left: auto;
}
/* Wskaźnik nadpisania: pole, którego wartość różni się od katalogowej,
   dostaje inne tło i obramowanie — po kilku wariantach ma być widać na
   pierwszy rzut oka, które liczby są prawdziwe (katalogowe), a które
   zmodelowane. Wartość katalogowa jest w atrybucie `title` na inpucie. */
.kalk-input-nadpisany {
  background: #fef3c7;
  border-color: #d97706;
}
.kalk-input-nadpisany:hover {
  background: #fde8a8;
}
.kalk-input-nadpisany:focus {
  background: #fff;
  border-color: #d97706;
}
.kalk-marza-scroll {
  overflow-x: auto;
}
.kalk-marza-table {
  min-width: 760px;
}
@media (max-width: 880px) {
  .kalk-split { grid-template-columns: 1fr !important; }
  .kalk-row2 { grid-template-columns: 1fr !important; }
  .kalk-output { border-left: 0 !important; padding-left: 0 !important; margin-top: 0.75rem; }
  .sticky { position: static; }
  .kalk-marza-table { min-width: 620px; }
  .kalk-input-stawka { width: 68px; }
  .kalk-input-koszt { width: 76px; }
  .kalk-input-koszt-staly { width: 76px; }
}
</style>
