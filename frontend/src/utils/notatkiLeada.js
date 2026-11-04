// Notatki leada w prawym panelu (ops#328). Czysta logika komponentu
// NotatkiLeadaPanel.vue: kolejnosc listy, widoczny wycinek, autor i wspolny
// sygnal "komentarze tego dokumentu sie zmienily". Notatka to zwykly
// `Comment` (comment_type "Comment"), ten sam co w zakladce "Komentarze",
// bez drugiego magazynu.

import { reactive } from 'vue'

// Ile ostatnich notatek panel pokazuje przed "Pokaz wszystkie".
export const LIMIT_ZWINIETYCH = 3

/** Najnowsze na gorze (API `komentarze` zwraca rosnaco po `creation`). */
export function posortujNotatki(lista) {
  return [...(lista || [])].sort((a, b) =>
    String(b?.creation ?? '').localeCompare(String(a?.creation ?? '')),
  )
}

/** Widoczny wycinek listy: zwiniete = `limit` najnowszych, rozwiniete = wszystkie. */
export function widoczneNotatki(
  posortowane,
  rozwiniete,
  limit = LIMIT_ZWINIETYCH,
) {
  const lista = posortowane || []
  return rozwiniete ? lista : lista.slice(0, limit)
}

/** Autor wyswietlany na liscie (backend juz zamaskowal CC przed handlowcem). */
export function autorNotatki(wpis) {
  return wpis?.comment_by || wpis?.owner || ''
}

// --- Wspolny sygnal zmian komentarzy ------------------------------------------
// Licznik wersji per doctype+nazwa. Kazde miejsce, ktore dodaje komentarz
// (zakladka "Komentarze", KomentarzeLeadaModal), podbija wersje, a panel
// notatek obserwuje ja i przeladowuje liste. Bez tego notatka dodana w
// zakladce pojawialaby sie w panelu dopiero po odswiezeniu strony.

const wersje = reactive({})

function klucz(doctype, name) {
  return `${doctype}::${name}`
}

export function zglosZmianeKomentarzy(doctype, name) {
  if (!doctype || !name) return
  const k = klucz(doctype, name)
  wersje[k] = (wersje[k] || 0) + 1
}

export function wersjaKomentarzy(doctype, name) {
  return wersje[klucz(doctype, name)] || 0
}
