// VOLTEO (issue #99, K3): czysta logika edycji inline kolumn listy leadow
// (Status CC, Status handlowy, Kolejny kontakt, Termin spotkania), uzywana
// przez LeadInlineCell.vue i LeadsListView.vue. Zero importu z '@/utils'
// (ten sam pulapka co w utils/aktualizacje.js: barel '@/utils' eagerly
// laduje unplugin-icons przez ~icons/lucide/*, ktorego vitest.config.js nie
// zna, wiec kazdy test transzytywnie importujacy '@/utils' by sie wywalil).

// Kolumny listy leadow obslugiwane inline (LeadsListView.vue renderuje dla
// nich LeadInlineCell.vue zamiast generycznej etykiety). custom_cc celowo
// nie jest tutaj: przypisanie CC idzie osobna akcja (przydziel_cc).
// lead_owner jest od b83 (prosba wlasciciela): zapis idzie ta sama sciezka co
// panel boczny (frappe.client.set_value -> doc.save -> CRMLead.validate /
// on_update), wiec mail o przydziale i odebranie widocznosci poprzedniemu
// handlowcowi odpalaja sie bez zmian. Kto moze edytowac w UI: patrz
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

// Role, ktore moga przypisywac handlowca z listy (decyzja wlasciciela b83:
// administracja, backoffice i CC). Handlowiec D2D widzi komorke tylko do
// odczytu. To jest wylacznie decyzja UI: serwer sprawdza uprawnienia sam.
export const ROLE_PRZYPISANIA_HANDLOWCA = [
  'System Manager',
  'Volteo Core Admin',
  'Volteo Backend',
  'Volteo Call Center',
]

export function mozePrzypisywacHandlowca(role, czyAdmin = false) {
  if (czyAdmin) return true
  const lista = Array.isArray(role) ? role : []
  return ROLE_PRZYPISANIA_HANDLOWCA.some((r) => lista.includes(r))
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
  if (column.key === 'lead_owner') {
    if (item && typeof item === 'object') return item.name || ''
    return item ?? ''
  }

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
