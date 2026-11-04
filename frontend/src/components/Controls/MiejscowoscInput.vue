<!--
  VOLTEO (ops#329): pole "Miejscowosc" leada (custom_install_city) w panelu
  bocznym. Zwykle pole tekstowe (wpis wlasnej wartosci jak dotad) plus
  przycisk z rozwijana lista miejscowosci dla kodu pocztowego leada, gdy
  lookup (crm.api.kod_pocztowy.wyszukaj) zna liste. Wybor z listy emituje
  `change` tak samo jak wpis recznie. Bledy lookupu sa ciche: pole dziala
  wtedy jak zwykly tekst.

  Lookup po ZMIANIE kodu (uzupelnienie wojewodztwa, powiatu, gminy) robi
  SidePanelLayout.vue przy zapisie kodu; ten komponent tylko czyta liste
  (wspolna reaktywna pamiec per kod w data/kodPocztowy.js, bez podwojnych
  zapytan). Przy "Ukryj puste pola" pusta Miejscowosc z lista zostaje
  widoczna (SidePanelLayout.vue, czyPokazacPustaMiejscowosc).
-->
<template>
  <div class="flex min-w-0 items-center gap-0.5">
    <FormControl
      class="form-control min-w-0 flex-1"
      type="text"
      :value="value"
      :placeholder="placeholder"
      :disabled="disabled"
      :debounce="500"
      @change.stop="emit('change', $event.target.value)"
    />
    <Dropdown
      v-if="!disabled && czyPokazacListe(lista, value)"
      :options="opcje"
      align="end"
    >
      <template #default>
        <Button
          variant="ghost"
          class="size-7 shrink-0"
          icon="chevron-down"
          data-testid="miejscowosc-lista"
          :title="__('Wybierz miejscowość dla kodu pocztowego')"
        />
      </template>
    </Dropdown>
  </div>
</template>

<script setup>
import { Dropdown } from 'frappe-ui'
import { computed } from 'vue'
import { miejscowosciKodu } from '@/data/kodPocztowy'
import { czyPokazacListe } from '@/utils/kodPocztowy'

const props = defineProps({
  value: { type: String, default: '' },
  kod: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['change'])

// Reaktywna lista dla kodu leada; pierwszy odczyt uruchamia lookup w tle.
const lista = computed(() =>
  props.disabled ? [] : miejscowosciKodu(props.kod),
)

const opcje = computed(() =>
  lista.value.map((miejscowosc) => ({
    label: miejscowosc,
    icon: miejscowosc === props.value ? 'check' : undefined,
    onClick: () => {
      if (miejscowosc !== props.value) emit('change', miejscowosc)
    },
  })),
)
</script>
