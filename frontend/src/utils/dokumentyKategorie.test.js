import { grupujDokumenty } from './dokumentyKategorie'

describe('grupujDokumenty', () => {
  it('puste wejście → []', () => {
    expect(grupujDokumenty([], [])).toEqual([])
    expect(grupujDokumenty([], ['Wzory umów'])).toEqual([])
  })

  it('kolejność wg kategorie, nie wg pierwszego wystąpienia w dokumenty', () => {
    const dokumenty = [
      { name: 'a', kategoria: 'Formularze' },
      { name: 'b', kategoria: 'Wzory umów' },
    ]
    const wynik = grupujDokumenty(dokumenty, ['Wzory umów', 'Karty katalogowe', 'Formularze'])
    expect(wynik.map((g) => g.kategoria)).toEqual(['Wzory umów', 'Formularze'])
  })

  it('puste grupy (kategoria z listy bez dokumentów) są pomijane', () => {
    const dokumenty = [{ name: 'a', kategoria: 'Formularze' }]
    const wynik = grupujDokumenty(dokumenty, ['Wzory umów', 'Karty katalogowe', 'Formularze'])
    expect(wynik).toEqual([{ kategoria: 'Formularze', dokumenty: [dokumenty[0]] }])
  })

  it('nieznana kategoria (spoza listy) trafia do grupy ""', () => {
    const dokumenty = [{ name: 'a', kategoria: 'Coś nieznanego' }]
    const wynik = grupujDokumenty(dokumenty, ['Wzory umów'])
    expect(wynik).toEqual([{ kategoria: '', dokumenty: [dokumenty[0]] }])
  })

  it('pusta kategoria ("" albo brak pola) trafia do grupy ""', () => {
    const dokumenty = [
      { name: 'a', kategoria: '' },
      { name: 'b' },
    ]
    const wynik = grupujDokumenty(dokumenty, ['Wzory umów'])
    expect(wynik).toEqual([{ kategoria: '', dokumenty }])
  })

  it('grupa "" zawsze na końcu, nawet gdy jej dokumenty poprzedzają znane kategorie na wejściu', () => {
    const dokumenty = [
      { name: 'x', kategoria: '' },
      { name: 'a', kategoria: 'Formularze' },
      { name: 'b', kategoria: 'Wzory umów' },
    ]
    const wynik = grupujDokumenty(dokumenty, ['Wzory umów', 'Formularze'])
    expect(wynik.map((g) => g.kategoria)).toEqual(['Wzory umów', 'Formularze', ''])
  })

  it('kolejność wewnątrz grupy zachowana (serwer już sortuje po kolejnosc, tytul)', () => {
    const dokumenty = [
      { name: 'b', kategoria: 'Wzory umów', kolejnosc: 120 },
      { name: 'a', kategoria: 'Wzory umów', kolejnosc: 110 },
      { name: 'c', kategoria: 'Wzory umów', kolejnosc: 130 },
    ]
    const wynik = grupujDokumenty(dokumenty, ['Wzory umów'])
    expect(wynik[0].dokumenty.map((d) => d.name)).toEqual(['b', 'a', 'c'])
  })

  it('nie mutuje wejściowych tablic/obiektów', () => {
    const dokumenty = [
      { name: 'a', kategoria: 'Formularze' },
      { name: 'b', kategoria: '' },
    ]
    const kategorie = ['Wzory umów', 'Formularze']
    const kopiaDokumentow = JSON.parse(JSON.stringify(dokumenty))
    const kopiaKategorii = [...kategorie]

    grupujDokumenty(dokumenty, kategorie)

    expect(dokumenty).toEqual(kopiaDokumentow)
    expect(kategorie).toEqual(kopiaKategorii)
  })

  it('same puste kategorie (kształt Czystego Powietrza) → jedna grupa ""', () => {
    const dokumenty = [
      { name: 'a', kategoria: '' },
      { name: 'b', kategoria: '' },
      { name: 'c', kategoria: '' },
    ]
    const wynik = grupujDokumenty(dokumenty, [])
    expect(wynik).toEqual([{ kategoria: '', dokumenty }])
  })

  it('kategorie undefined/null traktowane jak []', () => {
    const dokumenty = [{ name: 'a', kategoria: 'Formularze' }]
    expect(grupujDokumenty(dokumenty, undefined)).toEqual([{ kategoria: '', dokumenty }])
    expect(grupujDokumenty(dokumenty, null)).toEqual([{ kategoria: '', dokumenty }])
  })

  it('dokumenty undefined/null traktowane jak []', () => {
    expect(grupujDokumenty(undefined, ['Wzory umów'])).toEqual([])
    expect(grupujDokumenty(null, ['Wzory umów'])).toEqual([])
  })
})
