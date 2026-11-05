// Wspolny stan zwinietych i rozwinietych sekcji panelu bocznego (ops#330).
// Jeden reaktywny obiekt na uzytkownika i doctype w zasiegu modulu, wiec
// wszystkie instancje SidePanelLayout tego doctype (prawy panel leada,
// zakladka Szczegoly, MobileLead, szybki podglad na mapie) widza i
// zapisuja ten sam stan. Logika i magazyn: utils/stanSekcjiPanelu.js.

import { reactive, toRaw, toValue } from 'vue'
import { sessionStore } from '@/stores/session'
import { useSynchronizujSekcje } from '@/composables/useSynchronizujSekcje'
import {
  kluczStanuSekcji,
  wczytajStanSekcji,
  zapiszStanSekcji,
  rozstrzygnijOtwarcie,
  doctypeDlaWidoku,
} from '@/utils/stanSekcjiPanelu'

// Zwykla Mapa (nie reactive): wpis powstaje przy pierwszym odczycie w
// renderze, a zapis do reaktywnego obiektu w trakcie renderu wymuszalby
// kolejne przeliczenie. Reaktywny jest dopiero sam stan sekcji.
const pamiec = new Map()

function stanDla(user, doctype) {
  const klucz = kluczStanuSekcji(user, doctype)
  if (!pamiec.has(klucz)) {
    pamiec.set(klucz, reactive(wczytajStanSekcji(user, doctype)))
  }
  return pamiec.get(klucz)
}

/**
 * @param {string|import('vue').Ref<string>|() => string} doctype
 * @param {string|import('vue').Ref<string>|() => string} [widok] nazwa
 *   widoku dla przelacznika "Synchronizuj sekcje" (b84, zadanie F) -- pusty
 *   (domyslnie) = ta instancja zawsze dzieli stan z innymi panelami tego
 *   doctype (prawy panel leada). Niepusty (np. "szczegoly") = wlasny,
 *   niezalezny stan, gdy uzytkownik wylaczy synchronizacje (patrz
 *   doctypeDlaWidoku).
 */
export function useStanSekcjiPanelu(doctype, widok) {
  const session = sessionStore()
  const { synchronizujSekcje } = useSynchronizujSekcje()

  function doctypeEfektywny() {
    return doctypeDlaWidoku(
      toValue(doctype),
      toValue(widok),
      synchronizujSekcje.value,
    )
  }

  function czyOtwarta(nazwa, domyslny) {
    return rozstrzygnijOtwarcie(
      stanDla(session.user, doctypeEfektywny()),
      nazwa,
      domyslny,
    )
  }

  function ustaw(nazwa, otwarta) {
    if (!nazwa) return
    const d = doctypeEfektywny()
    const stan = stanDla(session.user, d)
    stan[nazwa] = !!otwarta
    zapiszStanSekcji(session.user, d, toRaw(stan))
  }

  return { czyOtwarta, ustaw }
}
