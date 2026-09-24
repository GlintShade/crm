// Wspoldzielony stan przelacznika "Ukryj puste pola" w panelach bocznych
// (issue #178). Jedno ustawienie na przegladarke dla wszystkich instancji
// SidePanelLayout na stronie -- na karcie leada dwie instancje (prawy panel
// i zakladka Szczegoly) musza widziec dokladnie ta sama wartosc, wiec `ref`
// zyje w zasiegu modulu (jeden na cala aplikacje), a nie wewnatrz funkcji
// composable.
//
// Uwaga na pulapke "sklep w zasiegu modulu psuje obcy komponent": stan tutaj
// to jeden boolean bez zadnych efektow ubocznych poza localStorage (przez
// panelPuste.js) -- to jest bezpieczne. Nie dodawac tu nic wiecej.

import { ref, watch } from 'vue'
import { wczytajUkryjPuste, zapiszUkryjPuste } from '@/utils/panelPuste'

const ukryjPuste = ref(wczytajUkryjPuste())

watch(ukryjPuste, (wartosc) => zapiszUkryjPuste(wartosc))

export function useUkryjPustePola() {
  return { ukryjPuste }
}
