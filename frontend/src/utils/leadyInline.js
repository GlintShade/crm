// VOLTEO (issue #99, K3): czysta logika edycji inline kolumn listy leadow
// (Status CC, Status handlowy, Kolejny kontakt, Termin spotkania), uzywana
// przez LeadInlineCell.vue i LeadsListView.vue. Zero importu z '@/utils'
// (ten sam pulapka co w utils/aktualizacje.js: barel '@/utils' eagerly
// laduje unplugin-icons przez ~icons/lucide/*, ktorego vitest.config.js nie
// zna, wiec kazdy test transzytywnie importujacy '@/utils' by sie wywalil).
// Import z './kodPocztowy' (plik siostrzany, nie barel) jest bezpieczny: ten
// modul tez nie dotyka '@/utils' ani Vue.

import { POLE_GMINY, POLE_KODU, czyKodPocztowy, latkaAdresuZKodu } from './kodPocztowy'

// Kolumny listy leadow obslugiwane inline (LeadsListView.vue renderuje dla
// nich LeadInlineCell.vue zamiast generycznej etykiety). custom_cc celowo
// nie jest tutaj: przypisanie CC idzie osobna akcja (przydziel_cc).
// lead_owner jest od b83 (prosba wlasciciela): zapis idzie przez
// crm.api.volteo_leady.przekaz_handlowcowi (ten sam co przycisk "Przekaz
// handlowcowi"), ktore robi doc.save -> CRMLead.validate / on_update, wiec
// mail o przydziale i odebranie widocznosci poprzedniemu handlowcowi
// odpalaja sie bez zmian, a w Aktywnosci zostaje slad przekazania. Kto moze edytowac w UI: patrz
// mozePrzypisywacHandlowca nizej; serwer i tak decyduje.
export const KOLUMNY_INLINE = new Set([
  'status',
  'custom_status_handlowy',
  'custom_kolejny_kontakt',
  'custom_termin_spotkania',
  'custom_czas_do_kontaktu',
  'custom_proby_kontaktu',
  'lead_owner',
  'custom_install_address',
  'custom_nr_domu',
  'custom_install_city',
  'custom_powiat',
  'custom_voivodeship',
  'custom_install_postal_code',
])

// b83: kolumny adresu edytowane zwyklym polem tekstowym (klik otwiera
// edycje, Enter albo opuszczenie pola zatwierdza, Escape anuluje).
// custom_powiat dostaje dodatkowo podpowiedzi z powiaty_filtra (datalist),
// ale wartosc nadal jest dowolnym tekstem.
export const KOLUMNY_TEKSTOWE_INLINE = new Set([
  'custom_install_address',
  'custom_nr_domu',
  'custom_install_city',
  'custom_powiat',
  'custom_install_postal_code',
])

// Zadanie K (prosba wlasciciela): wyglad komorki Miejscowosc (custom_install_
// city) na liscie leadow PRZED kliknieciem. Z poprawnym kodem pocztowym w
// tym wierszu (NN-NNN) komorka w spoczynku ma wygladac dokladnie jak inne
// kolumny-wybory z tego pliku (np. custom_status_handlowy): szara "pigulka"
// z placeholderem "Wybierz opcję" i chevronem, albo wartosc + chevron.
// Funkcja patrzy WYLACZNIE na format kodu pocztowego w wierszu -- nie na
// wynik lookupu listy miejscowosci (crm.api.kod_pocztowy.wyszukaj), ktory
// LeadInlineCell.vue nadal uruchamia dopiero po kliknieciu (montuje
// MiejscowoscInput pod `v-if="edytujeTekst"`, wydajnosc listy). `wartosc`
// biezacej komorki nie wplywa na decyzje (pusta i wypelniona komorka z
// poprawnym kodem obie dostaja wyglad 'wybor') -- parametr zostaje w
// sygnaturze, zeby wolajacy mial jedno miejsce decyzji z pelnym kontekstem
// komorki, tak jak surowaWartoscKomorki(column, item) powyzej. Bez
// poprawnego kodu komorka zostaje zwyklym polem tekstowym jak dotad: pusta
// w spoczynku, edycja po kliknieciu.
export function wygladKomorkiMiejscowosci(wartosc, kod) {
  return czyKodPocztowy(kod) ? 'wybor' : 'tekst'
}

// 16 wojewodztw malymi literami, dokladnie jak opcje Select
// custom_voivodeship (te same wartosci co KalkulatorTab.vue i
// crm/volteo_leady_import.py). Uzywane jako zapas, gdy meta pola nie ma
// jeszcze opcji.
export const WOJEWODZTWA = [
  'dolnośląskie',
  'kujawsko-pomorskie',
  'lubelskie',
  'lubuskie',
  'łódzkie',
  'małopolskie',
  'mazowieckie',
  'opolskie',
  'podkarpackie',
  'podlaskie',
  'pomorskie',
  'śląskie',
  'świętokrzyskie',
  'warmińsko-mazurskie',
  'wielkopolskie',
  'zachodniopomorskie',
]

