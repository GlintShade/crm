import { computed } from 'vue'
import { useStorage } from '@vueuse/core'
import { createResource } from 'frappe-ui'
import { KATEGORIE } from '@/utils/kategorieHandlowcow'

// Jeden współdzielony stan dla Listy, Mapy i Kalendarza (ops#393). Nie trafia do
// route.query (App.vue remontuje przy zmianie query) ani do zapisanego widoku.
let stan = null

function uzytkownik() {
  try {
    return new URLSearchParams(document.cookie.split('; ').join('&')).get('user_id') || ''
  } catch (e) {
    return ''
  }
}

export function useKategoriaFiltr() {
  if (!stan) {
    const zapisana = useStorage(`volteo.leady.kategoria:${uzytkownik()}`, '')
    const zasob = createResource({ url: 'crm.api.kategorie_handlowcow.tereny', auto: true })
    const widoczne = computed(() => zasob.data?.widoczne === true)
    const tereny = computed(() => (widoczne.value ? zasob.data?.tereny || [] : []))
    // Bez widoczności (handlowiec) lub przed wczytaniem terenów filtr jest wyłączony.
    const aktywna = computed({
      get: () =>
        widoczne.value && KATEGORIE.includes(zapisana.value) ? zapisana.value : null,
      set: (k) => {
        zapisana.value = k || ''
      },
    })
    stan = { aktywna, widoczne, tereny }
  }
  return stan
}
