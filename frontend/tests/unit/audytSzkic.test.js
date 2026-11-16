import { describe, expect, it } from 'vitest'
import {
  frazaBrakow,
  licznikSekcji,
  licznikZdjec,
  odmianaZdjec,
  podsumowanieSzkicu,
  podtytulSekcji,
  poleWypelnione,
  procentPostepu,
  stanPolaAudytu,
  stanZdjecia,
  wartoscWyswietlana,
  znacznikPola,
} from '@/utils/audytSzkic'

const tekst = { fieldname: 'a', label: 'A', type: 'select', required: 1 }
const liczba = { fieldname: 'm', label: 'M', type: 'number', required: 1, rule: 'positive' }
const opcja = { fieldname: 'uwagi', label: 'Uwagi', type: 'textarea', required: 0 }

describe('poleWypelnione', () => {
  it('tekst: niepusty', () => {
    expect(poleWypelnione(tekst, '')).toBe(false)
    expect(poleWypelnione(tekst, '  ')).toBe(false)
    expect(poleWypelnione(tekst, undefined)).toBe(false)
    expect(poleWypelnione(tekst, 'Tak')).toBe(true)
  })
  it('positive: wiekszy od zera', () => {
    expect(poleWypelnione(liczba, 0)).toBe(false)
    expect(poleWypelnione(liczba, '0')).toBe(false)
    expect(poleWypelnione(liczba, '')).toBe(false)
    expect(poleWypelnione(liczba, '12.5')).toBe(true)
  })
})

describe('wartoscWyswietlana', () => {
  it('zapisane 0 w polu positive jest puste, dopoki nie edytowane', () => {
    expect(wartoscWyswietlana(liczba, 0, new Set())).toBe('')
    expect(wartoscWyswietlana(liczba, '0', new Set())).toBe('')
    expect(wartoscWyswietlana(liczba, '0.00', undefined)).toBe('')
  })
  it('po edycji pokazuje wpisana wartosc, takze 0', () => {
    expect(wartoscWyswietlana(liczba, '0', new Set(['m']))).toBe('0')
  })
  it('inne wartosci bez zmian', () => {
    expect(wartoscWyswietlana(liczba, 12, new Set())).toBe(12)
    expect(wartoscWyswietlana(liczba, '', new Set())).toBe('')
    expect(wartoscWyswietlana(tekst, 'Tak', new Set())).toBe('Tak')
    expect(wartoscWyswietlana(liczba, null, new Set())).toBe('')
  })
  it('pole bez reguly positive: 0 zostaje', () => {
    const f = { fieldname: 'x', type: 'number', required: 0 }
    expect(wartoscWyswietlana(f, 0, new Set())).toBe(0)
  })
})

describe('stanPolaAudytu i znacznik', () => {
  it('wypelnione i opcjonalne bez stanu', () => {
    expect(stanPolaAudytu(tekst, 'Tak', false).stan).toBe('')
    expect(stanPolaAudytu(opcja, '', true).stan).toBe('')
  })
  it('brak: niebieski, po probie czerwony z komunikatem', () => {
    expect(stanPolaAudytu(tekst, '', false)).toEqual({ stan: 'brak', komunikat: '' })
    expect(stanPolaAudytu(liczba, 0, true)).toEqual({ stan: 'blad', komunikat: 'Uzupełnij to pole' })
  })
  it('znacznik opcjonalne tylko dla niewymaganych', () => {
    expect(znacznikPola(tekst)).toBe('')
    expect(znacznikPola(opcja)).toBe('opcjonalne')
  })
})

