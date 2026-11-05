// VOLTEO (ops#329): wspolny lookup kodu pocztowego w calej aplikacji (panel
// leada, ContactModal.vue, DaneKlientaTab.vue). Logika i testy:
// utils/kodPocztowy.js. Front woła API pelna sciezka.
import { call } from 'frappe-ui'
import { reactive } from 'vue'
import {
  POLE_MIEJSCOWOSCI,
  czyKodPocztowy,
  listaMiejscowosci,
  utworzLookup,
  uzupelnijAdresZKodu,
} from '@/utils/kodPocztowy'

export const METODA_LOOKUPU = 'crm.api.kod_pocztowy.wyszukaj'

// Reaktywna pamiec list miejscowosci per kod: czyta ja pole Miejscowosc i
// decyzja "Ukryj puste pola" w SidePanelLayout.vue.
const listy = reactive({})

export const pobierzDaneKodu = utworzLookup(
  (kod) => call(METODA_LOOKUPU, { kod }),
  (kod, wynik) => {
    listy[kod] = listaMiejscowosci(wynik)
  },
)

// Lista miejscowosci dla kodu (reaktywnie). Pierwsze wywolanie dla kodu
// uruchamia lookup w tle; do czasu odpowiedzi lista jest pusta.
export function miejscowosciKodu(kod) {
  const k = String(kod ?? '').trim()
  if (!czyKodPocztowy(k)) return []
  if (!(k in listy)) pobierzDaneKodu(k)
  return listy[k] || []
}

// Zadanie N (ops#329): czy lista miejscowosci dla kodu jest JUZ znana (lookup
// juz zwrocil odpowiedz, choc moze pusta) -- odczyt reaktywny BEZ
// uruchamiania nowego zapytania (w odroznieniu od miejscowosciKodu powyzej).
// Uzywa LeadInlineCell.vue: komorka Miejscowosc prefetchuje liste na
// mouseenter/focus (patrz prefetchMiejscowosci), a ten odczyt decyduje, czy
// w spoczynku pokazac juz prawdziwy select (lista znana) czy atrapa-pigulke
// (jeszcze w trakcie lookupu) -- bez niego kazdy render komorki musialby
// sam wywolywac lookup, zeby to sprawdzic.
export function listaMiejscowosciZnanaDlaKodu(kod) {
  const k = String(kod ?? '').trim()
  return czyKodPocztowy(k) && k in listy
}

export function uzupelnijAdresLeadaZKodu(doc) {
  return uzupelnijAdresZKodu(doc, pobierzDaneKodu, POLE_MIEJSCOWOSCI)
}