// Kto moze zmienic handlowca z listy. Ta sama bramka co serwerowe
// crm.api.volteo_leady.przekaz_handlowcowi, przez ktore idzie zapis:
// Administrator albo rola z BYPASS_ROLES (crm/permissions/org_hierarchy.py)
// zawsze, CC (Volteo Call Center) tylko na leadzie, ktorego custom_cc to on
// sam. Handlowiec D2D i wszyscy inni: komorka tylko do odczytu. Zwykly
// set_value na lead_owner nie wchodzi w gre: pole ma permlevel 1, a D2D, CC
// i Backend nie maja na nim write (sonda produkcji 2026-11-04). To jest
// wylacznie decyzja UI, serwer sprawdza to samo jeszcze raz.
export const ROLE_BYPASS_HANDLOWCA = [
  'System Manager',
  'Volteo Core Admin',
  'Volteo Backend',
]
export const ROLA_CC = 'Volteo Call Center'

export function mozePrzypisywacHandlowca({ uzytkownik, role, ccLeada } = {}) {
  if (uzytkownik === 'Administrator') return true
  const lista = Array.isArray(role) ? role : []
  if (ROLE_BYPASS_HANDLOWCA.some((r) => lista.includes(r))) return true
  return Boolean(
    uzytkownik && lista.includes(ROLA_CC) && ccLeada && ccLeada === uzytkownik,
  )
}

// CC leada z wiersza listy: parseRows daje dla custom_cc ten sam ksztalt co
// dla lead_owner ({label, ...getUser(email)}), surowy wiersz ma goly e-mail.
export function emailUzytkownikaZKomorki(item) {
  if (item && typeof item === 'object') return item.name || ''
  return typeof item === 'string' ? item : ''
}

// Kod pocztowy: pusty wpis czysci pole, "NN-NNN" przechodzi, piec cyfr
// bez myslnika ("12345") jest dopelniane do "12-345", wszystko inne to
// blad. Zwraca {ok, wartosc} albo {ok: false, blad}.
const WZOR_KODU = /^\d{2}-\d{3}$/

export function normalizujKodPocztowy(wpis) {
  const tekst = String(wpis ?? '').replace(/\s+/g, '')
  if (tekst === '') return { ok: true, wartosc: '' }
  if (WZOR_KODU.test(tekst)) return { ok: true, wartosc: tekst }
  if (/^\d{5}$/.test(tekst)) {
    return { ok: true, wartosc: `${tekst.slice(0, 2)}-${tekst.slice(2)}` }
  }
  return { ok: false, blad: 'Kod pocztowy musi mieć format NN-NNN, np. 00-950.' }
}

// Wpis z pola tekstowego -> wartosc do zapisu. Obcina spacje na brzegach,
// kod pocztowy przechodzi przez normalizujKodPocztowy.
export function wartoscTekstuDoZapisu(fieldname, wpis) {
  if (fieldname === 'custom_install_postal_code') {
    return normalizujKodPocztowy(wpis)
  }
  return { ok: true, wartosc: String(wpis ?? '').trim() }
}

// b84/ops#329: po edycji kodu pocztowego w komorce listy (format NN-NNN juz
// przeszedl przez normalizujKodPocztowy) trzeba dociagnac wojewodztwo, powiat
// i gmine tak samo jak w panelu leada -- ta sama funkcja czysta
// `latkaAdresuZKodu` (utils/kodPocztowy.js), tylko zbudowana z surowego
// wiersza listy zamiast z document.doc. Miejscowosc NIGDY nie wchodzi do
// latki (decyzja wlasciciela, latkaAdresuZKodu juz to gwarantuje).
//
// `row` to surowy wiersz listy (leads.data.data z backendu): moze nie miec
// klucza custom_gmina wcale, jesli ta kolumna nie jest w widoku -- to NIE
// jest to samo co "lead nie ma pola custom_gmina" (patrz
// czyPokazacPustaMiejscowosc / latkaAdresuZKodu w panelu, ktore sprawdzaja
// Object.hasOwn na pelnym document.doc). Dlatego obecnosc pola dostaje
// wolajacy jako osobny argument `maPoleGminy` (z meta doctype'u CRM Lead,
// LeadInlineCell.vue), niezaleznie od tego, czy wiersz akurat ma ta kolumne
// zaladowana.
export function polaAdresuZKoduWiersza(row, wynik, maPoleGminy) {
  const doc = {
    [POLE_KODU]: row?.custom_install_postal_code ?? '',
    custom_voivodeship: row?.custom_voivodeship ?? '',
    custom_powiat: row?.custom_powiat ?? '',
  }
  if (maPoleGminy) doc[POLE_GMINY] = row?.custom_gmina ?? ''
  return latkaAdresuZKodu(doc, wynik)
}

