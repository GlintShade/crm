<!--
  Kalkulator OZE -- cztery nowe rodzaje instalacji (Rozbudowa PV/ME,
  Klimatyzacja, Pompa ciepła, Kocioł; b68, "Wielki update kalkulatora OZE",
  chunk F3). Renderowany przez KalkulatorTab.vue (rodzic) w miejsce grida
  `.kalk-split` i bloku `done`, gdy `czyNowyRodzaj(sel.variant)` jest
  prawdziwe. Układ i słownik interakcji ("Wariant A, kokpit z paragonem")
  są te same co w KalkulatorTab.vue: sekcja 1 z kontrolkami segmentowymi
  (trzy warianty PV obok listy "Inne rodzaje" pokazującej aktywny nowy
  rodzaj), sekcja 2 z konfiguracją urządzenia, zwijane Finansowanie i
  prawa kolumna z paragonem (KalkulatorParagon.vue).

  ZERO matematyki cenowej w tym pliku (ten sam naglowek-komentarz co
  KalkulatorTab.vue/KalkulatorCPTab.vue) -- wycena jest zawsze liczona od
  nowa na serwerze przez `crm.api.kalkulator_oze.volteo_oze_calc`/
  `volteo_oze_create_deal`; logika formularza/kaskad zyje w `utils/ozeForm.js`.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto">
    <div class="mx-auto w-full max-w-[1180px] px-4 py-3">
      <div
        v-if="errorMsg"
        class="mb-2.5 flex items-center justify-between rounded border border-outline-red-3 bg-surface-red-2 px-3 py-2 text-sm text-ink-red-8"
      >
        <span>{{ errorMsg }}</span>
        <button class="ml-2 text-base font-bold leading-none" @click="errorMsg = ''">×</button>
      </div>

      <template v-if="flow !== 'done'">
        <div class="kalk-split grid items-start gap-x-5" style="grid-template-columns: minmax(0, 1.55fr) minmax(280px, 1fr)">
          <div>
            <!-- 1. Instalacja i klient (zawsze otwarta) -->
            <div class="kalk-part">
              <div class="kalk-part-heading mb-4 flex items-center gap-2 border-b border-outline-gray-1 pb-2.5 text-lg font-bold text-ink-gray-9">
                <span class="kalk-part-number">1</span>{{ __('Instalacja i klient') }}
                <FeatherIcon v-if="sekcja1Gotowa" name="check" class="h-4 w-4 text-ink-green-6" />
              </div>

              <div>
                <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Rodzaj instalacji') }}</div>
                <div class="flex flex-wrap items-center gap-2">
                  <WyborSegmentowy :model-value="''" :options="VARIANTS" @update:model-value="wybierzRodzaj" />
                  <select class="kalk-select kalk-select-inline" :aria-label="__('Inne rodzaje')" :value="form.rodzaj" @change="wybierzInnyRodzaj($event)">
                    <option value="">{{ __('Inne rodzaje') }}</option>
                    <option v-for="r in RODZAJE_NOWE" :key="r" :value="r">{{ r }}</option>
                  </select>
                </div>
              </div>

              <div class="mt-3 grid items-start grid-cols-2 gap-x-3 gap-y-3 kalk-row2">
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Typ klienta') }}</div>
                  <WyborSegmentowy v-model="form.typKlienta" :options="TYP_KLIENTA_OPTIONS" />
                </div>
              </div>
            </div>

            <div v-if="loading" class="kalk-part py-8 text-center text-sm text-ink-gray-5">
              {{ __('Ładowanie kalkulatora…') }}
            </div>
            <div v-else-if="catalogueError" class="kalk-part text-sm text-ink-red-8">
              {{ catalogueError }}
            </div>

            <template v-else>
              <!-- 2. Konfiguracja specyficzna dla rodzaju (zawsze otwarta) -->
              <div class="kalk-part">
                <div class="kalk-part-heading mb-4 flex items-center gap-2 border-b border-outline-gray-1 pb-2.5 text-lg font-bold text-ink-gray-9">
                  <span class="kalk-part-number">2</span>{{ __('Konfiguracja') }}
                  <FeatherIcon v-if="sekcja2Gotowa" name="check" class="h-4 w-4 text-ink-green-6" />
                </div>

                <!-- ROZBUDOWA -->
                <div v-if="form.rodzaj === OZE_ROZBUDOWA">
                  <div
                    v-for="blok in blokiRozbudowy" :key="blok.klucz"
                    class="border-t border-outline-gray-1 py-2.5 first:border-t-0 first:pt-0"
                  >
                    <div class="mb-0.5 text-sm text-ink-gray-5">
                      {{ blok.etykieta }}
                      <span v-if="blok.opis"> · {{ blok.opis }}</span>
                    </div>
                    <div class="flex flex-wrap items-center gap-2">
                      <WyborSegmentowy
                        :model-value="form.rozbudowa[blok.klucz] > 0 ? 'Tak' : 'Nie'"
                        :options="NIE_TAK"
                        :disabled="elementRozbudowyZablokowany(form.rozbudowa, blok.klucz)"
                        @update:model-value="przelaczRozbudowa(blok.klucz)"
                      />
                      <select
                        v-if="form.rozbudowa[blok.klucz] > 0"
                        v-model.number="form.rozbudowa[blok.klucz]"
                        class="kalk-select kalk-select-wariant"
                      >
                        <option v-for="n in blok.max" :key="n" :value="n">{{ n }} {{ odmianaPaneli(n) }}</option>
                      </select>
                    </div>
                    <p v-if="opisBlokady(blok.klucz)" class="mt-1 text-xs text-ink-gray-5">{{ opisBlokady(blok.klucz) }}</p>
                  </div>

                  <div class="mt-2 grid items-start grid-cols-2 gap-x-3 gap-y-3 kalk-row2">
                    <div>
                      <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Czy klient ma już instalację PV?') }}</div>
                      <WyborSegmentowy v-model="form.rozbudowa.istniejacaPv" :options="NIE_TAK" />
                    </div>
                    <div v-if="form.rozbudowa.istniejacaPv === 'Tak'" class="relative">
                      <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Moc istniejącej instalacji (kWp)') }}</div>
                      <input v-model.number="form.rozbudowa.istniejacaPvMocKwp" type="number" min="0" step="0.1" class="kalk-input kalk-input-unit" />
                      <span class="kalk-unit">kWp</span>
                    </div>
                    <div class="col-span-2">
                      <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Uzgodnienia PPOŻ') }}</div>
                      <div v-if="ppozProgLive" class="flex flex-wrap items-center gap-1.5 text-sm">
                        <FeatherIcon name="lock" class="h-3.5 w-3.5 text-ink-gray-5" />
                        <span class="font-semibold text-ink-gray-9">{{ __('Tak') }}</span>
                        <span class="text-ink-gray-5">{{ __('suma mocy nowej i istniejącej instalacji przekracza 6,5 kW') }}</span>
                      </div>
                      <template v-else>
                        <WyborSegmentowy v-model="form.rozbudowa.ppozRecznie" :options="NIE_TAK" />
                        <div class="mt-0.5 text-xs text-ink-gray-4">
                          {{ __('Ustaw Tak ręcznie, jeśli aktualna moc PV i dokładana moc PV w sumie przekroczą 6,5 kW.') }}
                        </div>
                      </template>
                    </div>
                  </div>
                </div>

                <!-- KLIMATYZACJA -->
                <div v-else-if="form.rodzaj === OZE_KLIMATYZACJA">
                  <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Rodzaj klimatyzacji') }}</div>
                  <WyborSegmentowy
                    :model-value="form.klimatyzacja.grupa"
                    :options="opcjeGrupyKlimy"
                    @update:model-value="wybierzGrupaKlimy"
                  />

                  <div v-if="form.klimatyzacja.grupa" class="mt-3">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Model') }}</div>
                    <WyborSegmentowy
                      :model-value="form.klimatyzacja.klucz"
                      :options="opcjeModeliKlimy"
                      @update:model-value="wybierzModelKlimy"
                    />
                  </div>

                  <div v-if="form.klimatyzacja.klucz" class="mt-3">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Moc') }}</div>
                    <select :value="form.klimatyzacja.kod" class="kalk-select" @change="wybierzMocKlimy($event.target.value)">
                      <option value="">{{ __('-- wybierz --') }}</option>
                      <option v-for="o in moceKlimyList" :key="o.kod" :value="o.kod">
                        {{ formatMoc(o.moc_kw) }} kW<template v-if="o.opis"> ({{ o.opis }})</template>
                      </option>
                    </select>
                  </div>
                </div>

                <!-- POMPA CIEPŁA -->
                <div v-else-if="form.rodzaj === OZE_POMPA_CIEPLA">
                  <div class="mb-3">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Zapotrzebowanie budynku na moc') }}</div>
                    <select v-model="form.pompa.zapotrzebowanie" class="kalk-select">
                      <option value="">{{ __('-- wybierz --') }}</option>
                      <option v-for="z in dane.zapotrzebowanie" :key="z.value" :value="z.value">{{ z.label }}</option>
                    </select>
                    <div class="mt-0.5 text-xs text-ink-gray-4">{{ __('Wartość na podstawie wyniku z ciepło.app.') }}</div>
                  </div>

                  <div class="mb-3">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Producent') }}</div>
                    <WyborSegmentowy
                      :model-value="form.pompa.producent"
                      :options="producenciPcList"
                      @update:model-value="wybierzProducentaPc"
                    />
                  </div>

                  <div class="mb-3">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Typ') }}</div>
                    <WyborSegmentowy v-model="form.pompa.typ" :options="opcjeTypowPc" />
                  </div>

                  <div class="mb-3">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Ogrzewanie') }}</div>
                    <WyborSegmentowy v-model="form.pompa.ogrzewanie" :options="OGRZEWANIE_OPCJE" />
                  </div>

                  <div class="mb-3">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Moc pompy ciepła (dobrana automatycznie)') }}</div>
                    <div v-if="!pcBrakDoboruLive && !bladDoboruSerwer" class="text-sm font-semibold text-ink-gray-9">
                      <template v-if="mocPcLiveLabel">{{ mocPcLiveLabel }}</template>
                      <span v-else class="font-normal text-ink-gray-4">-</span>
                    </div>
                    <!-- `bladDoboruSerwer` to druga linia obrony (patrz komentarz przy
                    `runCalc` w <script>) -- komunikat serwera, gdy ten kiedykolwiek
                    znajdzie "Brak doboru" mimo ze lokalny `pcBrakDoboruLive` byl `false`.
                    Ostrzezenie dla handlowca: neutralny styl informacyjny, nie bursztyn
                    (bursztyn zarezerwowany dla paneli administratora). -->
                    <div v-else class="rounded-md border border-outline-blue-2 bg-surface-blue-2 px-2.5 py-2 text-sm text-ink-blue-6">
                      {{ bladDoboruSerwer || __('Brak doboru pompy ciepła dla podanego zapotrzebowania. Najpierw ocieplenie budynku.') }}
                    </div>
                  </div>

                  <div class="mb-3">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Zasobnik CWU') }}</div>
                    <WyborSegmentowy v-model="form.pompa.cwu" :options="CWU_OPCJE" />
                  </div>

                  <div>
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Grzejniki niskotemperaturowe') }}</div>
                    <WyborSegmentowy
                      :model-value="grzejnikiWlaczone ? 'Tak' : 'Nie'"
                      :options="NIE_TAK"
                      @update:model-value="przelaczGrzejniki"
                    />

                    <div v-if="grzejnikiWlaczone" class="kalk-grzejniki-grid mt-2 grid grid-cols-5 items-start gap-2">
                      <div v-for="rozmiar in rozmiaryGrzejnikowList" :key="rozmiar.rozmiar">
                        <div class="mb-0.5 text-xs text-ink-gray-5">{{ rozmiar.nazwa || rozmiar.rozmiar }}</div>
                        <select
                          :value="form.pompa.grzejniki[rozmiar.rozmiar]"
                          class="kalk-select"
                          @change="ustawGrzejnik(rozmiar.rozmiar, $event.target.value)"
                        >
                          <option v-for="n in opcjeIlosciGrzejnika(form.pompa.grzejniki, rozmiar.rozmiar)" :key="n" :value="n">{{ n }}</option>
                        </select>
                      </div>
                      <div class="kalk-grzejniki-razem col-span-5 text-xs text-ink-gray-5">
                        {{ __('Razem: {0} / {1}', [sumaGrzejnikow(form.pompa.grzejniki), GRZEJNIKI_MAX]) }}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- KOCIOŁ -->
                <div v-else-if="form.rodzaj === OZE_KOCIOL">
                  <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Rodzaj kotła') }}</div>
                  <WyborSegmentowy
                    :model-value="form.kociol.typ"
                    :options="opcjeTypowKociol"
                    @update:model-value="wybierzTypKociol"
                  />

                  <div v-if="form.kociol.typ" class="mt-3">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Model') }}</div>
                    <select v-model="form.kociol.kod" class="kalk-select">
                      <option value="">{{ __('-- wybierz --') }}</option>
                      <option v-for="o in modeleKociolList" :key="o.kod" :value="o.kod">
                        {{ o.nazwa }}<template v-if="o.moc_kw"> ({{ formatMoc(o.moc_kw) }} kW)</template>
                      </option>
                    </select>
                  </div>

                  <div class="mt-3">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Zasobnik CWU') }}</div>
                    <WyborSegmentowy v-model="form.kociol.cwu" :options="CWU_OPCJE" />
                  </div>
                </div>
              </div>

              <!-- 3. Finansowanie (zwijana) -->
              <div class="kalk-part kalk-part-zwijana">
                <button type="button" class="kalk-part-toggle" :aria-expanded="otwarteFinansowanie" @click="otwarteFinansowanie = !otwarteFinansowanie">
                  <span class="kalk-part-number">3</span>
                  <span class="min-w-0 flex-1 text-left">
                    <span class="block text-lg font-bold text-ink-gray-9">{{ __('Finansowanie') }}</span>
                    <span v-if="!otwarteFinansowanie" class="mt-1 flex flex-wrap gap-1">
                      <span v-for="(p, i) in finansowaniePodsumowanie" :key="i" class="rounded-full bg-surface-gray-2 px-2 py-0.5 text-xs whitespace-nowrap text-ink-gray-7">{{ p.tekst }}</span>
                    </span>
                  </span>
                  <FeatherIcon :name="otwarteFinansowanie ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 shrink-0 text-ink-gray-5" />
                </button>

                <div v-if="otwarteFinansowanie" class="mt-4 grid items-start grid-cols-2 gap-x-3 gap-y-3">
                  <div v-if="ulgaDotyczyRodzaju">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Ulga termomodernizacyjna') }}</div>
                    <select v-model.number="form.ulgaPct" class="kalk-select">
                      <option :value="12">12%</option>
                      <option :value="19">19%</option>
                    </select>
                  </div>
                  <div>
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Okres finansowania (lat)') }}</div>
                    <select v-model.number="form.okresLat" class="kalk-select">
                      <option v-for="n in 10" :key="n" :value="n">{{ n }}</option>
                    </select>
                  </div>
                  <div class="relative">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Wpłata własna (PLN)') }}</div>
                    <input v-model.number="form.wplataWlasna" type="number" min="0" step="0.01" class="kalk-input kalk-input-unit" />
                    <span class="kalk-unit">zł</span>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <div class="kalk-output self-stretch border-l border-outline-gray-2 pl-5">
            <div class="kalk-sticky sticky top-3">
              <div v-if="$slots['client-picker']" class="mb-3 w-full min-w-0">
                <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Klient') }}</div>
                <slot name="client-picker" />
              </div>
              <div class="mb-2 text-base font-semibold text-ink-gray-9">{{ __('Wycena') }}</div>

              <KalkulatorParagon
                :summary="paragonSummary"
                :typ-klienta="form.typKlienta"
                :ulga-pct="Number(form.ulgaPct)"
                :okres-lat="Number(form.okresLat)"
                :pokaz-dotacje="false"
                :pokaz-ulge="ulgaDotyczyRodzaju"
                :pokaz-rate="true"
              />

              <Button
                class="mt-3 w-full"
                variant="solid"
                :disabled="!canGenerate || generating"
                @click="runCreateDeal"
              >{{ generating ? __('Generuję ofertę…') : __('Generuj ofertę') }}</Button>

              <div v-if="powodBrakuDoboru" class="mt-1 text-center text-xs text-ink-red-6">
                {{ powodBrakuDoboru }}
              </div>
              <div v-else-if="!contactSelected" class="mt-1 text-center text-xs text-ink-gray-5">
                {{ __('Wybierz klienta powyżej, aby wygenerować ofertę.') }}
              </div>

              <div class="mt-3">
                <button
                  type="button"
                  class="flex w-full items-center justify-between rounded-lg border border-outline-gray-2 px-2.5 py-1.5 text-sm text-ink-gray-7 hover:bg-surface-gray-2"
                  :aria-expanded="showNarzut"
                  @click="showNarzut = !showNarzut"
                >
                  <span>{{ __('Ustawienia niestandardowe') }}</span>
                  <FeatherIcon :name="showNarzut ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 text-ink-gray-5" />
                </button>
                <div v-if="showNarzut" class="mt-1.5 rounded-lg border border-outline-gray-2 px-2.5 py-1.5">
                  <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Wysokość narzutu') }}</div>
                  <input
                    v-model.number="form.narzut" type="number" min="0" :max="narzutMax > 0 ? narzutMax : undefined" step="0.01"
                    class="kalk-input"
                    @blur="form.narzut = narzutMax > 0 ? Math.min(narzutMax, Math.max(0, Number(form.narzut) || 0)) : Math.max(0, Number(form.narzut) || 0)"
                  />
                  <div v-if="!narzutValid" class="mt-0.5 text-xs text-ink-red-6">{{ narzutErrorMsg }}</div>
                </div>
              </div>

              <div v-if="hasInternal" class="mt-2.5">
                <button
                  type="button"
                  class="flex w-full items-center justify-between rounded-md border border-outline-amber-3 bg-surface-amber-2 px-2.5 py-1.5 text-sm font-semibold text-ink-amber-8 transition-colors hover:bg-surface-amber-3"
                  @click="showAdminBreakdown = !showAdminBreakdown"
                >
                  <span>{{ __('Admin - Ustawienia Zaawansowane') }}</span>
                  <FeatherIcon :name="showAdminBreakdown ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 text-ink-amber-8" />
                </button>
                <div v-show="showAdminBreakdown" class="mt-1.5 rounded-lg border border-dashed border-outline-amber-3 bg-surface-amber-2 p-2.5">
                  <div class="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-amber-8">{{ __('Rozbicie kosztów (administrator)') }}</div>
                  <div v-for="grupa in wewnetrzneGrupy.grupy" :key="grupa.klucz">
                    <div class="mt-2 mb-0.5 text-xs font-semibold uppercase tracking-wider text-ink-amber-8">{{ grupa.etykieta }}</div>
                    <div v-for="p in grupa.pozycje" :key="p.klucz" class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>{{ p.etykieta }}</span><span>{{ formatPln(p.kwota) }}</span></div>
                    <div class="mt-1 flex justify-between border-t border-outline-amber-2 pt-1 text-sm font-semibold tabular-nums text-ink-gray-9"><span>{{ __('Razem') }}</span><span>{{ formatPln(grupa.suma) }}</span></div>
                  </div>
                  <div class="mt-2 flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>{{ __('Narzut handlowca') }}</span><span>{{ formatPln(wewnetrzneGrupy.narzut) }}</span></div>
                  <div class="mt-1 flex justify-between border-t border-outline-amber-2 pt-1 text-sm font-semibold tabular-nums text-ink-gray-9"><span>{{ __('Marża') }}</span><span>{{ formatPln(wewnetrzneGrupy.marza) }}</span></div>
                  <div class="flex justify-between text-sm font-semibold tabular-nums" :class="wewnetrzneGrupy.zysk < 0 ? 'text-ink-red-6' : 'text-ink-amber-8'"><span>{{ __('Zysk') }}</span><span>{{ formatPln(wewnetrzneGrupy.zysk) }}</span></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div v-else class="py-4">
        <div class="mb-2 text-base font-semibold text-ink-gray-9">{{ __('Szansa utworzona') }}</div>
        <p class="mb-3 text-sm text-ink-gray-7">{{ successSummary }}</p>
        <div class="flex gap-2">
          <a class="inline-flex items-center rounded bg-surface-gray-10 px-3 py-1.5 text-sm font-medium text-ink-base hover:bg-surface-gray-9" :href="dealHref" target="_blank" rel="noopener">{{ __('Otwórz szansę w CRM') }}</a>
          <Button variant="ghost" @click="resetFlow">{{ __('Nowa oferta') }}</Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { call, Button, FeatherIcon } from 'frappe-ui'
