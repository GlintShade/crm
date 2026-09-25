import {
  ROZSZERZENIA_WIDEO,
  TYPY_PLIKOW_WIDEO,
  indeksDlaKlucza,
  jestPdf,
  jestWideo,
  nazwaPlikuZUrl,
  przesunIndeks,
  zbudujListePodgladu,
} from '@/utils/audytPodglad'

describe('jestPdf', () => {
  it('rozpoznaje URL z rozszerzeniem .pdf', () => {
    expect(jestPdf('/private/files/faktura.pdf')).toBe(true)
  })

  it('nie rozpoznaje URL z rozszerzeniem obrazu', () => {
    expect(jestPdf('/private/files/zdjecie.jpg')).toBe(false)
    expect(jestPdf('/private/files/zdjecie.png')).toBe(false)
  })

  it('odporne na wielkość liter (.PDF)', () => {
    expect(jestPdf('/private/files/FAKTURA.PDF')).toBe(true)
  })

  it('odporne na ?query po rozszerzeniu', () => {
    expect(jestPdf('/private/files/faktura.pdf?v=123')).toBe(true)
    expect(jestPdf('/private/files/zdjecie.jpg?v=123')).toBe(false)
  })

  it('odporne na #hash po rozszerzeniu', () => {
    expect(jestPdf('/private/files/faktura.pdf#page=2')).toBe(true)
  })

  it('null/undefined/pusty string -> false', () => {
    expect(jestPdf(null)).toBe(false)
    expect(jestPdf(undefined)).toBe(false)
    expect(jestPdf('')).toBe(false)
  })
})

describe('nazwaPlikuZUrl', () => {
  it('wyciąga ostatni segment ścieżki', () => {
    expect(nazwaPlikuZUrl('/private/files/rozdzielnica.jpg')).toBe('rozdzielnica.jpg')
  })

  it('obcina ?query i #hash', () => {
    expect(nazwaPlikuZUrl('/private/files/rozdzielnica.jpg?v=1')).toBe('rozdzielnica.jpg')
    expect(nazwaPlikuZUrl('/private/files/rozdzielnica.jpg#foo')).toBe('rozdzielnica.jpg')
  })

  it('dekoduje polskie znaki z URL-a', () => {
    expect(nazwaPlikuZUrl('/private/files/rozdzielni%C4%87a%20g%C5%82%C3%B3wna.jpg')).toBe(
      'rozdzielnića główna.jpg',
    )
  })

  it('gdy dekodowanie zawodzi (błędne % sekwencje), zwraca surowy segment', () => {
    expect(nazwaPlikuZUrl('/private/files/plik%.jpg')).toBe('plik%.jpg')
  })

  it('brak URL-a -> pusty string', () => {
    expect(nazwaPlikuZUrl(null)).toBe('')
    expect(nazwaPlikuZUrl(undefined)).toBe('')
    expect(nazwaPlikuZUrl('')).toBe('')
  })
})

describe('jestWideo', () => {
  it.each(['mp4', 'mov', 'webm', 'm4v'])('rozpoznaje rozszerzenie .%s', (rozszerzenie) => {
    expect(jestWideo(`/private/files/nagranie.${rozszerzenie}`)).toBe(true)
  })

  it('odporne na wielkość liter (.MP4, .MOV)', () => {
    expect(jestWideo('/private/files/NAGRANIE.MP4')).toBe(true)
    expect(jestWideo('/private/files/NAGRANIE.MOV')).toBe(true)
  })

  it('odporne na ?query po rozszerzeniu', () => {
    expect(jestWideo('/private/files/nagranie.mp4?v=123')).toBe(true)
  })

  it('odporne na #hash po rozszerzeniu', () => {
    expect(jestWideo('/private/files/nagranie.webm#t=5')).toBe(true)
  })

  it('nie rozpoznaje obrazu ani PDF-a', () => {
    expect(jestWideo('/private/files/zdjecie.jpg')).toBe(false)
    expect(jestWideo('/private/files/zdjecie.png')).toBe(false)
    expect(jestWideo('/private/files/faktura.pdf')).toBe(false)
  })

  it('nie daje się zmylić rozszerzeniem wideo w środku nazwy', () => {
    expect(jestWideo('/private/files/film.mp4.jpg')).toBe(false)
  })

  it('null/undefined/pusty string -> false', () => {
    expect(jestWideo(null)).toBe(false)
    expect(jestWideo(undefined)).toBe(false)
    expect(jestWideo('')).toBe(false)
  })
})

describe('TYPY_PLIKOW_WIDEO', () => {
  it('nie zawiera wpisu video/* (celowo, żeby nie dopuszczać wszystkich formatów wideo)', () => {
    expect(TYPY_PLIKOW_WIDEO).not.toContain('video/*')
  })

  it('zawiera kropka-rozszerzenie dla każdego wpisu z ROZSZERZENIA_WIDEO', () => {
    for (const rozszerzenie of ROZSZERZENIA_WIDEO) {
      expect(TYPY_PLIKOW_WIDEO).toContain(`.${rozszerzenie}`)
    }
  })
})

