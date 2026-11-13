import { describe, it, expect } from 'vitest'
import {
  PALETA_KOLOROW,
  kolorReguly,
  opisObszaru,
  etykietaKandydata,
  przesunNazwy,
  opisWynikuKodu,
  kontrolaHandlowca,
  walidujFormularzReguly,
  punktKodu,
} from '@/utils/regulyPrzydzialu'

describe('kolorReguly', () => {
  it('ma 6 kolorów i zawija indeks', () => {
    expect(PALETA_KOLOROW).toHaveLength(6)
    expect(kolorReguly(0)).toBe(PALETA_KOLOROW[0])
    expect(kolorReguly(6)).toBe(PALETA_KOLOROW[0])
    expect(kolorReguly(-1)).toBe(PALETA_KOLOROW[5])
    expect(kolorReguly(undefined)).toBe(PALETA_KOLOROW[0])
  })
})

describe('opisObszaru i etykietaKandydata', () => {
  it('buduje opis z promienia i nazwy', () => {
    expect(opisObszaru({ promien_km: 70, srodek_nazwa: 'Gorzów Wielkopolski' })).toBe(
      'do 70 km od: Gorzów Wielkopolski',
    )
    expect(opisObszaru({ promien_km: 5, srodek_nazwa: '', srodek_kod: '66-400' })).toBe('do 5 km od: 66-400')
  })
  it('etykieta kandydata pomija puste części', () => {
    expect(etykietaKandydata({ kod: '66-400', miejscowosc: 'Wawrów', wojewodztwo: 'lubuskie' })).toBe(
      '66-400, Wawrów, lubuskie',
    )
    expect(etykietaKandydata({ kod: '66-400', miejscowosc: '' })).toBe('66-400')
  })
})

describe('przesunNazwy', () => {
  it('zamienia sąsiadów i nie mutuje', () => {
    const a = ['a', 'b', 'c']
    expect(przesunNazwy(a, 1, 'wyzej')).toEqual(['b', 'a', 'c'])
    expect(przesunNazwy(a, 1, 'nizej')).toEqual(['a', 'c', 'b'])
    expect(a).toEqual(['a', 'b', 'c'])
  })
  it('zwraca null na krawędziach', () => {
    expect(przesunNazwy(['a', 'b'], 0, 'wyzej')).toBeNull()
    expect(przesunNazwy(['a', 'b'], 1, 'nizej')).toBeNull()
    expect(przesunNazwy([], 0, 'nizej')).toBeNull()
  })
})

describe('opisWynikuKodu', () => {
  it('wariant reguła z innymi pasującymi', () => {
    const w = opisWynikuKodu({
      kod: '66-200',
      znany: true,
      miejscowosc: 'Bobowicko',
      wojewodztwo: 'lubuskie',
      wynik: 'regula',
      regula: { kolejnosc: 1, handlowiec_nazwa: 'Jan K', srodek_nazwa: 'Gorzów', promien_km: 70 },
      odleglosc_km: 58,
      inne_pasujace: [{ kolejnosc: 2, srodek_nazwa: 'Zielona Góra', odleglosc_km: 35 }],
      najblizsza: null,
    })
    expect(w.wariant).toBe('regula')
    expect(w.lokalizacja).toBe('okolice: Bobowicko, lubuskie')
    expect(w.tytul).toBe('Trafi do: Jan K')
    expect(w.szczegoly[1]).toContain('Zielona Góra')
  })
  it('wariant CC bez reguły i z nieznanym kodem', () => {
    const b = opisWynikuKodu({
      kod: '64-920',
      znany: true,
      miejscowosc: 'Piła',
      wojewodztwo: 'wielkopolskie',
      wynik: 'cc',
      najblizsza: { kolejnosc: 1, srodek_nazwa: 'Gorzów', odleglosc_km: 111 },
    })
    expect(b.wariant).toBe('cc_brak_reguly')
    expect(b.szczegoly[0]).toContain('reguła 1, 111 km')
    const n = opisWynikuKodu({ kod: '99-999', znany: false, wynik: 'cc' })
    expect(n.wariant).toBe('cc_nieznany')
    expect(n.szczegoly[0]).toContain('99-999')
    expect(opisWynikuKodu(null)).toBeNull()
  })
})

describe('kontrola i walidacja', () => {
  it('kontrola handlowca ma dwie linie', () => {
    const k = kontrolaHandlowca({ ma_numer: true, ma_linie_leady: false })
    expect(k).toHaveLength(2)
    expect(k[0].ok).toBe(true)
    expect(k[1].tekst).toContain('wyłączony')
    expect(kontrolaHandlowca(null)).toEqual([])
  })
  it('walidacja formularza', () => {
    expect(walidujFormularzReguly({ handlowiec: '', srodek_kod: 'x', promien_km: 5 })).toMatch(/handlowca/)
    expect(walidujFormularzReguly({ handlowiec: 'a', srodek_kod: '', promien_km: 5 })).toMatch(/środek/)
    expect(walidujFormularzReguly({ handlowiec: 'a', srodek_kod: 'x', promien_km: 0 })).toMatch(/promień/)
    expect(walidujFormularzReguly({ handlowiec: 'a', srodek_kod: 'x', promien_km: 10 })).toBe('')
  })
})

describe('punktKodu', () => {
  it('zwraca punkt tylko dla liczbowych współrzędnych', () => {
    expect(punktKodu({ kod: '66-200', lat: 52.1, lng: 15.2 })).toEqual({ lat: 52.1, lng: 15.2, kod: '66-200' })
    expect(punktKodu({ kod: 'x', lat: null, lng: 15 })).toBeNull()
    expect(punktKodu({ kod: 'x', lat: '52', lng: 15 })).toBeNull()
    expect(punktKodu(null)).toBeNull()
  })
})