import { VARIANTS, podsumowanieFinansowania, ppozWymuszonyProgiem } from '@/utils/pvForm'
import { formatPln } from '@/utils/money'
import KalkulatorParagon from './KalkulatorParagon.vue'
import WyborSegmentowy from './WyborSegmentowy.vue'
import {
  ETYKIETA_GRUPY_KLIMY,
  GRUPY_KLIMY,
  GRZEJNIKI_MAX,
  OZE_KLIMATYZACJA,
  OZE_KOCIOL,
  OZE_POMPA_CIEPLA,
  OZE_ROZBUDOWA,
  RODZAJE_NOWE,
  brakDoboru,
  czyNowyRodzaj,
  dobierzMocPc,
  grupujWewnetrzneOze,
  kaskadaKlimy,
  kompletnyFormOze,
  kompletnyPompa,
  modeleKlimy,
  moceKlimy,
  odmianaPaneli,
  opcjeIlosciGrzejnika,
  producenciPc,
  pustyFormularzOze,
  rozmiaryGrzejnikow,
  sumaGrzejnikow,
  typyPcDostepne,
  ulgaDotyczy,
  zbudujPayloadOze,
  przelaczElementRozbudowy,
  elementRozbudowyZablokowany,
} from '@/utils/ozeForm'

const props = defineProps({
  contact: { type: Object, default: () => ({}) },
  rodzaj: { type: String, default: '' },
})
const emit = defineEmits(['update:rodzaj'])

