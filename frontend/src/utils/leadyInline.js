// VOLTEO (issue #99, K3): czysta logika edycji inline kolumn listy leadow
// (Status CC, Status handlowy, Kolejny kontakt, Termin spotkania), uzywana
// przez LeadInlineCell.vue i LeadsListView.vue. Zero importu z '@/utils'
// (ten sam pulapka co w utils/aktualizacje.js: barel '@/utils' eagerly
// laduje unplugin-icons przez ~icons/lucide/*, ktorego vitest.config.js nie
// zna, wiec kazdy test transzytywnie importujacy '@/utils' by sie wywalil).

// Kolumny listy leadow obslugiwane inline (LeadsListView.vue renderuje dla
// nich LeadInlineCell.vue zamiast generycznej etykiety). custom_cc i
// lead_owner celowo nie sa tutaj: przypisanie CC/handlowca idzie osobnymi
// akcjami (przydziel_cc / przekaz_handlowcowi), nie zwyklym set_value z
// przegladarki.
export const KOLUMNY_INLINE = new Set([
  'status',
  'custom_status_handlowy',
  'custom_kolejny_kontakt',
  'custom_termin_spotkania',
  'custom_czas_do_kontaktu',
  'custom_proby_kontaktu',
])

export function czyKolumnaInline(column) {
  return Boolean(column && KOLUMNY_INLINE.has(column.key))
}

// Wyciaga surowa (edytowalna) wartosc z ksztaltu komorki wyprodukowanego
// przez Leads.vue::parseRows: status to {label, color}, Date/Datetime to
// {label, value}, custom_status_handlowy to goly string (Select nie ma
// specjalnej galezi w parseRows).
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
