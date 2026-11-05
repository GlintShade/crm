<!--
  VOLTEO (ops#329): pole "Miejscowosc" leada (custom_install_city) w panelu
  bocznym. Decyzja wlasciciela: pole NIGDY nie wybiera miejscowosci samo
  (takze gdy kod ma dokladnie jedna) -- czlowiek wybiera zawsze recznie.

  Dwa tryby (funkcja czysta `trybPolaMiejscowosci`, utils/kodPocztowy.js):
  - 'lista': kod ma liste miejscowosci (cities) i uzytkownik nie wybral
    "Recznie" -- rozwijana lista (wyglad jak pole Select w panelu:
    placeholder "Wybierz", chevron w dol) z miejscowosciami kodu plus
    biezaca wartosc, gdy spoza listy (stara/recznie wpisana), plus na
    koncu ZAWSZE opcja "Recznie" (funkcja czysta `opcjeMiejscowosci`).
    Wybor "Recznie" przelacza lokalnie na tryb 'tekst' bez zmiany wartosci
    pola.
  - 'tekst': zwykle pole tekstowe (bez listy dla kodu -- jak dotad; albo
    po wyborze "Recznie"). Gdy lista dla kodu istnieje, obok pola jest mala
    ikonka powrotu do listy.

  Lookup po ZMIANIE kodu (uzupelnienie wojewodztwa, powiatu, gminy -- NIE
  miejscowosci) robi SidePanelLayout.vue przy zapisie kodu; ten komponent
  tylko czyta liste (wspolna reaktywna pamiec per kod w data/kodPocztowy.js,
  bez podwojnych zapytan). Bledy lookupu sa ciche: pole dziala wtedy jak
  zwykly tekst. Przy "Ukryj puste pola" pusta Miejscowosc z lista zostaje
  widoczna (SidePanelLayout.vue, czyPokazacPustaMiejscowosc).
-->
<template>
  <FormControl
    v-if="tryb === 'lista'"
    class="form-control cursor-pointer [&_select]:cursor-pointer truncate [&>*]:!ring-0"
    type="select"
    :model-value="value"
    :options="opcje"
    :placeholder="__('Wybierz')"
    :disabled="disabled"
    @update:model-value="wybierz"
  />
  <FormControl
    v-else
    class="form-control"
    type="text"
    :value="value"
    :placeholder="placeholder"
    :disabled="disabled"
    :debounce="500"
    @change.stop="emit('change', $event.target.value)"
  >
    <template v-if="!disabled && lista.length" #suffix>
      <Button
        variant="ghost"
        class="!size-5"
        icon="list"
        data-testid="miejscowosc-lista"
        :tooltip="__('Wybierz z listy miejscowości')"
        @click="powrotDoListy"
      />
    </template>
  </FormControl>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { miejscowosciKodu } from '@/data/kodPocztowy'
import {
  WARTOSC_RECZNIE,
  opcjeMiejscowosci,
  trybPolaMiejscowosci,
} from '@/utils/kodPocztowy'

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

const opcje = computed(() => opcjeMiejscowosci(lista.value, props.value))

// Stan UI: wybor "Recznie" (albo powrot do listy). Reset przy zmianie kodu
// -- nowa lista zawsze zaczyna od wyboru z listy, zeby "Recznie" wybrane dla
// poprzedniego kodu nie zostawalo "przyklejone" do nowego.
const recznieWybrane = ref(false)
watch(
  () => props.kod,
  () => {
    recznieWybrane.value = false
  },
)

const tryb = computed(() =>
  trybPolaMiejscowosci(lista.value, recznieWybrane.value),
)

function wybierz(wartosc) {
  if (wartosc === WARTOSC_RECZNIE) {
    recznieWybrane.value = true
    return
  }
  if (wartosc !== props.value) emit('change', wartosc)
}

function powrotDoListy() {
  recznieWybrane.value = false
}
</script>