const router = useRouter()

const TYP_KLIENTA_OPTIONS = [
  { value: 'indywidualny', label: 'Indywidualny' },
  { value: 'biznesowy', label: 'Biznesowy' },
]
const NIE_TAK = ['Nie', 'Tak']
const CWU_OPCJE = [
  { value: '', label: 'Nie' },
  { value: '200', label: '200 l' },
  { value: '300', label: '300 l' },
]
const TYPY_PC_WSZYSTKIE = ['Monoblok', 'Split']
const OGRZEWANIE_OPCJE = ['Podłogówka', 'Grzejniki', 'Mieszane']
const KOCIOL_TYPY = [
  { klucz: 'kociol_pellet', etykieta: 'Pellet' },
  { klucz: 'kociol_duo', etykieta: 'Drewno (DUO)' },
]

// --- Stan formularza ---------------------------------------------------------
const form = reactive(pustyFormularzOze(czyNowyRodzaj(props.rodzaj) ? props.rodzaj : OZE_ROZBUDOWA))

watch(
  () => props.rodzaj,
  (nowy) => {
    if (czyNowyRodzaj(nowy) && nowy !== form.rodzaj) {
      form.rodzaj = nowy
      errorMsg.value = ''
      clearResult()
    }
  },
)

// Kliknięcie starego wariantu (PV/PV+ME/ME) oddaje kontrolę rodzicowi --
// KalkulatorTab.vue przełączy v-if na swój własny grid, ten komponent
// zostanie odmontowany. Kliknięcie jednego z czterech nowych rodzajów
// aktualizuje formularz lokalnie I emituje w górę, żeby `sel.variant`
// rodzica (prop `rodzaj`, v-model) został zsynchronizowany.
function wybierzRodzaj(r) {
  if (r === form.rodzaj) return
  if (czyNowyRodzaj(r)) {
    form.rodzaj = r
    errorMsg.value = ''
    clearResult()
  }
  emit('update:rodzaj', r)
}

