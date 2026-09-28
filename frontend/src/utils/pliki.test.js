import { beforeEach, describe, expect, it } from 'vitest'
import {
  IKONA_DOKUMENT,
  IKONA_INNY,
  IKONA_OBRAZ,
  IKONA_PDF,
  IKONA_WIDEO,
  KIERUNKI_SORTU,
  TRYBY,
  TRYB_DOKUMENTY,
  TRYB_MEDIA,
  TRYB_WSZYSTKO,
  dlaPodgladu,
  filtrujTryb,
  filtrujZrodla,
  formatujRozmiar,
  ikonaDla,
  liczbyZrodelPoTrybie,
  sortuj,
  wczytajUstawienia,
  zapiszUstawienia,
} from './pliki'

function wiersz(nadpisania = {}) {
  return {
    klucz: 'FILE-1',
    file_name: 'plik.pdf',
    file_url: '/files/plik.pdf',
    file_size: 1024,
    file_type: 'application/pdf',
    kategoria: 'dokument',
    zrodlo: 'luzem',
    zrodlo_etykieta: 'Luzem',
    zakladka: 'attachments',
    autor: 'a@example.com',
    autor_nazwa: 'Anna Testowa',
    data: '2026-09-20 10:00:00',
    mozna_zmienic_nazwe: false,
    mozna_usunac: true,
    is_private: 1,
    ...nadpisania,
  }
}

describe('TRYBY', () => {
  it('trzy tryby przełącznika, Dokumenty pierwszy (domyślny)', () => {
    expect(TRYBY).toEqual([TRYB_DOKUMENTY, TRYB_MEDIA, TRYB_WSZYSTKO])
  })
})

describe('filtrujTryb', () => {
  const dok = wiersz({ klucz: 'DOK', kategoria: 'dokument' })
  const inny = wiersz({ klucz: 'INNY', kategoria: 'inny' })
  const obraz = wiersz({ klucz: 'OBRAZ', kategoria: 'obraz' })
  const wideo = wiersz({ klucz: 'WIDEO', kategoria: 'wideo' })
  const wszystkieWiersze = [dok, inny, obraz, wideo]

  it('tryb "dokumenty" = kategoria dokument oraz inny', () => {
    const wynik = filtrujTryb(wszystkieWiersze, TRYB_DOKUMENTY)
    expect(wynik.map((w) => w.klucz).sort()).toEqual(['DOK', 'INNY'])
  })

  it('tryb "media" = kategoria obraz oraz wideo', () => {
    const wynik = filtrujTryb(wszystkieWiersze, TRYB_MEDIA)
    expect(wynik.map((w) => w.klucz).sort()).toEqual(['OBRAZ', 'WIDEO'])
  })

  it('tryb "wszystko" nie filtruje niczego', () => {
    expect(filtrujTryb(wszystkieWiersze, TRYB_WSZYSTKO)).toHaveLength(4)
  })

  it('nieznany/pusty tryb spada bezpiecznie na "wszystko" (nigdy nie chowa całego feedu)', () => {
    expect(filtrujTryb(wszystkieWiersze, undefined)).toHaveLength(4)
    expect(filtrujTryb(wszystkieWiersze, 'literowka')).toHaveLength(4)
  })

  it('wejście nie-tablicowe daje pustą listę', () => {
    expect(filtrujTryb(null, TRYB_WSZYSTKO)).toEqual([])
  })
})

describe('filtrujZrodla', () => {
  const a = wiersz({ klucz: 'A', zrodlo: 'faktura' })
  const b = wiersz({ klucz: 'B', zrodlo: 'luzem' })
  const c = wiersz({ klucz: 'C', zrodlo: 'komentarz' })

  it('pokazuje tylko wiersze, których zrodlo jest zaznaczone', () => {
    const wynik = filtrujZrodla([a, b, c], ['faktura', 'komentarz'])
    expect(wynik.map((w) => w.klucz)).toEqual(['A', 'C'])
  })

  it('pusty wybór daje pusty wynik (nie "pokaż wszystko")', () => {
    expect(filtrujZrodla([a, b, c], [])).toEqual([])
  })

  it('przyjmuje Set tak samo jak tablicę', () => {
    const wynik = filtrujZrodla([a, b, c], new Set(['luzem']))
    expect(wynik.map((w) => w.klucz)).toEqual(['B'])
  })
})

