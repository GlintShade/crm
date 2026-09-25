<!--
  Modal podglądu zdjęć i wideo w zakładce Audyt (OZE i CP): powiększenie w
  oknie CRM z nawigacją strzałkami/klawiaturą i licznikiem, zamiast
  otwierania surowego pliku w nowej karcie. Wyłącznie prezentacyjny: dostaje
  gotową listę pozycji (patrz `zbudujListePodgladu` w `@/utils/audytPodglad`)
  i aktualny indeks, zero wywołań API i zero logiki uprawnień. PDF-y nie
  trafiają tu wcale, zostają otwierane w nowej karcie przez AudytPhotoSlot,
  więc lista zawiera obrazy i wideo.
-->
<template>
  <Dialog
    :open="modelValue"
    @update:open="(v) => emit('update:modelValue', v)"
    size="5xl"
    :title="aktualny?.etykieta || ''"
  >
    <template #default>
      <div v-if="aktualny" class="flex flex-col gap-3">
        <div class="relative flex items-center justify-center">
          <Button
            v-if="zdjecia.length > 1"
            class="absolute left-2 top-1/2 z-10 -translate-y-1/2"
            variant="subtle"
            theme="gray"
            icon="lucide-chevron-left"
            :tooltip="__('Poprzednie zdjęcie')"
            @click="poprzednie"
          />
          <!--
            `:key` na URL-u wymusza pełny remount elementu przy przejściu do
            sąsiedniej pozycji, żeby poprzednie wideo faktycznie przestało
            grać w tle zamiast zostać podmienione samym `src`. `preload=
            "metadata"` trzyma modal od razu przy otwarciu bez ściągania
            całego pliku, dociąga treść dopiero po kliknięciu play (galeria
            CP może trzymać 20 plików po 50 MB).
          -->
          <video
            v-if="jestWideo(aktualny.url)"
            :key="aktualny.url"
            :src="aktualny.url"
            controls
            playsinline
            preload="metadata"
            class="mx-auto max-h-[80vh] max-w-full"
          />
          <img
            v-else
            :src="aktualny.url"
            :alt="aktualny.etykieta"
            class="mx-auto max-h-[80vh] max-w-full object-contain"
          />
          <Button
            v-if="zdjecia.length > 1"
            class="absolute right-2 top-1/2 z-10 -translate-y-1/2"
            variant="subtle"
            theme="gray"
            icon="lucide-chevron-right"
            :tooltip="__('Następne zdjęcie')"
            @click="nastepne"
          />
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm text-ink-gray-6">
            {{ __('{0} z {1}', [indeks + 1, zdjecia.length]) }}
          </span>
          <Button
            :label="__('Otwórz oryginał')"
            variant="subtle"
            iconLeft="lucide-external-link"
            @click="otworzOryginal"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { jestWideo, przesunIndeks } from '@/utils/audytPodglad'
import { Button, Dialog } from 'frappe-ui'
import { computed, onUnmounted, watch } from 'vue'

const props = defineProps({
  // Gotowa lista z `zbudujListePodgladu`: [{ klucz, url, etykieta }, ...].
  zdjecia: { type: Array, required: true },
  modelValue: { type: Boolean, default: false },
  indeks: { type: Number, default: 0 },
})

const emit = defineEmits(['update:modelValue', 'update:indeks'])

const aktualny = computed(() => props.zdjecia[props.indeks] || null)

function poprzednie() {
  emit('update:indeks', przesunIndeks(props.indeks, props.zdjecia.length, -1))
}

function nastepne() {
  emit('update:indeks', przesunIndeks(props.indeks, props.zdjecia.length, 1))
}

function otworzOryginal() {
  if (aktualny.value?.url) window.open(aktualny.value.url, '_blank', 'noopener')
}

// Escape jest już obsłużony przez Dialog (dismissible domyślnie true), tu
// dokładamy tylko lewo/prawo, i tylko kiedy modal jest faktycznie otwarty,
// żeby nie przechwytywać strzałek gdziekolwiek indziej w aplikacji.
function onKeydown(e) {
  if (e.key === 'ArrowLeft') poprzednie()
  else if (e.key === 'ArrowRight') nastepne()
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) window.addEventListener('keydown', onKeydown)
    else window.removeEventListener('keydown', onKeydown)
  },
)

onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>
