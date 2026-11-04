// Wspolny stan zwinietych i rozwinietych sekcji panelu bocznego (ops#330).
// Jeden reaktywny obiekt na uzytkownika i doctype w zasiegu modulu, wiec
// wszystkie instancje SidePanelLayout tego doctype (prawy panel leada,
// zakladka Szczegoly, MobileLead, szybki podglad na mapie) widza i
// zapisuja ten sam stan. Logika i magazyn: utils/stanSekcjiPanelu.js.

import { reactive, toRaw, toValue } from 'vue'
import { sessionStore } from '@/stores/session'
import {
  kluczStanuSekcji,
  wczytajStanSekcji,
  zapiszStanSekcji,
  rozstrzygnijOtwarcie,
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

/** @param {string|import('vue').Ref<string>|() => string} doctype */
export function useStanSekcjiPanelu(doctype) {
  const session = sessionStore()

  function czyOtwarta(nazwa, domyslny) {
    return rozstrzygnijOtwarcie(
      stanDla(session.user, toValue(doctype)),
      nazwa,
      domyslny,
    )
  }

  function ustaw(nazwa, otwarta) {
    if (!nazwa) return
    const stan = stanDla(session.user, toValue(doctype))
    stan[nazwa] = !!otwarta
    zapiszStanSekcji(session.user, toValue(doctype), toRaw(stan))
  }

  return { czyOtwarta, ustaw }
}