// Lista "Inne rodzaje" pokazuje aktywny nowy rodzaj jako swoja wartosc; wybor
// pustej pozycji (placeholder) nic nie zmienia, wiec przywracamy wyswietlana
// wartosc.
function wybierzInnyRodzaj(event) {
  const v = event.target.value
  if (v) wybierzRodzaj(v)
  else event.target.value = form.rodzaj
}

// --- Katalog -------------------------------------------------------------
const loading = ref(true)
const catalogueError = ref('')
const dane = reactive({ pozycje: [], dobor: [], zapotrzebowanie: [] })
const narzutMax = ref(0)

onMounted(async () => {
  try {
    const data = await call('crm.api.kalkulator_oze.volteo_oze_pozycje')
    dane.pozycje = data.pozycje || []
    dane.dobor = data.dobor || []
    dane.zapotrzebowanie = data.zapotrzebowanie || []
    dane.ppoz = Number(data.ppoz) || 0
    dane.panelMocWp = Number(data.panel_moc_wp) || 500
    narzutMax.value = Number(data.narzut_max) || 0
  } catch (err) {
    catalogueError.value = extractErrorMessage(err)
  } finally {
    loading.value = false
  }
})

// --- Rozbudowa: bloki panele/panele+mikro/bateria ---------------------------
const blokiRozbudowy = [
  { klucz: 'panele', etykieta: 'Panele PV', max: 5, opis: '' },
  { klucz: 'paneleMikro', etykieta: 'Panele PV + mikrofalownik', max: 5, opis: '' },
  { klucz: 'bateria', etykieta: 'Moduł baterii', max: 4, opis: '5 kWh / moduł' },
]

