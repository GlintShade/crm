<!--
  Notatki prywatne administracji na zakładce Montaż (issue #213, OZE i
  Czyste Powietrze). Doctype całkowicie osobny od `Volteo Notatka`
  (`NotatkiStrumien.vue`) - `Volteo Notatka Prywatna`
  (`ops/crm-notatki-prywatne.py`), widoczny i zapisywalny WYŁĄCZNIE dla
  `System Manager` / `Volteo Core Admin`. `Volteo Backend`, `Volteo D2D
  Sales` i `Volteo Call Center` nie mają na tym doctype ani jednego bitu
  uprawnień - zero wiersza DocPerm, nie wiersz z samymi zerami - więc ten
  komponent musi nie wysłać ŻADNEGO żądania, gdy wołający nie jest adminem,
  nie tylko ukryć wynik.

  Bramka admina ŻYJE TUTAJ (root `v-if="jestAdmin"`), ale samo `v-if` nie
  wystarcza: `<script setup>` komponentu i tak by się wykonał (Vue montuje
  komponent, który rodzic umieścił w drzewie, niezależnie od tego, co jego
  WŁASNY szablon potem ukrywa), a `createResource({ auto: true })` odpaliłby
  żądanie natychmiast przy montowaniu. Dlatego zasób tworzony jest z
  `auto: false` i odpalany ręcznie w `watch(jestAdmin, ..., { immediate:
  true })` - jedyny sposób, żeby backoffice/D2D/CC nigdy nie zobaczyli
  żądania `crm.api.notatki.lista_prywatne` w sieci, nie tylko pustego ekranu.

  `isVolteoAdmin()` jest destrukturyzowana jako FUNKCJA (nie computed) ze
  store - bezpieczne, w odróżnieniu od pułapki destrukturyzacji computed
  (`{ crmUsers }` daje snapshot, patrz CLAUDE.md "Pinia setup store
  rozpakowuje computed") - wzór identyczny jak `StatusZakladki.vue`:
  `const { isVolteoAdmin } = usersStore()`, potem `computed(() =>
  isVolteoAdmin())`.

  Załączniki: w odróżnieniu od `NotatkiStrumien.vue` (upload "roboczy" na
  CRM Deal PRZED utworzeniem notatki, bo tamten doctype jest współdzielony
  przez osiem zakładek i upload może zacząć się zanim użytkownik w ogóle
  kliknie "Dodaj"), tutaj wybrane pliki są trzymane WYŁĄCZNIE w pamięci
  przeglądarki (`wybranePliki`, zwykłe obiekty `File`) do chwili zapisu -
  żaden request nie leci do serwera, dopóki admin nie kliknie "Dodaj".
  Dopiero po sukcesie `dodaj_prywatna` (który zwraca `name` nowej notatki)
  każdy wybrany plik jest wysyłany osobno przez `FilesUploadHandler`
  (`@/components/FilesUploader/filesUploaderHandler`, ten sam silnik co
  `FilesUploaderArea.vue`, ale bez jej dialogu/draftu - tu nie jest
  potrzebny) z `doctype: 'Volteo Notatka Prywatna'`, `docname: <name>` -
  `is_private=1` jest wymuszane przez sam handler niezależnie od tego, co
  przekażemy (patrz jego komentarz), więc nie trzeba tego powtarzać tutaj.
  Błąd pojedynczego uploadu NIE cofa już zapisanej notatki - tylko toast,
  tekst zostaje (ten sam duch co `crm.api.montaz`/`crm.api.notatki` gdzie
  indziej: utrata jednego załącznika jest gorsza niż utrata całej notatki).

  Karty renderowane przez `NotatkaKarta.vue` (wspólny komponent z
  `NotatkiStrumien.vue`/feedem "Notatki") z `etykietaZakladkiOverride` (ten
  sam mechanizm, którego feed już używa dla Audyt/AudytCP - źródła spoza
  ośmiu zakładek `Volteo Notatka`) i nowym opcjonalnym propem `pokazUsun`
  (dodanym w tym issue, domyślnie false - żadne z ośmiu istniejących użyć
  go nie ustawia, więc "BEZ kosza" dla zwykłych notatek zostaje nienaruszone).

  Kolorystyka (issue #213): przemalowane z neutralnego szarego na bursztynowy
  (`outline-amber-3`/`surface-amber-2`/`ink-amber-8`) - dokładnie ten sam
  zestaw tokenów, którym MontazKosztyPanel.vue, KalkulatorTab.vue
  (rozbicie kosztów), KalkulatorCPTab.vue (rozbicie kosztów i piaskownica
  modelowania) i ZestawTab.vue (blok prowizji) oznaczają "to jest strefa
  administracji" w całej tej rodzinie zakładek szansy, patrz komentarz przy
  bloku prowizji w ZestawTab.vue ("NOT the plain gray of the customer-facing
  subsidy box above, so nobody mistakes it for a quotable figure"). Tylko
  kontener-ramka i etykieta nagłówka ("Notatki prywatne" / "Widoczne tylko
  dla administracji") dostają bursztyn - dokładnie jak nagłówki/obwódki w
  tamtych plikach; dane wewnątrz (stan "Ładowanie…"/"Brak notatek
  prywatnych.", dymki załączników w edytorze) zostają w zwykłej szarej
  palecie, bo to samo robi MontazKosztyPanel.vue dla "Brak dodatkowych
  pozycji" wewnątrz swojego bursztynowego panelu. Pole edytora
  (`bg-surface-white`) było już białą kartą na (wtedy szarym) tle i zostaje
  bez zmian - ten sam kontrast "biała karta na kolorowym tle", którym
  `.mk-input` w MontazKosztyPanel.vue radzi sobie z polami edytowalnymi na
  bursztynowym tle. `NotatkaKarta.vue` sama w sobie nie ma własnego tła
  (celowo, żeby pasować do białego tła zakładek, w których normalnie żyje),
  więc na bursztynowym tle tego panelu dostaje `class="bg-surface-white"`
  z rodzica - Vue scala atrybut `class` automatycznie z korzeniem
  komponentu (brak `inheritAttrs: false`, jeden korzeń), więc to nie
  wymaga żadnej zmiany w samym współdzielonym komponencie ani nie wpływa
  na pozostałych siedem miejsc, które go używają.
-->
<template>
  <div v-if="jestAdmin" class="rounded-lg border border-outline-amber-3 bg-surface-amber-2 p-4">
    <div class="mb-3 flex items-start gap-2">
      <FeatherIcon name="lock" class="mt-0.5 h-4 w-4 shrink-0 text-ink-amber-8" />
      <div>
        <div class="text-base font-medium text-ink-amber-8">{{ __('Notatki prywatne') }}</div>
        <div class="text-xs text-ink-amber-8">{{ __('Widoczne tylko dla administracji') }}</div>
      </div>
    </div>

    <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-3">
      <TextEditor
        ref="textEditor"
        :content="draft.tekst"
        :editor-class="['prose-sm max-w-none min-h-[4rem]']"
        :placeholder="__('Np. Ustalenia wewnętrzne, niewidoczne dla handlowca ani backoffice…')"
        :editable="true"
        @change="draft.tekst = $event"
      />

      <div v-if="wybranePliki.length" class="mt-2 flex flex-wrap gap-2">
        <div
          v-for="(plik, idx) in wybranePliki"
          :key="`${plik.name}-${idx}`"
          class="flex items-center gap-1.5 rounded border border-outline-gray-2 bg-surface-gray-1 px-2 py-1 text-xs text-ink-gray-7"
        >
          <FilePdfIcon class="h-3.5 w-3.5 shrink-0 text-ink-gray-5" />
          <span class="max-w-[10rem] truncate">{{ plik.name }}</span>
          <Button
            variant="ghost"
            size="xs"
            icon="lucide-x"
            :tooltip="__('Usuń plik')"
            @click.stop="wybranePliki = wybranePliki.filter((_, i) => i !== idx)"
          />
        </div>
      </div>

      <div class="mt-3 flex items-center justify-between gap-2">
        <Button
          variant="subtle"
          size="sm"
          iconLeft="lucide-paperclip"
          :label="__('Załącz plik')"
          @click="fileInput?.click()"
        />
        <Button
          variant="solid"
          size="sm"
          :label="__('Dodaj')"
          :loading="adding"
          :disabled="tekstPusty(draft.tekst)"
          @click="dodaj"
        />
      </div>

      <input
        ref="fileInput"
        type="file"
        multiple
        class="hidden"
        :accept="TYPY_PLIKOW_NOTATKI.join(',')"
        @change="onFilesSelected"
      />
    </div>

    <div class="mt-3">
      <div v-if="notatki.loading" class="py-6 text-center text-sm text-ink-gray-5">
        {{ __('Ładowanie…') }}
      </div>
      <div v-else-if="!wpisy.length" class="py-6 text-center text-sm text-ink-gray-5">
        {{ __('Brak notatek prywatnych.') }}
      </div>
      <div v-else class="flex flex-col gap-3">
        <NotatkaKarta
          v-for="w in wpisy"
          :key="w.name"
          class="bg-surface-white"
          :wpis="w"
          :etykieta-zakladki-override="__('Notatka prywatna')"
          pokaz-usun
          @usun="usunNotatke"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import FilePdfIcon from '@/components/Icons/FilePdfIcon.vue'
import FilesUploadHandler from '@/components/FilesUploader/filesUploaderHandler'
import NotatkaKarta from '@/components/deal/NotatkaKarta.vue'
import { globalStore } from '@/stores/global'
import { usersStore } from '@/stores/users'
import { tekstPusty } from '@/utils/aktualizacje'
import { TYPY_PLIKOW_NOTATKI } from '@/utils/notatki'
import { Button, FeatherIcon, TextEditor, call, createResource, toast } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  dealId: { type: String, required: true },
})

const PRYWATNA_DOCTYPE = 'Volteo Notatka Prywatna'

const { isVolteoAdmin } = usersStore()
const { $dialog } = globalStore()

// Funkcja (nie computed) ze store - wrappowana lokalnym computed, patrz
// komentarz nagłówka pliku.
const jestAdmin = computed(() => isVolteoAdmin())

const draft = reactive({ tekst: '' })
const adding = ref(false)
const textEditor = ref(null)
const fileInput = ref(null)
const wybranePliki = ref([])

const notatki = createResource({
  url: 'crm.api.notatki.lista_prywatne',
  params: { deal: props.dealId },
  auto: false,
  onError: (e) => toast.error(e?.messages?.[0] || __('Nie udało się pobrać notatek prywatnych')),
})

// Odpala żądanie WYŁĄCZNIE gdy wołający jest adminem - patrz komentarz
// nagłówka pliku. `immediate: true` pokrywa przypadek, gdy usersStore już
// zdążył się załadować zanim ten komponent zamontował się.
watch(
  jestAdmin,
  (admin) => {
    if (admin && !notatki.data && !notatki.loading) notatki.fetch()
  },
  { immediate: true },
)

const wpisy = computed(() => notatki.data?.wpisy || [])

function onFilesSelected(event) {
  const pliki = Array.from(event.target.files || [])
  wybranePliki.value = [...wybranePliki.value, ...pliki]
  event.target.value = ''
}

function uploadJedenPlik(plik, docname) {
  const handler = new FilesUploadHandler()
  return handler.upload(plik, {
    fileObj: plik,
    doctype: PRYWATNA_DOCTYPE,
    docname,
    folder: 'Home/Attachments',
  })
}

async function dodaj() {
  if (tekstPusty(draft.tekst)) return
  adding.value = true
  try {
    const wynik = await call('crm.api.notatki.dodaj_prywatna', {
      deal: props.dealId,
      tekst: draft.tekst,
    })
    for (const plik of wybranePliki.value) {
      try {
        await uploadJedenPlik(plik, wynik.name)
      } catch {
        toast.error(__('Nie udało się przesłać załącznika {0}', [plik.name]))
      }
    }
    // TipTap po wyczyszczeniu treści zwraca "<p></p>", nie pusty string -
    // tekstPusty() (bramkująca przycisk wyżej) to rozpoznaje, ten sam
    // komentarz co w NotatkiStrumien.vue/AktualizacjeTab.vue.
    textEditor.value?.editor?.commands.clearContent()
    draft.tekst = ''
    wybranePliki.value = []
    await notatki.reload()
  } catch (err) {
    toast.error(err?.messages?.[0] || err?.message || __('Nie udało się dodać notatki'))
  } finally {
    adding.value = false
  }
}

function usunNotatke(name) {
  $dialog({
    title: __('Usuń notatkę prywatną'),
    message: __('Czy na pewno usunąć tę notatkę? Tej operacji nie można cofnąć.'),
    actions: [
      {
        label: __('Usuń'),
        theme: 'red',
        variant: 'solid',
        onClick: async (close) => {
          try {
            await call('crm.api.notatki.usun_prywatna', { name })
            await notatki.reload()
            close()
          } catch (err) {
            toast.error(err?.messages?.[0] || err?.message || __('Nie udało się usunąć notatki'))
          }
        },
      },
    ],
  })
}
</script>
