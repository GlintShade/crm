<!--
  Wspólny strumień notatek na zakładce szansy (issue #200, "W2 notatki na
  szansie"). Bezstanowy co do zakładki: konkretną zakładkę (nazwę doctype po
  stronie serwera nie zna wcale - tylko klucz `zakladka` z @/utils/notatki)
  dostarcza prop, dokładnie jak konfig.doctype w AktualizacjeTab.vue robi to
  dla Montaż/Trify. Backend, `Volteo Notatka` + `crm.api.notatki.*` (issue
  W1, ta sama paczka), jest wspólny dla wszystkich ośmiu zakładek już teraz;
  ten komponent jest dziś wpięty tylko na czterech (Zestaw, Umowa, Kredyt,
  Faktury) - Montaż/OSD/Dotacja/Trify dostają wpięcie w kolejnych issue, bez
  zmian w tym pliku.

  Bramka OZE ŻYJE TUTAJ, nie w Deal.vue/MobileDeal.vue (te pliki zmieniają
  inne issue tej paczki, kolizje są pewne): czyta zbuforowany dokument
  szansy przez `getCachedDocumentResource('CRM Deal', dealId)` z frappe-ui -
  już utworzony i ładowany przez Deal.vue (`useDocument('CRM Deal',
  dealId)`), więc to nie jest drugie zapytanie o tę samą szansę, tylko
  odczyt tego samego reaktywnego obiektu z cache. Renderuje `null` (żaden
  DOM), gdy `custom_rodzaj_umowy` nie jest w OZE_RODZAJE - lustro
  `crm/volteo_pipeline.py` i `Deal.vue`'s own OZE_RODZAJE (ok. linii 602).

  Wzmianki @użytkownik: dokładnie ten sam mechanizm co AktualizacjeTab.vue
  (TRIFY) - `TextEditor` z frappe-ui bierze `mentions` jako SNAPSHOT przy
  montowaniu edytora, więc trzeba przekazać obiektowy getter
  `{ mentions: () => listaWzmianek() }`, nigdy samą listę, inaczej
  podpowiedzi otwarte przed dociągnięciem listy przez usersStore zostają
  puste na zawsze. Patrz komentarz przy `mentionsKonfig` w
  AktualizacjeTab.vue dla pełnego wyjaśnienia pułapki.

  Nagłówek "Notatki (N)" jest zwijany, ale karta "Dodaj notatkę" NIE jest
  częścią tego, co zwija - jest zawsze widoczna (gdy `can_add`), żeby dodanie
  pierwszej notatki na pustej zakładce nie wymagało najpierw rozwinięcia
  niczego. Domyślny stan rozwinięcia (raz, po pierwszym załadowaniu danych):
  rozwinięty gdy N > 0, zwinięty gdy N == 0 - użytkownik może to przełączyć
  ręcznie w każdą stronę po tym pierwszym ustawieniu.

  Upload plików roboczych idzie przez forkowy FilesUploader.vue z
  `fieldname="notatka_robocza"`, identycznie na każdej zakładce (kontrakt
  API nie rozróżnia zakładek dla plików roboczych - backend filtruje je po
  swojemu). `@after` odpala TYLKO po ostatnim pliku wsadu
  (FilesUploader.vue, `attachFile`: `if (i === files.value.length - 1)`),
  więc odświeżenie listy roboczych dzieje się też w `watch(showUploader)`
  przy zamknięciu dialogu (wzór MontazZdjecia.vue, ops#191) - jedyne pewne
  miejsce po sukcesie, anulowaniu i częściowym błędzie naraz.
-->
<template>
  <div v-if="ozeWidoczne" class="rounded-lg border border-outline-gray-2" :class="kompakt ? 'p-3' : 'p-4'">
    <button
      type="button"
      class="flex w-full items-center gap-2 text-left"
      @click="rozwinieta = !rozwinieta"
    >
      <FeatherIcon
        :name="rozwinieta ? 'chevron-down' : 'chevron-right'"
        class="h-4 w-4 shrink-0 text-ink-gray-5"
      />
      <span class="text-base font-medium text-ink-gray-8">
        {{ __('Notatki ({0})', [liczbaWpisow]) }}
      </span>
    </button>

    <div
      v-if="!notatki.loading && canAdd"
      class="mt-3 rounded-lg border border-outline-gray-2 p-3"
    >
      <div class="mb-2 flex items-center gap-2">
        <FormControl type="select" :options="typyOpcje" v-model="draft.typ" class="w-48" />
      </div>
      <TextEditor
        ref="textEditor"
        :content="draft.tekst"
        :editor-class="['prose-sm max-w-none min-h-[4rem]']"
        :placeholder="placeholderText"
        :editable="true"
        :mentions="mentionsKonfig"
        @change="draft.tekst = $event"
      />

      <div v-if="robocze.length" class="mt-2 flex flex-wrap gap-2">
        <div
          v-for="p in robocze"
          :key="p.name"
          class="flex items-center gap-1.5 rounded border border-outline-gray-2 bg-surface-gray-1 px-2 py-1 text-xs text-ink-gray-7"
        >
          <img
            v-if="roboczeObrazy.has(p.name)"
            :src="p.file_url"
            class="h-4 w-4 shrink-0 rounded object-cover"
            :alt="p.file_name"
          />
          <FilePdfIcon v-else class="h-3.5 w-3.5 shrink-0 text-ink-gray-5" />
          <span class="max-w-[10rem] truncate">{{ p.file_name }}</span>
          <Button
            variant="ghost"
            size="xs"
            icon="lucide-x"
            :tooltip="__('Usuń plik')"
            @click.stop="usunPlikRoboczy(p)"
          />
        </div>
      </div>

      <div class="mt-3 flex items-center justify-between gap-2">
        <Button
          variant="subtle"
          size="sm"
          iconLeft="lucide-paperclip"
          :label="__('Załącz plik')"
          @click="showUploader = true"
        />
        <Button
          variant="solid"
          size="sm"
          :label="__('Dodaj')"
          :loading="adding"
          :disabled="tekstPusty(draft.tekst)"
          @click="dodajNotatke"
        />
      </div>
    </div>

    <div v-if="rozwinieta" class="mt-3">
      <div v-if="notatki.loading" class="py-6 text-center text-sm text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>
      <div v-else-if="!wpisy.length" class="py-6 text-center text-sm text-ink-gray-5">
        {{ pustyText }}
      </div>
      <div v-else class="flex flex-col gap-3">
        <NotatkaKarta v-for="w in wpisy" :key="w.name" :wpis="w" />
      </div>
    </div>

    <FilesUploader
      v-if="showUploader"
      v-model="showUploader"
      doctype="CRM Deal"
      :docname="dealId"
      fieldname="notatka_robocza"
      :options="opcjeUploadu"
      @after="notatki.reload()"
    />
  </div>
</template>

<script setup>
import FilePdfIcon from '@/components/Icons/FilePdfIcon.vue'
import FilesUploader from '@/components/FilesUploader/FilesUploader.vue'
import NotatkaKarta from '@/components/deal/NotatkaKarta.vue'
import { usersStore } from '@/stores/users'
import { tekstPusty } from '@/utils/aktualizacje'
import { TYPY_PLIKOW_NOTATKI, ZAKLADKI, czyOze, podzielPliki, typyDla } from '@/utils/notatki'
import { Button, FeatherIcon, FormControl, TextEditor, call, createResource, getCachedDocumentResource, toast } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  dealId: { type: String, required: true },
  // Klucz stały per instancja/zakładka (Zestaw/Umowa/Kredyt/Faktury/...),
  // niewidoczny dla użytkownika - patrz @/utils/notatki ZAKLADKI.
  zakladka: { type: String, required: true },
  // Tylko dla zakładki Kredyt: name aktualnie wybranego formularza
  // kredytowego (zmienna `wybrany` w KredytTab.vue). Notatka dodana bez
  // wybranego formularza ma `kredyt` puste - `lista()` i tak zwraca
  // WSZYSTKIE notatki zakładki Kredyt niezależnie od tego pola, kontrakt
  // API nie filtruje po formularzu.
  kredyt: { type: String, default: '' },
  kompakt: { type: Boolean, default: false },
})