function przelaczRozbudowa(klucz) {
  if (elementRozbudowyZablokowany(form.rozbudowa, klucz)) return
  form.rozbudowa = przelaczElementRozbudowy(form.rozbudowa, klucz)
}

function opisBlokady(klucz) {
  if (!elementRozbudowyZablokowany(form.rozbudowa, klucz)) return ''
  return klucz === 'panele' ? 'Niedostępne razem z panelami PV + mikrofalownik' : 'Niedostępne razem z panelami PV'
}

// Stan wyniku kalkulacji (serwer) -- zadeklarowany TUTAJ, przed
// `ppozProgLive` nizej, bo ten computed jest odczytywany synchronicznie w
// chwili tworzenia (`watch(ppozProgLive, ...)` ewaluuje swoje zrodlo raz
// przy starcie, zeby ustalic wartosc poczatkowa do porownania, niezaleznie
// od opcji `immediate`). `const result` zadeklarowany nizej w pliku trafilby
// w strefe martwa (temporal dead zone) tego computed -- dokladnie to
// powodowalo `ReferenceError: Cannot access 'v' before initialization` przy
// kazdym kliknieciu jednego z czterech nowych kafelkow rodzaju.
const result = reactive({
  netto: 0, vat: 0, vat_rate: 0, brutto: 0, narzut: 0,
  cena_po_uldze: 0, ulga: 0,
  raty: { brutto: 0, po_dotacji: 0, po_uldze: 0 },
  linie: [],
  pompa: null,
  // Tri-state: `null` = brak jeszcze odpowiedzi serwera (podgląd lokalny
  // obowiązuje), `true`/`false` = autorytatywna odpowiedź serwera. NIGDY
  // `delete` -- `reactive()` + `hasOwnProperty` jest martwa pulapka Proxy
  // (patrz komentarz w KalkulatorCPTab.vue przy `hasInternal`), stad klucz
  // zawsze istnieje, czytany wylacznie jako wlasciwosc.
  ppoz: null,
  ppoz_prog: null,
  // `= null`, nigdy `delete` -- jak wyzej: bramka panelu admina
  // (`hasInternal`) czyta ta wlasciwosc wprost, nigdy przez `hasOwnProperty`.
  wewnetrzne: null,
})

// Podgląd PPOŻ -- WYŁĄCZNIE prezentacja, serwer (`result.ppoz_prog`) jest
// autorytatywny, gdy juz dostepny; lustro tej samej blokady/odblokowania co
// KalkulatorTab.vue (ppozRecznieSprzedLock).
const mocDodanaRozbudowyKw = computed(
  () => ((Number(form.rozbudowa.panele) || 0) + (Number(form.rozbudowa.paneleMikro) || 0)) * (dane.panelMocWp || 500) / 1000,
)
const ppozProgLive = computed(() => {
  if (result.ppoz_prog !== null) return result.ppoz_prog
  return ppozWymuszonyProgiem({
    mocNowaKw: mocDodanaRozbudowyKw.value,
    istniejacaPv: form.rozbudowa.istniejacaPv,
    mocIstniejacaKwp: form.rozbudowa.istniejacaPvMocKwp,
  })
})

let ppozRecznieSprzedLock = null
watch(ppozProgLive, (locked) => {
  if (locked) {
    if (ppozRecznieSprzedLock === null) ppozRecznieSprzedLock = form.rozbudowa.ppozRecznie
    form.rozbudowa.ppozRecznie = 'Tak'
  } else if (ppozRecznieSprzedLock !== null) {
    form.rozbudowa.ppozRecznie = ppozRecznieSprzedLock
    ppozRecznieSprzedLock = null
  }
})

// Czyszczenie mocy, gdy klient wraca na "Nie" (ten sam wzorzec co
// KalkulatorTab.vue, ops#194).
watch(
  () => form.rozbudowa.istniejacaPv,
  () => {
    if (form.rozbudowa.istniejacaPv === 'Nie') form.rozbudowa.istniejacaPvMocKwp = null
  },
)

