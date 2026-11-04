/**
 * Kalendarz spotkań na żywo (ops#331).
 *
 * Odświeża dane kalendarza bez przeładowania strony:
 * - sygnał socketu `volteo_kalendarz` (po zapisie leada/grafiku u kogokolwiek),
 *   gdy jego daty przecinają widoczny zakres; seria sygnałów w ciągu
 *   ODSTEP_ODSWIEZENIA_MS daje jedno zapytanie,
 * - powrót na kartę (`visibilitychange`) i ponowne połączenie socketu
 *   (sygnały z czasu rozłączenia przepadły),
 * - łagodny polling co ODSTEP_POLLINGU_MS, gdy karta jest widoczna, a od
 *   ostatniego odświeżenia nic nie przyszło (socket rozłączony albo cisza).
 * Ukryta karta nie odpytuje serwera; nadrabia po powrocie.
 *
 * `odswiez` to funkcja, która pobiera dane ponownie bez ruszania stanu
 * widoku (zakres, handlowiec, przewinięcie zostają).
 */
import { getCurrentInstance, onMounted, onUnmounted } from 'vue'
import {
  ODSTEP_ODSWIEZENIA_MS,
  ODSTEP_SPRAWDZANIA_MS,
  ZDARZENIE_KALENDARZA,
  czasNaPolling,
  dotyczyZakresu,
} from '@/utils/kalendarzLive'

function kartaWidoczna() {
  return (
    typeof document === 'undefined' || document.visibilityState !== 'hidden'
  )
}

export function useKalendarzLive({ okres, odswiez, socket } = {}) {
  const gniazdo =
    socket !== undefined
      ? socket
      : getCurrentInstance()?.appContext.config.globalProperties.$socket || null
  let ostatnie = Date.now()
  let odroczone = null
  let sprawdzanie = null

  function zaplanuj() {
    if (odroczone) return
    odroczone = setTimeout(() => {
      odroczone = null
      ostatnie = Date.now()
      odswiez()
    }, ODSTEP_ODSWIEZENIA_MS)
  }

  function onSygnal(tresc) {
    if (!kartaWidoczna()) return
    const { od, do: doDaty } = okres() || {}
    if (dotyczyZakresu(tresc, od, doDaty)) zaplanuj()
  }

  function onWidocznosc() {
    if (kartaWidoczna()) zaplanuj()
  }

  function onPolaczenie() {
    if (kartaWidoczna()) zaplanuj()
  }

  function sprawdzPolling() {
    if (
      czasNaPolling({
        teraz: Date.now(),
        ostatnie,
        widoczna: kartaWidoczna(),
      })
    )
      zaplanuj()
  }

  onMounted(() => {
    ostatnie = Date.now()
    if (gniazdo) {
      gniazdo.on(ZDARZENIE_KALENDARZA, onSygnal)
      gniazdo.on('connect', onPolaczenie)
    }
    document.addEventListener('visibilitychange', onWidocznosc)
    sprawdzanie = setInterval(sprawdzPolling, ODSTEP_SPRAWDZANIA_MS)
  })

  onUnmounted(() => {
    if (gniazdo) {
      gniazdo.off(ZDARZENIE_KALENDARZA, onSygnal)
      gniazdo.off('connect', onPolaczenie)
    }
    document.removeEventListener('visibilitychange', onWidocznosc)
    clearTimeout(odroczone)
    clearInterval(sprawdzanie)
    odroczone = null
  })

  /** Odświeżenie z innego źródła (nawigacja, zapis) przesuwa polling. */
  function oznaczOdswiezenie() {
    ostatnie = Date.now()
  }

  return { oznaczOdswiezenie }
}