// Czy zapis ma sens: null/undefined i '' traktujemy jako ta sama pusta
// wartosc, zeby opuszczenie pustej komorki nie wysylalo zapytania.
export function czyWartoscSieZmienila(stara, nowa) {
  const a = stara === null || stara === undefined ? '' : String(stara)
  const b = nowa === null || nowa === undefined ? '' : String(nowa)
  return a !== b
}

export function czyKolumnaInline(column) {
  return Boolean(column && KOLUMNY_INLINE.has(column.key))
}

// Wyciaga surowa (edytowalna) wartosc z ksztaltu komorki wyprodukowanego
// przez Leads.vue::parseRows: status to {label, color}, Date/Datetime to
// {label, value}, custom_status_handlowy to goly string (Select nie ma
// specjalnej galezi w parseRows), lead_owner to obiekt uzytkownika.
// Puste Próby kontaktu (null, '', undefined) znaczą "0": pole Select ma opcje
// 0..5, wiec pusta wartosc nie moze byc osobnym wyborem.
export function probyKontaktuDoWyswietlenia(wartosc) {
  if (wartosc === null || wartosc === undefined) return '0'
  const tekst = String(wartosc).trim()
  return tekst === '' ? '0' : tekst
}

export function surowaWartoscKomorki(column, item) {
  if (!column) return item ?? ''

  if (column.key === 'custom_proby_kontaktu') {
    return probyKontaktuDoWyswietlenia(item)
  }

  // lead_owner: parseRows daje {label, ...getUser(email)}, getUser trzyma
  // e-mail w `name`. Pusty wlasciciel to {label: ''} bez `name`.
  if (column.key === 'lead_owner') return emailUzytkownikaZKomorki(item)

  if (column.key === 'status') {
    if (item && typeof item === 'object') return item.label ?? ''
    return item ?? ''
  }

  if (column.type === 'Date' || column.type === 'Datetime') {
    if (item && typeof item === 'object') return item.value ?? null
    return item ?? null
  }

  if (column.type === 'Duration') return Number(item) || 0

  return item ?? ''
}

// Zwraca NOWA tablice surowych wierszy (ta sama postac co leads.data.data z
// backendu, nie sparsowane rows z parseRows) z podmienionym jednym polem w
// jednym wierszu -- niemutowalnie: wiersz docelowy to nowy obiekt, inne
// wiersze zostaja tymi samymi referencjami, wejsciowa tablica nie jest
// modyfikowana. Podmiana surowego pola (nie gotowej postaci wyswietlania)
// jest celowa: Leads.vue::rows to computed zalezny od leads.data.data, wiec
// po tej podmianie parseRows sam przeliczy kolor statusu / etykiete daty --
// LeadInlineCell.vue nie musi duplikowac tej logiki.
export function nowaListaZPodmienionymPolem(lista, name, fieldname, wartosc) {
  return lista.map((wiersz) =>
    wiersz.name === name ? { ...wiersz, [fieldname]: wartosc } : wiersz,
  )
}

// Minimalne szerokosci kolumn (px) przy recznym przeciaganiu krawedzi
// naglowka: frappe-ui trzyma twardy prog 32 px (patch), a te kolumny maja
// zawartosc, ktora przy wezszej szerokosci jest obcinana.
export const MIN_SZEROKOSC_KOLUMNY_PX = {
  custom_czas_do_kontaktu: 72,
  custom_proby_kontaktu: 64,
  _comment_count: 32,
}

export function ograniczSzerokoscKolumny(key, widthPx) {
  const min = MIN_SZEROKOSC_KOLUMNY_PX[key] || 0
  const w = Number(widthPx)
  return Math.max(min, Number.isFinite(w) ? w : 0)
}

// Egzekwuje minimum przy wczytaniu zapisanego widoku: zwraca nowy obiekt
// kolumny z szerokoscia "NNNpx" tylko gdy zapisana szerokosc (px lub rem,
// 1rem = 16px jak w frappe-ui) jest ponizej minimum; w pozostalych
// przypadkach zwraca ta sama kolumne bez zmian.
export function szerokoscKolumnyZMinimum(column) {
  const min = column && MIN_SZEROKOSC_KOLUMNY_PX[column.key]
  if (!min || !column.width) return column
  const m = String(column.width).match(/^\s*([\d.]+)\s*(px|rem)?\s*$/)
  if (!m) return column
  const px = parseFloat(m[1]) * (m[2] === 'rem' ? 16 : 1)
  if (!Number.isFinite(px) || px >= min) return column
  return { ...column, width: `${min}px` }
}
