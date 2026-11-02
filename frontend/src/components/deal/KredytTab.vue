<!--
  Kredyt tab (Szansa view), credit-application data collection form for the
  bank/leasing partner, plus PDF generation and Autenti e-signature. Since
  ops#157 through #163, a single szansa can carry SEVERAL independent
  credit-form records (`Volteo Kredyt` is no longer 1:1 with `CRM Deal`):
  this tab shows a picker bar over the form, switches between records via
  the EXISTING hydrateFrom()/hydratingForm guard (no remount), and carries
  an editable "Dane wnioskodawcy" block, a snapshot of the applicant's
  identity/address taken when the record was created, editable afterwards,
  independent of the deal's current CRM contact.

  E-signature (ops#164 correction): this tab is NOT missing e-signature
  integration. It shares crm.integrations.autenti.api's Autenti flow with
  UmowaTab.vue through the SAME composable, @/composables/useAutenti.js,
  parameterized per record (docParam: 'kredyt', docId = the currently
  selected form's record name) instead of per deal. Sending/status/download
  work exactly as in UmowaTab; the one real difference is that signing a
  credit form does NOT advance the deal's pipeline status
  (awansuj_po_podpisie=False server-side): the credit form has no stage of
  its own in the OZE pipeline.

  API (crm/api/kredyt.py, whitelisted fork methods, every call() below MUST
  use the full dotted path, a bare command name resolves only for Server
  Scripts and 417s here, see CLAUDE.md "Ścieżka wywołania API" / UmowaTab's
  own header comment for the full story):
    crm.api.kredyt.volteo_kredyt_lista({ deal })      -> { formularze: [...] }
      (list of this deal's records: name, wnioskodawca_nazwisko/imiona,
      status, autenti_status, creation, modified, creation asc)
    crm.api.kredyt.volteo_kredyt_get({ kredyt })      -> { kredyt, prefill,
      prefill_kontakt, brakujace_pola, brakujace_dane_wnioskodawcy }
      (`prefill` is the re-keyed APPLICANT SNAPSHOT already saved on this
      record; `prefill_kontakt` is the deal's CURRENT primary contact, same
      keys, used only by "Przywróć dane klienta")
    crm.api.kredyt.volteo_kredyt_create({ deal })     -> { kredyt, prefill,
      brakujace_pola } (`prefill` here is the CONTACT prefill, used to seed
      the new record's applicant block; always reload with `get` right
      after, see utworzFormularz() below, so the tab works from one
      consistent response shape everywhere else)
    crm.api.kredyt.volteo_kredyt_save({ kredyt, dane }) -> same shape as get
    crm.api.kredyt.volteo_kredyt_pdf({ kredyt })      -> { file_url, file_name }
      (throws with a Polish message when the record OR the applicant block
      is incomplete)

  `brakujace_pola` is a TOP-LEVEL key on every endpoint above, do not nest
  a lookup under a `wyliczenia` key, there is no such key in this contract.

  The 10 applicant fields (`wnioskodawca_*`, canon in
  @/utils/kredytForm.js's POLA_WNIOSKODAWCY/ETYKIETY_WNIOSKODAWCY) are
  ordinary fields of `dane`/buildDane()'s payload, saved the same way as
  every other field of the form, they are NOT part of `prefill`'s contract
  once the record exists; `prefill`/`prefill_kontakt` are read-only
  reference data for the "Przywróć dane klienta" button only.

  Form-state logic (defaultForm/buildDane/hydrateFrom/GRUPY/option arrays/
  the applicant-block mirrors) lives in @/utils/kredytForm.js so it is
  unit-testable without mounting Vue, this file only wires that logic to
  the template.
-->
<template>
  <div class="flex flex-1 flex-col overflow-y-auto p-5">
    <div class="mx-auto w-full max-w-3xl">
      <!-- Loading (initial list + first record fetch) -->
      <div v-if="loading" class="py-16 text-center text-base text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>

      <!-- Load failed, bail out, never render a misleading state -->
      <div
        v-else-if="loadError"
        class="rounded-lg border border-outline-red-3 bg-surface-red-2 px-4 py-3 text-sm text-ink-red-8"
      >
        {{ loadError }}
      </div>

      <!-- Empty state, no kredyt record yet for this deal -->
      <div
        v-else-if="!formularze.length"
        class="flex flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <KredytIcon class="h-10 w-10 text-ink-gray-4" />
        <div class="text-lg font-medium text-ink-gray-7">
          {{ __('Brak wniosku kredytowego') }}
        </div>
        <div class="max-w-md text-sm text-ink-gray-5">
          {{
            __(
              'Utwórz formularz danych do wniosku kredytowego, aby zebrać informacje potrzebne bankowi.',
            )
          }}
        </div>
        <Button
          variant="solid"
          :label="__('Utwórz wniosek')"
          :disabled="creating"
          :loading="creating"
          @click="utworzFormularz"
        />
      </div>

      <!-- Switching between records, the previous form is gone, the new one hasn't landed yet -->
      <div
        v-else-if="!formGotowy"
        class="py-16 text-center text-base text-ink-gray-5"
      >
        {{ __('Ładowanie…') }}
      </div>

      <!-- Form -->
      <div v-else ref="formRoot" class="kredyt-form flex flex-col gap-6">
        <!-- Form picker: which of this deal's several Volteo Kredyt records is shown -->
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div ref="pickerRoot" class="relative">
            <Button
              id="kredyt-picker-toggle-btn"
              variant="outline"
              icon-left="file-text"
              :label="etykietaFormularza(wybrany)"
              :disabled="wybierajac"
              @click="showPicker = !showPicker"
            />
            <div
              v-if="showPicker"
              class="absolute left-0 z-20 mt-1 w-80 rounded-lg border border-outline-gray-2 bg-surface-elevation-2 shadow-lg"
            >
              <ul class="max-h-72 overflow-y-auto p-1.5">
                <li
                  v-for="w in formularze"
                  :key="w.name"
                  class="flex cursor-pointer items-center justify-between gap-2 rounded p-2 hover:bg-surface-gray-1"
                  :class="w.name === wybrany?.name ? 'bg-surface-gray-2' : ''"
                  @click="onWybierzFormularz(w)"
                >
                  <span class="truncate text-sm text-ink-gray-8">{{ etykietaFormularza(w) }}</span>
                  <span class="flex shrink-0 items-center gap-1">
                    <Badge
                      :theme="w.status === 'Kompletny' ? 'green' : 'gray'"
                      variant="subtle"
                      size="sm"
                      :label="w.status"
                    />
                    <Badge
                      v-if="badgeFor(w.autenti_status, 'kredyt')"
                      :theme="badgeFor(w.autenti_status, 'kredyt').theme"
                      variant="subtle"
                      size="sm"
                      :label="badgeFor(w.autenti_status, 'kredyt').label"
                    />
                    <Badge
                      v-if="badgeStatusuFinansowania(w.status_finansowania)"
                      :theme="badgeStatusuFinansowania(w.status_finansowania).theme"
                      variant="subtle"
                      size="sm"
                      :label="badgeStatusuFinansowania(w.status_finansowania).label"
                    />
                  </span>
                </li>
              </ul>
            </div>
          </div>
          <Button
            variant="outline"
            icon-left="plus"
            :label="__('Nowy formularz')"
            :disabled="creating || wybierajac"
            :loading="creating"
            @click="utworzFormularz"
          />
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <div class="text-lg font-semibold text-ink-gray-8">
              {{ __('Wniosek kredytowy') }}
            </div>
            <Badge
              v-if="autentiEnabled && autentiBadgeEntry"
              :theme="autentiBadgeEntry.theme"
              variant="subtle"
              size="lg"
              :label="autentiBadgeEntry.label"
            />
            <!-- Status finansowania (ops#197): backoffice/admins get an
            editable dropdown, everyone else a read-only badge. -->
            <Dropdown
              v-if="canSetStatusFinansowania"
              :options="opcjeStatusuFinansowania"
              placement="bottom-start"
            >
              <template #default="{ open }">
                <Button
                  :label="statusFinansowaniaButtonLabel"
                  :iconRight="open ? 'chevron-up' : 'chevron-down'"
                  :class="statusButtonClass(statusFinansowaniaColor)"
                  :disabled="ustawiajacStatusFinansowania"
                >
                  <template #prefix>
                    <IndicatorIcon :class="statusFinansowaniaColor" />
                  </template>
                </Button>
              </template>
            </Dropdown>
            <Badge
              v-else-if="badgeStatusuFinansowania(kredyt?.status_finansowania)"
              :theme="badgeStatusuFinansowania(kredyt?.status_finansowania).theme"
              variant="subtle"
              size="lg"
              :label="badgeStatusuFinansowania(kredyt?.status_finansowania).label"
            />
          </div>
          <div class="flex items-center gap-3">
            <span v-if="saveState === 'saving'" class="text-xs text-ink-gray-4">
              {{ __('Zapisywanie…') }}
            </span>
            <span v-else-if="saveState === 'saved'" class="text-xs text-ink-green-6">
              {{ __('Zapisano') }} ✓
            </span>
            <span v-else-if="saveState === 'error'" class="text-xs text-ink-red-6">
              {{ __('Błąd zapisu') }}
            </span>
            <Button
              v-if="showAutentiSendButton"
              variant="outline"
              :label="autentiSendLabel"
              @click="toggleAutentiConfirm"
            />
            <Button
              v-if="autentiEnabled && autentiStatus === 'Podpisana' && autenti.signed_pdf_file"
              variant="outline"
              :label="__('Pobierz podpisany wniosek')"
              @click="openSignedPdf"
            />
            <Button
              variant="outline"
              :label="__('Generuj PDF')"
              :disabled="generatingPdf"
              :loading="generatingPdf"
              :tooltip="pdfTooltip"
              @click="generatePdf"
            />
            <Button
              variant="solid"
              :label="__('Zapisz')"
              :disabled="saving"
              :loading="saving"
              @click="saveForm"
            />
          </div>
        </div>

        <!-- Autenti timestamps, small muted line under the header/badges -->
        <div
          v-if="autentiEnabled && (autentiSentAtDisplay || autentiSignedAtDisplay)"
          class="-mt-4 flex flex-wrap gap-3 text-xs text-ink-gray-4"
        >
          <span v-if="autentiSentAtDisplay">
            {{ __('Wysłano') }}: {{ autentiSentAtDisplay }}
          </span>
          <span v-if="autentiSignedAtDisplay">
            {{ __('Podpisano') }}: {{ autentiSignedAtDisplay }}
          </span>
        </div>

        <!-- Autenti error, shown only for a failed send -->
        <div
          v-if="autentiEnabled && autentiStatus === 'Błąd' && autenti.error_message"
          class="rounded-lg border border-outline-red-3 bg-surface-red-2 px-4 py-3 text-sm text-ink-red-8"
        >
          {{ autenti.error_message }}
        </div>

        <!-- Autenti send confirmation, inline panel, not a modal -->
        <div
          v-if="showAutentiConfirm"
          class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4"
        >
          <div class="mb-2 text-sm font-medium text-ink-gray-8">
            {{ __('Potwierdź wysyłkę do podpisu') }}
          </div>

          <div v-if="signerMissingEmail" class="mb-3 text-sm text-ink-red-5">
            {{ __('Kontakt szansy nie ma adresu e-mail, uzupełnij go w CRM.') }}
          </div>
          <div v-else class="mb-3 text-sm text-ink-gray-6">
            <div>{{ __('Formularz kredytowy zostanie wysłany do:') }}</div>
            <div v-if="recipientGroups.signers.length" class="mt-2">
              <div class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">
                {{ __('Podpisują:') }}
              </div>
              <div
                v-for="r in recipientGroups.signers"
                :key="'signer-' + r.email"
                class="font-medium text-ink-gray-8"
              >
                {{ r.full_name }} ({{ r.email }})
              </div>
            </div>
            <div v-if="recipientGroups.viewers.length" class="mt-2">
              <div class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">
                {{ __('Do wglądu:') }}
              </div>
              <div
                v-for="r in recipientGroups.viewers"
                :key="'viewer-' + r.email"
                class="font-medium text-ink-gray-8"
              >
                {{ r.full_name }} ({{ r.email }})
              </div>
            </div>
          </div>

          <!-- Fail-safe warning: the backend (client.py) uses the production
          Autenti URL ONLY when environment === 'Production'; an empty/null
          environment (unconfigured Single) goes to SANDBOX. So the warning
          must fire on anything that is NOT 'Production', not only on the
          literal 'Sandbox' string, or a rep with a never-configured
          environment sees no warning and believes the signature is legally
          binding (ops#144, F8). -->
          <div
            v-if="autenti.environment !== 'Production'"
            class="mb-3 rounded-lg border border-outline-amber-3 bg-surface-amber-2 px-3 py-2 text-sm text-ink-amber-8"
          >
            {{
              __(
                'Środowisko testowe Autenti (albo brak konfiguracji środowiska). Podpis NIE jest prawnie wiążący.',
              )
            }}
          </div>

          <div class="flex gap-2">
            <Button
              variant="solid"
              :label="__('Wyślij')"
              :loading="sendingAutenti"
              :disabled="signerMissingEmail"
              @click="confirmSendAutenti"
            />
            <Button variant="ghost" :label="__('Anuluj')" @click="toggleAutentiConfirm" />
          </div>
        </div>

        <!-- Applicant data block: editable snapshot taken at record creation -->
        <div class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4">
          <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <div class="text-sm font-semibold text-ink-gray-7">
                {{ __('Dane wnioskodawcy') }}
              </div>
              <Badge
                v-bind="badgeLicznika(wnioskodawcaLicznik)"
                variant="subtle"
                size="sm"
                data-testid="kredyt-licznik-wnioskodawca"
              >
                <template v-if="wnioskodawcaLicznik.stan === 'komplet'" #prefix>
                  <LucideCheck class="h-3 w-3" />
                </template>
              </Badge>
            </div>
            <div class="flex items-center gap-2">
              <Button
                variant="ghost"
                :label="__('Przywróć dane klienta')"
                :disabled="saving"
                @click="przywrocDaneKlienta"
              />
              <Button
                variant="outline"
                :label="wnioskodawcaEdytowalny ? __('Zakończ edycję') : __('Edytuj')"
                :disabled="saving"
                @click="przelaczEdycjeWnioskodawcy"
              />
            </div>
          </div>

          <div
            v-if="wnioskodawcaEdytowalny && podtytulOznaczenia(wnioskodawcaOznaczenie)"
            class="-mt-1 mb-3 text-sm text-ink-gray-5"
          >
            {{ podtytulOznaczenia(wnioskodawcaOznaczenie) }}
          </div>

          <div v-if="!wnioskodawcaEdytowalny" class="kredyt-siatka-3 grid gap-3">
            <div v-for="p in wnioskodawcaWyswietlanie" :key="p.fieldname" class="min-w-0">
              <div class="text-xs text-ink-gray-5">
                {{ p.label }}
                <span v-if="brakWnioskodawcySet.has(p.fieldname)" :class="KROPKA_BRAK_KLASY">&nbsp;●</span>
              </div>
              <TelefonLink
                v-if="czyPoleTelefonu(p.fieldname) && p.value"
                :numer="p.value"
                klasa="text-sm text-ink-gray-8"
              />
              <div v-else class="break-words text-sm text-ink-gray-8">{{ p.value || '-' }}</div>
            </div>
          </div>
          <div v-else class="kredyt-siatka-3 grid gap-4">
            <KredytPole
              v-for="f in wnioskodawcaPola"
              :key="f.fieldname"
              :data-pole="f.fieldname"
              :f="f"
              v-model="form[f.fieldname]"
              :stan="stanDla(f.fieldname).stan"
              :komunikat="stanDla(f.fieldname).komunikat"
              :znacznik="znacznikPola(wnioskodawcaOznaczenie, wymaganeSet, f.fieldname)"
              :wymagany="wymaganeSet.has(f.fieldname)"
              :telefon="czyPoleTelefonu(f.fieldname)"
              :disabled="saving"
              @blur="dotknij(f.fieldname)"
            />
          </div>

          <div class="mt-3 text-xs text-ink-gray-4">
            {{
              __(
                'Dane pobrane z karty klienta przy założeniu formularza. Możesz je nadpisać dla innej osoby.',
              )
            }}
          </div>
        </div>

        <!-- Summary banner (ops#321): blue while filling, red after a failed
        "Generuj PDF" attempt. Never amber (amber is reserved for admin-only
        panels). -->
        <div
          v-if="banerWidoczny"
          data-testid="kredyt-baner"
          :class="[
            'rounded-lg border px-4 py-3 text-sm',
            probaGenerowania
              ? 'border-outline-red-3 bg-surface-red-2 text-ink-red-8'
              : 'border-outline-blue-2 bg-surface-blue-2 text-ink-blue-8',
          ]"
        >
          <div class="font-medium">
            <template v-if="probaGenerowania">
              {{
                __('Nie można wygenerować wniosku. Popraw {0} {1}:', [
                  liczbaDoPoprawy,
                  odmianaPol(liczbaDoPoprawy, 'biernik'),
                ])
              }}
            </template>
            <template v-else-if="podsumowanie.razem > 0">
              {{
                __('Brakuje {0} {1}', [podsumowanie.razem, odmianaPol(podsumowanie.razem, 'dopelniacz')])
              }}
            </template>
          </div>
          <div v-if="podsumowanie.sekcje.length" data-testid="kredyt-baner-sekcje">
            {{ podsumowanie.sekcje.map((x) => `${x.label} ${x.liczba}`).join(', ') }}
          </div>
          <div v-if="bledyFormatuLista.length">
            {{ __('Błędny format:') }} {{ bledyFormatuLista.join(', ') }}
          </div>
          <Button
            v-if="probaGenerowania"
            class="mt-2"
            variant="outline"
            size="sm"
            :label="__('Przejdź do pierwszego')"
            @click="przejdzDoPierwszego"
          />
        </div>

        <!-- §1-3: base sections -->
        <section v-for="sec in sekcjeBazowe" :key="sec.key">
          <div class="mb-3 flex flex-wrap items-start justify-between gap-2">
            <div class="min-w-0">
              <div class="text-sm font-semibold uppercase tracking-wide text-ink-gray-5">
                {{ sec.label }}
              </div>
              <div v-if="podtytulOznaczenia(sec.oznaczenie)" class="mt-0.5 text-sm text-ink-gray-5">
                {{ podtytulOznaczenia(sec.oznaczenie) }}
              </div>
            </div>
            <Badge
              v-bind="badgeLicznika(sec.licznik)"
              variant="subtle"
              size="sm"
              class="shrink-0"
              :data-testid="'kredyt-licznik-' + sec.key"
            >
              <template v-if="sec.licznik.stan === 'komplet'" #prefix>
                <LucideCheck class="h-3 w-3" />
              </template>
            </Badge>
          </div>
          <div class="kredyt-siatka-3 grid gap-4">
            <KredytPole
              v-for="f in sec.pola"
              :key="f.fieldname"
              :data-pole="f.fieldname"
              :class="f.fullWidth ? 'kredyt-span-3' : ''"
              :f="f"
              v-model="form[f.fieldname]"
              :stan="stanDla(f.fieldname).stan"
              :komunikat="stanDla(f.fieldname).komunikat"
              :znacznik="znacznikPola(sec.oznaczenie, wymaganeSet, f.fieldname)"
              :wymagany="wymaganeSet.has(f.fieldname)"
              :tytul="etykietaPelna(f.fieldname)"
              :disabled="saving"
              @blur="onBlurPola(f)"
              @input="onPoleInput(f, $event)"
            />
          </div>
        </section>

        <!-- §4-9: income groups -->
        <section v-for="g in sekcjeGrup" :key="g.grupa.key" class="kalk-part">
          <div class="kalk-part-heading mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-outline-gray-1 pb-2.5 text-base font-semibold text-ink-gray-9">
            <div class="min-w-0">
              <div>{{ g.grupa.label }}</div>
              <div
                v-if="g.grupa.podtytul || (g.wlaczona && podtytulOznaczenia(g.oznaczenie))"
                class="mt-0.5 text-sm font-normal text-ink-gray-5"
              >
                {{ g.grupa.podtytul }}
                <template v-if="g.wlaczona && podtytulOznaczenia(g.oznaczenie)">
                  {{ podtytulOznaczenia(g.oznaczenie) }}
                </template>
              </div>
            </div>
            <div class="flex shrink-0 items-center gap-3">
              <Badge
                v-if="g.wlaczona"
                v-bind="badgeLicznika(g.licznik)"
                variant="subtle"
                size="sm"
                class="shrink-0"
                :data-testid="'kredyt-licznik-' + g.grupa.key"
              >
                <template v-if="g.licznik.stan === 'komplet'" #prefix>
                  <LucideCheck class="h-3 w-3" />
                </template>
              </Badge>
              <button
                type="button"
                role="switch"
                :aria-checked="g.wlaczona"
                :aria-label="g.grupa.label"
                class="kalk-switch shrink-0"
                :class="g.wlaczona ? 'kalk-switch-on' : 'kalk-switch-off'"
                :disabled="saving"
                @click="form[g.grupa.wlaczone] = !form[g.grupa.wlaczone]"
              ><span class="kalk-switch-knob" /></button>
            </div>
          </div>

          <div
            v-if="g.wlaczona"
            :class="[
              'grid gap-4',
              g.grupa.key === 'inne' ? 'kredyt-siatka-2' : 'kredyt-siatka-3',
            ]"
          >
            <template v-for="el in g.elementy" :key="el.f.fieldname">
              <!-- Para dat "od / do" w jednej komórce, pod wspólną etykietą -->
              <div v-if="el.doPole" :data-pole="el.f.fieldname" class="min-w-0">
                <div class="mb-1.5 whitespace-nowrap text-base text-ink-gray-5">
                  {{ __('Zatrudnienie od / do') }}
                  <span
                    v-if="g.oznaczenie === 'gwiazdki' && (wymaganeSet.has(el.f.fieldname) || wymaganeSet.has(el.doPole.fieldname))"
                    class="select-none text-ink-gray-5"
                  >*</span>
                  <span
                    v-if="stanDla(el.f.fieldname).stan === 'brak' || stanDla(el.doPole.fieldname).stan === 'brak'"
                    :class="KROPKA_BRAK_KLASY"
                  >&nbsp;●</span>
                </div>
                <div class="grid grid-cols-2 gap-2">
                  <KredytPole
                    v-for="pole in [el.f, el.doPole]"
                    :key="pole.fieldname"
                    :data-pole="pole.fieldname"
                    :f="pole"
                    bez-etykiety
                    v-model="form[pole.fieldname]"
                    :stan="stanDla(pole.fieldname).stan"
                    :komunikat="stanDla(pole.fieldname).komunikat"
                    :disabled="saving"
                    @blur="onBlurPola(pole)"
                  />
                </div>
              </div>
              <KredytPole
                v-else
                :data-pole="el.f.fieldname"
                :class="el.f.kolumny === 2 ? 'kredyt-span-2' : ''"
                :f="el.f"
                v-model="form[el.f.fieldname]"
                :stan="stanDla(el.f.fieldname).stan"
                :komunikat="stanDla(el.f.fieldname).komunikat"
                :znacznik="znacznikPola(g.oznaczenie, wymaganeSet, el.f.fieldname)"
                :wymagany="wymaganeSet.has(el.f.fieldname)"
                :tytul="etykietaPelna(el.f.fieldname)"
                :telefon="czyPoleTelefonu(el.f.fieldname)"
                :disabled="saving"
                @blur="onBlurPola(el.f)"
              />
            </template>
          </div>
        </section>
      </div>

      <!--
        Strumień notatek (issue #200): sibling wobec całego łańcucha
        loading/pusty/brak-wybranego-formularza/formularz powyżej, widoczny
        niezależnie od stanu formularza. `kredyt` to `wybrany?.name`:
        notatka dodana bez wybranego formularza (wybrany === null) ma
        `kredyt` puste, `lista()` i tak pokazuje WSZYSTKIE notatki zakładki
        Kredyt niezależnie od tego, który formularz jest akurat otwarty.
      -->
      <NotatkiStrumien class="mt-5" :deal-id="dealId" zakladka="Kredyt" :kredyt="wybrany?.name" />
    </div>
  </div>
</template>

<script setup>
import KredytIcon from '@/components/Icons/KredytIcon.vue'
import TelefonLink from '@/components/TelefonLink.vue'
import KredytPole from '@/components/deal/KredytPole.vue'
import LucideCheck from '~icons/lucide/check'
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import NotatkiStrumien from '@/components/deal/NotatkiStrumien.vue'
import { onClickOutside } from '@vueuse/core'
import { Badge, Button, Dropdown, call, toast } from 'frappe-ui'
import { computed, h, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useAutenti } from '@/composables/useAutenti'
import { badgeFor } from '@/utils/autentiStatus'
import { usersStore } from '@/stores/users'
import { statusButtonClass } from '@/utils/statusColors'
import { parseColor } from '@/utils'
import {
  GRUPY,
  POLA_WNIOSKODAWCY,
  ETYKIETY_WNIOSKODAWCY,
  TAK_NIE_OPCJE,
  WYKSZTALCENIE_OPCJE,
  RODZAJ_DOKUMENTU_OPCJE,
  STAN_CYWILNY_OPCJE,
  PRACA_FORMA_OPCJE,
  PRACA_OKRES_OPCJE,
  DZIALALNOSC_FORMA_OPCJE,
  defaultForm,
  buildDane,
  hydrateFrom,
  normalizujKwote,
  formatujNumerRachunku,
  formatujNumerRachunkuZKursorem,
  widocznePola,
  brakujacePola,
  brakujaceDaneWnioskodawcy,
  wymaganePola,
  bladFormatu,
  stanPola,
  licznikSekcji,
  oznaczenieWymaganych,
  odmianaPol,
  podsumowanieBrakow,
  znacznikPola,
  prefillDoWnioskodawcy,
  etykietaFormularza,
  ETYKIETY_POL,
  etykietaPelna,
  STATUSY_FINANSOWANIA_OPCJE,
  KOLOR_STATUSU_FINANSOWANIA,
  badgeStatusuFinansowania,
} from '@/utils/kredytForm'

const props = defineProps({
  dealId: { type: String, required: true },
})

// --- Static form definition (§1-3, base fields) ---------------------------
// Same Vue 3 trap as UmowaTab: `v-if` + `v-for` on one node is evaluated
// before the loop variable exists, so filtering happens in script
// (visibleFields()) and the template stays a bare `v-for`.
// Every field `label` below reads from ETYKIETY_POL (kredytForm.js): the
// single canon shared with crm/volteo_kredyt.py's ETYKIETY_POL and the
// backend's PDF-blocking message (ops#148: the literal strings this file
// used to carry inline had drifted from both the doctype and the backend).
// Only the field-grid STRUCTURE (grouping, order, type, options,
// placeholder) still lives here; wording never does.
const formSections = [
  {
    key: 'podstawowe',
    label: __('Dane podstawowe'),
    fields: [
      { fieldname: 'miejsce_urodzenia', label: __(ETYKIETY_POL.miejsce_urodzenia), type: 'text' },
      {
        fieldname: 'rodzaj_dokumentu',
        label: __(ETYKIETY_POL.rodzaj_dokumentu),
        type: 'select',
        options: RODZAJ_DOKUMENTU_OPCJE,
      },
      {
        fieldname: 'seria_numer_dokumentu',
        label: __(ETYKIETY_POL.seria_numer_dokumentu),
        type: 'text',
      },
      {
        fieldname: 'data_wydania_dokumentu',
        label: __(ETYKIETY_POL.data_wydania_dokumentu),
        type: 'date',
      },
      {
        fieldname: 'data_waznosci_dokumentu',
        label: __(ETYKIETY_POL.data_waznosci_dokumentu),
        type: 'date',
      },
    ],
  },
  {
    key: 'adresy',
    label: __('Adresy'),
    fields: [
      {
        fieldname: 'adres_zameldowania_taki_sam',
        label: __(ETYKIETY_POL.adres_zameldowania_taki_sam),
        type: 'select',
        options: TAK_NIE_OPCJE,
      },
      {
        fieldname: 'adres_zameldowania',
        label: __(ETYKIETY_POL.adres_zameldowania),
        type: 'text',
      },
      {
        fieldname: 'adres_korespondencji_taki_sam',
        label: __(ETYKIETY_POL.adres_korespondencji_taki_sam),
        type: 'select',
        options: TAK_NIE_OPCJE,
      },
      {
        fieldname: 'adres_korespondencji',
        label: __(ETYKIETY_POL.adres_korespondencji),
        type: 'text',
      },
    ],
  },
  {
    key: 'wnioskodawca',
    label: __('Informacje o wnioskodawcy'),
    fields: [
      {
        fieldname: 'wyksztalcenie',
        label: __(ETYKIETY_POL.wyksztalcenie),
        type: 'select',
        options: WYKSZTALCENIE_OPCJE,
      },
      {
        fieldname: 'stan_cywilny',
        label: __(ETYKIETY_POL.stan_cywilny),
        type: 'select',
        options: STAN_CYWILNY_OPCJE,
      },
      {
        fieldname: 'liczba_osob_na_utrzymaniu',
        label: __(ETYKIETY_POL.liczba_osob_na_utrzymaniu),
        type: 'text',
        inputmode: 'numeric',
      },
      {
        fieldname: 'kwota_800_plus',
        label: __(ETYKIETY_POL.kwota_800_plus),
        type: 'text',
        inputmode: 'decimal',
      },
      {
        fieldname: 'dochod_wspolmalzonka',
        label: __(ETYKIETY_POL.dochod_wspolmalzonka),
        type: 'text',
        inputmode: 'decimal',
      },
      {
        fieldname: 'zrodlo_dochodu_malzonka',
        label: __(ETYKIETY_POL.zrodlo_dochodu_malzonka),
        type: 'text',
      },
      {
        fieldname: 'oplaty_miesieczne',
        label: __(ETYKIETY_POL.oplaty_miesieczne),
        type: 'text',
        inputmode: 'decimal',
      },
      {
        // K6, ops#148: on-screen label is the shortened ETYKIETY_POL entry
        // ("Suma miesięcznych zobowiązań"). The full canon
        // ("...kredytowych i finansowych") lives in ETYKIETY_PELNE and
        // surfaces via the field's title tooltip and the missing-fields
        // banner (fieldLabelByName below), never truncated silently.
        fieldname: 'suma_zobowiazan',
        label: __(ETYKIETY_POL.suma_zobowiazan),
        type: 'text',
        inputmode: 'decimal',
      },
      {
        fieldname: 'numer_rachunku',
        label: __(ETYKIETY_POL.numer_rachunku),
        type: 'text',
        // Full-width, at the shared 1/3-column width the last digits of a
        // 26-digit IBAN-style account number were getting visually cut off
        // (owner feedback after click-testing).
        fullWidth: true,
      },
    ],
  },
]

// Fields carrying a phone number, across the applicant block
// (wnioskodawca_telefon) and the income groups (praca_telefon,
// dzialalnosc_telefon): the small "Zadzwon" icon button next to the input,
// and the tel: link on the read-only applicant display, both key off this.
const POLA_TELEFONU = new Set([
  'wnioskodawca_telefon',
  'praca_telefon',
  'dzialalnosc_telefon',
])

function czyPoleTelefonu(fieldname) {
  return POLA_TELEFONU.has(fieldname)
}

// --- Applicant block field metadata (10 wnioskodawca_* fields) -------------
// Canon (fieldnames, order, PL labels) lives entirely in kredytForm.js's
// POLA_WNIOSKODAWCY/ETYKIETY_WNIOSKODAWCY, the JS twin of
// crm/volteo_kredyt.py's own canon, this array only adds the render TYPE,
// same split as formSections/grupaPola above. Every field is a plain text
// input: none of the 10 needs a Select/Date control.
const wnioskodawcaPola = POLA_WNIOSKODAWCY.map((fieldname) => ({
  fieldname,
  label: __(ETYKIETY_WNIOSKODAWCY[fieldname]),
  type: 'text',
}))

// --- Income group field metadata (§4-9) ------------------------------------
// Keyed by GRUPY[].key from kredytForm.js, the fieldname LIST there is the
// single source of truth for which fields exist per group (and what
// buildDane()/hydrateFrom() operate on); this map only adds the per-field
// label/type needed to render them, so the two can never drift on
// fieldnames (a missing/extra field here would leave a hole in the grid,
// not a data-shape bug). Conditional visibility is no longer declared
// inline here. It lives in kredytForm.js's WARUNKI_WIDOCZNOSCI, read
// through widocznePola() below (see that map's header comment for why).
const grupaPola = {
  praca: [
    {
      fieldname: 'praca_forma',
      label: __(ETYKIETY_POL.praca_forma),
      type: 'select',
      options: PRACA_FORMA_OPCJE,
    },
    {
      fieldname: 'praca_okres',
      label: __(ETYKIETY_POL.praca_okres),
      type: 'select',
      options: PRACA_OKRES_OPCJE,
    },
    {
      fieldname: 'praca_okres_od',
      label: __(ETYKIETY_POL.praca_okres_od),
      type: 'date',
    },
    {
      fieldname: 'praca_okres_do',
      label: __(ETYKIETY_POL.praca_okres_do),
      type: 'date',
    },
    {
      fieldname: 'praca_nip',
      label: __(ETYKIETY_POL.praca_nip),
      type: 'text',
      inputmode: 'numeric',
      placeholder: __('10 cyfr'),
    },
    {
      fieldname: 'praca_nazwa_zakladu',
      label: __(ETYKIETY_POL.praca_nazwa_zakladu),
      type: 'text',
      placeholder: __('Nazwa pracodawcy'),
      kolumny: 2,
    },
    {
      fieldname: 'praca_adres',
      label: __(ETYKIETY_POL.praca_adres),
      type: 'text',
      placeholder: __('Ulica i numer, kod pocztowy, miejscowość'),
      kolumny: 2,
    },
    {
      fieldname: 'praca_telefon',
      label: __(ETYKIETY_POL.praca_telefon),
      type: 'text',
      inputmode: 'tel',
      placeholder: __('np. 61 812 40 00'),
    },
    {
      fieldname: 'praca_kwota_dochodu',
      label: __(ETYKIETY_POL.praca_kwota_dochodu),
      type: 'text',
      inputmode: 'decimal',
    },
  ],
  emerytura: [
    { fieldname: 'emerytura_numer_swiadczenia', label: __(ETYKIETY_POL.emerytura_numer_swiadczenia), type: 'text' },
    { fieldname: 'emerytura_od_kiedy', label: __(ETYKIETY_POL.emerytura_od_kiedy), type: 'date' },
    {
      fieldname: 'emerytura_kwota_dochodu',
      label: __(ETYKIETY_POL.emerytura_kwota_dochodu),
      type: 'text',
      inputmode: 'decimal',
    },
  ],
  renta: [
    { fieldname: 'renta_numer_swiadczenia', label: __(ETYKIETY_POL.renta_numer_swiadczenia), type: 'text' },
    { fieldname: 'renta_od_kiedy', label: __(ETYKIETY_POL.renta_od_kiedy), type: 'date' },
    {
      fieldname: 'renta_kwota_dochodu',
      label: __(ETYKIETY_POL.renta_kwota_dochodu),
      type: 'text',
      inputmode: 'decimal',
    },
  ],
  dzialalnosc: [
    {
      fieldname: 'dzialalnosc_forma_opodatkowania',
      label: __(ETYKIETY_POL.dzialalnosc_forma_opodatkowania),
      type: 'select',
      options: DZIALALNOSC_FORMA_OPCJE,
    },
    {
      fieldname: 'dzialalnosc_forma_inna',
      label: __(ETYKIETY_POL.dzialalnosc_forma_inna),
      type: 'text',
    },
    { fieldname: 'dzialalnosc_nip', label: __(ETYKIETY_POL.dzialalnosc_nip), type: 'text', inputmode: 'numeric' },
    { fieldname: 'dzialalnosc_nazwa', label: __(ETYKIETY_POL.dzialalnosc_nazwa), type: 'text' },
    { fieldname: 'dzialalnosc_adres', label: __(ETYKIETY_POL.dzialalnosc_adres), type: 'text' },
    { fieldname: 'dzialalnosc_telefon', label: __(ETYKIETY_POL.dzialalnosc_telefon), type: 'text' },
    { fieldname: 'dzialalnosc_od_kiedy', label: __(ETYKIETY_POL.dzialalnosc_od_kiedy), type: 'date' },
    {
      fieldname: 'dzialalnosc_kwota_dochodu',
      label: __(ETYKIETY_POL.dzialalnosc_kwota_dochodu),
      type: 'text',
      inputmode: 'decimal',
    },
  ],
  gospodarstwo: [
    { fieldname: 'gospodarstwo_nip', label: __(ETYKIETY_POL.gospodarstwo_nip), type: 'text', inputmode: 'numeric' },
    { fieldname: 'gospodarstwo_od_kiedy', label: __(ETYKIETY_POL.gospodarstwo_od_kiedy), type: 'date' },
    {
      fieldname: 'gospodarstwo_kwota_dochodu',
      label: __(ETYKIETY_POL.gospodarstwo_kwota_dochodu),
      type: 'text',
      inputmode: 'decimal',
    },
  ],
  inne: [
    { fieldname: 'inne_1_typ', label: __(ETYKIETY_POL.inne_1_typ), type: 'text' },
    {
      fieldname: 'inne_1_kwota',
      label: __(ETYKIETY_POL.inne_1_kwota),
      type: 'text',
      inputmode: 'decimal',
    },
    { fieldname: 'inne_2_typ', label: __(ETYKIETY_POL.inne_2_typ), type: 'text' },
    {
      fieldname: 'inne_2_kwota',
      label: __(ETYKIETY_POL.inne_2_kwota),
      type: 'text',
      inputmode: 'decimal',
    },
  ],
}

// Full-canon labels for the missing-fields banner: combines both static
// section fields and every income-group field so any fieldname the server
// reports in brakujace_pola resolves to a readable label. Deliberately
// reads etykietaPelna(fieldname), NOT f.label: a field whose on-screen
// label is shortened (today only suma_zobowiazan, K6/ops#148) must still
// show its FULL canon in the banner, never the truncated screen version.
const fieldLabelByName = new Map([
  ...formSections.flatMap((s) => s.fields.map((f) => [f.fieldname, etykietaPelna(f.fieldname)])),
  ...Object.values(grupaPola).flatMap((fields) =>
    fields.map((f) => [f.fieldname, etykietaPelna(f.fieldname)]),
  ),
])

// Thin wrapper around kredytForm.js's widocznePola(): field visibility
// rules now live in WARUNKI_WIDOCZNOSCI (single source of truth, unit
// tested in kredytForm.test.js), with `brakujace` passed through as the
// safety net so a field the server reports missing is always rendered,
// even if a rule and the backend ever disagree again (see ops#139).
function visibleFields(fields) {
  return widocznePola(fields, form, brakujace.value)
}

// Amount fields (inputmode: 'decimal') get their typed text normalized to
// "123,45" on blur, owner feedback after click-testing: the rep should see
// what was understood before saving, not just find out server-side. Every
// non-amount field is a no-op here (inputmode check).
function onKwotaBlur(f) {
  if (f.inputmode !== 'decimal') return
  form[f.fieldname] = normalizujKwote(form[f.fieldname])
}

// Wyjście z pola: najpierw normalizacja kwoty (jak dotąd), potem pole liczy
// się jako opuszczone (od tej chwili może pokazać błąd formatu).
function onBlurPola(f) {
  onKwotaBlur(f)
  dotknij(f.fieldname)
}

// Live NRB space-grouping for numer_rachunku, applied on every keystroke
// (not just on blur, like the amount fields above) so the rep sees the
// bank's own grouping while typing. `el.value` and the caret are written
// BEFORE the reactive `form[...]` assignment on purpose: Vue's v-model
// patches the DOM value from `form` on next tick, and if that patch were
// the first write, the caret would already have been reset to the end of
// the input by the browser's own re-render, writing the already-correct
// value+caret here first makes that later patch a no-op diff, so the
// caret never jumps mid-typing.
function onPoleInput(f, event) {
  if (f.fieldname !== 'numer_rachunku') return
  const el = event.target
  const raw = el.value
  const { tekst, kursor } = formatujNumerRachunkuZKursorem(raw, el.selectionStart ?? raw.length)
  if (tekst !== raw) {
    el.value = tekst
    el.setSelectionRange(kursor, kursor)
  }
  form[f.fieldname] = tekst
}

// --- Load state --------------------------------------------------------------
const loading = ref(true)
const loadError = ref('')
const formularze = ref([])
const wybrany = ref(null)
const kredyt = ref(null)
const prefillKontakt = ref({})
const creating = ref(false)
const wybierajac = ref(false)
const showPicker = ref(false)
const wnioskodawcaEdytowalny = ref(false)
const saving = ref(false)
const saveState = ref('idle') // idle | saving | saved | error
const brakujace = ref([])

const pickerRoot = ref(null)
onClickOutside(pickerRoot, () => {
  showPicker.value = false
}, { ignore: ['#kredyt-picker-toggle-btn'] })

// True only once the loaded `kredyt` actually belongs to `wybrany`. While
// switching records (wybierzFormularz below), `wybrany` is updated first,
// synchronously, and `kredyt`/`form` still hold the PREVIOUS record's data
// until the `get` call resolves. Gating the whole form section on this
// avoids a flash of the old record's fields under the newly selected
// picker row.
const formGotowy = computed(() => Boolean(wybrany.value && kredyt.value && kredyt.value.name === wybrany.value.name))

const form = reactive(defaultForm())

// True only while `form` is being programmatically replaced from a server
// record (load/create/save/switch): see przyjmijRekord() below. The watch
// just below must not react to THAT kind of change, or every successful
// save (or record switch) would immediately flip its own "Zapisano" badge
// back to idle again.
let hydratingForm = false

// K3: previously there was no watch on `form` at all, so `saveState`
// stayed 'saved' forever once a save succeeded: editing a field after
// saving left the "Zapisano" badge showing stale confidence (a rep could
// change the income amount, never click "Zapisz" again, and the badge
// would still claim the form was saved). Any genuine edit now drops the
// badge back to 'idle' so it only ever claims what is actually true. This
// also covers "Przywróć dane klienta" (ops#163): overwriting the applicant
// block is a real, unsaved edit, so the badge must drop to 'idle' too.
watch(
  form,
  () => {
    if (hydratingForm) return
    if (saveState.value === 'saved') saveState.value = 'idle'
  },
  { deep: true },
)

// Read-only display of the applicant block, sourced LIVE from `form` (the
// snapshot is an ordinary part of the form payload since ops#157/#158, not
// a separate read-only prop), flips to editable FormControl inputs when
// wnioskodawcaEdytowalny is true (see the template).
const wnioskodawcaWyswietlanie = computed(() =>
  POLA_WNIOSKODAWCY.map((fieldname) => ({
    fieldname,
    label: __(ETYKIETY_WNIOSKODAWCY[fieldname]),
    value: form[fieldname] || '',
  })),
)

function przelaczEdycjeWnioskodawcy() {
  wnioskodawcaEdytowalny.value = !wnioskodawcaEdytowalny.value
}

// "Przywróć dane klienta": overwrites the applicant block with the deal's
// CURRENT contact-card data (prefillKontakt, loaded alongside the record by
// loadKredyt below). A real, rep-initiated edit, NOT wrapped in the
// hydratingForm guard, so the watch above correctly drops saveState back to
// 'idle' and the rep must click "Zapisz" to persist it, same as any other
// field edit.
function przywrocDaneKlienta() {
  Object.assign(form, prefillDoWnioskodawcy(prefillKontakt.value))
}

// --- Autenti e-signature state ------------------------------------------------
// Shared with UmowaTab.vue via useAutenti(), see that composable's header
// comment for the push-based refresh (ops#303), and for docParam/docId
// (ops#163): this instance is keyed by the SELECTED record's name
// (`kredyt`), not by the deal, since one deal can carry several records.
// `restart()` is called explicitly by wybierzFormularz() below whenever the
// rep switches records, the composable's own onMounted load is a no-op
// here until `wybrany` first resolves (docId falsy at mount, before the
// initial list/record fetch completes).
const {
  autenti,
  showAutentiConfirm,
  sendingAutenti,
  loadAutentiStatus,
  restart: restartAutenti,
  toggleAutentiConfirm,
  confirmSendAutenti,
  openSignedPdf,
  autentiEnabled,
  autentiStatus,
  autentiBadgeEntry,
  autentiSendLabel,
  showAutentiSendButton,
  signerMissingEmail,
  recipientGroups,
  autentiSentAtDisplay,
  autentiSignedAtDisplay,
} = useAutenti({
  docId: () => wybrany.value?.name,
  // Nazwa szansy: pokój zdarzeń `volteo_autenti_status` (ops#303).
  dealId: () => props.dealId,
  docParam: 'kredyt',
  statusMethod: 'crm.integrations.autenti.api.autenti_kredyt_status',
  sendMethod: 'crm.integrations.autenti.api.autenti_send_kredyt',
  sentToastLabel: __('Formularz kredytowy wysłany do podpisu'),
  // 'Formularz kredytowy' is grammatically masculine, see useAutenti.js's
  // header comment on `dokument` for why this changes badge/button wording.
  dokument: 'kredyt',
})

// Keeps the picker row's own Autenti badge (formularze[].autenti_status)
// live as the composable's status changes (send/poll/webhook-driven
// reload), without a full list re-fetch, the picker must never show a
// stale badge for the currently selected row while its status is moving.
watch(autentiStatus, (status) => {
  if (!wybrany.value) return
  formularze.value = formularze.value.map((w) =>
    w.name === wybrany.value.name ? { ...w, autenti_status: status } : w,
  )
})

// brakujace_pola is a TOP-LEVEL key on every kredyt endpoint (unlike
// UmowaTab's nested wyliczenia.brakujace_pola), centralised here so all
// call sites read it identically.
function extractBrakujace(data) {
  const list = data?.brakujace_pola
  return Array.isArray(list) ? list : []
}

// Hydrate `form` from a saved/created/loaded/switched kredyt record, then
// re-group numer_rachunku into the display mask. Records saved before this
// masking existed (or edited directly in the database) come back unspaced
//, this makes them render grouped immediately on load, not only after the
// rep next touches the field, and the next save persists them grouped too.
function przyjmijRekord(record) {
  hydratingForm = true
  Object.assign(form, hydrateFrom(record))
  form.numer_rachunku = formatujNumerRachunku(form.numer_rachunku)
  // Reset the guard only after the watch above has had its chance to run
  // for this batch of changes (Vue's default 'pre'-flush watchers run
  // before the post-flush nextTick queue), so the programmatic hydration
  // itself is never mistaken for a rep's edit.
  nextTick(() => {
    hydratingForm = false
  })
}

// --- List + record loading ----------------------------------------------------

async function loadLista() {
  const data = await call('crm.api.kredyt.volteo_kredyt_lista', { deal: props.dealId })
  formularze.value = data?.formularze || []
}

async function loadKredyt(nazwa) {
  const data = await call('crm.api.kredyt.volteo_kredyt_get', { kredyt: nazwa })
  kredyt.value = data?.kredyt || null
  prefillKontakt.value = data?.prefill_kontakt || {}
  brakujace.value = extractBrakujace(data)
  przyjmijRekord(kredyt.value)
}

// Single entry point for "show this record": updates the selection, closes
// the picker's own edit mode (a stale "Edytuj" toggle from the previous
// record would be confusing), fetches the record, and restarts the Autenti
// composable for the newly selected docId. Used by the picker's click
// handler, by the initial mount selection, and after utworzFormularz().
async function wybierzFormularz(row) {
  wybierajac.value = true
  try {
    wybrany.value = row
    wnioskodawcaEdytowalny.value = false
    probaGenerowania.value = false
    dotkniete.value = new Set()
    await loadKredyt(row.name)
    await restartAutenti()
  } catch (err) {
    loadError.value = extractErrorMessage(err)
  } finally {
    wybierajac.value = false
  }
}

async function onWybierzFormularz(row) {
  showPicker.value = false
  if (wybrany.value?.name === row.name) return
  await wybierzFormularz(row)
}

async function initKredyt() {
  loading.value = true
  loadError.value = ''
  try {
    await loadLista()
    if (formularze.value.length) {
      await wybierzFormularz(formularze.value[0])
    }
  } catch (err) {
    loadError.value = extractErrorMessage(err)
  } finally {
    loading.value = false
  }
}

onMounted(initKredyt)

// Missing-fields semantics (ops#147, K3/K4/K8): brakujaceLokalne is
// computed LIVE from `form` (kredytForm.js's brakujacePola, a pure mirror
// of crm/volteo_kredyt.py brakujace_pola), it is the PRIMARY source for
// the field states (brakiWszystkieSet, ops#321) and for whether
// "Generuj PDF" is blocked, so completing the last required field, or switching an
// income-group toggle off, updates the banner and the button instantly,
// with no need to click "Zapisz" first.
//
// The server's list (`brakujace`, refreshed after get/create/save) only
// feeds widocznePola()'s safety-net parameter in visibleFields() below, so
// a field the server ever reports missing is always rendered even if a
// frontend rule disagrees (the ops#139 pattern). It never reaches the banner
// or the counters: those are live-only.
const brakujaceLokalne = computed(() => brakujacePola(form))

// Applicant-block (wnioskodawca) completeness (ops#157/#158/#163): computed
// LIVE from `form`, the same "no server round trip" pattern as
// brakujaceLokalne above. kredytForm.js's brakujaceDaneWnioskodawcy() is a
// pure mirror of crm.volteo_kredyt.brakujace_dane_wnioskodawcy(). These
// fields live inside `form` now (not a separate contact-card prop), so a
// red ring on them would be redundant with the "Dane wnioskodawcy" block's
// own read-only/edit display; they only gate "Generuj PDF" and get their
// own banner line, mirroring crm.api.kredyt.volteo_kredyt_pdf's own check
// server-side.
const brakujaceKlienta = computed(() =>
  brakujaceDaneWnioskodawcy(form).map((fn) => __(ETYKIETY_WNIOSKODAWCY[fn] || fn)),
)

// --- Trzy poziomy pól (ops#321) ------------------------------------------------
// wymagane -> brakuje (LIVE, niebieskie) -> błąd (czerwone: zły format po
// wyjściu z pola, albo próba generowania z brakami). Cała logika stanów jest w
// kredytForm.js (stanPola/licznikSekcji/bladFormatu), tu tylko stan Vue.
const probaGenerowania = ref(false)
const dotkniete = ref(new Set())

function dotknij(fieldname) {
  if (dotkniete.value.has(fieldname)) return
  dotkniete.value = new Set([...dotkniete.value, fieldname])
}

// Zbiór brakujących: pola formularza (lokalnie, na żywo) plus pola bloku
// wnioskodawcy. Nazwy się nie krzyżują.
const brakujaceKlientaPola = computed(() => brakujaceDaneWnioskodawcy(form))
const brakWnioskodawcySet = computed(() => new Set(brakujaceKlientaPola.value))
const brakiWszystkieSet = computed(
  () => new Set([...brakujaceLokalne.value, ...brakujaceKlientaPola.value]),
)

// Pola z regułą formatu (NIP, telefon zakładu pracy), liczone tylko dla grup,
// które są włączone. "Surowe" = wszystkie błędy, bez względu na to, czy pole
// było już opuszczone; to ich używa generatePdf() do decyzji o próbie.
const POLA_Z_FORMATEM = ['praca_nip', 'praca_telefon', 'dzialalnosc_nip', 'gospodarstwo_nip']
const bledyFormatuSurowe = computed(() => {
  const out = {}
  POLA_Z_FORMATEM.forEach((fn) => {
    const wlaczone = GRUPY.some((g) => g.fields.includes(fn) && form[g.wlaczone])
    if (!wlaczone) return
    const komunikat = bladFormatu(fn, form[fn])
    if (komunikat) out[fn] = komunikat
  })
  return out
})
// Błąd formatu pokazujemy dopiero po opuszczeniu pola albo po próbie generowania.
const bledyFormatu = computed(() =>
  Object.fromEntries(
    Object.entries(bledyFormatuSurowe.value).filter(
      ([fn]) => probaGenerowania.value || dotkniete.value.has(fn),
    ),
  ),
)
const bledyFormatuLista = computed(() =>
  Object.keys(bledyFormatu.value).map((fn) => fieldLabelByName.get(fn) || fn),
)

const ctxStanu = computed(() => ({
  brakujace: brakiWszystkieSet.value,
  bledyFormatu: bledyFormatu.value,
  probaGenerowania: probaGenerowania.value,
}))
function stanDla(fieldname) {
  return stanPola(fieldname, ctxStanu.value)
}

// Wymagane: wymaganePola() formularza plus 9 pól wnioskodawcy (wszystkie
// poza nr lokalu, własna reguła brakujaceDaneWnioskodawcy).
const wymaganeSet = computed(
  () =>
    new Set([
      ...wymaganePola(form),
      ...POLA_WNIOSKODAWCY.filter((p) => p !== 'wnioskodawca_nr_lokalu'),
    ]),
)

const wnioskodawcaOznaczenie = computed(() =>
  oznaczenieWymaganych(POLA_WNIOSKODAWCY, wymaganeSet.value),
)

function podtytulOznaczenia(oznaczenie) {
  if (oznaczenie === 'wszystkie') return __('Wszystkie pola są wymagane.')
  if (oznaczenie === 'opcjonalne') {
    return __('Wszystkie pola są wymagane, poza oznaczonymi jako opcjonalne.')
  }
  return ''
}

const wnioskodawcaLicznik = computed(() => licznikSekcji(POLA_WNIOSKODAWCY, ctxStanu.value))

// Sekcje bazowe: widoczne pola, licznik w nagłówku, flaga "wszystkie wymagane".
function opisSekcji(pola) {
  const nazwy = pola.map((f) => f.fieldname)
  const oznaczenie = oznaczenieWymaganych(nazwy, wymaganeSet.value)
  return {
    licznik: licznikSekcji(nazwy, ctxStanu.value),
    oznaczenie,
    wszystkie: oznaczenie === 'wszystkie',
  }
}
const sekcjeBazowe = computed(() =>
  formSections.map((sec) => {
    const pola = visibleFields(sec.fields)
    return { ...sec, pola, ...opisSekcji(pola) }
  }),
)

// Grupy dochodu. W grupie praca "Czas określony" łączy daty od i do w jedną
// komórkę pod wspólną etykietą, więc lista elementów do narysowania jest
// zbudowana tu, nie w szablonie.
function elementyGrupy(grupa, pola) {
  if (grupa.key !== 'praca' || form.praca_okres !== 'Czas określony') {
    return pola.map((f) => ({ f }))
  }
  const doPole = pola.find((f) => f.fieldname === 'praca_okres_do')
  return pola.flatMap((f) => {
    if (f.fieldname === 'praca_okres_do' && doPole) return []
    if (f.fieldname === 'praca_okres_od' && doPole) return [{ f, doPole }]
    return [{ f }]
  })
}
const sekcjeGrup = computed(() =>
  GRUPY.map((grupa) => {
    const pola = visibleFields(grupaPola[grupa.key])
    return {
      grupa,
      wlaczona: Boolean(form[grupa.wlaczone]),
      elementy: elementyGrupy(grupa, pola),
      ...opisSekcji(pola),
    }
  }),
)

function badgeLicznika(licznik) {
  if (licznik.stan === 'blad') return { theme: 'red', label: __('{0} do poprawy', [licznik.liczba]) }
  if (licznik.stan === 'brak') return { theme: 'blue', label: __('Brakuje {0}', [licznik.liczba]) }
  return { theme: 'green', label: __('Komplet') }
}

// Ta sama kropka co przy etykiecie pola w KredytPole.vue: znak ● po nbsp,
// zawija się razem z ostatnim słowem (treść w szablonie: &nbsp;●).
const KROPKA_BRAK_KLASY = 'select-none align-middle text-[0.6em] text-ink-blue-6'

// Baner liczy WYŁĄCZNIE z żywych źródeł (te same co liczniki sekcji) i tylko
// z pól widocznych: odpowiedź serwera (`brakujace`) go nie dotyczy.
const sekcjeBanera = computed(() => [
  { label: __('Dane wnioskodawcy'), pola: POLA_WNIOSKODAWCY },
  ...sekcjeBazowe.value.map((sec) => ({
    label: sec.label,
    pola: sec.pola.map((f) => f.fieldname),
  })),
  ...sekcjeGrup.value
    .filter((g) => g.wlaczona)
    .map((g) => ({
      label: g.grupa.label,
      pola: g.elementy.flatMap((el) =>
        el.doPole ? [el.f.fieldname, el.doPole.fieldname] : [el.f.fieldname],
      ),
    })),
])
const podsumowanie = computed(() => podsumowanieBrakow(sekcjeBanera.value, brakiWszystkieSet.value))
const liczbaDoPoprawy = computed(() => podsumowanie.value.razem + bledyFormatuLista.value.length)

const banerWidoczny = computed(() => liczbaDoPoprawy.value > 0)

// Gdy nic już nie brakuje ani nie jest błędne, próba generowania jest
// "rozliczona": kolejny brak ma znów zacząć jako niebieski, nie czerwony.
watch(banerWidoczny, (widoczny) => {
  if (!widoczny) probaGenerowania.value = false
})

// Kolejność pól na ekranie, do "Przejdź do pierwszego".
const kolejnoscPol = [
  ...POLA_WNIOSKODAWCY,
  ...formSections.flatMap((s) => s.fields.map((f) => f.fieldname)),
  ...GRUPY.flatMap((g) => grupaPola[g.key].map((f) => f.fieldname)),
]
const formRoot = ref(null)

async function przejdzDoPierwszego() {
  const pierwsze = kolejnoscPol.find((fn) => stanDla(fn).stan === 'blad')
  if (!pierwsze) return
  // Blok wnioskodawcy w trybie podglądu nie ma inputów.
  if (pierwsze.startsWith('wnioskodawca_')) wnioskodawcaEdytowalny.value = true
  await nextTick()
  const el = formRoot.value?.querySelector(`[data-pole="${pierwsze}"]`)
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  el.querySelector('input, select, textarea, button')?.focus({ preventScroll: true })
}

const pdfZablokowany = computed(
  () => brakujaceLokalne.value.length > 0 || brakujaceKlienta.value.length > 0,
)
const pdfTooltip = computed(() => {
  if (brakujaceLokalne.value.length > 0) return __('Uzupełnij wszystkie wymagane pola')
  if (brakujaceKlienta.value.length > 0) return __('Uzupełnij dane wnioskodawcy w formularzu')
  return ''
})

// --- Create --------------------------------------------------------------------
// Shared by the empty state's "Utwórz wniosek" and the picker toolbar's
// "Nowy formularz", both create the same way. The backend's own dedup
// guard (an untouched Roboczy record on this deal is returned instead of a
// new one, see crm/api/kredyt.py's _formularz_nietkniety) means the name
// returned here may already exist in `formularze`; reloading the list and
// selecting by name handles both cases identically.
async function utworzFormularz() {
  if (creating.value) return
  creating.value = true
  try {
    const data = await call('crm.api.kredyt.volteo_kredyt_create', { deal: props.dealId })
    const nazwa = data?.kredyt?.name
    await loadLista()
    const wiersz = formularze.value.find((w) => w.name === nazwa) || null
    if (wiersz) {
      await wybierzFormularz(wiersz)
    }
    toast.success(__('Utworzono wniosek kredytowy'))
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    creating.value = false
  }
}

// Keeps the picker row's label/status source in sync with what the server
// just computed after a save, without a full list re-fetch: editing the
// applicant block changes wnioskodawca_nazwisko/imiona (the picker's own
// label, via etykietaFormularza), and every save can flip
// Roboczy/Kompletny. Immutable array replace, same convention as the rest
// of this file's list updates.
function aktualizujWierszListy(record) {
  if (!record) return
  formularze.value = formularze.value.map((w) =>
    w.name === record.name
      ? {
          ...w,
          wnioskodawca_nazwisko: record.wnioskodawca_nazwisko,
          wnioskodawca_imiona: record.wnioskodawca_imiona,
          status: record.status,
          status_finansowania: record.status_finansowania,
        }
      : w,
  )
  if (wybrany.value?.name === record.name) {
    wybrany.value = formularze.value.find((w) => w.name === record.name) || wybrany.value
  }
}

// --- Status finansowania (ops#197) -----------------------------------------------
// A third, independent status, changed only through
// crm.api.kredyt.volteo_kredyt_status_finansowania (never part of
// buildDane()/saveForm()). Backoffice/admins get the dropdown below;
// everyone else only ever reads kredyt.value.status_finansowania as a
// badge (see the template).
const { isVolteoAdmin, isBackend } = usersStore()
const canSetStatusFinansowania = computed(() => isVolteoAdmin() || isBackend())

const ustawiajacStatusFinansowania = ref(false)

const statusFinansowaniaColor = computed(() => {
  const wartosc = kredyt.value?.status_finansowania
  return parseColor(wartosc ? KOLOR_STATUSU_FINANSOWANIA[wartosc] || 'gray' : 'gray')
})

const statusFinansowaniaButtonLabel = computed(() => {
  const wartosc = kredyt.value?.status_finansowania
  return wartosc ? __(wartosc) : __('Status finansowania')
})

const opcjeStatusuFinansowania = computed(() =>
  STATUSY_FINANSOWANIA_OPCJE.map((s) => ({
    label: __(s),
    value: s,
    icon: () => h(IndicatorIcon, { class: parseColor(KOLOR_STATUSU_FINANSOWANIA[s]) }),
    onClick: () => ustawStatusFinansowania(s),
  })),
)

// No optimistic update (mirrors LeadInlineCell.vue's zapiszWartosc): the
// button keeps showing the OLD status until the server confirms the new
// one, so a failed call never shows a status that was never actually
// persisted.
async function ustawStatusFinansowania(s) {
  if (!wybrany.value || ustawiajacStatusFinansowania.value) return
  if (s === kredyt.value?.status_finansowania) return
  ustawiajacStatusFinansowania.value = true
  try {
    const data = await call('crm.api.kredyt.volteo_kredyt_status_finansowania', {
      kredyt: wybrany.value.name,
      status: s,
    })
    kredyt.value = data?.kredyt || kredyt.value
    aktualizujWierszListy(kredyt.value)
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    ustawiajacStatusFinansowania.value = false
  }
}

// --- Save (draft-safe: incomplete saves are allowed) -----------------------------
// Returns whether the record is now complete (no braki); callers (notably
// generatePdf() below) must not rely on any ref's side effect to learn the
// outcome, since brakujace.value/kredyt.value can each independently be
// stale for a tick relative to when this promise actually settles.
async function saveForm() {
  if (saving.value || !wybrany.value) return false
  saving.value = true
  saveState.value = 'saving'
  try {
    const data = await call('crm.api.kredyt.volteo_kredyt_save', {
      kredyt: wybrany.value.name,
      dane: buildDane(form),
    })
    kredyt.value = data?.kredyt || kredyt.value
    const braki = extractBrakujace(data)
    brakujace.value = braki
    przyjmijRekord(kredyt.value)
    aktualizujWierszListy(kredyt.value)
    saveState.value = 'saved'
    if (braki.length) {
      toast.success(__('Zapisano jako roboczy: część pól nadal brakuje.'))
    } else {
      toast.success(__('Zapisano wniosek kredytowy'))
    }
    return braki.length === 0
  } catch (err) {
    saveState.value = 'error'
    toast.error(extractErrorMessage(err))
    return false
  } finally {
    saving.value = false
  }
}

// --- Generate PDF ------------------------------------------------------------------
const generatingPdf = ref(false)

// K3: the backend prints whatever is already in the database
// (crm/api/kredyt.py's volteo_kredyt_pdf reads the saved doc, it never
// sees `form` directly), so generating a PDF without saving first could
// silently print a stale value the rep just typed but never persisted.
// Saving is therefore always the first step here, never optional and
// never left to the rep to remember: if the save reports braki (or
// throws), stop before ever calling the PDF endpoint.
async function generatePdf() {
  if (generatingPdf.value || !wybrany.value) return

  // ops#321: przycisk jest zawsze aktywny, a kliknięcie z brakami albo ze
  // złym formatem włącza "próbę generowania" (braki i błędy robią się
  // czerwone, baner też). Braki nadal blokują generowanie, jak dotąd
  // blokował je disabled; sam zły format nie blokuje niczego.
  const maBraki = pdfZablokowany.value
  const maBledyFormatu = Object.keys(bledyFormatuSurowe.value).length > 0
  if (maBraki || maBledyFormatu) probaGenerowania.value = true
  if (maBraki) {
    await przejdzDoPierwszego()
    return
  }

  generatingPdf.value = true
  try {
    const zapisano = await saveForm()
    if (!zapisano) return
    if (brakujaceKlienta.value.length) {
      toast.error(__('Dane wnioskodawcy są niekompletne, uzupełnij je w bloku „Dane wnioskodawcy”.'))
      return
    }

    const data = await call('crm.api.kredyt.volteo_kredyt_pdf', { kredyt: wybrany.value.name })
    if (data?.file_url) {
      // Po udanym generowaniu próba jest rozliczona. Pola z błędem formatu
      // zostają czerwone (liczą się jako opuszczone), bo format nie blokował.
      dotkniete.value = new Set([...dotkniete.value, ...Object.keys(bledyFormatuSurowe.value)])
      probaGenerowania.value = false
      window.open(data.file_url, '_blank')
      toast.success(__('Wygenerowano PDF wniosku'))
      // Optimistic local flip so the Autenti send button can appear
      // instantly, mirroring UmowaTab.vue's generatePdf(). New object, not
      // a mutation, per the ref-replace convention.
      if (autenti.value) {
        autenti.value = { ...autenti.value, pdf_exists: true }
      }
      // Follow up with a real reload so `dokument_exists`/`pdf_exists` and
      // anything else in the payload get corrected too.
      await loadAutentiStatus()
    } else {
      toast.error(__('Wystąpił błąd - spróbuj ponownie'))
    }
  } catch (err) {
    toast.error(extractErrorMessage(err))
  } finally {
    generatingPdf.value = false
  }
}

// --- Helpers -----------------------------------------------------------------------
// Copied verbatim from the extractErrorMessage() pattern used across the
// deal tabs (useAutenti.js, KredytTab.vue, UmowaTab.vue, ...), but that
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
        return first.message || __('Wystąpił błąd - spróbuj ponownie')
      }
    }
    if (err && err.exception) {
      const parts = String(err.exception).split(': ')
      return parts[parts.length - 1] || __('Wystąpił błąd - spróbuj ponownie')
    }
    if (err && err.message) return err.message
  } catch (e) {
    /* fall through */
  }
  return __('Wystąpił błąd - spróbuj ponownie')
}
</script>

<style scoped>
/* Układ siatek wg szerokości FORMULARZA (nie okna): wokół są dwa paski
   boczne, więc kolumna treści bywa wąska nawet na dużym monitorze.
   Poniżej 560 px jedna kolumna, od 560 px trzy (dwa w grupie "inne"). */
.kredyt-form {
  container-type: inline-size;
}
.kredyt-siatka-3,
.kredyt-siatka-2 {
  grid-template-columns: minmax(0, 1fr);
}
@container (min-width: 560px) {
  .kredyt-siatka-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .kredyt-siatka-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .kredyt-span-2 {
    grid-column: span 2 / span 2;
  }
  .kredyt-span-3 {
    grid-column: span 3 / span 3;
  }
}

/* Income-group card + iOS-style TAK/NIE switch, copied from
   KalkulatorCPTab.vue's `.kalk-part`/`.kalk-switch` pattern (see that
   file's CSS comments for the full rationale). Colours are fixed by owner
   decision: green = on, BLACK = off, never grey/red. Dark mode: BLACK-off
   would vanish against a dark surface, so it gets an explicit
   [data-theme="dark"] override below (same pattern as RatingInput.vue),
   everything else here uses var() references that flip automatically. */
.kalk-part {
  border: 1px solid var(--outline-gray-1);
  border-radius: 0.75rem;
  background: var(--surface-elevation-1);
  padding: 1.25rem 1.25rem 1.375rem;
}
.kalk-part-heading {
  letter-spacing: -0.01em;
}
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
.kalk-switch-on {
  background: #16a34a;
}
.kalk-switch-off {
  background: #111827;
}
/* Dark mode: black-off is unreadable against a dark card background. */
[data-theme='dark'] .kalk-switch-off {
  background: var(--surface-gray-4);
}
.kalk-switch:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.kalk-switch:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}
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
.kalk-switch-on .kalk-switch-knob {
  transform: translateX(18px);
}
</style>