const { listaWzmianek } = usersStore()

// PUŁAPKA frappe-ui (patrz komentarz w AktualizacjeTab.vue przy
// `mentionsKonfig`): getter, nie wartość, bo TextEditor bierze `mentions`
// jako snapshot przy montowaniu, zanim usersStore zdąży się załadować.
const mentionsKonfig = { mentions: () => listaWzmianek() }

// `getCachedDocumentResource` odczytuje ten sam reaktywny obiekt, który
// Deal.vue już utworzył i ładuje przez `useDocument('CRM Deal', dealId)` -
// to nie jest drugie zapytanie o szansę, tylko odczyt z cache frappe-ui.
const dealDoc = computed(() => getCachedDocumentResource('CRM Deal', props.dealId))
const ozeWidoczne = computed(() => czyOze(dealDoc.value?.doc?.custom_rodzaj_umowy))

const zakladkaKonfig = computed(() => ZAKLADKI[props.zakladka] || {})
const typyOpcje = computed(() => typyDla(props.zakladka))
const placeholderText = computed(() => __(zakladkaKonfig.value.placeholder || ''))
const pustyText = computed(() => __(zakladkaKonfig.value.pusty || 'Brak notatek.'))

const draft = reactive({ typ: typyOpcje.value[0], tekst: '' })
const adding = ref(false)
const textEditor = ref(null)
const showUploader = ref(false)