describe('liczbyZrodelPoTrybie', () => {
  const wiersze = [
    wiersz({ klucz: '1', kategoria: 'dokument', zrodlo: 'faktura' }),
    wiersz({ klucz: '2', kategoria: 'dokument', zrodlo: 'faktura' }),
    wiersz({ klucz: '3', kategoria: 'obraz', zrodlo: 'audyt_slot' }),
    wiersz({ klucz: '4', kategoria: 'obraz', zrodlo: 'faktura' }),
  ]

  it('liczy tylko wiersze widoczne w danym trybie', () => {
    expect(liczbyZrodelPoTrybie(wiersze, TRYB_DOKUMENTY)).toEqual({ faktura: 2 })
    expect(liczbyZrodelPoTrybie(wiersze, TRYB_MEDIA)).toEqual({ audyt_slot: 1, faktura: 1 })
    expect(liczbyZrodelPoTrybie(wiersze, TRYB_WSZYSTKO)).toEqual({ faktura: 3, audyt_slot: 1 })
  })

  it('pusta lista daje pusty obiekt liczników', () => {
    expect(liczbyZrodelPoTrybie([], TRYB_WSZYSTKO)).toEqual({})
  })
})

describe('ikonaDla', () => {
  it('PDF dostaje własną ikonę, mimo że kategoria to "dokument"', () => {
    expect(ikonaDla(wiersz({ file_name: 'umowa.pdf', kategoria: 'dokument' }))).toBe(IKONA_PDF)
  })

  it('rozpoznaje PDF po rozszerzeniu, nie po file_type (bywa puste)', () => {
    expect(
      ikonaDla(wiersz({ file_name: 'skan.pdf', file_type: '', kategoria: 'dokument' })),
    ).toBe(IKONA_PDF)
  })

  it('dokument nie-PDF dostaje ikonę dokumentu', () => {
    expect(ikonaDla(wiersz({ file_name: 'raport.docx', kategoria: 'dokument' }))).toBe(
      IKONA_DOKUMENT,
    )
  })

  it('obraz i wideo dostają swoje klucze', () => {
    expect(ikonaDla(wiersz({ file_name: 'zdjecie.jpg', kategoria: 'obraz' }))).toBe(IKONA_OBRAZ)
    expect(ikonaDla(wiersz({ file_name: 'film.mp4', kategoria: 'wideo' }))).toBe(IKONA_WIDEO)
  })

  it('kategoria "inny" i wejście puste dają ikonę "inny"', () => {
    expect(ikonaDla(wiersz({ file_name: 'dane.xyz', kategoria: 'inny' }))).toBe(IKONA_INNY)
    expect(ikonaDla(null)).toBe(IKONA_INNY)
  })
})

describe('formatujRozmiar', () => {
  it('bajty poniżej 1024 zostają w B, bez miejsc po przecinku', () => {
    expect(formatujRozmiar(512)).toBe('512 B')
    expect(formatujRozmiar(0)).toBe('0 B')
  })

  it('kolejne jednostki z dwoma miejscami po przecinku', () => {
    expect(formatujRozmiar(2048)).toBe('2.00 KB')
    expect(formatujRozmiar(1024 * 1024 * 3)).toBe('3.00 MB')
  })

  it('wejście niepoprawne/ujemne/NaN daje "0 B" zamiast rzucać', () => {
    expect(formatujRozmiar(null)).toBe('0 B')
    expect(formatujRozmiar(undefined)).toBe('0 B')
    expect(formatujRozmiar(-5)).toBe('0 B')
    expect(formatujRozmiar('nie liczba')).toBe('0 B')
  })
})

describe('dlaPodgladu', () => {
  it('zawęża do obrazów i wideo, w kształcie {klucz, url, etykieta}', () => {
    const wiersze = [
      wiersz({ klucz: 'PDF', kategoria: 'dokument', file_url: '/f/a.pdf' }),
      wiersz({ klucz: 'IMG', kategoria: 'obraz', file_url: '/f/b.jpg', file_name: 'b.jpg' }),
      wiersz({ klucz: 'VID', kategoria: 'wideo', file_url: '/f/c.mp4', file_name: 'c.mp4' }),
    ]
    expect(dlaPodgladu(wiersze)).toEqual([
      { klucz: 'IMG', url: '/f/b.jpg', etykieta: 'b.jpg' },
      { klucz: 'VID', url: '/f/c.mp4', etykieta: 'c.mp4' },
    ])
  })

  it('pomija wiersze bez file_url', () => {
    expect(dlaPodgladu([wiersz({ kategoria: 'obraz', file_url: '' })])).toEqual([])
  })

  it('wejście nie-tablicowe daje pustą listę', () => {
    expect(dlaPodgladu(null)).toEqual([])
  })
})