// --- Klimatyzacja: kaskada grupa -> model -> moc -----------------------------
const modeleKlimyList = computed(() => modeleKlimy(dane.pozycje, form.klimatyzacja.grupa))
const moceKlimyList = computed(() => moceKlimy(dane.pozycje, form.klimatyzacja.grupa, form.klimatyzacja.klucz))

const opcjeGrupyKlimy = computed(() => GRUPY_KLIMY.map((g) => ({ value: g, label: ETYKIETA_GRUPY_KLIMY[g] })))
const opcjeModeliKlimy = computed(() =>
  modeleKlimyList.value.map((m) => ({ value: m.klucz, label: `${m.producent} ${m.model}`, swatch: kolorSwatchStyle(m.kolor) })),
)

function wybierzGrupaKlimy(grupa) {
  form.klimatyzacja = kaskadaKlimy(dane.pozycje, { ...form.klimatyzacja, grupa })
}
function wybierzModelKlimy(klucz) {
  form.klimatyzacja = kaskadaKlimy(dane.pozycje, { ...form.klimatyzacja, klucz })
}
function wybierzMocKlimy(kod) {
  form.klimatyzacja = kaskadaKlimy(dane.pozycje, { ...form.klimatyzacja, kod })
}

function kolorSwatchStyle(kolor) {
  const k = (kolor || '').toLowerCase()
  if (k.includes('czar')) return { background: '#111827' }
  if (k.includes('bia')) return { background: '#ffffff', border: '1px solid var(--outline-gray-3)' }
  return { background: 'var(--surface-gray-4)' }
}

// --- Pompa ciepła -------------------------------------------------------------
const producenciPcList = producenciPc()

function wybierzProducentaPc(producent) {
  form.pompa.producent = producent
  // Rotenso nie ma wariantu Split -- przelaczenie producenta czysci typ,
  // gdy przestal byc dostepny (nigdy nie wybiera nowego za klienta).
  if (!typyPcDostepne(producent).includes(form.pompa.typ)) form.pompa.typ = ''
}
const typyPcDostepneList = computed(() => typyPcDostepne(form.pompa.producent))
const opcjeTypowPc = computed(() =>
  TYPY_PC_WSZYSTKIE.map((t) => {
    const dostepny = typyPcDostepneList.value.includes(t)
    return { value: t, label: t, disabled: !dostepny, title: dostepny ? '' : __('Niedostępne dla tego producenta') }
  }),
)

const mocPcLive = computed(() =>
  dobierzMocPc(dane.dobor, form.pompa.zapotrzebowanie, form.pompa.producent, form.pompa.typ, form.pompa.ogrzewanie),
)
const pcBrakDoboruLive = computed(
  () => kompletnyPompa(form.pompa) && brakDoboru(mocPcLive.value),
)
const mocPcLiveLabel = computed(() => {
  if (!kompletnyPompa(form.pompa)) return ''
  return brakDoboru(mocPcLive.value) ? '' : `${formatMoc(mocPcLive.value)} kW`
})

function formatMoc(mocKw) {
  const n = Number(mocKw) || 0
  return Number.isInteger(n) ? String(n) : String(n).replace('.', ',')
}

const grzejnikiWlaczone = ref(false)
function przelaczGrzejniki() {
  grzejnikiWlaczone.value = !grzejnikiWlaczone.value
  if (!grzejnikiWlaczone.value) {
    for (const rozmiar of Object.keys(form.pompa.grzejniki)) form.pompa.grzejniki[rozmiar] = 0
  }
}
function ustawGrzejnik(rozmiar, wartosc) {
  form.pompa.grzejniki[rozmiar] = Number(wartosc) || 0
}
const rozmiaryGrzejnikowList = computed(() => rozmiaryGrzejnikow(dane.pozycje))

// --- Kocioł --------------------------------------------------------------------
const modeleKociolList = computed(() => {
  if (!form.kociol.typ) return []
  return dane.pozycje
    .filter((p) => p.grupa === form.kociol.typ)
    .slice()
    .sort((a, b) => (Number(a.sort) || 0) - (Number(b.sort) || 0))
    .map((p) => ({ kod: p.kod, nazwa: p.nazwa, moc_kw: p.moc_kw }))
})
const opcjeTypowKociol = KOCIOL_TYPY.map((t) => ({ value: t.klucz, label: t.etykieta }))
function wybierzTypKociol(typ) {
  form.kociol.typ = typ
  form.kociol.kod = ''
}

// --- Finansowanie / ulga -------------------------------------------------------
const ulgaDotyczyRodzaju = computed(() => ulgaDotyczy(form.rodzaj))
const otwarteFinansowanie = ref(false)
// Pigulka ulgi tylko dla rodzajow, ktorych ulga dotyczy (Klimatyzacja: nie).
const finansowaniePodsumowanie = computed(() =>
  podsumowanieFinansowania(form, { formatPln }).filter((p) => ulgaDotyczyRodzaju.value || !p.tekst.startsWith('Ulga')),
)
const sekcja1Gotowa = computed(() => !!form.typKlienta && !!form.rodzaj)
const sekcja2Gotowa = computed(() => kompletnyFormOze(form))

// --- Narzut --------------------------------------------------------------------
const showNarzut = ref(false)
const narzutValid = computed(() => {
  const n = Number(form.narzut)
  return !isNaN(n) && n >= 0 && (narzutMax.value <= 0 || n <= narzutMax.value)
})
const narzutErrorMsg = computed(() =>
  narzutMax.value > 0
    ? `Narzut musi być od 0 do ${narzutMax.value} zł.`
    : 'Narzut nie może być ujemny.',
)

// --- Wynik kalkulacji (serwer) -----------------------------------------------
const flow = ref('idle') // idle | done
const generating = ref(false)
const errorMsg = ref('')
const showAdminBreakdown = ref(false)
const successSummary = ref('')
const dealHref = ref('#')