const notatki = createResource({
  url: 'crm.api.notatki.lista',
  params: { deal: props.dealId, zakladka: props.zakladka },
  auto: true,
  onError: (e) => toast.error(e?.messages?.[0] || __('Nie udało się pobrać notatek')),
})

const wpisy = computed(() => notatki.data?.wpisy || [])
const robocze = computed(() => notatki.data?.robocze || [])
const canAdd = computed(() => Boolean(notatki.data?.can_add))
const liczbaWpisow = computed(() => wpisy.value.length)
const roboczeObrazy = computed(() => new Set(podzielPliki(robocze.value).obrazy.map((p) => p.name)))

// Domyślny stan rozwinięcia ustawiany RAZ, po pierwszym dotarciu danych
// (N > 0 -> rozwinięta, N == 0 -> zwinięta) - dalsze przeładowania
// (`reload()` po dodaniu notatki) nie nadpisują już ręcznego wyboru
// użytkownika.
const rozwinieta = ref(true)
let rozwinietaZainicjalizowana = false
watch(
  () => notatki.data,
  (dane) => {
    if (rozwinietaZainicjalizowana || !dane) return
    rozwinieta.value = (dane.wpisy || []).length > 0
    rozwinietaZainicjalizowana = true
  },
)

const opcjeUploadu = {
  folder: 'Home/Attachments',
  allowMultiple: true,
  allowWebLink: false,
  restrictions: {
    allowedFileTypes: TYPY_PLIKOW_NOTATKI,
  },
}

// `@after` (po ostatnim pliku wsadu) ORAZ watch na zamknięcie dialogu
// (sukces/anulowanie/częściowy błąd) - wzór MontazZdjecia.vue, ops#191,
// patrz komentarz w nagłówku pliku.
watch(showUploader, (otwarty) => {
  if (!otwarty) notatki.reload()
})

async function usunPlikRoboczy(p) {
  try {
    await call('crm.api.notatki.usun_plik_roboczy', { deal: props.dealId, name: p.name })
    await notatki.reload()
  } catch (err) {
    toast.error(err?.messages?.[0] || err?.message || __('Nie udało się usunąć pliku'))
  }
}

async function dodajNotatke() {
  if (tekstPusty(draft.tekst)) return
  adding.value = true
  try {
    await call('crm.api.notatki.dodaj', {
      deal: props.dealId,
      zakladka: props.zakladka,
      tekst: draft.tekst,
      typ: draft.typ,
      pliki: JSON.stringify(robocze.value.map((p) => p.name)),
      kredyt: props.kredyt || '',
    })
    // TipTap po wyczyszczeniu treści zwraca "<p></p>", nie pusty string -
    // tekstPusty() (bramkująca przycisk wyżej) to rozpoznaje, więc to
    // oczekiwany stan "pusto", nie błąd. Patrz identyczny komentarz w
    // AktualizacjeTab.vue.
    textEditor.value?.editor?.commands.clearContent()
    draft.tekst = ''
    draft.typ = typyOpcje.value[0]
    rozwinieta.value = true
    await notatki.reload()
  } catch (err) {
    toast.error(err?.messages?.[0] || err?.message || __('Nie udało się dodać notatki'))
  } finally {
    adding.value = false
  }
}
</script>