describe('sekcje', () => {
  it('podtytul', () => {
    expect(podtytulSekcji([tekst, liczba])).toBe('Wszystkie pola są wymagane.')
    expect(podtytulSekcji([tekst, opcja])).toBe('Wszystkie pola są wymagane, poza oznaczonymi jako opcjonalne.')
    expect(podtytulSekcji([opcja])).toBe('')
  })
  it('licznik', () => {
    expect(licznikSekcji([opcja], {}, false)).toBeNull()
    expect(licznikSekcji([tekst, liczba], { a: 'x', m: 3 }, false)).toEqual({ liczba: 0, stan: 'komplet' })
    expect(licznikSekcji([tekst, liczba], { a: '', m: 0 }, false)).toEqual({ liczba: 2, stan: 'brak' })
    expect(licznikSekcji([tekst, liczba], { a: '', m: 0 }, true)).toEqual({ liczba: 2, stan: 'blad' })
  })
  it('licznik zdjec i stan zdjecia', () => {
    const sloty = [{ key: 'a' }, { key: 'b' }]
    expect(licznikZdjec(sloty, { a: 'u' }, false)).toEqual({ liczba: 1, stan: 'brak' })
    expect(licznikZdjec(sloty, { a: 'u', b: 'v' }, true)).toEqual({ liczba: 0, stan: 'komplet' })
    expect(stanZdjecia(true, null, false)).toBe('brak')
    expect(stanZdjecia(true, null, true)).toBe('blad')
    expect(stanZdjecia(true, 'u', true)).toBe('')
    expect(stanZdjecia(false, null, true)).toBe('')
  })
})

describe('odmiana i fraza', () => {
  it('zdjecia', () => {
    expect(odmianaZdjec(1, 'biernik')).toBe('zdjęcie')
    expect(odmianaZdjec(2, 'biernik')).toBe('zdjęcia')
    expect(odmianaZdjec(5, 'biernik')).toBe('zdjęć')
    expect(odmianaZdjec(12, 'biernik')).toBe('zdjęć')
    expect(odmianaZdjec(22, 'biernik')).toBe('zdjęcia')
    expect(odmianaZdjec(1, 'dopelniacz')).toBe('zdjęcia')
    expect(odmianaZdjec(3, 'dopelniacz')).toBe('zdjęć')
  })
  it('fraza', () => {
    expect(frazaBrakow(6, 3, 'dopelniacz')).toBe('6 pól i 3 zdjęć')
    expect(frazaBrakow(6, 3, 'biernik')).toBe('6 pól i 3 zdjęcia')
    expect(frazaBrakow(1, 0, 'dopelniacz')).toBe('1 pola')
    expect(frazaBrakow(0, 1, 'biernik')).toBe('1 zdjęcie')
    expect(frazaBrakow(2, 1, 'biernik')).toBe('2 pola i 1 zdjęcie')
  })
})

describe('podsumowanieSzkicu', () => {
  const sekcje = [
    { label: 'S1', fields: [tekst, liczba] },
    { label: 'Uwagi', fields: [opcja] },
    { label: 'S3', fields: [{ ...tekst, fieldname: 'b' }] },
  ]
  const sloty = [{ key: 'f1' }, { key: 'f2' }]
  it('liczy braki i wskazuje pierwszy', () => {
    const r = podsumowanieSzkicu(sekcje, sloty, { a: 'x', m: 0, b: '' }, { f1: 'u' }, 'Dokumentacja zdjęciowa')
    expect(r.pola).toBe(2)
    expect(r.zdjecia).toBe(1)
    expect(r.sekcje).toEqual([
      { label: 'S1', liczba: 1 },
      { label: 'S3', liczba: 1 },
      { label: 'Dokumentacja zdjęciowa', liczba: 1 },
    ])
    expect(r.pierwszy).toEqual({ typ: 'pole', klucz: 'm' })
  })
  it('gdy brakuje tylko zdjec, pierwszy to zdjecie', () => {
    const r = podsumowanieSzkicu(sekcje, sloty, { a: 'x', m: 2, b: 'y' }, {}, 'Z')
    expect(r.pola).toBe(0)
    expect(r.pierwszy).toEqual({ typ: 'zdjecie', klucz: 'f1' })
  })
  it('komplet', () => {
    const r = podsumowanieSzkicu(sekcje, sloty, { a: 'x', m: 2, b: 'y' }, { f1: 'u', f2: 'v' }, 'Z')
    expect(r).toEqual({ pola: 0, zdjecia: 0, sekcje: [], pierwszy: null })
  })
})

describe('procentPostepu', () => {
  it('liczy razem', () => {
    expect(procentPostepu(5, 11, 1, 4)).toBe(40)
    expect(procentPostepu(0, 0, 0, 0)).toBe(0)
    expect(procentPostepu(11, 11, 4, 4)).toBe(100)
  })
})
