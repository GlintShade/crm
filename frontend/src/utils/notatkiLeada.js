// Notatki leada w prawym panelu (ops#328). Czysta logika komponentu
// NotatkiLeadaPanel.vue: zamiana zwyklego tekstu na HTML komentarza,
// kolejnosc listy, skrot zapisu i wspolny sygnal "komentarze tego dokumentu
// sie zmienily". Notatka to zwykly `Comment` (comment_type "Comment"),
// ten sam co w zakladce "Komentarze", bez drugiego magazynu.

import { reactive } from 'vue'

// Ile ostatnich notatek panel pokazuje przed "Pokaz wszystkie".
export const LIMIT_ZWINIETYCH = 3

const ENCJE = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
}

function escapuj(tekst) {
  return tekst.replace(/[&<>"']/g, (z) => ENCJE[z])
}

/** Pusty tekst (same spacje i entery) blokuje zapis. */
export function czyPustaNotatka(tekst) {
  return !String(tekst ?? '').trim()
}

/**
 * Zwykly tekst z pola notatki na HTML tresci komentarza (ten sam format co
 * edytor w zakladce "Komentarze"): kazda linia to osobny akapit, pusta linia
 * to pusty akapit, znaki HTML sa escapowane (tekst nie moze wstrzyknac
 * znacznikow). Puste linie na poczatku i koncu sa obcinane.
 */
export function tekstNaHtml(tekst) {
  const linie = String(tekst ?? '')
    .replace(/\r\n?/g, '\n')
    .split('\n')
    .map((l) => l.replace(/\s+$/, ''))
  while (linie.length && !linie[0].trim()) linie.shift()
  while (linie.length && !linie[linie.length - 1].trim()) linie.pop()
  return linie
    .map((l) => (l.trim() ? `<p>${escapuj(l)}</p>` : '<p><br></p>'))
    .join('')
}

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

/** Ctrl+Enter (Windows/Linux) albo Cmd+Enter (Mac). */
export function czySkrotZapisu(e) {
  return Boolean(e && e.key === 'Enter' && (e.ctrlKey || e.metaKey))
}

// --- Wspolny sygnal zmian komentarzy ------------------------------------------
// Licznik wersji per doctype+nazwa. Kazde miejsce, ktore dodaje komentarz
// (zakladka "Komentarze", KomentarzeLeadaModal, panel notatek), podbija
// wersje, a panel notatek obserwuje ja i przeladowuje liste. Bez tego
// notatka dodana w zakladce pojawialaby sie w panelu dopiero po odswiezeniu
// strony.

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