// Czytane jako wlasciwosc reaktywnego `result`, NIGDY przez
// `Object.prototype.hasOwnProperty` -- `MutableReactiveHandler` Vue nie
// definiuje pulapki `getOwnPropertyDescriptor`, ktorej `hasOwnProperty`
// wymaga, wiec taki odczyt nie rejestruje zaleznosci i `computed` zamarlby
// na pierwszej wartosci (dokladnie ten blad opisany przy `hasInternal` w
// KalkulatorCPTab.vue).
const hasInternal = computed(() => Boolean(result.wewnetrzne))
const wewnetrzneGrupy = computed(() => grupujWewnetrzneOze(result.wewnetrzne))

const c = computed(() => props.contact || {})
const contactSelected = computed(() => Boolean(c.value.name))
// Serwer jako druga linia obrony (patrz komentarz przy `runCalc` nizej) --
// gdy mimo lokalnego wykrycia brak doboru przeszedl przez `runCalc` i
// serwer i tak zwrocil "Brak doboru", blokuje generowanie tak samo jak
// `pcBrakDoboruLive`.
const bladDoboruSerwer = ref('')
const pcBlokadaDoboru = computed(() => pcBrakDoboruLive.value || Boolean(bladDoboruSerwer.value))
const canGenerate = computed(
  () => result.linie.length > 0 && contactSelected.value && narzutValid.value && !pcBlokadaDoboru.value,
)

// Czerwony komunikat pod przyciskiem "Generuj ofertę" tylko dla "Brak
// doboru" (formularz niepoliczalny niezaleznie od klienta, klik-test
// 2026-10-05); sama potrzeba wybrania klienta to neutralna podpowiedz w
// szablonie.
const powodBrakuDoboru = computed(() =>
  form.rodzaj === OZE_POMPA_CIEPLA && pcBlokadaDoboru.value
    ? __('Brak doboru pompy ciepła dla podanego zapotrzebowania. Wybierz inne parametry.')
    : '',
)

// Adapter ksztaltu `result` (serwer) na ksztalt oczekiwany przez
// KalkulatorParagon.vue; zadnych obliczen, pola serwera bez zmian nazw.
// Nowe rodzaje nie maja dotacji (zawsze 0, paragon jej nie rysuje).
const paragonSummary = computed(() => ({
  lines: result.linie,
  netto: result.netto,
  vat: result.vat,
  vat_rate: result.vat_rate,
  brutto: result.brutto,
  dotacja: 0,
  ulga: result.ulga,
  cena_po_uldze: result.cena_po_uldze,
  raty: result.raty,
}))

function clearResult() {
  result.netto = 0; result.vat = 0; result.vat_rate = 0; result.brutto = 0; result.narzut = 0
  result.cena_po_uldze = 0; result.ulga = 0
  result.raty.brutto = 0; result.raty.po_dotacji = 0; result.raty.po_uldze = 0
  result.linie = []
  result.pompa = null
  result.ppoz = null
  result.ppoz_prog = null
  result.wewnetrzne = null
}

function formatQty(q) {
  const n = Number(q) || 0
  return String(n)
}

// Skopiowane dosłownie z KalkulatorTab.vue (ten sam wzorzec w
// useAutenti.js/KredytTab.vue/UmowaTab.vue) -- call() z frappe-ui konsumuje
// `_server_messages` samo i rzuca błąd, w którym właściwy polski tekst
// żyje pod `err.messages[0]`, nie pod `_server_messages`/`exception`.
function extractErrorMessage(err) {
  try {
    if (err?.messages?.length && err.messages[0]) return err.messages[0]
    if (err && err._server_messages) {
      const msgs = JSON.parse(err._server_messages)
      if (msgs && msgs.length) {
        const first = JSON.parse(msgs[0])
        return first.message || 'Wystąpił błąd - spróbuj ponownie'
      }
    }
    if (err && err.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || 'Wystąpił błąd - spróbuj ponownie'
    }
    if (err && err.message) return err.message
  } catch (e) {
    /* fall through */
  }
  return 'Wystąpił błąd - spróbuj ponownie'
}

// --- Kalkulacja (debounced) ---------------------------------------------------
let calcTimer = null
let calcRequest = 0

watch(
  form,
  () => {
    errorMsg.value = ''
    bladDoboruSerwer.value = ''
    if (calcTimer) clearTimeout(calcTimer)
    calcTimer = setTimeout(runCalc, 350)
  },
  { deep: true },
)

async function runCalc() {
  const request = ++calcRequest
  if (!kompletnyFormOze(form) || loading.value) {
    clearResult()
    return
  }
  // Pompa ciepła: "Brak doboru" jest wykrywalne lokalnie, tym samym
  // doborem co serwer (`dobierzMocPc`/`brakDoboru` w utils/ozeForm.js) --
  // nie wysylaj wtedy volteo_oze_calc. Bez tej bramki serwer i tak
  // zwrocilby `frappe.throw` (HTTP 417) i pokazalby czerwony baner u gory
  // strony DUBLUJACY to samo ostrzezenie, ktore juz stoi przy polu "Moc
  // pompy cieplej" (klik-test 2026-10-05,
  // shots/chromium-d2d-1f-pc-brak-doboru.png).
  if (form.rodzaj === OZE_POMPA_CIEPLA && pcBrakDoboruLive.value) {
    clearResult()
    return
  }
  try {
    const data = await call('crm.api.kalkulator_oze.volteo_oze_calc', { wejscie: zbudujPayloadOze(form) })
    if (request !== calcRequest) return
    result.netto = data.netto || 0
    result.vat = data.vat || 0
    result.vat_rate = data.vat_rate || 0
    result.brutto = data.brutto || 0
    result.narzut = data.narzut || 0
    result.cena_po_uldze = data.cena_po_uldze || 0
    result.ulga = data.ulga || 0
    result.raty.brutto = (data.raty && data.raty.brutto) || 0
    result.raty.po_dotacji = (data.raty && data.raty.po_dotacji) || 0
    result.raty.po_uldze = (data.raty && data.raty.po_uldze) || 0
    result.linie = data.linie || []
    result.pompa = data.pompa ?? null
    result.ppoz = typeof data.ppoz === 'boolean' ? data.ppoz : null
    result.ppoz_prog = typeof data.ppoz_prog === 'boolean' ? data.ppoz_prog : null
    // `data` jest zwyklym obiektem ze sparsowanej odpowiedzi serwera, NIE
    // `reactive` -- `hasOwnProperty` tutaj jest bezpieczne (w odroznieniu
    // od `result`, patrz komentarz przy `hasInternal` wyzej).
    result.wewnetrzne = Object.prototype.hasOwnProperty.call(data, 'wewnetrzne') ? data.wewnetrzne : null
  } catch (err) {
    if (request !== calcRequest) return
    clearResult()
    const msg = extractErrorMessage(err)
    // Druga linia obrony: gdyby serwer mimo lokalnej bramki wyzej zwrocil
    // "Brak doboru" (np. katalog pozycji rozjechal sie z lokalnym mirror'em
    // `dobierzMocPc`), pokaz go WYLACZNIE przy polu "Moc pompy cieplej"
    // (szablon, blok `bladDoboruSerwer`), nigdy jako czerwony baner u gory
    // strony.
    if (msg.includes('Brak doboru')) {
      bladDoboruSerwer.value = msg
    } else {
      errorMsg.value = msg
    }
  }
}

