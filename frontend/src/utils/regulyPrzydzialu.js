// Panel "Przydział leadów", tryb "Reguły bezpośrednie" (ops#346, issue 350):
// czysty JS bez frappe-ui, lustro kontraktu crm/api/reguly_przydzialu.py.

// Stała paleta kolorów reguł (hex), czytelna na jasnych i ciemnych kafelkach mapy.
export const PALETA_KOLOROW = ['#2563eb', '#16a34a', '#d97706', '#9333ea', '#dc2626', '#0891b2']

export const MIN_ZNAKOW_SZUKANIA = 2
export const PROMIEN_DOMYSLNY_KM = 50

export function kolorReguly(indeks) {
  const n = PALETA_KOLOROW.length
  const i = Number.isInteger(indeks) ? ((indeks % n) + n) % n : 0
  return PALETA_KOLOROW[i]
}

// "do 70 km od: Gorzów Wielkopolski" (bez odmiany nazw)
export function opisObszaru(regula) {
  const promien = Number(regula?.promien_km) || 0
  const nazwa = (regula?.srodek_nazwa || regula?.srodek_kod || '').trim()
  return nazwa ? `do ${promien} km od: ${nazwa}` : `do ${promien} km`
}

// Pozycja listy podpowiedzi: "66-400, Wawrów, lubuskie"
export function etykietaKandydata(k) {
  return [k?.kod, k?.miejscowosc, k?.wojewodztwo].filter((c) => c && String(c).trim()).join(', ')
}

// Nowa kolejność nazw po przesunięciu o jedną pozycję; null, gdy ruch jest niemożliwy.
export function przesunNazwy(nazwy, indeks, kierunek) {
  const lista = Array.isArray(nazwy) ? nazwy : []
  const cel = indeks + (kierunek === 'wyzej' ? -1 : 1)
  if (!Number.isInteger(indeks) || indeks < 0 || indeks >= lista.length) return null
  if (cel < 0 || cel >= lista.length) return null
  const kopia = [...lista]
  ;[kopia[indeks], kopia[cel]] = [kopia[cel], kopia[indeks]]
  return kopia
}

// Opis wyniku sprawdzenia kodu dla widoku: wariant "regula" | "cc_brak_reguly" | "cc_nieznany".
export function opisWynikuKodu(w) {
  if (!w) return null
  const lokalizacja = [w.miejscowosc ? `okolice: ${w.miejscowosc}` : '', w.wojewodztwo || '']
    .filter(Boolean)
    .join(', ')
  if (!w.znany) {
    return {
      wariant: 'cc_nieznany',
      lokalizacja: '',
      tytul: 'Trafi do: call center',
      szczegoly: [`Nie znamy położenia kodu ${w.kod}, więc nie da się policzyć odległości.`],
    }
  }
  if (w.wynik === 'regula' && w.regula) {
    const szczegoly = [
      `${w.odleglosc_km} km od: ${w.regula.srodek_nazwa}, reguła ${w.regula.kolejnosc}`,
    ]
    const inne = (w.inne_pasujace || []).map(
      (i) => `${i.srodek_nazwa}, ${i.odleglosc_km} km (reguła ${i.kolejnosc})`,
    )
    if (inne.length) {
      szczegoly.push(`Pasuje też: ${inne.join('; ')}. Wygrywa reguła wyżej na liście.`)
    }
    return {
      wariant: 'regula',
      lokalizacja,
      tytul: `Trafi do: ${w.regula.handlowiec_nazwa}`,
      szczegoly,
    }
  }
  const szczegoly = ['Żadna aktywna reguła nie obejmuje tego kodu.']
  if (w.najblizsza) {
    szczegoly[0] += ` Najbliżej: reguła ${w.najblizsza.kolejnosc}, ${w.najblizsza.odleglosc_km} km.`
  }
  return { wariant: 'cc_brak_reguly', lokalizacja, tytul: 'Trafi do: call center', szczegoly }
}

// Kontrola handlowca w oknie reguły: dwie linie ze statusem
export function kontrolaHandlowca(h) {
  if (!h) return []
  return [
    { ok: Boolean(h.ma_numer), tekst: `Numer telefonu do SMS: ${h.ma_numer ? 'jest' : 'brak'}` },
    {
      ok: Boolean(h.ma_linie_leady),
      tekst: `Dostęp do modułu Leady: ${h.ma_linie_leady ? 'włączony' : 'wyłączony'}`,
    },
  ]
}

export function walidujFormularzReguly(f) {
  if (!f.handlowiec) return 'Wybierz handlowca.'
  if (!f.srodek_kod) return 'Wybierz środek obszaru z listy albo wpisz kod pocztowy.'
  const promien = Number(f.promien_km)
  if (!Number.isFinite(promien) || promien < 1) return 'Podaj promień w km (co najmniej 1).'
  return ''
}

// Punkt kodu z odpowiedzi `sprawdz_kod` (lat i lng liczbami), inaczej null.
export function punktKodu(d) {
  const lat = typeof d?.lat === 'number' ? d.lat : NaN
  const lng = typeof d?.lng === 'number' ? d.lng : NaN
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null
  return { lat, lng, kod: String(d.kod || '') }
}