describe('sortuj', () => {
  it('domyślnie od najnowszych (malejąco po polu data)', () => {
    const wiersze = [
      wiersz({ klucz: 'STARY', data: '2026-01-01 10:00:00' }),
      wiersz({ klucz: 'NOWY', data: '2026-09-01 10:00:00' }),
    ]
    expect(sortuj(wiersze).map((w) => w.klucz)).toEqual(['NOWY', 'STARY'])
  })

  it('od najstarszych, rosnąco, gdy kierunek to KIERUNKI_SORTU.NAJSTARSZE', () => {
    const wiersze = [
      wiersz({ klucz: 'NOWY', data: '2026-09-01 10:00:00' }),
      wiersz({ klucz: 'STARY', data: '2026-01-01 10:00:00' }),
    ]
    expect(sortuj(wiersze, KIERUNKI_SORTU.NAJSTARSZE).map((w) => w.klucz)).toEqual([
      'STARY',
      'NOWY',
    ])
  })

  it('nie mutuje wejścia', () => {
    const wiersze = [wiersz({ klucz: 'A', data: '2026-01-01' }), wiersz({ klucz: 'B', data: '2026-02-01' })]
    const kopia = [...wiersze]
    sortuj(wiersze)
    expect(wiersze).toEqual(kopia)
  })
})

describe('wczytajUstawienia / zapiszUstawienia', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('bez zapisu w localStorage domyślnie zaznacza wszystkie dostępne klucze, sort najnowsze', () => {
    const wynik = wczytajUstawienia(['faktura', 'luzem'])
    expect(wynik).toEqual({ zaznaczone: ['faktura', 'luzem'], kierunek: KIERUNKI_SORTU.NAJNOWSZE })
  })

  it('zapiszUstawienia, potem wczytajUstawienia odzyskuje ten sam wybór (przeżywa "przeładowanie")', () => {
    zapiszUstawienia(['faktura'], KIERUNKI_SORTU.NAJSTARSZE)
    const wynik = wczytajUstawienia(['faktura', 'luzem', 'audyt_slot'])
    expect(wynik).toEqual({ zaznaczone: ['faktura'], kierunek: KIERUNKI_SORTU.NAJSTARSZE })
  })

  it('klucze zapisane wcześniej, których już nie ma w kluczeDostepne, są przycinane', () => {
    zapiszUstawienia(['faktura', 'zniknelo'], KIERUNKI_SORTU.NAJNOWSZE)
    const wynik = wczytajUstawienia(['faktura', 'luzem'])
    expect(wynik.zaznaczone).toEqual(['faktura'])
  })

  it('pusty wybór po przycięciu wraca do domyślnego (wszystkie dostępne)', () => {
    zapiszUstawienia(['zniknelo'], KIERUNKI_SORTU.NAJNOWSZE)
    const wynik = wczytajUstawienia(['faktura', 'luzem'])
    expect(wynik.zaznaczone).toEqual(['faktura', 'luzem'])
  })

  it('JSON uszkodzony w localStorage nie rzuca, spada na domyślny stan', () => {
    localStorage.setItem('pliki-filtr', '{niepoprawny json')
    const wynik = wczytajUstawienia(['faktura'])
    expect(wynik).toEqual({ zaznaczone: ['faktura'], kierunek: KIERUNKI_SORTU.NAJNOWSZE })
  })

  it('klucz localStorage jest własny ("pliki-filtr"), nie koliduje z "notatki-filtr"', () => {
    localStorage.setItem('notatki-filtr', JSON.stringify({ zaznaczone: ['cos-innego'], kierunek: 'asc' }))
    const wynik = wczytajUstawienia(['faktura', 'luzem'])
    expect(wynik).toEqual({ zaznaczone: ['faktura', 'luzem'], kierunek: KIERUNKI_SORTU.NAJNOWSZE })
  })
})
