<!--
  Kalkulator OZE -- cztery nowe rodzaje instalacji (Rozbudowa PV/ME,
  Klimatyzacja, Pompa ciepła, Kocioł; b68, "Wielki update kalkulatora OZE",
  chunk F3). Renderowany przez KalkulatorTab.vue (rodzic) w miejsce grida
  `.kalk-split` i bloku `done`, gdy `czyNowyRodzaj(sel.variant)` jest
  prawdziwe -- ten komponent niesie WŁASNĄ kopię karty 1 "Rodzaj
  instalacji" (ten sam rząd siedmiu kafelków, `kafelkiRodzaju()`), żeby
  przełączenie na stary wariant PV/PV+ME/ME nie wymagało znikania i
  ponownego pokazywania się całej karty na granicy rodzica/dziecka.

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
        <div class="kalk-split grid items-start gap-x-5" style="grid-template-columns: minmax(0, 1.6fr) minmax(280px, 1fr)">
          <div>
            <!-- Karta 1: Rodzaj instalacji (wlasna kopia tego samego rzedu
                 kafelkow co KalkulatorTab.vue, zeby przelaczenie na stary
                 wariant PV/PV+ME/ME dzialalo bez skoku layoutu). -->
            <div class="kalk-part">
              <div class="kalk-part-heading mb-4 flex items-center gap-2 border-b border-outline-gray-1 pb-2.5 text-lg font-bold text-ink-gray-9">
                <span class="kalk-part-number">1</span>{{ __('Rodzaj instalacji') }}
              </div>
              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="r in kafelki" :key="r"
                  type="button"
                  class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                  :class="form.rodzaj === r
                    ? 'border-outline-gray-7 bg-surface-gray-10 text-ink-base'
                    : 'border-transparent bg-surface-gray-2 text-ink-gray-5 hover:bg-surface-gray-3'"
                  @click="wybierzRodzaj(r)"
                >{{ r }}</button>
              </div>

              <div class="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 kalk-row2">
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Typ klienta') }}</div>
                  <div class="flex flex-wrap gap-1.5">
                    <button
                      v-for="opt in TYP_KLIENTA_OPTIONS" :key="opt.value"
                      type="button"
                      class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                      :class="form.typKlienta === opt.value
                        ? 'border-outline-gray-7 bg-surface-gray-10 text-ink-base'
                        : 'border-transparent bg-surface-gray-2 text-ink-gray-5 hover:bg-surface-gray-3'"
                      @click="form.typKlienta = opt.value"
                    >{{ opt.label }}</button>
                  </div>
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
              <!-- Karta 2: konfiguracja specyficzna dla rodzaju -->
              <div class="kalk-part">
                <div class="kalk-part-heading mb-4 flex items-center gap-2 border-b border-outline-gray-1 pb-2.5 text-lg font-bold text-ink-gray-9">
                  <span class="kalk-part-number">2</span>{{ __('Konfiguracja') }}
                </div>

                <!-- ROZBUDOWA -->
                <div v-if="form.rodzaj === OZE_ROZBUDOWA">
                  <div
                    v-for="blok in blokiRozbudowy" :key="blok.klucz"
                    class="border-t border-outline-gray-1 py-2.5 first:border-t-0"
                  >
                    <div class="flex items-center gap-2.5">
                      <span class="w-56 shrink-0 text-sm font-medium text-ink-gray-7">
                        {{ blok.etykieta }}
                        <span v-if="blok.opis" class="font-normal text-ink-gray-5"> · {{ blok.opis }}</span>
                      </span>
                      <button
                        type="button" role="switch"
                        :aria-checked="form.rozbudowa[blok.klucz] > 0"
                        :aria-label="blok.etykieta"
                        :disabled="elementRozbudowyZablokowany(form.rozbudowa, blok.klucz)"
                        class="kalk-switch shrink-0"
                        :class="[
                          form.rozbudowa[blok.klucz] > 0 ? 'kalk-switch-on' : 'kalk-switch-off',
                          elementRozbudowyZablokowany(form.rozbudowa, blok.klucz) ? 'opacity-50 cursor-not-allowed' : '',
                        ]"
                        @click="przelaczRozbudowa(blok.klucz)"
                      ><span class="kalk-switch-knob" /></button>
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

                  <div class="mt-2 grid grid-cols-2 gap-x-3 gap-y-2 kalk-row2">
                    <div>
                      <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Czy klient ma już instalację PV?') }}</div>
                      <select v-model="form.rozbudowa.istniejacaPv" class="kalk-select">
                        <option value="Nie">{{ __('Nie') }}</option>
                        <option value="Tak">{{ __('Tak') }}</option>
                      </select>
                    </div>
                    <div v-if="form.rozbudowa.istniejacaPv === 'Tak'">
                      <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Moc istniejącej instalacji (kWp)') }}</div>
                      <input v-model.number="form.rozbudowa.istniejacaPvMocKwp" type="number" min="0" step="0.1" class="kalk-input" />
                    </div>
                    <div class="col-span-2">
                      <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Uzgodnienia PPOŻ') }}</div>
                      <select v-model="form.rozbudowa.ppozRecznie" class="kalk-select" :disabled="ppozProgLive">
                        <option value="Nie">{{ __('Nie') }}</option>
                        <option value="Tak">{{ __('Tak') }}</option>
                      </select>
                      <div class="mt-0.5 text-xs text-ink-gray-4">
                        {{ ppozProgLive
                          ? __('Wymagane automatycznie: suma mocy nowej i istniejącej instalacji przekracza 6,5 kW.')
                          : __('Ustaw Tak ręcznie, jeśli aktualna moc PV i dokładana moc PV w sumie przekroczą 6,5 kW.') }}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- KLIMATYZACJA -->
                <div v-else-if="form.rodzaj === OZE_KLIMATYZACJA">
                  <div class="mb-1.5 text-sm font-medium text-ink-gray-7">{{ __('Rodzaj klimatyzacji') }}</div>
                  <div class="flex flex-wrap gap-1.5">
                    <button
                      v-for="g in GRUPY_KLIMY" :key="g"
                      type="button"
                      class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                      :class="form.klimatyzacja.grupa === g
                        ? 'border-outline-gray-7 bg-surface-gray-10 text-ink-base'
                        : 'border-transparent bg-surface-gray-2 text-ink-gray-5 hover:bg-surface-gray-3'"
                      @click="wybierzGrupaKlimy(g)"
                    >{{ ETYKIETA_GRUPY_KLIMY[g] }}</button>
                  </div>

                  <div v-if="form.klimatyzacja.grupa" class="mt-2.5">
                    <div class="mb-1.5 text-sm font-medium text-ink-gray-7">{{ __('Model') }}</div>
                    <div class="flex flex-wrap gap-1.5">
                      <button
                        v-for="m in modeleKlimyList" :key="m.klucz"
                        type="button"
                        class="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                        :class="form.klimatyzacja.klucz === m.klucz
                          ? 'border-outline-gray-7 bg-surface-gray-10 text-ink-base'
                          : 'border-transparent bg-surface-gray-2 text-ink-gray-5 hover:bg-surface-gray-3'"
                        @click="wybierzModelKlimy(m.klucz)"
                      ><span class="kalk-kolor-dot" :style="kolorSwatchStyle(m.kolor)" />{{ m.producent }} {{ m.model }}</button>
                    </div>
                  </div>

                  <div v-if="form.klimatyzacja.klucz" class="mt-2.5">
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
                  <div class="mb-2">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Zapotrzebowanie budynku na moc') }}</div>
                    <select v-model="form.pompa.zapotrzebowanie" class="kalk-select">
                      <option value="">{{ __('-- wybierz --') }}</option>
                      <option v-for="z in dane.zapotrzebowanie" :key="z.value" :value="z.value">{{ z.label }}</option>
                    </select>
                    <div class="mt-0.5 text-xs text-ink-gray-4">{{ __('Wartość na podstawie wyniku z ciepło.app.') }}</div>
                  </div>

                  <div class="mb-1.5 text-sm font-medium text-ink-gray-7">{{ __('Producent') }}</div>
                  <div class="flex flex-wrap gap-1.5">
                    <button
                      v-for="p in producenciPcList" :key="p"
                      type="button"
                      class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                      :class="form.pompa.producent === p
                        ? 'border-outline-gray-7 bg-surface-gray-10 text-ink-base'
                        : 'border-transparent bg-surface-gray-2 text-ink-gray-5 hover:bg-surface-gray-3'"
                      @click="wybierzProducentaPc(p)"
                    >{{ p }}</button>
                  </div>

                  <div class="mt-2.5 mb-1.5 text-sm font-medium text-ink-gray-7">{{ __('Typ') }}</div>
                  <div class="flex flex-wrap gap-1.5">
                    <button
                      v-for="t in TYPY_PC_WSZYSTKIE" :key="t"
                      type="button"
                      class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                      :class="form.pompa.typ === t
                        ? 'border-outline-gray-7 bg-surface-gray-10 text-ink-base'
                        : 'border-transparent bg-surface-gray-2 text-ink-gray-5 hover:bg-surface-gray-3'"
                      :disabled="!typyPcDostepneList.includes(t)"
                      :title="typyPcDostepneList.includes(t) ? '' : __('Niedostępne dla tego producenta')"
                      @click="form.pompa.typ = t"
                    >{{ t }}</button>
                  </div>

                  <div class="mt-2.5 mb-1.5 text-sm font-medium text-ink-gray-7">{{ __('Ogrzewanie') }}</div>
                  <div class="flex flex-wrap gap-1.5">
                    <button
                      v-for="o in OGRZEWANIE_OPCJE" :key="o"
                      type="button"
                      class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                      :class="form.pompa.ogrzewanie === o
                        ? 'border-outline-gray-7 bg-surface-gray-10 text-ink-base'
                        : 'border-transparent bg-surface-gray-2 text-ink-gray-5 hover:bg-surface-gray-3'"
                      @click="form.pompa.ogrzewanie = o"
                    >{{ o }}</button>
                  </div>

                  <div class="mt-3">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Moc pompy ciepła (dobrana automatycznie)') }}</div>
                    <input v-if="!pcBrakDoboruLive && !bladDoboruSerwer" :value="mocPcLiveLabel" type="text" class="kalk-input" disabled />
                    <!-- `bladDoboruSerwer` to druga linia obrony (patrz komentarz przy
                    `runCalc` w <script>) -- komunikat serwera, gdy ten kiedykolwiek
                    znajdzie "Brak doboru" mimo ze lokalny `pcBrakDoboruLive` byl `false`. -->
                    <div v-else class="rounded-md border border-outline-amber-3 bg-surface-amber-2 px-2.5 py-2 text-sm text-ink-amber-8">
                      {{ bladDoboruSerwer || __('Brak doboru pompy ciepła dla podanego zapotrzebowania. Najpierw ocieplenie budynku.') }}
                    </div>
                  </div>

                  <div class="mt-2.5 grid grid-cols-2 gap-x-3 gap-y-2 kalk-row2">
                    <div>
                      <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Zasobnik CWU') }}</div>
                      <select v-model="form.pompa.cwu" class="kalk-select">
                        <option value="">{{ __('Nie') }}</option>
                        <option value="200">{{ __('200 l') }}</option>
                        <option value="300">{{ __('300 l') }}</option>
                      </select>
                    </div>
                  </div>

                  <div class="mt-2.5">
                    <div class="flex items-center gap-2.5">
                      <span class="w-56 shrink-0 text-sm font-medium text-ink-gray-7">{{ __('Grzejniki niskotemperaturowe') }}</span>
                      <button
                        type="button" role="switch"
                        :aria-checked="grzejnikiWlaczone"
                        :aria-label="__('Grzejniki niskotemperaturowe')"
                        class="kalk-switch shrink-0"
                        :class="grzejnikiWlaczone ? 'kalk-switch-on' : 'kalk-switch-off'"
                        @click="przelaczGrzejniki"
                      ><span class="kalk-switch-knob" /></button>
                    </div>

                    <div v-if="grzejnikiWlaczone" class="kalk-grzejniki-grid mt-2 grid grid-cols-5 gap-2">
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
                  <div class="mb-1.5 text-sm font-medium text-ink-gray-7">{{ __('Rodzaj kotła') }}</div>
                  <div class="flex flex-wrap gap-1.5">
                    <button
                      v-for="t in KOCIOL_TYPY" :key="t.klucz"
                      type="button"
                      class="rounded-md border px-2.5 py-1 text-sm font-medium transition-colors"
                      :class="form.kociol.typ === t.klucz
                        ? 'border-outline-gray-7 bg-surface-gray-10 text-ink-base'
                        : 'border-transparent bg-surface-gray-2 text-ink-gray-5 hover:bg-surface-gray-3'"
                      @click="wybierzTypKociol(t.klucz)"
                    >{{ t.etykieta }}</button>
                  </div>

                  <div v-if="form.kociol.typ" class="mt-2.5">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Model') }}</div>
                    <select v-model="form.kociol.kod" class="kalk-select">
                      <option value="">{{ __('-- wybierz --') }}</option>
                      <option v-for="o in modeleKociolList" :key="o.kod" :value="o.kod">
                        {{ o.nazwa }}<template v-if="o.moc_kw"> ({{ formatMoc(o.moc_kw) }} kW)</template>
                      </option>
                    </select>
                  </div>

                  <div class="mt-2.5">
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Zasobnik CWU') }}</div>
                    <select v-model="form.kociol.cwu" class="kalk-select">
                      <option value="">{{ __('Nie') }}</option>
                      <option value="200">{{ __('200 l') }}</option>
                      <option value="300">{{ __('300 l') }}</option>
                    </select>
                  </div>
                </div>
              </div>

              <!-- Karta 3: Finansowanie -->
              <div class="kalk-part">
                <div class="kalk-part-heading mb-4 flex items-center gap-2 border-b border-outline-gray-1 pb-2.5 text-lg font-bold text-ink-gray-9">
                  <span class="kalk-part-number">3</span>{{ __('Finansowanie') }}
                </div>
                <div class="grid grid-cols-2 gap-x-3 gap-y-2">
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
                  <div>
                    <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Wpłata własna (PLN)') }}</div>
                    <input v-model.number="form.wplataWlasna" type="number" min="0" step="0.01" class="kalk-input" />
                  </div>
                </div>
              </div>
            </template>
          </div>

          <div class="kalk-output border-l border-outline-gray-2 pl-5">
            <div class="sticky top-3">
              <div class="mb-2.5">
                <button
                  type="button"
                  class="flex w-full items-center justify-between rounded-md border border-outline-gray-1 bg-surface-gray-1 px-2.5 py-1.5 text-sm font-medium text-ink-gray-7 transition-colors hover:bg-surface-gray-2"
                  @click="showNarzut = !showNarzut"
                >
                  <span>{{ showNarzut ? __('Ukryj ustawienia niestandardowe') : __('Pokaż ustawienia niestandardowe') }}</span>
                  <FeatherIcon :name="showNarzut ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 text-ink-gray-5" />
                </button>
                <div v-if="showNarzut" class="mt-1.5">
                  <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Wysokość narzutu') }}</div>
                  <input
                    v-model.number="form.narzut" type="number" min="0" :max="narzutMax > 0 ? narzutMax : undefined" step="0.01"
                    class="kalk-input"
                    @blur="form.narzut = narzutMax > 0 ? Math.min(narzutMax, Math.max(0, Number(form.narzut) || 0)) : Math.max(0, Number(form.narzut) || 0)"
                  />
                  <div v-if="!narzutValid" class="mt-0.5 text-xs text-ink-red-6">{{ narzutErrorMsg }}</div>
                </div>
              </div>

              <div class="mb-2 text-base font-semibold text-ink-gray-9">{{ __('Wycena') }}</div>

              <div v-if="result.linie.length" class="mb-2">
                <div
                  v-for="(ln, i) in result.linie" :key="i"
                  class="flex items-center gap-2 border-t border-outline-gray-1 py-1.5 text-sm first:border-t-0"
                >
                  <span class="min-w-[88px] text-ink-gray-5">{{ ln.typ }}</span>
                  <span class="flex-1 text-ink-gray-8">{{ ln.nazwa }}</span>
                  <span class="tabular-nums text-ink-gray-7">×{{ formatQty(ln.ilosc) }}</span>
                </div>
              </div>
              <div v-else class="mb-2 text-sm text-ink-gray-5">{{ __('Uzupełnij konfigurację, aby zobaczyć wycenę.') }}</div>

              <template v-if="result.linie.length">
                <div class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 p-2.5">
                  <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                    <span>{{ __('Suma netto') }}</span><span>{{ formatPln(result.netto) }}</span>
                  </div>
                  <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                    <span>{{ __('VAT ({0}%)', [result.vat_rate]) }}</span><span>{{ formatPln(result.vat) }}</span>
                  </div>
                  <div class="mt-1 flex justify-between border-t border-outline-gray-2 pt-1.5 text-base font-semibold tabular-nums text-ink-gray-9">
                    <span>{{ __('Suma brutto') }}</span><span>{{ formatPln(result.brutto) }}</span>
                  </div>

                  <div class="mt-1.5 flex justify-between py-0.5 text-xs tabular-nums text-ink-gray-5">
                    <span>{{ __('Rata ({0} lat)', [form.okresLat]) }}</span>
                    <span>{{ formatPln(result.raty.brutto) }} /mies.</span>
                  </div>

                  <template v-if="ulgaDotyczyRodzaju && form.typKlienta === 'indywidualny'">
                    <div class="mt-1.5 border-t border-dashed border-outline-gray-2 pt-1.5">
                      <div class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7">
                        <span>{{ __('Ulga termo. ({0}%)', [form.ulgaPct]) }}</span><span>− {{ formatPln(result.ulga) }}</span>
                      </div>
                      <div class="flex justify-between py-0.5 text-sm font-semibold tabular-nums text-ink-gray-9">
                        <span>{{ __('Cena po uldze') }}</span><span>{{ formatPln(result.cena_po_uldze) }}</span>
                      </div>
                      <div class="flex justify-between py-0.5 text-xs tabular-nums text-ink-gray-5">
                        <span>{{ __('Rata po uldze') }}</span><span>{{ formatPln(result.raty.po_uldze) }} /mies.</span>
                      </div>
                    </div>
                  </template>
                </div>
              </template>

              <div v-if="$slots['client-picker']" class="mb-2 mt-2">
                <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Klient') }}</div>
                <slot name="client-picker" />
              </div>

              <Button
                class="mt-2 w-full"
                variant="solid"
                :disabled="!canGenerate || generating"
                @click="runCreateDeal"
              >{{ generating ? __('Generuję ofertę…') : __('Generuj ofertę') }}</Button>

              <div v-if="powodBlokadyGeneracji" class="mt-1 text-center text-xs text-ink-red-6">
                {{ powodBlokadyGeneracji }}
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
import { ppozWymuszonyProgiem } from '@/utils/pvForm'
import { formatPln } from '@/utils/money'
import {
  ETYKIETA_GRUPY_KLIMY,
  GRUPY_KLIMY,
  GRZEJNIKI_MAX,
  OZE_KLIMATYZACJA,
  OZE_KOCIOL,
  OZE_POMPA_CIEPLA,
  OZE_ROZBUDOWA,
  brakDoboru,
  czyNowyRodzaj,
  dobierzMocPc,
  grupujWewnetrzneOze,
  kafelkiRodzaju,
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
const TYPY_PC_WSZYSTKIE = ['Monoblok', 'Split']
const OGRZEWANIE_OPCJE = ['Podłogówka', 'Grzejniki', 'Mieszane']
const KOCIOL_TYPY = [
  { klucz: 'kociol_pellet', etykieta: 'Pellet' },
  { klucz: 'kociol_duo', etykieta: 'Drewno (DUO)' },
]

// --- Stan formularza ---------------------------------------------------------
const kafelki = kafelkiRodzaju()
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
function wybierzTypKociol(typ) {
  form.kociol.typ = typ
  form.kociol.kod = ''
}

// --- Finansowanie / ulga -------------------------------------------------------
const ulgaDotyczyRodzaju = computed(() => ulgaDotyczy(form.rodzaj))

// --- Narzut --------------------------------------------------------------------
const showNarzut = ref(true)
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

// Komunikat powodu blokady pod przyciskiem "Generuj ofertę" -- "Brak
// doboru" ma priorytet przed "Wybierz klienta", bo bez doboru mocy
// formularz jest i tak niepoliczalny niezaleznie od tego, czy klient jest
// juz wybrany (klik-test 2026-10-05).
const powodBlokadyGeneracji = computed(() => {
  if (form.rodzaj === OZE_POMPA_CIEPLA && pcBlokadaDoboru.value) {
    return __('Brak doboru pompy ciepła dla podanego zapotrzebowania. Wybierz inne parametry.')
  }
  if (!contactSelected.value) {
    return __('Wybierz klienta, aby wygenerować ofertę.')
  }
  return ''
})

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
  height: 28px;
  width: 100%;
  border-radius: 0.25rem;
  border: 1px solid var(--outline-gray-1);
  background: var(--surface-gray-2);
  padding: 0 8px;
  font-size: 14px;
  color: var(--ink-gray-8);
  outline: none;
  transition: background-color 0.15s, border-color 0.15s;
  cursor: pointer;
}
.kalk-input { cursor: text; }
.kalk-input:hover,
.kalk-select:hover {
  background: var(--surface-gray-3);
}
.kalk-input:focus,
.kalk-select:focus {
  border-color: var(--outline-gray-4);
  background: var(--surface-base);
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.kalk-input:disabled,
.kalk-select:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
.kalk-select-wariant {
  width: auto;
  flex: 0 0 auto;
}
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
/* iOS-style TAK/NIE switch -- identyczny wzorzec co KalkulatorTab.vue /
   KalkulatorCPTab.vue: kolor I pozycja gałki niosą stan, czarne OFF
   (nigdy szare/czerwone), zielone ON. */
.kalk-switch {
  position: relative;
  display: inline-block;
  flex-shrink: 0;
  width: 40px;
  height: 22px;
  padding: 0;
  border: none;
  border-radius: 9999px;
  cursor: pointer;
  vertical-align: middle;
  transition: background-color 0.15s;
}
.kalk-switch-on { background: #16a34a; }
.kalk-switch-off { background: #111827; }
[data-theme='dark'] .kalk-switch-off { background: var(--surface-gray-4); }
.kalk-switch:disabled { opacity: 0.5; cursor: not-allowed; }
.kalk-switch:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }
.kalk-switch-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 9999px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
  transition: transform 0.15s;
}
.kalk-switch-on .kalk-switch-knob { transform: translateX(18px); }
/* Plamka koloru na kafelku modelu klimatyzacji (Czarny/Biały) -- wylacznie
   wizualne oznaczenie linii produktowej, nie wplywa na wybor. */
.kalk-kolor-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  flex-shrink: 0;
}
@media (max-width: 880px) {
  .kalk-split { grid-template-columns: 1fr !important; }
  .kalk-row2 { grid-template-columns: 1fr !important; }
  .kalk-output { border-left: 0 !important; padding-left: 0 !important; margin-top: 0.75rem; }
  .sticky { position: static; }
  .kalk-part { padding: 1rem; }
  /* Grid 5 selectow grzejnikow na jedna kolumne pod 880px (plan b68, F3).
     `grid-template-columns: 1fr` samo nie wystarcza: wiersz podsumowania
     "Razem" niesie Tailwindowe `col-span-5` (bez wariantu mobilnego), a
     CSS Grid DOGENERUJE niejawne kolumny, zeby pomiescic span-5, nawet gdy
     jawna definicja ma tylko 1 kolumne -- stad bez tej drugiej reguly siatka
     i tak renderowala 5 kolumn (znalezione headless, PW viewport 375px:
     `getComputedStyle(grid).gridTemplateColumns` dalej zwracal 5 torow mimo
     `!important` powyzej). */
  .kalk-grzejniki-grid { grid-template-columns: 1fr !important; }
  .kalk-grzejniki-razem { grid-column: span 1 !important; }
}
</style>
