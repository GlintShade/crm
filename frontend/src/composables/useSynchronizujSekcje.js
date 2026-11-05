// Przelacznik "Synchronizuj sekcje" (b84, zadanie F): wlaczony (domyslnie)
// -- prawy panel leada i zakladka "Szczegoly" dziela jeden stan zwiniecia
// sekcji, jak dotad. Wylaczony -- kazdy widok dostaje wlasny, niezalezny
// zapis (patrz doctypeDlaWidoku w utils/stanSekcjiPanelu.js).
//
// Stan jest per uzytkownik (w przeciwienstwie do "Ukryj puste pola", jeden
// boolean per uzytkownik w zasiegu modulu -- przelaczenie konta w tej samej
// przegladarce dostaje wlasny zapis), wiec -- tak jak useStanSekcjiPanelu --
// trzymamy mape refow w zasiegu modulu zamiast jednego globalnego refa.

import { ref, watch } from 'vue'
import { sessionStore } from '@/stores/session'
import {
  wczytajSynchronizujSekcje,
  zapiszSynchronizujSekcje,
} from '@/utils/stanSekcjiPanelu'

const pamiec = new Map()

function stanDla(user) {
  if (!pamiec.has(user)) {
    const synchronizuj = ref(wczytajSynchronizujSekcje(user))
    watch(synchronizuj, (wartosc) => zapiszSynchronizujSekcje(user, wartosc))
    pamiec.set(user, synchronizuj)
  }
  return pamiec.get(user)
}

export function useSynchronizujSekcje() {
  const session = sessionStore()
  return { synchronizujSekcje: stanDla(session.user) }
}