describe('zbudujListePodgladu', () => {
  it('zachowuje kolejność wejściową i pomija PDF-y oraz puste sloty', () => {
    const wejscie = [
      { klucz: 'a', url: '/private/files/a.jpg', etykieta: 'A' },
      { klucz: 'b', url: null, etykieta: 'B' },
      { klucz: 'c', url: '/private/files/c.pdf', etykieta: 'C' },
      { klucz: 'd', url: '/private/files/d.png', etykieta: 'D' },
    ]
    expect(zbudujListePodgladu(wejscie)).toEqual([
      { klucz: 'a', url: '/private/files/a.jpg', etykieta: 'A' },
      { klucz: 'd', url: '/private/files/d.png', etykieta: 'D' },
    ])
  })

  it('zachowuje wideo obok obrazu w kolejności wejściowej i pomija PDF', () => {
    const wejscie = [
      { klucz: 'a', url: '/private/files/a.jpg', etykieta: 'A' },
      { klucz: 'b', url: '/private/files/b.mp4', etykieta: 'B' },
      { klucz: 'c', url: '/private/files/c.pdf', etykieta: 'C' },
    ]
    expect(zbudujListePodgladu(wejscie)).toEqual([
      { klucz: 'a', url: '/private/files/a.jpg', etykieta: 'A' },
      { klucz: 'b', url: '/private/files/b.mp4', etykieta: 'B' },
    ])
  })

  it('nie mutuje tablicy wejściowej', () => {
    const wejscie = [
      { klucz: 'a', url: '/private/files/a.jpg', etykieta: 'A' },
      { klucz: 'b', url: '/private/files/b.pdf', etykieta: 'B' },
    ]
    const kopia = JSON.parse(JSON.stringify(wejscie))
    zbudujListePodgladu(wejscie)
    expect(wejscie).toEqual(kopia)
  })

  it('zwraca nową tablicę, nie referencję do wejścia', () => {
    const wejscie = [{ klucz: 'a', url: '/private/files/a.jpg', etykieta: 'A' }]
    expect(zbudujListePodgladu(wejscie)).not.toBe(wejscie)
  })

  it('lista pusta -> pusta tablica', () => {
    expect(zbudujListePodgladu([])).toEqual([])
  })

  it('null/undefined -> pusta tablica', () => {
    expect(zbudujListePodgladu(null)).toEqual([])
    expect(zbudujListePodgladu(undefined)).toEqual([])
  })

  it('lista złożona wyłącznie z PDF-ów -> pusta tablica', () => {
    expect(
      zbudujListePodgladu([{ klucz: 'a', url: '/private/files/a.pdf', etykieta: 'A' }]),
    ).toEqual([])
  })
})

describe('indeksDlaKlucza', () => {
  const lista = [
    { klucz: 'a', url: '/x/a.jpg', etykieta: 'A' },
    { klucz: 'b', url: '/x/b.jpg', etykieta: 'B' },
    { klucz: 'c', url: '/x/c.jpg', etykieta: 'C' },
  ]

  it('zwraca indeks pozycji o danym kluczu', () => {
    expect(indeksDlaKlucza(lista, 'b')).toBe(1)
  })

  it('zwraca -1 dla nieistniejącego klucza', () => {
    expect(indeksDlaKlucza(lista, 'nie-ma-takiego')).toBe(-1)
  })

  it('pusta lista -> -1', () => {
    expect(indeksDlaKlucza([], 'a')).toBe(-1)
  })

  it('null/undefined lista -> -1', () => {
    expect(indeksDlaKlucza(null, 'a')).toBe(-1)
    expect(indeksDlaKlucza(undefined, 'a')).toBe(-1)
  })
})

describe('przesunIndeks', () => {
  it('przesuwa w prawo w środku listy', () => {
    expect(przesunIndeks(1, 5, 1)).toBe(2)
  })

  it('przesuwa w lewo w środku listy', () => {
    expect(przesunIndeks(2, 5, -1)).toBe(1)
  })

  it('zawija z ostatniej pozycji na pierwszą (w prawo)', () => {
    expect(przesunIndeks(4, 5, 1)).toBe(0)
  })

  it('zawija z pierwszej pozycji na ostatnią (w lewo)', () => {
    expect(przesunIndeks(0, 5, -1)).toBe(4)
  })

  it('lista jednoelementowa zawija na samą siebie w obie strony', () => {
    expect(przesunIndeks(0, 1, 1)).toBe(0)
    expect(przesunIndeks(0, 1, -1)).toBe(0)
  })

  it('długość <= 0 -> zawsze 0', () => {
    expect(przesunIndeks(0, 0, 1)).toBe(0)
    expect(przesunIndeks(3, -1, -1)).toBe(0)
  })
})