// --- Generowanie szansy --------------------------------------------------------
async function runCreateDeal() {
  if (!canGenerate.value || generating.value) return
  errorMsg.value = ''
  generating.value = true
  try {
    const data = await call('crm.api.kalkulator_oze.volteo_oze_create_deal', {
      wejscie: zbudujPayloadOze(form),
      contact: c.value.name || '',
    })
    successSummary.value =
      'Szansa ' + data.deal + ' została utworzona. Suma brutto: ' + formatPln(result.brutto) + '.'
    dealHref.value = router.resolve({ name: 'Deal', params: { dealId: data.deal } }).href
    flow.value = 'done'
  } catch (err) {
    errorMsg.value = extractErrorMessage(err)
  } finally {
    generating.value = false
  }
}

function resetFlow() {
  flow.value = 'idle'
  successSummary.value = ''
  Object.assign(form, pustyFormularzOze(form.rodzaj))
  grzejnikiWlaczone.value = false
  clearResult()
}

onBeforeUnmount(() => {
  if (calcTimer) clearTimeout(calcTimer)
})
</script>

<style scoped>
.kalk-input,
.kalk-select {
  height: 32px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  border-radius: 0.375rem;
  border: 1px solid var(--outline-gray-2);
  background: var(--surface-gray-2);
  padding: 0 8px;
  font-size: 14px;
  color: var(--ink-gray-8);
  outline: none;
  transition: background-color 0.15s, border-color 0.15s;
  cursor: pointer;
}
.kalk-select {
  appearance: none;
  -webkit-appearance: none;
  padding-right: 28px;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'/></svg>");
  background-repeat: no-repeat;
  background-position: right 9px center;
}
.kalk-select-inline { width: auto; min-width: 0; max-width: 100%; flex: 0 1 150px; }
.kalk-select-wariant {
  width: auto;
  flex: 0 0 auto;
}
.kalk-split > *,
.kalk-part .grid > * { min-width: 0; }
.kalk-select:disabled {
  border-style: dashed;
  color: var(--ink-gray-4);
  cursor: not-allowed;
}
.kalk-input { cursor: text; }
.kalk-input-unit { padding-right: 64px; }
.kalk-unit {
  position: absolute;
  right: 10px;
  bottom: 7px;
  font-size: 12px;
  line-height: 1;
  color: var(--ink-gray-4);
  pointer-events: none;
}
.kalk-input:hover,
.kalk-select:hover:not(:disabled) {
  background-color: var(--surface-gray-3);
}
.kalk-input:focus,
.kalk-select:focus {
  border-color: var(--outline-gray-4);
  background-color: var(--surface-base);
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.kalk-part-toggle {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}
.kalk-part-zwijana { padding-top: 0.875rem; padding-bottom: 0.875rem; }
.kalk-part-heading { letter-spacing: -0.01em; }
.kalk-part {
  border: 1px solid var(--outline-gray-1);
  border-radius: 0.75rem;
  background: var(--surface-elevation-1);
  padding: 1.25rem 1.25rem 1.375rem;
}
.kalk-part + .kalk-part { margin-top: 1rem; }
.kalk-part-number {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 1.375rem;
  height: 1.375rem;
  border-radius: 9999px;
  background: var(--surface-gray-2);
  color: var(--ink-gray-4);
  font-size: 0.7rem;
  font-weight: 700;
}
/* Paragon przyklejony: wysokosc = okno minus naglowek strony (LayoutHeader) i marginesy */
.kalk-sticky {
  max-height: calc(100vh - 7rem);
  overflow-y: auto;
  padding-right: 0.5rem;
  scrollbar-width: thin;
}
@media (max-width: 880px) {
  .kalk-split { grid-template-columns: minmax(0, 1fr) !important; }
  .kalk-row2 { grid-template-columns: minmax(0, 1fr) !important; }
  .kalk-output { border-left: 0 !important; padding-left: 0 !important; margin-top: 0.75rem; }
  .sticky { position: static; }
  .kalk-sticky { max-height: none; overflow: visible; padding-right: 0; }
  .kalk-part { padding: 1rem; }
  /* Grid 5 selectow grzejnikow na jedna kolumne pod 880px (plan b68, F3).
     `grid-template-columns: 1fr` samo nie wystarcza: wiersz podsumowania
     "Razem" niesie Tailwindowe `col-span-5` (bez wariantu mobilnego), a
     CSS Grid DOGENERUJE niejawne kolumny, zeby pomiescic span-5, nawet gdy
     jawna definicja ma tylko 1 kolumne -- stad bez tej drugiej reguly siatka
     i tak renderowala 5 kolumn. */
  .kalk-grzejniki-grid { grid-template-columns: minmax(0, 1fr) !important; }
  .kalk-grzejniki-razem { grid-column: span 1 !important; }
}
</style>
