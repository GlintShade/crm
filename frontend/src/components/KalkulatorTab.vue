<!--
  Volteo Kalkulator — native-styled quote builder tab in the Klient view.
  Styled to match the CRM's frappe-ui design system exactly.
  ZERO pricing math in this file — all computed server-side.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto">
    <div class="mx-auto w-full max-w-[1180px] px-4 py-3">
      <div v-if="errorMsg" class="mb-2.5 flex items-center justify-between rounded border border-outline-red-3 bg-surface-red-2 px-3 py-2 text-sm text-ink-red-8">
        <span>{{ errorMsg }}</span>
        <button class="ml-2 text-base font-bold leading-none" @click="errorMsg = ''">×</button>
      </div>

      <!-- Cztery nowe rodzaje OZE (Rozbudowa PV/ME, Klimatyzacja, Pompa
           ciepła, Kocioł; b68, chunk F3) mają własny kalkulator z własną
           kartą "Rodzaj instalacji" i własnym blokiem "Szansa utworzona" --
           całe poniższe (grid .kalk-split ORAZ blok done) jest zastąpione
           jednym komponentem. Watcher(y) kalkulacji/sanitizacji dodatków
           PV poniżej (runCalc, [variant, producent, falownik]) są
           nieszkodliwe dla nowych rodzajów (zerują/czyszczą lokalny stan),
           ale `runCalc` samo jest jawnie zagrodzone przed wysłaniem
           `volteo_quote_calc` dla nich (patrz guard na początku funkcji) --
           inaczej stare `sel.producent`/`sel.falownik` pozostałe po
           przełączeniu z wariantu PV mogłyby wciąż spełniać `isComplete`. -->
      <KalkulatorOzeRozszerzony
        v-if="czyNowyRodzaj(sel.variant)"
        :contact="props.contact"
        v-model:rodzaj="sel.variant"
      >
        <template #client-picker>
          <slot name="client-picker" />
        </template>
      </KalkulatorOzeRozszerzony>

      <template v-else>
      <template v-if="flow !== 'done'">
        <!-- Pasek nagłówka: status uzupełnienia (wybór klienta jest w prawej kolumnie). -->
        <div class="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2">
          <div class="text-sm text-ink-gray-5">{{ statusFormularza }}</div>
        </div>

        <div class="kalk-split grid items-start gap-x-5" style="grid-template-columns: minmax(0, 1.55fr) minmax(280px, 1fr)">

          <div>
            <!-- 1. Instalacja i klient (zawsze otwarta) -->
            <div class="kalk-part">
              <div class="kalk-part-heading mb-4 flex items-center gap-2 border-b border-outline-gray-1 pb-2.5 text-lg font-bold text-ink-gray-9">
                <span class="kalk-part-number">1</span>Instalacja i klient
                <FeatherIcon v-if="sekcja1Gotowa" name="check" class="h-4 w-4 text-ink-green-6" />
              </div>

              <div>
                <div class="mb-0.5 text-sm text-ink-gray-5">Rodzaj instalacji</div>
                <div class="flex flex-wrap items-center gap-2">
                  <WyborSegmentowy v-model="sel.variant" :options="VARIANTS" />
                  <select class="kalk-select kalk-select-inline" aria-label="Inne rodzaje" :value="''" @change="wybierzInnyRodzaj($event)">
                    <option value="">Inne rodzaje</option>
                    <option v-for="r in RODZAJE_NOWE" :key="r" :value="r">{{ r }}</option>
                  </select>
                </div>
              </div>

              <div class="mt-3 grid items-start grid-cols-2 gap-x-3 gap-y-3 kalk-row2">
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Typ klienta</div>
                  <WyborSegmentowy v-model="sel.typKlienta" :options="TYP_KLIENTA_OPTIONS" />
                </div>

                <div v-if="sel.typKlienta === 'indywidualny'" class="col-span-2">
                  <div class="mb-0.5 text-sm text-ink-gray-5">{{ __('Zasady dotacji') }}</div>
                  <WyborSegmentowy v-model="sel.zasadyDotacji" :options="zasadyOpcje" />
                </div>

                <!-- Battery-only has no PV to size, so this input (a PV-sizing
                     parameter) is meaningless for that variant and is hidden. -->
                <div v-if="hasPv" class="col-span-2 grid items-start gap-x-3 gap-y-2 kalk-row2" style="grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)">
                  <div>
                    <div class="relative">
                      <div class="mb-0.5 text-sm text-ink-gray-5">Roczne zużycie (kWh)</div>
                      <input
                        v-model.number="sel.consumption" type="number" min="0" step="1"
                        class="kalk-input kalk-input-unit"
                      />
                      <span class="kalk-unit">kWh/rok</span>
                    </div>
                    <div class="mt-1 text-xs leading-snug text-ink-gray-4">Opcjonalne, nie jest wymagane. Po wpisaniu kalkulator sam wyliczy dobór zestawu.</div>
                  </div>

                  <div v-if="sel.consumption > 0 && autodoborAktywny" class="rounded-lg border border-dashed border-outline-gray-3 bg-surface-gray-1 p-2.5 text-xs leading-relaxed text-ink-gray-5" data-testid="autodobor-cel">
                    <div>Podpowiedź dla {{ sel.consumption }} kWh</div>
                    <div class="text-sm font-semibold text-ink-gray-8">Cel: {{ celPvTekst }} kWp i {{ celMeTekst }} kWh</div>
                    <div>(zestaw COMFORT PREMIUM)</div>
                    <button type="button" class="mt-1 font-medium text-ink-blue-link hover:underline" @click="zastosujAutodobor">Dobierz urządzenia</button>
                  </div>
                  <div v-else-if="sel.consumption > 0" class="rounded-lg border border-dashed border-outline-gray-3 bg-surface-gray-1 p-2.5 text-xs leading-relaxed text-ink-gray-5">
                    <div>Podpowiedź dla {{ sel.consumption }} kWh</div>
                    <div class="text-sm font-semibold text-ink-gray-8">
                      {{ plLiczba(suggestedKwp) }} kWp<template v-if="hasBat"> i {{ plLiczba(suggestedStorage) }} kWh</template>
                    </div>
                    <div>Sug. moc: {{ plLiczba(suggestedKwp) }} kW<template v-if="hasBat"> · magazyn: {{ suggestedStorage }} kWh</template></div>
                    <button type="button" class="mt-1 font-medium text-ink-blue-link hover:underline" @click="applyFromConsumption">Dobierz urządzenia</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 2. Zestaw i urządzenia (zawsze otwarta) -->
            <div class="kalk-part">
              <div class="kalk-part-heading mb-4 flex items-center gap-2 border-b border-outline-gray-1 pb-2.5 text-lg font-bold text-ink-gray-9">
                <span class="kalk-part-number">2</span>Zestaw i urządzenia
                <FeatherIcon v-if="isComplete" name="check" class="h-4 w-4 text-ink-green-6" />
              </div>

              <div v-if="hasBat" class="mb-3" data-testid="zestaw-row">
                <div class="mb-1 text-sm text-ink-gray-5">Zestaw</div>
                <div class="grid grid-cols-3 gap-2 kalk-zestawy">
                  <button
                    v-for="z in ZESTAWY" :key="z.kod"
                    type="button"
                    role="radio"
                    :aria-checked="sel.zestaw === z.kod"
                    class="relative flex items-start gap-2 rounded-lg border p-2.5 text-left transition-colors"
                    :class="sel.zestaw === z.kod
                      ? 'border-outline-gray-7 bg-surface-gray-2'
                      : 'border-outline-gray-2 hover:bg-surface-gray-1'"
                    :data-testid="'zestaw-' + z.kod"
                    @click="sel.zestaw = z.kod"
                  >
                    <span
                      class="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border"
                      :class="sel.zestaw === z.kod ? 'border-outline-gray-8' : 'border-outline-gray-4'"
                    ><span v-if="sel.zestaw === z.kod" class="h-2 w-2 rounded-full bg-surface-gray-9"></span></span>
                    <span class="min-w-0 pr-4">
                      <span class="block text-sm font-bold text-ink-gray-9">{{ z.kod }}</span>
                      <span class="block text-sm text-ink-gray-7">{{ z.producent }}</span>
                      <span v-if="opisZestawu(z)" class="block text-xs text-ink-gray-4">{{ opisZestawu(z) }}</span>
                    </span>
                    <FeatherIcon v-if="sel.zestaw === z.kod" name="check" class="absolute right-2 top-2 h-4 w-4 text-ink-gray-8" />
                  </button>
                </div>
              </div>

              <div class="mb-3">
                <div class="mb-1 text-sm text-ink-gray-5">Producent</div>
                <div v-if="producentOptions.length === 1" class="text-sm">
                  <span class="font-semibold text-ink-gray-9">{{ producentOptions[0] }}</span>
                  <span class="text-ink-gray-5"> · {{ hasBat ? 'wynika z zestawu' : 'jedyny dostępny' }}</span>
                </div>
                <WyborSegmentowy v-else v-model="sel.producent" :options="producentOptions" />
              </div>

              <div class="grid grid-cols-2 gap-x-3 gap-y-2.5">
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Falownik</div>
                  <select v-model="sel.falownik" class="kalk-select">
                    <option value="">-- wybierz --</option>
                    <option v-for="c in falownikOptions" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
                  </select>
                </div>

                <div v-if="hasBat">
                  <div class="mb-0.5 text-sm text-ink-gray-5">Magazyn energii</div>
                  <select v-model="sel.bateria" class="kalk-select">
                    <option value="">-- wybierz --</option>
                    <template v-if="bateriaGrupy.length > 1">
                      <optgroup v-for="g in bateriaGrupy" :key="g.naglowek" :label="g.naglowek">
                        <option v-for="c in g.opcje" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
                      </optgroup>
                    </template>
                    <template v-else>
                      <option v-for="c in bateriaOptions" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
                    </template>
                  </select>
                </div>

                <template v-if="hasPv">
                  <div>
                    <div class="mb-0.5 text-sm text-ink-gray-5">Panel fotowoltaiczny</div>
                    <select v-model="sel.panel" class="kalk-select">
                      <option value="">-- wybierz --</option>
                      <option v-for="c in panelOptions" :key="c.name" :value="c.name">{{ panelLabel(c) }}</option>
                    </select>
                  </div>
                  <div>
                    <div class="mb-0.5 text-sm text-ink-gray-5">Moc instalacji PV</div>
                    <select v-model.number="sel.mocPvKw" class="kalk-select" :disabled="!sel.panel">
                      <option :value="null">{{ sel.panel ? '-- wybierz --' : 'Najpierw wybierz panel' }}</option>
                      <template v-if="mocGrupy.length > 1">
                        <optgroup v-for="g in mocGrupy" :key="g.naglowek" :label="g.naglowek">
                          <option v-for="o in g.opcje" :key="o.value" :value="o.value">{{ o.label }}</option>
                        </optgroup>
                      </template>
                      <template v-else>
                        <option v-for="o in mocOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
                      </template>
                    </select>
                  </div>
                  <div>
                    <div class="mb-0.5 text-sm text-ink-gray-5">Konstrukcja</div>
                    <select v-model="sel.konstrukcja" class="kalk-select">
                      <option value="">-- wybierz --</option>
                      <option v-for="c in konstrukcjaOptions" :key="c.name" :value="c.name">{{ compLabel(c) }}</option>
                    </select>
                  </div>
                </template>
              </div>
            </div>

            <!-- 3. Montaż i przyłącze (zwijana) -->
            <div class="kalk-part kalk-part-zwijana">
              <button type="button" class="kalk-part-toggle" :aria-expanded="otwarte.montaz" @click="otwarte.montaz = !otwarte.montaz">
                <span class="kalk-part-number">3</span>
                <span class="min-w-0 flex-1 text-left">
                  <span class="block text-lg font-bold text-ink-gray-9">Montaż i przyłącze</span>
                  <span v-if="!otwarte.montaz" class="mt-1 flex flex-wrap gap-1">
                    <span v-for="(p, i) in montazPodsumowanie" :key="i" class="rounded-full px-2 py-0.5 text-xs whitespace-nowrap" :class="PIGULKA_KLASY[p.ton] || PIGULKA_KLASY.neutral">{{ p.tekst }}</span>
                  </span>
                </span>
                <FeatherIcon :name="otwarte.montaz ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 shrink-0 text-ink-gray-5" />
              </button>

              <div v-if="otwarte.montaz" class="mt-4 grid items-start grid-cols-2 gap-x-3 gap-y-3">
                <div class="relative">
                  <div class="mb-0.5 text-sm text-ink-gray-5">Dodatkowy kabel (m)</div>
                  <input v-model.number="sel.kabelM" type="number" min="0" step="1" class="kalk-input kalk-input-unit" />
                  <span class="kalk-unit">m</span>
                </div>
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Spółdzielnia energetyczna</div>
                  <WyborSegmentowy v-model="sel.spoldzielnia" :options="NIE_TAK" />
                </div>
                <div v-if="licznikDostepny(sel.producent)">
                  <div class="mb-0.5 text-sm text-ink-gray-5">Dodatkowy licznik (stary falownik / mikrofalowniki)<span v-if="licznikCena > 0"> · +{{ formatPln(licznikCena) }} netto</span></div>
                  <WyborSegmentowy v-model="sel.licznik" :options="NIE_TAK" />
                </div>

                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Czy klient ma już instalację PV?</div>
                  <WyborSegmentowy v-model="sel.istniejacaPv" :options="NIE_TAK" />
                </div>
                <div v-if="sel.istniejacaPv === 'Tak'" class="relative">
                  <div class="mb-0.5 text-sm text-ink-gray-5">Moc istniejącej instalacji (kWp)</div>
                  <input v-model.number="sel.istniejacaPvMocKwp" type="number" min="0" step="0.1" class="kalk-input kalk-input-unit" />
                  <span class="kalk-unit">kWp</span>
                </div>
                <div>
                  <!-- Wybór ręczny handlowca, zablokowany na Tak gdy próg mocy
                       jest przekroczony (decyzja właściciela, ops#194). -->
                  <div class="mb-0.5 text-sm text-ink-gray-5">Uzgodnienia PPOŻ<span v-if="ppozWymaganeLive && ppozCena > 0"> · +{{ formatPln(ppozCena) }} netto</span></div>
                  <div v-if="ppozProgLive" class="flex flex-wrap items-center gap-1.5 text-sm">
                    <FeatherIcon name="lock" class="h-3.5 w-3.5 text-ink-gray-5" />
                    <span class="font-semibold text-ink-gray-9">Tak</span>
                    <span class="text-ink-gray-5">suma mocy przekracza 6,5 kW</span>
                  </div>
                  <template v-else>
                    <WyborSegmentowy v-model="sel.ppozRecznie" :options="NIE_TAK" />
                    <div class="mt-0.5 text-xs text-ink-gray-4">Ustaw Tak ręcznie, jeśli aktualna moc PV i dokładana moc PV w sumie przekroczą 6,5 kW.</div>
                  </template>
                </div>

                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Operator energetyczny</div>
                  <select v-model="sel.operator" class="kalk-select">
                    <option value="">-</option>
                    <option v-for="c in operatorOptions" :key="c.name" :value="c.nazwa">{{ c.nazwa }}</option>
                  </select>
                </div>
                <!-- Battery-only has no roof install, so there is no mounting
                     direction to choose for that variant. -->
                <div v-if="hasPv">
                  <div class="mb-0.5 text-sm text-ink-gray-5">Kierunek montażu</div>
                  <select v-model="sel.kierunek" class="kalk-select">
                    <option value="">-</option>
                    <option v-for="c in kierunekOptions" :key="c.name" :value="c.nazwa">{{ c.nazwa }}</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- 4. Finansowanie (zwijana) -->
            <div class="kalk-part kalk-part-zwijana">
              <button type="button" class="kalk-part-toggle" :aria-expanded="otwarte.finansowanie" @click="otwarte.finansowanie = !otwarte.finansowanie">
                <span class="kalk-part-number">4</span>
                <span class="min-w-0 flex-1 text-left">
                  <span class="block text-lg font-bold text-ink-gray-9">Finansowanie</span>
                  <span v-if="!otwarte.finansowanie" class="mt-1 flex flex-wrap gap-1">
                    <span v-for="(p, i) in finansowaniePodsumowanie" :key="i" class="rounded-full px-2 py-0.5 text-xs whitespace-nowrap" :class="PIGULKA_KLASY[p.ton] || PIGULKA_KLASY.neutral">{{ p.tekst }}</span>
                  </span>
                </span>
                <FeatherIcon :name="otwarte.finansowanie ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 shrink-0 text-ink-gray-5" />
              </button>

              <div v-if="otwarte.finansowanie" class="mt-4 grid items-start grid-cols-2 gap-x-3 gap-y-3">
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Ulga termomodernizacyjna</div>
                  <select v-model.number="sel.ulgaPct" class="kalk-select">
                    <option :value="12">12%</option>
                    <option :value="19">19%</option>
                  </select>
                </div>
                <div>
                  <div class="mb-0.5 text-sm text-ink-gray-5">Okres finansowania (lat)</div>
                  <select v-model.number="sel.okresLat" class="kalk-select">
                    <option v-for="n in 10" :key="n" :value="n">{{ n }}</option>
                  </select>
                </div>

                <div class="relative">
                  <div class="mb-0.5 text-sm text-ink-gray-5">Wpłata własna (PLN)</div>
                  <input v-model.number="sel.wplataWlasna" type="number" min="0" step="0.01" class="kalk-input kalk-input-unit" />
                  <span class="kalk-unit">zł</span>
                </div>
              </div>
            </div>

            <!-- 5. Opcje dodatkowe do istniejącego zestawu PV / PV+ME / ME
                 (ops#225). Stopniowe odsłanianie: każdy wiersz pokazuje
                 wyłącznie nazwę i włącznik Nie/Tak, a jego szczegółowe opcje
                 renderują się dopiero po włączeniu. Karta znika całkowicie,
                 gdy żaden dodatek nie jest dostępny. -->
            <div v-if="anyDodatkiAvailable" class="kalk-part kalk-part-zwijana">
              <button type="button" class="kalk-part-toggle" :aria-expanded="otwarte.dodatki" @click="otwarte.dodatki = !otwarte.dodatki">
                <span class="kalk-part-number">5</span>
                <span class="min-w-0 flex-1 text-left">
                  <span class="block text-lg font-bold text-ink-gray-9">Opcje dodatkowe</span>
                  <span v-if="!otwarte.dodatki" class="mt-1 flex flex-wrap gap-1">
                    <span v-for="(p, i) in dodatkiPodsumowanie" :key="i" class="rounded-full px-2 py-0.5 text-xs whitespace-nowrap" :class="PIGULKA_KLASY[p.ton] || PIGULKA_KLASY.neutral">{{ p.tekst }}</span>
                  </span>
                </span>
                <FeatherIcon :name="otwarte.dodatki ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 shrink-0 text-ink-gray-5" />
              </button>

              <div v-if="otwarte.dodatki" class="mt-4">
                <div class="flex flex-col gap-3">
                  <div v-if="klimaDostepnaNow">
                    <div class="flex items-center justify-between gap-2">
                      <div class="text-sm font-medium text-ink-gray-7">Klimatyzacja</div>
                      <WyborSegmentowy :model-value="dodatkiUi.klimaOn ? 'Tak' : 'Nie'" :options="NIE_TAK" @update:model-value="dodatkiUi.klimaOn = $event === 'Tak'" />
                    </div>
                    <div v-if="dodatkiUi.klimaOn" class="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-2">
                      <div>
                        <div class="mb-0.5 text-sm text-ink-gray-5">Rodzaj</div>
                        <select v-model="dodatkiUi.klimaRodzaj" class="kalk-select">
                          <option value="">-- wybierz --</option>
                          <option v-for="r in RODZAJE_KLIMY_DODATKU" :key="r.value" :value="r.value">{{ r.label }}</option>
                        </select>
                      </div>
                      <div v-if="dodatkiUi.klimaRodzaj">
                        <div class="mb-0.5 text-sm text-ink-gray-5">Model</div>
                        <select v-model="dodatkiUi.klimaModel" class="kalk-select">
                          <option value="">-- wybierz --</option>
                          <option v-for="m in modeleKlimyOptions" :key="m.model" :value="m.model">Rotenso {{ m.label }}</option>
                        </select>
                      </div>
                      <div v-if="dodatkiUi.klimaRodzaj && dodatkiUi.klimaModel">
                        <div class="mb-0.5 text-sm text-ink-gray-5">Moc</div>
                        <select v-model="sel.dodatki.klimaKod" class="kalk-select">
                          <option value="">-- wybierz --</option>
                          <option v-for="o in moceKlimyOptions" :key="o.kod" :value="o.kod">{{ o.label }}<template v-if="o.cena > 0"> · +{{ formatPln(o.cena) }} netto</template></option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div v-if="paneleDostepneNow">
                    <div class="flex items-center justify-between gap-2">
                      <div class="text-sm font-medium text-ink-gray-7">Panele PV</div>
                      <WyborSegmentowy :model-value="dodatkiUi.paneleOn ? 'Tak' : 'Nie'" :options="NIE_TAK" @update:model-value="dodatkiUi.paneleOn = $event === 'Tak'" />
                    </div>
                    <div v-if="dodatkiUi.paneleOn" class="mt-1.5">
                      <div class="mb-0.5 text-sm text-ink-gray-5">Ilość</div>
                      <select v-model.number="sel.dodatki.panele" class="kalk-select">
                        <option :value="0">-- wybierz --</option>
                        <option v-for="o in paneleDodatekOptions" :key="o.kod" :value="o.ilosc">{{ o.ilosc }} szt. · +{{ formatPln(o.cena) }} netto</option>
                      </select>
                    </div>
                  </div>

                  <div v-if="paneleDostepneNow">
                    <div class="flex items-center justify-between gap-2">
                      <div class="text-sm font-medium text-ink-gray-7">Panele PV + mikro</div>
                      <WyborSegmentowy :model-value="dodatkiUi.paneleMikroOn ? 'Tak' : 'Nie'" :options="NIE_TAK" @update:model-value="dodatkiUi.paneleMikroOn = $event === 'Tak'" />
                    </div>
                    <div v-if="dodatkiUi.paneleMikroOn" class="mt-1.5">
                      <div class="mb-0.5 text-sm text-ink-gray-5">Ilość</div>
                      <select v-model.number="sel.dodatki.paneleMikro" class="kalk-select">
                        <option :value="0">-- wybierz --</option>
                        <option v-for="o in paneleMikroDodatekOptions" :key="o.kod" :value="o.ilosc">{{ o.ilosc }} szt. · +{{ formatPln(o.cena) }} netto</option>
                      </select>
                    </div>
                  </div>

                  <div v-if="emsDostepnyNow">
                    <div class="flex items-center justify-between gap-2">
                      <div class="text-sm font-medium text-ink-gray-7">EMS Zeronest<span v-if="emsCena > 0"> · +{{ formatPln(emsCena) }} netto</span></div>
                      <WyborSegmentowy
                        :model-value="dodatkiUi.emsOn ? 'tak' : 'nie'"
                        :options="NIE_TAK_MALE"
                        :disabled="emsWymuszonyNow"
                        testid-prefix="ems-"
                        @update:model-value="ustawEms($event === 'tak')"
                      />
                    </div>
                    <div v-if="emsWymuszonyNow" class="mt-1 flex items-center gap-1.5 text-xs text-ink-gray-5">
                      <FeatherIcon name="lock" class="h-3.5 w-3.5" />
                      <span data-testid="ems-wymuszony">w zestawie COMFORT PREMIUM, zawsze</span>
                    </div>
                  </div>

                  <div v-if="pstrykDostepnyNow">
                    <div class="flex items-center justify-between gap-2">
                      <div class="text-sm font-medium text-ink-gray-7">Licznik Pstryk</div>
                      <WyborSegmentowy :model-value="dodatkiUi.pstrykOn ? 'Tak' : 'Nie'" :options="NIE_TAK" @update:model-value="dodatkiUi.pstrykOn = $event === 'Tak'" />
                    </div>
                    <div class="mt-0.5 text-xs text-ink-gray-4">bez dopłaty, do zamówienia</div>
                  </div>

                  <div v-if="evDostepneNow">
                    <div class="flex items-center justify-between gap-2">
                      <div class="text-sm font-medium text-ink-gray-7">Ładowarka EV</div>
                      <WyborSegmentowy :model-value="dodatkiUi.evOn ? 'Tak' : 'Nie'" :options="NIE_TAK" @update:model-value="dodatkiUi.evOn = $event === 'Tak'" />
                    </div>
                    <div v-if="dodatkiUi.evOn" class="mt-1.5">
                      <div class="mb-0.5 text-sm text-ink-gray-5">Typ</div>
                      <select v-model="sel.dodatki.evKod" class="kalk-select">
                        <option value="">-- wybierz --</option>
                        <option v-for="o in evOpcjeList" :key="o.kod" :value="o.kod">{{ o.nazwa }}<template v-if="o.cena > 0"> · +{{ formatPln(o.cena) }} netto</template></option>
                      </select>
                    </div>
                  </div>
                </div>

                <div v-if="summary.dodatki_netto > 0" class="mt-3 flex justify-between border-t border-outline-gray-1 pt-2 text-sm font-medium tabular-nums text-ink-gray-8">
                  <span>Dodatki razem</span><span>+{{ formatPln(summary.dodatki_netto) }} netto</span>
                </div>
              </div>
            </div>
          </div>

          <div class="kalk-output border-l border-outline-gray-2 pl-5">
            <div class="sticky top-3">
              <div v-if="$slots['client-picker']" class="mb-3 w-full min-w-0">
                <div class="mb-0.5 text-sm text-ink-gray-5">Klient</div>
                <slot name="client-picker" />
              </div>
              <div class="mb-2 text-base font-semibold text-ink-gray-9">Wycena</div>

              <KalkulatorParagon
                :summary="summary"
                :typ-klienta="sel.typKlienta"
                :zasady-dotacji="sel.zasadyDotacji"
                :ulga-pct="Number(sel.ulgaPct)"
                :okres-lat="Number(sel.okresLat)"
              />

              <Button
                class="mt-3 w-full"
                variant="solid"
                :disabled="!canGenerate || generating"
                @click="runGenerate"
              >
                {{ generating ? 'Generuję ofertę…' : 'Generuj ofertę' }}
              </Button>

              <div v-if="!c.name" class="mt-1 text-center text-xs text-ink-gray-5">
                Wybierz klienta powyżej, aby wygenerować ofertę.
              </div>

              <div class="mt-3">
                <button
                  type="button"
                  class="flex w-full items-center justify-between rounded-lg border border-outline-gray-2 px-2.5 py-1.5 text-sm text-ink-gray-7 hover:bg-surface-gray-2"
                  :aria-expanded="showNarzut"
                  @click="showNarzut = !showNarzut"
                >
                  <span>Ustawienia niestandardowe</span>
                  <FeatherIcon :name="showNarzut ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 text-ink-gray-5" />
                </button>
                <div v-if="showNarzut" class="mt-1.5 rounded-lg border border-outline-gray-2 px-2.5 py-1.5">
                  <div class="mb-0.5 text-sm text-ink-gray-5">Wysokość narzutu</div>
                  <input
                    v-model.number="sel.narzut" type="number" min="0" :max="narzutMax > 0 ? narzutMax : undefined" step="0.01"
                    class="kalk-input"
                    @blur="sel.narzut = narzutMax > 0 ? Math.min(narzutMax, Math.max(0, Number(sel.narzut) || 0)) : Math.max(0, Number(sel.narzut) || 0)"
                  />
                  <div v-if="!narzutValid" class="mt-0.5 text-xs text-ink-red-6">{{ narzutErrorMsg }}</div>
                </div>
              </div>

              <div v-if="summary.is_admin && summary.breakdown" class="mt-2.5">
                <button
                  type="button"
                  class="flex w-full items-center justify-between rounded-md border border-outline-amber-3 bg-surface-amber-2 px-2.5 py-1.5 text-sm font-semibold text-ink-amber-8 transition-colors hover:bg-surface-amber-3"
                  @click="showAdminBreakdown = !showAdminBreakdown"
                >
                  <span>Admin - Ustawienia Zaawansowane</span>
                  <FeatherIcon :name="showAdminBreakdown ? 'chevron-up' : 'chevron-down'" class="h-4 w-4 text-ink-amber-8" />
                </button>
                <div v-show="showAdminBreakdown" class="mt-1.5 rounded-lg border border-dashed border-outline-amber-3 bg-surface-amber-2 p-2.5">
                <div class="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-amber-8">Rozbicie kosztów (administrator)</div>
                <div v-for="grupa in grupyBreakdown" :key="grupa.klucz">
                  <div :class="grupa.klucz === 'hurtownia' ? 'mt-0' : 'mt-2'" class="mb-0.5 text-xs font-semibold uppercase tracking-wider text-ink-amber-8">{{ grupa.etykieta }}</div>
                  <div v-if="grupa.adnotacja" class="py-0.5 text-sm text-ink-gray-7" data-testid="prog-magazynu">{{ grupa.adnotacja }}</div>
                  <div v-for="p in grupa.pozycje" :key="p.klucz" class="flex justify-between py-0.5 text-sm tabular-nums text-ink-gray-7"><span>{{ p.etykieta }}</span><span>{{ formatPln(p.kwota) }}</span></div>
                  <div class="mt-1 flex justify-between border-t border-outline-amber-2 pt-1 text-sm font-semibold tabular-nums text-ink-gray-9"><span>Razem</span><span>{{ formatPln(grupa.suma) }}</span></div>
                </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </template>

      <div v-else class="py-4">
        <div class="mb-2 text-base font-semibold text-ink-gray-9">Szansa utworzona</div>
        <p class="mb-3 text-sm text-ink-gray-7">{{ successSummary }}</p>
        <div class="flex gap-2">
          <a class="inline-flex items-center rounded bg-surface-gray-10 px-3 py-1.5 text-sm font-medium text-ink-base hover:bg-surface-gray-9" :href="dealHref" target="_blank" rel="noopener">Otwórz szansę w CRM</a>
          <Button variant="ghost" @click="resetFlow">Nowa oferta</Button>
        </div>
      </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { call, Button, FeatherIcon } from 'frappe-ui'
import {
  VARIANTS,
  VARIANT_PV,
  VARIANT_PV_BAT,
  variantHasPv,
  variantHasBattery,
  producentOptionsFor,
  ZESTAWY,
  DOMYSLNY_ZESTAW,
  zestawProducent,
  licznikDostepny,
  panelLabel,
  buildMocOptionsForPanel,
  paneleDlaZestawu,
  snapMocToPanel,
  pickMocForTarget,
  suggestedKwp as suggestedKwpFor,
  suggestedStorageKwh,
  czyAutodobor,
  celKwpComfortPremium,
  celKwhComfortPremium,
  dobierzMocComfortPremium,
  dobierzMagazynComfortPremium,
  pickBySpec,
  pickMounting,
  ppozWymagane,
  ppozWymuszonyProgiem,
  RODZAJE_KLIMY_DODATKU,
  klimaDodatekDostepna,
  dodatekPaneleDostepny,
  emsDostepny,
  emsWymuszony,
  pstrykDostepny,
  evDostepne,
  moceDodatkuKlimy,
  modeleDodatkuKlimy,
  domyslnyStanEms,
  evOpcje,
  sanitizujDodatki,
  grupujMocePv,
  grupujMagazyny,
  opisZestawu,
  PROG_PPOZ_KW,
  podsumowanieMontazu,
  podsumowanieFinansowania,
  podsumowanieDodatkow,
} from '@/utils/pvForm'
import { formatPln } from '@/utils/money'
import { grupujBreakdown } from '@/utils/pvBreakdown'
import { czyNowyRodzaj, RODZAJE_NOWE } from '@/utils/ozeForm'
import KalkulatorOzeRozszerzony from './KalkulatorOzeRozszerzony.vue'
import KalkulatorParagon from './KalkulatorParagon.vue'
import WyborSegmentowy from './WyborSegmentowy.vue'

const props = defineProps({
  contact: { type: Object, default: () => ({}) },
})

const router = useRouter()

// Rodzaj instalacji: trzy stare warianty PV/magazynu (VARIANTS) to segmenty,
// cztery nowe rodzaje OZE (RODZAJE_NOWE, b68) trafiają do selecta "Inne
// rodzaje". Wybranie jednego z czterech nowych rodzajów ustawia sel.variant
// tak samo jak dawne kafelki i przełącza cały widok na
// KalkulatorOzeRozszerzony.vue (patrz szablon wyżej).
function wybierzInnyRodzaj(event) {
  const v = event.target.value
  if (v) sel.variant = v
  event.target.value = ''
}

const NIE_TAK = ['Nie', 'Tak']
const NIE_TAK_MALE = [
  { value: 'nie', label: 'Nie' },
  { value: 'tak', label: 'Tak' },
]
const plLiczba = (n) => String(n).replace('.', ',')

const VOIVODESHIPS = [
  'dolnośląskie', 'kujawsko-pomorskie', 'lubelskie', 'lubuskie', 'łódzkie',
  'małopolskie', 'mazowieckie', 'opolskie', 'podkarpackie', 'podlaskie',
  'pomorskie', 'śląskie', 'świętokrzyskie', 'warmińsko-mazurskie',
  'wielkopolskie', 'zachodniopomorskie',
]
const TYP_KLIENTA_OPTIONS = [
  { value: 'indywidualny', label: 'Indywidualny' },
  { value: 'biznesowy', label: 'Biznesowy' },
]
const ZASADY_DOTACJI_OPTIONS = [
  { value: 'Nowe zasady', label: 'Nowe zasady' },
  { value: 'Stare zasady', label: 'Stare zasady' },
]

// --- Prefill client data from the current contact --------------------------
const c = computed(() => props.contact || {})
function composeAddress() {
  const parts = [c.value.custom_ulica, c.value.custom_nr_domu].filter(Boolean).join(' ').trim()
  return c.value.custom_nr_mieszkania ? parts + '/' + c.value.custom_nr_mieszkania : parts
}
const voivodeshipPrefill = computed(() => {
  const w = (c.value.custom_wojewodztwo || '').toLowerCase().trim()
  return VOIVODESHIPS.indexOf(w) !== -1 ? w : ''
})

// --- Selections --------------------------------------------------------------
const sel = reactive({
  typKlienta: 'indywidualny',
  variant: 'Fotowoltaika + Magazyn',
  zestaw: DOMYSLNY_ZESTAW,
  producent: '',
  falownik: '',
  bateria: '',
  panel: '',
  mocPvKw: null,
  konstrukcja: '',
  kabelM: 0,
  spoldzielnia: 'Nie',
  licznik: 'Nie',
  istniejacaPv: 'Nie',
  istniejacaPvMocKwp: null,
  ppozRecznie: 'Nie',
  ulgaPct: 12,
  okresLat: 10, // domyślny okres finansowania 10 lat (decyzja właściciela 2026-09-10, było 5)
  wplataWlasna: 0,
  narzut: 0,
  operator: '',
  kierunek: '',
  consumption: null,
  zasadyDotacji: 'Nowe zasady',
  // Opcje dodatkowe (ops#225): payload wysyłany do serwera. Wszystko
  // wyłączone na starcie (decyzja właściciela 2026-10-05, dotyczy też EMS
  // Zeronest) - sanitizujDodatki poniżej tylko zeruje, nigdy nie włącza.
  dodatki: {
    klimaKod: '',
    panele: 0,
    paneleMikro: 0,
    emsBreeze: 'Nie',
    pstryk: 'Nie',
    evKod: '',
  },
})

// Stan włączników/pośrednich wyborów karty "Opcje dodatkowe" - WYŁĄCZNIE UI,
// nigdy nie trafia do payloadu. "Rodzaj" klimatyzacji jest pośrednim krokiem
// (rodzaj -> model -> moc), więc nie ma odpowiednika w sel.dodatki.
const dodatkiUi = reactive({
  klimaOn: false,
  klimaRodzaj: '',
  klimaModel: '',
  paneleOn: false,
  paneleMikroOn: false,
  emsOn: false,
  pstrykOn: false,
  evOn: false,
})

const hasPv = computed(() => variantHasPv(sel.variant))
const hasBat = computed(() => variantHasBattery(sel.variant))

// Cascade: PV-only forces FoxESS; PV+Magazyn / Magazyn take the producer of the chosen zestaw (ops#291).
const producentOptions = computed(() => producentOptionsFor(sel.variant, sel.zestaw))

watch(
  () => [sel.variant, sel.zestaw],
  () => {
    if (!producentOptions.value.includes(sel.producent)) sel.producent = producentOptions.value[0]
    if (!hasPv.value) { sel.panel = ''; sel.mocPvKw = null; sel.konstrukcja = ''; sel.kierunek = ''; sel.consumption = null }
    if (!hasBat.value) sel.bateria = ''
  },
  { immediate: true },
)

// Reset downstream picks whenever producent changes (cascade rule).
watch(
  () => sel.producent,
  () => {
    sel.falownik = ''
    sel.bateria = ''
    if (!licznikDostepny(sel.producent)) sel.licznik = 'Nie'
  },
)

// Clearing "Czy klient ma już instalację PV?" back to Nie also clears its
// power, so a stale value cannot silently re-enter the PPOŻ sum (ops#194).
watch(
  () => sel.istniejacaPv,
  () => {
    if (sel.istniejacaPv === 'Nie') sel.istniejacaPvMocKwp = null
  },
)

// --- Catalog (names + non-secret tags only — no prices ever fetched) -------
const catMap = reactive({})
// Katalog dodatków (ops#225): data.dodatki z volteo_quote_components, każda
// pozycja niesie już gotową klientowi "cena" (patrz komentarz w pvForm.js) -
// to jedyne miejsce w tym pliku, gdzie ceny przychodzą z serwera dla
// wyświetlenia, nie są tu liczone.
const dodatkiCatalog = ref([])
// Pozycje klimatyzacji samodzielnej (volteo_oze_pozycje, grupy klima_*):
// jedyne źródło przypisania modelu do rodzaju (dod_klima rodzaju nie niesie).
// Pobierane osobno i miękko: błąd = brak modeli w dodatku, kalkulator działa.
const pozycjeKlimy = ref([])
function byKat(kat) {
  return catMap[kat] || []
}
function compLabel(x) {
  return [x.nazwa, x.model].filter(Boolean).join(' ')
}

async function loadComponents() {
  try {
    const data = await call('volteo_quote_components')
    const comps = (data && data.components) || []
    const m = {}
    for (const x of comps) {
      ;(m[x.kategoria] = m[x.kategoria] || []).push(x)
    }
    for (const k in m) catMap[k] = m[k]
    // narzut_max: 0 or a missing field means no upper limit in this UI. The
    // server remains authoritative and rejects an out-of-range narzut with a
    // readable error regardless of what the client enforces here.
    narzutMax.value = Number(data && data.narzut_max) || 0
    // dotacja_limity: per-rule subsidy caps, keyed by ZASADY_DOTACJI_OPTIONS
    // value. 0 or missing for a given key means the limit is unknown; the
    // server remains authoritative during calc regardless of what is shown here.
    dotacjaLimity.value = (data && data.dotacja_limity) || {}
    // licznik_dodatkowy: customer list price of the "Dodatkowy licznik"
    // add-on, for display in the label only. 0 or missing means unknown; the
    // server remains authoritative and computes the actual amount at calc.
    licznikCena.value = Number(data && data.licznik_dodatkowy) || 0
    // ppoz: customer list price of PPOZ fire-protection agreements, for
    // display in the label only. 0 or missing means unknown; the server
    // remains authoritative and computes the actual amount at calc (ops#194).
    ppozCena.value = Number(data && data.ppoz) || 0
    // dodatki: katalog dodatków PV/PV+ME/ME (ops#225), patrz komentarz przy
    // deklaracji dodatkiCatalog powyżej.
    dodatkiCatalog.value = (data && data.dodatki) || []
  } catch (err) {
    errorMsg.value = extractErrorMessage(err)
  }
}
loadComponents()

async function loadPozycjeKlimy() {
  try {
    const data = await call('crm.api.kalkulator_oze.volteo_oze_pozycje')
    pozycjeKlimy.value = ((data && data.pozycje) || []).filter((p) => String(p.grupa || '').startsWith('klima_'))
  } catch (err) {
    pozycjeKlimy.value = []
  }
}
loadPozycjeKlimy()

const falownikOptions = computed(() => byKat('Falownik').filter((x) => x.producent === sel.producent))
const bateriaOptions = computed(() => byKat('Magazyn energii').filter((x) => x.producent === sel.producent))
const konstrukcjaOptions = computed(() => byKat('Konstrukcja'))
const operatorOptions = computed(() => byKat('Operator'))
const kierunekOptions = computed(() => byKat('Kierunek montazu'))
// ops#292: karty paneli zależą od zestawu (sama PV: tylko karty uniwersalne).
const panelOptions = computed(() =>
  paneleDlaZestawu(byKat('Panel PV'), hasBat.value ? sel.zestaw : ''),
)

// --- Opcje dodatkowe (ops#225) -----------------------------------------------
// Typ falownika Sigenergy ("TP2"/"AIO") - steruje dostępnością ładowarki EV
// DC (wyłącznie AIO) w evOpcje() poniżej.
const sigenTyp = computed(() => falownikOptions.value.find((c) => c.name === sel.falownik)?.sigen_typ || '')

const klimaDostepnaNow = computed(() => klimaDodatekDostepna(sel.variant))
const paneleDostepneNow = computed(() => dodatekPaneleDostepny(sel.variant))
const emsDostepnyNow = computed(() => emsDostepny({ producent: sel.producent, variant: sel.variant }))
const emsWymuszonyNow = computed(() => emsWymuszony({ producent: sel.producent, variant: sel.variant }))
const pstrykDostepnyNow = computed(() => pstrykDostepny({ producent: sel.producent, variant: sel.variant }))
const evDostepneNow = computed(() => evDostepne({ producent: sel.producent, variant: sel.variant }))
const anyDodatkiAvailable = computed(() =>
  klimaDostepnaNow.value || paneleDostepneNow.value || emsDostepnyNow.value || pstrykDostepnyNow.value || evDostepneNow.value,
)

const modeleKlimyOptions = computed(() =>
  modeleDodatkuKlimy(dodatkiCatalog.value, pozycjeKlimy.value, dodatkiUi.klimaRodzaj),
)
const moceKlimyOptions = computed(() => moceDodatkuKlimy(dodatkiCatalog.value, dodatkiUi.klimaModel))

// EMS Zeronest (kod ems_breeze): domyślnie Tak, gdy dostępny (#237). emsRecznie przechowuje
// WARTOŚĆ wyboru użytkownika (null = brak wyboru). Decyzja właściciela
// 2026-10-10: ręczny wybór jest trwały przez całe życie formularza, także
// gdy EMS na chwilę przestaje być dostępny (zmiana producenta/wariantu).
const emsRecznie = ref(null)
function ustawEms(on) {
  emsRecznie.value = on
  dodatkiUi.emsOn = on
}
function zastosujDomyslnyEms() {
  dodatkiUi.emsOn = domyslnyStanEms({
    producent: sel.producent,
    variant: sel.variant,
    wyborReczny: emsRecznie.value,
  })
}
const paneleDodatekOptions = computed(() =>
  dodatkiCatalog.value.filter((d) => d.grupa === 'dod_panele').sort((a, b) => a.ilosc - b.ilosc),
)
const paneleMikroDodatekOptions = computed(() =>
  dodatkiCatalog.value.filter((d) => d.grupa === 'dod_panele_mikro').sort((a, b) => a.ilosc - b.ilosc),
)
const emsCena = computed(() => dodatkiCatalog.value.find((d) => d.kod === 'ems_breeze')?.cena || 0)
const evOpcjeList = computed(() =>
  evOpcje(dodatkiCatalog.value, { producent: sel.producent, variant: sel.variant, sigenTyp: sigenTyp.value }),
)

// Wyłączenie wiersza czyści jego wybory (decyzja z briefu F2); EMS Zeronest /
// Pstryk to proste włączniki bez dalszych pod-wyborów, więc ich sel.dodatki
// jest bezpośrednio zwierciadłem toggle'a Tak/Nie.
watch(
  () => dodatkiUi.klimaOn,
  (on) => {
    if (!on) {
      dodatkiUi.klimaRodzaj = ''
      dodatkiUi.klimaModel = ''
      sel.dodatki.klimaKod = ''
    }
  },
)
watch(
  () => dodatkiUi.klimaRodzaj,
  () => {
    // Zmiana rodzaju unieważnia model i moc - wymusza ponowny wybór.
    dodatkiUi.klimaModel = ''
    sel.dodatki.klimaKod = ''
  },
)
watch(
  () => dodatkiUi.klimaModel,
  () => {
    // Zmiana modelu unieważnia moc.
    sel.dodatki.klimaKod = ''
  },
)
watch(
  () => dodatkiUi.paneleOn,
  (on) => {
    if (!on) sel.dodatki.panele = 0
  },
)
watch(
  () => dodatkiUi.paneleMikroOn,
  (on) => {
    if (!on) sel.dodatki.paneleMikro = 0
  },
)
watch(
  () => dodatkiUi.emsOn,
  (on) => {
    sel.dodatki.emsBreeze = on ? 'Tak' : 'Nie'
  },
)
watch(
  () => dodatkiUi.pstrykOn,
  (on) => {
    sel.dodatki.pstryk = on ? 'Tak' : 'Nie'
  },
)
watch(
  () => dodatkiUi.evOn,
  (on) => {
    if (!on) sel.dodatki.evKod = ''
  },
)

// Sanityzacja dodatków na zmianę wariantu/producenta/falownika (sigenTyp
// pochodzi z falownika) - sel.dodatki.* jest tylko zerowane, nigdy włączane
// (sanitizujDodatki w pvForm.js); tu dodatkowo synchronizujemy włączniki UI
// z tą samą dostępnością, żeby wiersz nie zostawał "włączony" bez wyboru.
watch(
  () => [sel.variant, sel.producent, sel.falownik],
  () => {
    sel.dodatki = sanitizujDodatki(sel.dodatki, {
      variant: sel.variant,
      producent: sel.producent,
      sigenTyp: sigenTyp.value,
    })
    if (!klimaDostepnaNow.value) dodatkiUi.klimaOn = false
    if (!paneleDostepneNow.value) {
      dodatkiUi.paneleOn = false
      dodatkiUi.paneleMikroOn = false
    }
    zastosujDomyslnyEms()
    if (!pstrykDostepnyNow.value) dodatkiUi.pstrykOn = false
    if (!evDostepneNow.value) dodatkiUi.evOn = false
  },
)

// Stan startowy: producent/wariant bywają już ustawione przy montowaniu.
zastosujDomyslnyEms()

function panelMocWp(panelName) {
  const p = panelOptions.value.find((x) => x.name === panelName)
  return p ? Number(p.moc_wp) || 0 : 0
}

// Moc-PV dropdown is panel-dependent: the panel count the server derives is
// round(moc_pv_kw * 1000 / moc_wp), so the client must only ever offer moc
// values that came from buildMocOptionsForPanel() of the selected panel.
const mocOptions = computed(() => {
  const wp = panelMocWp(sel.panel)
  return wp > 0 ? buildMocOptionsForPanel(wp) : []
})

// Changing the panel re-snaps an already-chosen moc to the new panel's grid;
// clearing the panel clears the dependent moc pick (mirrors the variant-reset
// convention above).
watch(
  () => sel.panel,
  (newPanel) => {
    if (!newPanel) {
      sel.mocPvKw = null
      return
    }
    if (sel.mocPvKw) {
      sel.mocPvKw = snapMocToPanel(sel.mocPvKw, panelMocWp(newPanel))
    }
  },
)

// Default panel-card preselection: pick the first active card (lowest sort)
// once the catalog loads, and again whenever the current pick falls out of
// the active list. Never touches sel.panel for battery-only variants — the
// variant watcher above already owns clearing it there.
watch(
  [panelOptions, hasPv],
  ([opcje, pv]) => {
    if (!pv || !opcje.length) return
    if (!sel.panel || !opcje.some((c) => c.name === sel.panel)) {
      sel.panel = opcje[0].name
    }
  },
  { immediate: true },
)

// --- Auto-assembly suggestion from Roczne zużycie ---------------------------
// Sizing heuristics live in pvForm.js (display-only estimate — the server
// remains the source of truth for pricing/BOM once fields are set).
const suggestedKwp = computed(() => suggestedKwpFor(sel.consumption, sel.variant))

// Storage sizing always uses the ×1.0 (PV+Magazyn) power suggestion, never the
// ×1.4 PV-only oversizing — the oversize ratio is meant to push surplus PV
// production to the grid, not to inflate the battery.
const suggestedStorage = computed(() =>
  suggestedStorageKwh(sel.consumption, suggestedKwpFor(sel.consumption, VARIANT_PV_BAT)),
)

// --- Autodobor COMFORT PREMIUM (ops#295) ------------------------------------
// Dla PV + Magazyn w zestawie COMFORT PREMIUM kalkulator sam podstawia moc PV,
// magazyn i falownik z rocznego zużycia (tylko dobór, ceny liczy serwer).
// Podstawienie odpala się wyłącznie przy zmianie zużycia, zestawu lub panelu
// (watch niżej), więc ręczna zmiana mocy/magazynu/falownika jest trwała do
// następnej zmiany któregoś z tych trzech (wzorzec emsRecznie, #237).
const autodoborAktywny = computed(() => czyAutodobor({ variant: sel.variant, zestaw: sel.zestaw }))
const fmtPl = (n) => n.toFixed(2).replace('.', ',')
const celPvTekst = computed(() => fmtPl(celKwpComfortPremium(sel.consumption)))
const celMeTekst = computed(() => fmtPl(celKwhComfortPremium(sel.consumption)))

function zastosujAutodobor() {
  if (!autodoborAktywny.value || !(sel.consumption > 0)) return
  const wp = panelMocWp(sel.panel)
  if (!wp) return
  const moc = dobierzMocComfortPremium(sel.consumption, wp)
  if (moc == null) return
  sel.mocPvKw = moc
  const prod = zestawProducent(sel.zestaw)
  const inverters = byKat('Falownik').filter((c) => c.producent === prod)
  const fal = pickBySpec(inverters, 'moc_kw', moc)
  if (fal) sel.falownik = fal.name
  const bat = dobierzMagazynComfortPremium(
    sel.consumption,
    byKat('Magazyn energii').filter((c) => c.producent === prod),
  )
  if (bat) sel.bateria = bat.name
  const k = pickMounting(byKat('Konstrukcja'))
  if (k && !sel.konstrukcja) sel.konstrukcja = k.name
}

// flush 'post': watchery kaskady (zestaw -> producent -> czyszczenie
// falownika/baterii, auto-wybór panelu, snap mocy) kończą się przed doborem.
watch(
  () => [sel.consumption, sel.zestaw, sel.panel, sel.variant, catMap['Falownik'], catMap['Magazyn energii']],
  zastosujAutodobor,
  { flush: 'post' },
)

// "Ustaw z zużycia" — fills the configuration from the suggestion, respecting
// the currently selected variant. Never runs automatically; only on click.
// Everything stays editable afterwards. Base fields (variant/producent) are
// set first, then we await a tick so the cascade watchers above finish
// resetting downstream fields BEFORE we set the dependent picks — otherwise
// they'd get clobbered.
async function applyFromConsumption() {
  if (sel.variant === VARIANT_PV_BAT) {
    const kwp = suggestedKwp.value
    const storage = suggestedStorage.value
    if (!kwp) return

    sel.producent = zestawProducent(sel.zestaw)
    await nextTick()

    if (!sel.panel) {
      const firstPanel = panelOptions.value[0]
      if (firstPanel) sel.panel = firstPanel.name
    }
    sel.mocPvKw = pickMocForTarget(kwp, panelMocWp(sel.panel))

    // Falownik: producent zestawu (Sigenergy tylko TP2), smallest moc_kw >= kwp, else largest.
    const inverters = byKat('Falownik').filter(
      (c) => c.producent === sel.producent && (sel.producent !== 'Sigenergy' || c.sigen_typ === 'TP2'),
    )
    const fal = pickBySpec(inverters, 'moc_kw', kwp)
    if (fal) sel.falownik = fal.name

    // Bateria: producent zestawu, smallest pojemnosc_kwh >= storage, else largest.
    const bats = byKat('Magazyn energii').filter((c) => c.producent === sel.producent)
    const bat = pickBySpec(bats, 'pojemnosc_kwh', storage)
    if (bat) sel.bateria = bat.name

    // Konstrukcja: prefer "…blacha", else first available.
    const k = pickMounting(byKat('Konstrukcja'))
    if (k) sel.konstrukcja = k.name
    return
  }

  if (sel.variant === VARIANT_PV) {
    const kwp = suggestedKwp.value
    if (!kwp) return

    // producentOptionsFor forces FoxESS for PV-only.
    sel.producent = 'FoxESS'
    await nextTick()

    if (!sel.panel) {
      const firstPanel = panelOptions.value[0]
      if (firstPanel) sel.panel = firstPanel.name
    }
    sel.mocPvKw = pickMocForTarget(kwp, panelMocWp(sel.panel))

    // Falownik: FoxESS, smallest moc_kw >= kwp, else largest. No sigen_typ
    // filter — FoxESS rows carry no such field.
    const inverters = byKat('Falownik').filter((c) => c.producent === 'FoxESS')
    const fal = pickBySpec(inverters, 'moc_kw', kwp)
    if (fal) sel.falownik = fal.name

    // Konstrukcja: prefer "…blacha", else first available.
    const k = pickMounting(byKat('Konstrukcja'))
    if (k) sel.konstrukcja = k.name
    return
  }

  // Battery-only (VARIANT_BAT) has no consumption-based suggestion: the
  // "Roczne zużycie" input that triggered this function is hidden entirely
  // for that variant (owner decision 2026-08-13), so the rep picks the
  // battery directly from the list instead.
}

// --- Flow / result state ----------------------------------------------------
const flow = ref('idle') // idle | done
const generating = ref(false)
const errorMsg = ref('')
const summary = reactive({
  netto: 0, vat: 0, brutto: 0, narzut: 0, vat_rate: 0,
  dotacja: 0, cena_po_dotacji: 0, ulga: 0, cena_po_uldze: 0,
  raty: { brutto: 0, po_dotacji: 0, po_uldze: 0 },
  lines: [],
  is_admin: false,
  breakdown: null,
  // Server-authoritative PPOŻ verdict ("Tak"/"Nie"/"" before the first calc
  // response); "" means no result yet, so the UI falls back to the local
  // heuristic in ppozWymaganeLive (ops#194).
  ppoz: '',
  // Server-authoritative "threshold alone requires PPOŻ" flag ("Tak"/"Nie"/
  // "" before the first calc response), used to lock sel.ppozRecznie on Tak
  // (ops#194).
  ppoz_prog: '',
  // ops#225: wybór dodatków echowany z powrotem przez serwer (po
  // neutralizacji) i ich łączna cena netto. Wyłącznie do wyświetlenia -
  // sel.dodatki pozostaje źródłem prawdy dla payloadu.
  dodatki: { klima: '', panele: 0, panele_mikro: 0, ems_breeze: 'Nie', pstryk: 'Nie', ev_ladowarka: '' },
  dodatki_netto: 0,
})
const grupyBreakdown = computed(() => grupujBreakdown(summary.breakdown))

const successSummary = ref('')
const dealHref = ref('#')

// --- Narzut: wiersz podsumowania, edycja po kliknięciu ikony ołówka ---
const showNarzut = ref(false)
// Collapsed by default so the admin cost breakdown is not visible during screenshares.
const showAdminBreakdown = ref(false)

// --- Completeness gate (mirrors the server-side validation) -----------------
const isComplete = computed(() => {
  if (!sel.typKlienta || !sel.variant || !sel.producent || !sel.falownik) return false
  if (hasPv.value && (!sel.panel || !sel.mocPvKw || !sel.konstrukcja)) return false
  if (hasBat.value && !sel.bateria) return false
  return true
})

// narzut_max comes from volteo_quote_components (loadComponents above);
// 0 means the server reported no upper limit.
const narzutMax = ref(0)

// dotacja_limity comes from volteo_quote_components (loadComponents above);
// keyed by ZASADY_DOTACJI_OPTIONS value, 0 or missing means unknown.
const dotacjaLimity = ref({})

// licznik_dodatkowy comes from volteo_quote_components (loadComponents
// above); 0 or missing means the price is unknown, so the label shows no
// amount. Display only, server stays authoritative.
const licznikCena = ref(0)

// ppoz comes from volteo_quote_components (loadComponents above); 0 or
// missing means the price is unknown, so the label shows no amount. Display
// only, server stays authoritative (ops#194).
const ppozCena = ref(0)

// Local, presentation-only mirror of the server's PPOŻ threshold check
// (ppozWymuszonyProgiem in pvForm.js), used to lock sel.ppozRecznie on Tak
// while the rep types, before the debounced calc response arrives. Once a
// calc result exists, summary.ppoz_prog (server-authoritative) takes over
// (ops#194).
const ppozProgLive = computed(() => {
  if (summary.ppoz_prog === 'Tak' || summary.ppoz_prog === 'Nie') return summary.ppoz_prog === 'Tak'
  return ppozWymuszonyProgiem({
    mocNowaKw: hasPv.value ? sel.mocPvKw : 0,
    istniejacaPv: sel.istniejacaPv,
    mocIstniejacaKwp: sel.istniejacaPvMocKwp,
  })
})

// Local, presentation-only mirror of the server's PPOŻ rule (ppozWymagane in
// pvForm.js), so the "Uzgodnienia PPOŻ" row updates live as the rep types,
// instead of only after the debounced calc response arrives. Once a calc
// result exists, summary.ppoz (server-authoritative) takes over; the local
// heuristic stays as the fallback while the form is incomplete or before the
// first response (ops#194).
const ppozWymaganeLive = computed(() => {
  if (summary.ppoz === 'Tak' || summary.ppoz === 'Nie') return summary.ppoz === 'Tak'
  return ppozWymagane({
    mocNowaKw: hasPv.value ? sel.mocPvKw : 0,
    istniejacaPv: sel.istniejacaPv,
    mocIstniejacaKwp: sel.istniejacaPvMocKwp,
    ppozRecznie: sel.ppozRecznie,
  })
})

// When the threshold alone requires PPOŻ, the select must show Tak and gets
// disabled, so the rep cannot touch it during the lock; their last free
// choice is remembered here and restored the moment the lock lifts, so a
// correction that drops the power back below the threshold does not leave
// the pricing-affecting select silently stuck on Tak (ops#194).
let ppozRecznieSprzedLock = null
watch(ppozProgLive, (locked) => {
  if (locked) {
    if (ppozRecznieSprzedLock === null) ppozRecznieSprzedLock = sel.ppozRecznie
    sel.ppozRecznie = 'Tak'
  } else if (ppozRecznieSprzedLock !== null) {
    sel.ppozRecznie = ppozRecznieSprzedLock
    ppozRecznieSprzedLock = null
  }
})

const narzutValid = computed(() => {
  const n = Number(sel.narzut)
  return !isNaN(n) && n >= 0 && (narzutMax.value <= 0 || n <= narzutMax.value)
})

const narzutErrorMsg = computed(() =>
  narzutMax.value > 0
    ? `Narzut musi być w zakresie 0-${narzutMax.value} zł.`
    : 'Narzut nie może być ujemny.',
)

// --- Prezentacja wariantu A (kokpit z paragonem) -----------------------------
// Stan zwijania sekcji 3-5 trzymany tylko w komponencie (bez localStorage).
// Sekcje nigdy nie otwierają się same (np. po włączeniu PPOŻ), żeby układ nie
// skakał; wymóg PPOŻ widać w podsumowaniu zwiniętej sekcji.
const otwarte = reactive({ montaz: false, finansowanie: false, dodatki: false })

const sekcja1Gotowa = computed(() => !!sel.typKlienta && !!sel.variant && (!hasPv.value || sel.consumption > 0))
const statusFormularza = computed(() =>
  isComplete.value ? 'Sekcje 1-2 uzupełnione, gotowe do wyceny' : 'Uzupełnij instalację i zestaw',
)

const zasadyOpcje = computed(() =>
  ZASADY_DOTACJI_OPTIONS.map((o) => ({
    ...o,
    hint: Number(dotacjaLimity.value[o.value]) > 0 ? `(do ${formatPln(dotacjaLimity.value[o.value])})` : '',
  })),
)

const ppozEtykietaPowyzej = computed(
  () =>
    `Powyżej ${String(PROG_PPOZ_KW).replace('.', ',')} kW: uzgodnienia PPOŻ` +
    (ppozCena.value > 0 ? ` +${formatPln(ppozCena.value)} netto` : ''),
)
const mocGrupy = computed(() =>
  grupujMocePv(mocOptions.value, {
    istniejacaKwp: sel.istniejacaPv === 'Tak' ? Number(sel.istniejacaPvMocKwp) || 0 : 0,
    etykietaPowyzej: ppozEtykietaPowyzej.value,
  }),
)
const bateriaGrupy = computed(() => grupujMagazyny(bateriaOptions.value))

const PIGULKA_KLASY = {
  neutral: 'bg-surface-gray-2 text-ink-gray-7',
  info: 'bg-surface-blue-2 text-ink-blue-6',
  muted: 'border border-outline-gray-2 text-ink-gray-4',
}
const montazPodsumowanie = computed(() =>
  podsumowanieMontazu(sel, {
    licznikDostepny: licznikDostepny(sel.producent),
    ppozWymagane: ppozWymaganeLive.value,
    ppozCena: ppozCena.value,
    hasPv: hasPv.value,
    formatPln,
  }),
)
const finansowaniePodsumowanie = computed(() => podsumowanieFinansowania(sel, { formatPln }))
const dodatkiPodsumowanie = computed(() => {
  const wybrane = []
  const wiersz = (dostepny, nazwa, wlaczony) => {
    if (dostepny && wlaczony) wybrane.push(nazwa)
  }
  wiersz(klimaDostepnaNow.value, 'klimatyzacja', dodatkiUi.klimaOn)
  wiersz(paneleDostepneNow.value, 'panele PV', dodatkiUi.paneleOn)
  wiersz(paneleDostepneNow.value, 'panele PV + mikro', dodatkiUi.paneleMikroOn)
  wiersz(emsDostepnyNow.value, 'EMS Zeronest', dodatkiUi.emsOn)
  wiersz(pstrykDostepnyNow.value, 'licznik Pstryk', dodatkiUi.pstrykOn)
  wiersz(evDostepneNow.value, 'ładowarka EV', dodatkiUi.evOn)
  return podsumowanieDodatkow({ wybrane, dodatkiNetto: summary.dodatki_netto, formatPln })
})

const canGenerate = computed(() => isComplete.value && !!c.value.name && narzutValid.value)

function buildCalcPayload() {
  return {
    typ_klienta: sel.typKlienta,
    variant: sel.variant,
    zestaw_typ: hasBat.value ? sel.zestaw : '',
    producent: sel.producent,
    falownik: sel.falownik || '',
    bateria: hasBat.value ? sel.bateria || '' : '',
    panel: hasPv.value ? sel.panel || '' : '',
    konstrukcja: hasPv.value ? sel.konstrukcja || '' : '',
    moc_pv_kw: hasPv.value ? Number(sel.mocPvKw) || 0 : 0,
    kabel_m: Number(sel.kabelM) || 0,
    spoldzielnia: sel.spoldzielnia,
    licznik_dodatkowy: sel.licznik,
    istniejaca_pv: sel.istniejacaPv,
    istniejaca_pv_moc_kwp: sel.istniejacaPv === 'Tak' ? Number(sel.istniejacaPvMocKwp) || 0 : 0,
    ppoz_recznie: sel.ppozRecznie,
    ulga_pct: Number(sel.ulgaPct),
    okres_lat: Number(sel.okresLat),
    wplata_wlasna: Number(sel.wplataWlasna) || 0,
    narzut: Number(sel.narzut) || 0,
    zasady_dotacji: sel.zasadyDotacji,
    // ops#225: opcje dodatkowe PV/PV+ME/ME - serwer neutralizuje wybory
    // niedostępne dla bieżącej konfiguracji, front tylko ukrywa je wcześniej
    // (sanitizujDodatki, watcher [variant, producent, falownik] powyżej).
    dod_klima: sel.dodatki.klimaKod || '',
    dod_panele: Number(sel.dodatki.panele) || 0,
    dod_panele_mikro: Number(sel.dodatki.paneleMikro) || 0,
    ems_breeze: sel.dodatki.emsBreeze,
    pstryk: sel.dodatki.pstryk,
    ev_ladowarka: sel.dodatki.evKod || '',
  }
}

function clearSummary() {
  summary.netto = 0; summary.vat = 0; summary.brutto = 0; summary.narzut = 0; summary.vat_rate = 0
  summary.dotacja = 0; summary.cena_po_dotacji = 0; summary.ulga = 0; summary.cena_po_uldze = 0
  summary.raty.brutto = 0; summary.raty.po_dotacji = 0; summary.raty.po_uldze = 0
  summary.lines = []
  summary.is_admin = false
  summary.breakdown = null
  summary.ppoz = ''
  summary.ppoz_prog = ''
  summary.dodatki = { klima: '', panele: 0, panele_mikro: 0, ems_breeze: 'Nie', pstryk: 'Nie', ev_ladowarka: '' }
  summary.dodatki_netto = 0
}

// --- Live pricing (server-side; debounced) ----------------------------------
let calcTimer = null
watch(
  () => [
    sel.typKlienta, sel.variant, sel.zestaw, sel.producent, sel.falownik, sel.bateria,
    sel.panel, sel.mocPvKw, sel.konstrukcja, sel.kabelM, sel.spoldzielnia, sel.licznik, sel.ulgaPct,
    sel.okresLat, sel.wplataWlasna, sel.narzut, sel.zasadyDotacji,
    sel.istniejacaPv, sel.istniejacaPvMocKwp, sel.ppozRecznie,
    sel.dodatki.klimaKod, sel.dodatki.panele, sel.dodatki.paneleMikro,
    sel.dodatki.emsBreeze, sel.dodatki.pstryk, sel.dodatki.evKod,
  ],
  () => {
    if (calcTimer) clearTimeout(calcTimer)
    calcTimer = setTimeout(runCalc, 350)
  },
)

async function runCalc() {
  // Cztery nowe rodzaje OZE mają własny kalkulator (KalkulatorOzeRozszerzony.vue,
  // v-if w szablonie) -- jawny guard tutaj, bo stale sel.producent/sel.falownik
  // pozostałe po przełączeniu z wariantu PV mogłyby po cichu spełnić
  // `isComplete` i wysłać `volteo_quote_calc` z nieaktualnym payloadem PV.
  if (czyNowyRodzaj(sel.variant)) {
    clearSummary()
    return
  }
  if (!isComplete.value) {
    clearSummary()
    return
  }
  try {
    const data = await call('volteo_quote_calc', buildCalcPayload())
    summary.netto = data.netto || 0
    summary.vat = data.vat || 0
    summary.brutto = data.brutto || 0
    summary.narzut = data.narzut || 0
    summary.vat_rate = data.vat_rate || 0
    summary.dotacja = data.dotacja || 0
    summary.cena_po_dotacji = data.cena_po_dotacji || 0
    summary.ulga = data.ulga || 0
    summary.cena_po_uldze = data.cena_po_uldze || 0
    summary.raty.brutto = (data.raty && data.raty.brutto) || 0
    summary.raty.po_dotacji = (data.raty && data.raty.po_dotacji) || 0
    summary.raty.po_uldze = (data.raty && data.raty.po_uldze) || 0
    summary.lines = data.lines || []
    summary.is_admin = !!data.is_admin
    summary.breakdown = data.is_admin ? data.breakdown || null : null
    summary.ppoz = data.ppoz || ''
    summary.ppoz_prog = data.ppoz_prog || ''
    summary.dodatki = data.dodatki || { klima: '', panele: 0, panele_mikro: 0, ems_breeze: 'Nie', pstryk: 'Nie', ev_ladowarka: '' }
    summary.dodatki_netto = data.dodatki_netto || 0
  } catch (err) {
    clearSummary()
    errorMsg.value = extractErrorMessage(err)
  }
}

// --- Generate ----------------------------------------------------------------
async function runGenerate() {
  // Nieosiągalne z UI (przycisk żyje wyłącznie w gridzie poniżej, który
  // zamienia się na KalkulatorOzeRozszerzony.vue dla nowych rodzajów), ale
  // ta sama zasada fail-closed jak w runCalc powyżej.
  if (czyNowyRodzaj(sel.variant)) return
  errorMsg.value = ''
  generating.value = true
  try {
    const result = await call('volteo_quote_generate', {
      ...buildCalcPayload(),
      contact: c.value.name || '',
      first_name: c.value.first_name || '',
      last_name: c.value.last_name || '',
      phone: c.value.mobile_no || '',
      email: c.value.email_id || '',
      install_address: composeAddress(),
      install_city: c.value.custom_miasto || '',
      install_postal_code: c.value.custom_kod_pocztowy || '',
      voivodeship: voivodeshipPrefill.value,
      operator: sel.operator,
      kierunek: sel.kierunek,
      annual_consumption_kwh: sel.consumption || 0,
    })
    successSummary.value =
      'Szansa ' + result.deal + ' została utworzona. Suma brutto: ' + formatPln(result.brutto) + '.'
    dealHref.value = router.resolve({ name: 'Deal', params: { dealId: result.deal } }).href
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
}

// --- Helpers -----------------------------------------------------------------
// Copied verbatim from the extractErrorMessage() pattern used across the
// deal tabs (useAutenti.js, KredytTab.vue, UmowaTab.vue, ...) — but that
// pattern was blind to the actual shape of errors thrown by frappe-ui's
// call() (see frontend/node_modules/frappe-ui/src/utils/frappeRequest.js
// ~L82-124): call() consumes _server_messages itself and re-throws an
// error whose `message` is just "{url} {exc_type}" and whose `messages` is
// the already-parsed array of server message strings (the Polish text
// lives there, not under `_server_messages`/`exception`). Without the
// `err.messages` branch below, the name-mismatch ValidationError always
// fell through to the raw "{url} {exc_type}" fallback instead of the
// server's Polish message. The old `_server_messages`/`exception` branches
// are kept as a fallback for any caller that isn't call().
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
/* Bordered cards make visual grouping clearer than thin divider rules; the
   muted numeral chip is a non-interactive step/order indicator. */
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
@media (max-width: 880px) {
  .kalk-split { grid-template-columns: minmax(0, 1fr) !important; }
  .kalk-row2 { grid-template-columns: minmax(0, 1fr) !important; }
  .kalk-zestawy { grid-template-columns: minmax(0, 1fr) !important; }
  .kalk-output { border-left: 0 !important; padding-left: 0 !important; margin-top: 0.75rem; }
  .sticky { position: static; }
  .kalk-part { padding: 1rem; }
}
</style>
