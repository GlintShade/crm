<!--
  Jeden wiersz feedu "Pliki" (issue GlintShade/proenergy-crm-ops#203, uwaga
  47): ikona typu pliku (miniatura dla obrazu), nazwa jako link, rozmiar,
  chip źródła, autor, data i godzina 24h, akcje (otwórz/zmień nazwę/usuń).

  Bezstanowy - dostaje gotowy wiersz z kontraktu `crm.api.pliki.feed`
  (`crm.volteo_pliki.klasyfikuj_plik_szansy`) jako prop i emituje zdarzenia,
  cała logika (otwieranie, zmiana nazwy, kasowanie, nawigacja do zakładki
  źródłowej) żyje w rodzicu (`PlikiTab.vue`) - ten sam podział
  odpowiedzialności co `AttachmentArea.vue`/`MontazZdjecia.vue`.

  `canRename` to globalna flaga z odpowiedzi API (`feed.can_rename`, czyli
  `czy_admin_lub_bypass()`), `wiersz.mozna_zmienic_nazwe` to flaga PER
  WIERSZ (to samo ORAZ plik nie jest systemowy) - ołówek wymaga OBU, tak
  samo jak `AttachmentArea.vue` sprawdza `mozeZmieniacNazwe &&
  attachment.mozna_zmienic_nazwe`. `wiersz.mozna_usunac` jest już w pełni
  policzone serwerowo (prawo zapisu ORAZ źródło dokładnie "luzem"), więc kosz
  nie potrzebuje żadnej dodatkowej flagi z zewnątrz.
-->
<template>
  <div
    class="activity flex items-center justify-between gap-2 rounded p-2.5 hover:bg-surface-sidebar"
  >
    <div class="flex min-w-0 flex-1 gap-2">
      <button
        type="button"
        class="flex size-11 flex-shrink-0 items-center justify-center overflow-hidden rounded bg-surface-base"
        :class="{ border: klucz !== 'obraz' }"
        @click="emit('otworz', wiersz)"
      >
        <img
          v-if="klucz === 'obraz'"
          class="size-full object-cover"
          :src="wiersz.file_url"
          :alt="wiersz.file_name"
        />
        <component :is="komponentIkony" v-else class="size-4 text-ink-gray-7" />
      </button>

      <div class="flex min-w-0 flex-1 flex-col justify-center gap-1">
        <button
          type="button"
          class="truncate text-left text-base text-ink-gray-8 hover:underline"
          @click="emit('otworz', wiersz)"
        >
          {{ wiersz.file_name }}
        </button>
        <div class="flex flex-wrap items-center gap-2 text-sm text-ink-gray-5">
          <button type="button" @click="emit('przejdz-do-zakladki', wiersz)">
            <Badge variant="subtle" theme="gray" size="sm" :label="wiersz.zrodlo_etykieta" />
          </button>
          <span>{{ formatujRozmiar(wiersz.file_size) }}</span>
          <span v-if="autorWyswietlany">{{ autorWyswietlany }}</span>
          <span>{{ dataTekst }}</span>
        </div>
      </div>
    </div>

    <div class="flex shrink-0 items-center gap-1">
      <Button
        :tooltip="__('Otwórz')"
        class="!size-6"
        icon="lucide-external-link"
        variant="ghost"
        @click="emit('otworz', wiersz)"
      />
      <Button
        v-if="canRename && wiersz.mozna_zmienic_nazwe"
        :tooltip="__('Zmień nazwę')"
        class="!size-6"
        variant="ghost"
        @click="emit('zmien-nazwe', wiersz)"
      >
        <template #icon>
          <span class="lucide-pencil size-3 text-ink-gray-7" aria-hidden="true" />
        </template>
      </Button>
      <Button
        v-if="wiersz.mozna_usunac"
        :tooltip="__('Usuń')"
        class="!size-6"
        variant="ghost"
        theme="red"
        icon="lucide-trash-2"
        @click="emit('usun', wiersz)"
      />
    </div>
  </div>
</template>

<script setup>
import FileIcon from '@/components/Icons/FileIcon.vue'
import FilePdfIcon from '@/components/Icons/FilePdfIcon.vue'
import FileTextIcon from '@/components/Icons/FileTextIcon.vue'
import FileVideoIcon from '@/components/Icons/FileVideoIcon.vue'
import { formatujTermin } from '@/utils/dataPolska'
import { formatujRozmiar, ikonaDla } from '@/utils/pliki'
import { Badge, Button } from 'frappe-ui'
import { computed } from 'vue'

const props = defineProps({
  wiersz: { type: Object, required: true },
  canRename: { type: Boolean, default: false },
})

const emit = defineEmits(['otworz', 'zmien-nazwe', 'usun', 'przejdz-do-zakladki'])

// Klucz z `ikonaDla` (frappe-free, patrz utils/pliki.js): 'pdf'|'obraz'|
// 'wideo'|'dokument'|'inny'. Wideo NIE dostaje odtwarzacza w wierszu -
// tylko ikonka, ten sam wymóg co "żaden <video> poza modalem podglądu"
// z issue ops#190/ops#203.
const klucz = computed(() => ikonaDla(props.wiersz))

const KOMPONENTY_IKON = {
  pdf: FilePdfIcon,
  wideo: FileVideoIcon,
  dokument: FileTextIcon,
  inny: FileIcon,
}

const komponentIkony = computed(() => KOMPONENTY_IKON[klucz.value] || FileIcon)

const autorWyswietlany = computed(() => props.wiersz.autor_nazwa || props.wiersz.autor || '')

const dataTekst = computed(() => formatujTermin(props.wiersz.data))
</script>
