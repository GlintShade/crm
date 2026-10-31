<!--
  VOLTEO (ops#309): pole "Czas do pierwszego kontaktu" w formacie gg:mm
  (maks. 24:00). Wartosc to sekundy (Duration). Zapis tylko po Enter/blur, gdy
  wpis jest poprawny i rozny od biezacej wartosci; wpis nieparsowalny albo
  powyzej 24:00 daje toast bledu i przywrocenie poprzedniej wartosci, nigdy
  zapis. Puste pole czysci wartosc (emit 0).
-->
<template>
  <TextInput
    ref="inputRef"
    size="sm"
    :value="wyswietlana"
    :placeholder="placeholder"
    :disabled="disabled"
    @focus="onFocus"
    @input="onInput"
    @blur="onBlur"
    @keydown="onKeydown"
  />
</template>

<script setup>
import {
  czyCzasPoprawny,
  formatujGgMm,
  parsujGgMm,
} from '@/utils/czasKontaktu'
import { TextInput, toast } from 'frappe-ui'
import { computed, ref } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  disabled: { type: Boolean, default: false },
  placeholder: { type: String, default: 'gg:mm' },
})

const emit = defineEmits(['change'])

const inputRef = ref(null)
const edytuje = ref(false)
const wpis = ref('')

const wyswietlana = computed(() =>
  edytuje.value ? wpis.value : formatujGgMm(props.value),
)

function onFocus() {
  edytuje.value = true
  wpis.value = formatujGgMm(props.value)
}

function onInput(e) {
  wpis.value = e.target.value
}

function zatwierdz() {
  if (!edytuje.value) return
  const surowy = wpis.value.trim()
  edytuje.value = false
  const biezaca = Number(props.value) || 0
  if (surowy === '') {
    if (biezaca !== 0) emit('change', 0)
    return
  }
  const sekundy = parsujGgMm(surowy)
  if (sekundy === null) {
    toast.error(__('Nieprawidłowy format. Wpisz czas jako gg:mm, np. 1:30.'))
    return
  }
  if (!czyCzasPoprawny(sekundy)) {
    toast.error(__('Czas do pierwszego kontaktu nie może przekraczać 24:00.'))
    return
  }
  if (sekundy !== biezaca) emit('change', sekundy)
}

function onBlur() {
  zatwierdz()
}

function onKeydown(e) {
  if (e.key === 'Enter') {
    e.preventDefault()
    inputRef.value?.el?.blur()
  } else if (e.key === 'Escape') {
    edytuje.value = false
    inputRef.value?.el?.blur()
  }
}
</script>
