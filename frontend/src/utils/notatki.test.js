import { beforeEach, describe, expect, it } from 'vitest'
import {
  ETYKIETY_ZRODEL,
  KIERUNKI_SORTU,
  OZE_RODZAJE,
  TYPY_PLIKOW_NOTATKI,
  ZAKLADKI,
  czyOze,
  etykietaDnia,
  etykietaZakladki,
  filtrujFeed,
  grupujPoDniu,
  nazwaAutora,
  plikiDoPodgladu,
  podzielPliki,
  sortujFeed,
  typyDla,
  wczytajFiltr,
  zapiszFiltr,
} from './notatki'

describe('ZAKLADKI', () => {
  it('zna wszystkie osiem zakładek strumienia notatek', () => {
    expect(Object.keys(ZAKLADKI).sort()).toEqual(
      ['Dotacja', 'Faktury', 'Kredyt', 'Montaz', 'OSD', 'Trify', 'Umowa', 'Zestaw'].sort(),
    )
  })

  it('każda zakładka ma etykietę, niepustą listę typów, placeholder i tekst pusty', () => {
    for (const [klucz, konfig] of Object.entries(ZAKLADKI)) {
      expect(konfig.etykieta, klucz).toBeTruthy()
      expect(Array.isArray(konfig.typy), klucz).toBe(true)
      expect(konfig.typy.length, klucz).toBeGreaterThan(0)
      expect(konfig.placeholder, klucz).toBeTruthy()
      expect(konfig.pusty, klucz).toBeTruthy()
    }
  })
})

describe('typyDla', () => {
  it('zwraca bazowy zestaw typów dla Zestaw/Umowa/Kredyt/Faktury/OSD/Dotacja', () => {
    const baza = ['Notatka', 'Telefon', 'Wizyta', 'Ustalenie', 'Problem', 'Dokument']
    for (const zakladka of ['Zestaw', 'Umowa', 'Kredyt', 'Faktury', 'OSD', 'Dotacja']) {
      expect(typyDla(zakladka), zakladka).toEqual(baza)
    }
  })

  it('Montaż dokłada "Termin montażu" na końcu bazowego zestawu', () => {
    expect(typyDla('Montaz')).toEqual([
      'Notatka',
      'Telefon',
      'Wizyta',
      'Ustalenie',
      'Problem',
      'Dokument',
      'Termin montażu',
    ])
  })

  it('Trify ma własny, odrębny zestaw typów', () => {
    expect(typyDla('Trify')).toEqual([
      'Notatka',
      'Wniosek Trify',
      'Decyzja Trify',
      'Umowa Trify',
      'Wypłata Trify',
      'Problem',
    ])
  })

  it('zwraca pustą tablicę dla nieznanej zakładki', () => {
    expect(typyDla('CośNieistniejącego')).toEqual([])
    expect(typyDla(undefined)).toEqual([])
  })
})

describe('etykietaZakladki', () => {
  it('zwraca polską etykietę znanej zakładki', () => {
    expect(etykietaZakladki('Zestaw')).toBe('Zestaw')
    expect(etykietaZakladki('Montaz')).toBe('Montaż')
  })

  it('dla nieznanego klucza zwraca sam klucz, nigdy pusty string', () => {
    expect(etykietaZakladki('Cokolwiek')).toBe('Cokolwiek')
  })

  it('dla braku klucza zwraca pusty string, nie undefined/null', () => {
    expect(etykietaZakladki(undefined)).toBe('')
    expect(etykietaZakladki(null)).toBe('')
    expect(etykietaZakladki('')).toBe('')
  })
})

describe('TYPY_PLIKOW_NOTATKI', () => {
  it('zawiera MIME plus kropka-rozszerzenie dla PDF i obrazów, nigdy samo image/*', () => {
    expect(TYPY_PLIKOW_NOTATKI).toEqual([
      'application/pdf',
      'image/jpeg',
      'image/png',
      'image/webp',
      '.pdf',
      '.jpg',
      '.jpeg',
      '.png',
      '.webp',
    ])
    expect(TYPY_PLIKOW_NOTATKI).not.toContain('image/*')
  })
})

describe('podzielPliki', () => {
  it('rozdziela pliki na dokumenty i obrazy po rozszerzeniu nazwy', () => {
    const pliki = [
      { name: 'f1', file_name: 'umowa.pdf', file_url: '/files/umowa.pdf' },
      { name: 'f2', file_name: 'zdjecie.jpg', file_url: '/files/zdjecie.jpg' },
      { name: 'f3', file_name: 'plan.PNG', file_url: '/files/plan.PNG' },
      { name: 'f4', file_name: 'skan.webp', file_url: '/files/skan.webp' },
    ]
    const { dokumenty, obrazy } = podzielPliki(pliki)
    expect(dokumenty.map((p) => p.name)).toEqual(['f1'])
    expect(obrazy.map((p) => p.name)).toEqual(['f2', 'f3', 'f4'])
  })

  it('rozpoznaje rozszerzenie z file_url, gdy file_name brak', () => {
    const pliki = [{ name: 'f1', file_url: '/private/files/notatka.jpeg?x=1' }]
    const { obrazy } = podzielPliki(pliki)
    expect(obrazy.map((p) => p.name)).toEqual(['f1'])
  })

  it('traktuje nieznane/brakujące rozszerzenie jako dokument, nie obraz', () => {
    const pliki = [
      { name: 'f1', file_name: 'bez_rozszerzenia' },
      { name: 'f2', file_name: 'archiwum.zip' },
    ]
    const { dokumenty, obrazy } = podzielPliki(pliki)
    expect(dokumenty.map((p) => p.name)).toEqual(['f1', 'f2'])
    expect(obrazy).toEqual([])
  })

  it('zachowuje kolejność wejściową w obu listach i nie mutuje wejścia', () => {
    const pliki = [
      { name: 'a', file_name: 'a.jpg' },
      { name: 'b', file_name: 'b.pdf' },
      { name: 'c', file_name: 'c.png' },
    ]
    const kopiaPrzed = JSON.stringify(pliki)
    const { dokumenty, obrazy } = podzielPliki(pliki)
    expect(obrazy.map((p) => p.name)).toEqual(['a', 'c'])
    expect(dokumenty.map((p) => p.name)).toEqual(['b'])
    expect(JSON.stringify(pliki)).toBe(kopiaPrzed)
  })

  it('dla braku/niepoprawnego wejścia zwraca dwie puste listy', () => {
    expect(podzielPliki(undefined)).toEqual({ dokumenty: [], obrazy: [] })
    expect(podzielPliki(null)).toEqual({ dokumenty: [], obrazy: [] })
    expect(podzielPliki([null, undefined])).toEqual({ dokumenty: [], obrazy: [] })
  })
})

describe('plikiDoPodgladu', () => {
  it('mapuje obrazy na kształt {klucz, url, etykieta}, pomijając wiersze bez name/file_url', () => {
    const obrazy = [
      { name: 'f2', file_name: 'zdjecie.jpg', file_url: '/files/zdjecie.jpg' },
      { name: '', file_name: 'brak_name.jpg', file_url: '/files/brak_name.jpg' },
      { name: 'f3', file_name: 'plan.png', file_url: '' },
    ]
    expect(plikiDoPodgladu(obrazy)).toEqual([
      { klucz: 'f2', url: '/files/zdjecie.jpg', etykieta: 'zdjecie.jpg' },
    ])
  })

  it('dla pustej listy zwraca pustą listę', () => {
    expect(plikiDoPodgladu([])).toEqual([])
  })
})

describe('nazwaAutora', () => {
  const getUser = (email) => {
    if (email === 'znany@proenergy.pro') return { full_name: 'Jan Kowalski' }
    if (email === 'bez_nazwiska@proenergy.pro') return { full_name: '' }
    return null
  }

  it('preferuje autor_nazwa z API, gdy jest obecne', () => {
    expect(nazwaAutora({ autor_nazwa: 'Anna Nowak', owner: 'znany@proenergy.pro' }, getUser)).toBe(
      'Anna Nowak',
    )
  })

  it('spada na getUser(owner).full_name, gdy autor_nazwa brak', () => {
    expect(nazwaAutora({ owner: 'znany@proenergy.pro' }, getUser)).toBe('Jan Kowalski')
  })

  it('spada ostatecznie na sam e-mail (owner), gdy nic innego nie ma', () => {
    expect(nazwaAutora({ owner: 'nieznany@proenergy.pro' }, getUser)).toBe('nieznany@proenergy.pro')
    expect(nazwaAutora({ owner: 'bez_nazwiska@proenergy.pro' }, getUser)).toBe(
      'bez_nazwiska@proenergy.pro',
    )
  })

  it('zwraca pusty string dla braku wpisu, nie rzuca wyjątku', () => {
    expect(nazwaAutora(null, getUser)).toBe('')
    expect(nazwaAutora(undefined, getUser)).toBe('')
  })

  it('działa bez getUser (nie jest funkcją)', () => {
    expect(nazwaAutora({ owner: 'ktos@proenergy.pro' }, undefined)).toBe('ktos@proenergy.pro')
  })
})

describe('OZE_RODZAJE / czyOze', () => {
  it('rozpoznaje dokładnie trzy rodzaje OZE', () => {
    expect(OZE_RODZAJE.size).toBe(3)
    expect(czyOze('Fotowoltaika')).toBe(true)
    expect(czyOze('Fotowoltaika + Magazyn')).toBe(true)
    expect(czyOze('Magazyn energii')).toBe(true)
  })

  it('odrzuca Czyste Powietrze i wartości puste/nieznane', () => {
    expect(czyOze('Czyste Powietrze')).toBe(false)
    expect(czyOze('')).toBe(false)
    expect(czyOze(undefined)).toBe(false)
    expect(czyOze(null)).toBe(false)
  })
})

describe('ETYKIETY_ZRODEL', () => {
  it('zna wszystkie dziesięć źródeł feedu (osiem zakładek plus Audyt/AudytCP)', () => {
    expect(Object.keys(ETYKIETY_ZRODEL).sort()).toEqual(
      [...Object.keys(ZAKLADKI), 'Audyt', 'AudytCP'].sort(),
    )
  })

  it('Montaż ma etykietę z ogonkiem, Audyt/AudytCP mają własne etykiety', () => {
    expect(ETYKIETY_ZRODEL.Montaz).toBe('Montaż')
    expect(ETYKIETY_ZRODEL.Audyt).toBe('Audyt')
    expect(ETYKIETY_ZRODEL.AudytCP).toBe('Audyt CP')
  })
})

describe('KIERUNKI_SORTU', () => {
  it('ma dokładnie dwie wartości, zgodne z backendowym posortuj()', () => {
    expect(KIERUNKI_SORTU.NAJNOWSZE).toBe('desc')
    expect(KIERUNKI_SORTU.NAJSTARSZE).toBe('asc')
  })
})

describe('etykietaDnia', () => {
  const teraz = new Date(2026, 8, 28, 15, 0, 0) // 28 wrz 2026, lokalny czas

  it('zwraca "Dziś" dla tego samego dnia kalendarzowego co `teraz`', () => {
    expect(etykietaDnia('2026-09-28 08:00:00', teraz)).toBe('Dziś')
    // Granica północy: 23:59:59 tego samego dnia to nadal "Dziś".
    expect(etykietaDnia('2026-09-28 23:59:59', teraz)).toBe('Dziś')
  })

  it('zwraca "Wczoraj" dla dnia bezpośrednio poprzedzającego `teraz`', () => {
    expect(etykietaDnia('2026-09-27 23:59:59', teraz)).toBe('Wczoraj')
    // Granica północy z drugiej strony: 00:00:00 dnia poprzedniego to
    // nadal "Wczoraj", nie "Dziś" - liczy się data, nie godzina.
    expect(etykietaDnia('2026-09-27 00:00:00', teraz)).toBe('Wczoraj')
  })

  it('zwraca pełną polską datę bez godziny dla starszych wpisów', () => {
    expect(etykietaDnia('2026-09-25 17:00:00', teraz)).toBe('pt., 25 wrz 2026')
  })

  it('zwraca pełną datę też dla dnia w przyszłości względem `teraz`', () => {
    expect(etykietaDnia('2026-09-29 09:00:00', teraz)).toBe('wt., 29 wrz 2026')
  })

  it('zwraca pusty string dla wejścia bez rozpoznawalnej daty', () => {
    expect(etykietaDnia('', teraz)).toBe('')
    expect(etykietaDnia(null, teraz)).toBe('')
    expect(etykietaDnia('nie-data', teraz)).toBe('')
  })
})

describe('grupujPoDniu', () => {
  const teraz = new Date(2026, 8, 28, 15, 0, 0)

  it('grupuje wpisy tego samego dnia razem, w kolejności napotkania', () => {
    const wpisy = [
      { klucz: 'a', data: '2026-09-28 12:00:00' },
      { klucz: 'b', data: '2026-09-28 09:00:00' },
      { klucz: 'c', data: '2026-09-27 18:00:00' },
    ]
    const grupy = grupujPoDniu(wpisy, teraz)
    expect(grupy.map((g) => g.etykieta)).toEqual(['Dziś', 'Wczoraj'])
    expect(grupy[0].wpisy.map((w) => w.klucz)).toEqual(['a', 'b'])
    expect(grupy[1].wpisy.map((w) => w.klucz)).toEqual(['c'])
  })

  it('rozdziela wpisy z dwóch stron granicy północy do różnych grup', () => {
    const wpisy = [
      { klucz: 'przed-polnoca', data: '2026-09-27 23:59:59' },
      { klucz: 'po-polnocy', data: '2026-09-28 00:00:00' },
    ]
    const grupy = grupujPoDniu(wpisy, teraz)
    expect(grupy).toHaveLength(2)
    expect(grupy[0].etykieta).toBe('Wczoraj')
    expect(grupy[0].wpisy.map((w) => w.klucz)).toEqual(['przed-polnoca'])
    expect(grupy[1].etykieta).toBe('Dziś')
    expect(grupy[1].wpisy.map((w) => w.klucz)).toEqual(['po-polnocy'])
  })

  it('zwraca pustą listę grup dla pustego wejścia', () => {
    expect(grupujPoDniu([], teraz)).toEqual([])
    expect(grupujPoDniu(undefined, teraz)).toEqual([])
  })

  it('pomija wpisy null/undefined bez rzucania', () => {
    const grupy = grupujPoDniu([null, { klucz: 'a', data: '2026-09-28 10:00:00' }, undefined], teraz)
    expect(grupy).toHaveLength(1)
    expect(grupy[0].wpisy).toEqual([{ klucz: 'a', data: '2026-09-28 10:00:00' }])
  })
})

describe('filtrujFeed', () => {
  const wpisy = [
    { klucz: 'a', zrodlo: 'Zestaw' },
    { klucz: 'b', zrodlo: 'Audyt' },
    { klucz: 'c', zrodlo: 'Umowa' },
  ]

  it('zwraca tylko wpisy z zaznaczonych źródeł', () => {
    expect(filtrujFeed(wpisy, ['Zestaw']).map((w) => w.klucz)).toEqual(['a'])
    expect(filtrujFeed(wpisy, ['Zestaw', 'Umowa']).map((w) => w.klucz)).toEqual(['a', 'c'])
  })

  it('akceptuje Set tak samo jak tablicę', () => {
    expect(filtrujFeed(wpisy, new Set(['Audyt'])).map((w) => w.klucz)).toEqual(['b'])
  })

  it('pusty wybór daje pusty wynik (nie "pokaż wszystko")', () => {
    expect(filtrujFeed(wpisy, [])).toEqual([])
    expect(filtrujFeed(wpisy, new Set())).toEqual([])
  })

  it('wszystkie źródła zaznaczone zwraca wszystkie wpisy, w tej samej kolejności', () => {
    expect(filtrujFeed(wpisy, ['Zestaw', 'Audyt', 'Umowa']).map((w) => w.klucz)).toEqual(['a', 'b', 'c'])
  })

  it('nie rzuca dla pustej/brakującej listy wpisów', () => {
    expect(filtrujFeed([], ['Zestaw'])).toEqual([])
    expect(filtrujFeed(undefined, ['Zestaw'])).toEqual([])
  })
})

describe('sortujFeed', () => {
  const wpisy = [
    { klucz: 'srodkowy', data: '2026-09-27 10:00:00' },
    { klucz: 'najnowszy', data: '2026-09-28 10:00:00' },
    { klucz: 'najstarszy', data: '2026-09-26 10:00:00' },
  ]

  it('domyślnie sortuje od najnowszych', () => {
    expect(sortujFeed(wpisy).map((w) => w.klucz)).toEqual(['najnowszy', 'srodkowy', 'najstarszy'])
  })

  it('KIERUNKI_SORTU.NAJSTARSZE sortuje rosnąco', () => {
    expect(sortujFeed(wpisy, KIERUNKI_SORTU.NAJSTARSZE).map((w) => w.klucz)).toEqual([
      'najstarszy',
      'srodkowy',
      'najnowszy',
    ])
  })

  it('nie mutuje tablicy wejściowej', () => {
    const kopia = [...wpisy]
    sortujFeed(wpisy, KIERUNKI_SORTU.NAJSTARSZE)
    expect(wpisy).toEqual(kopia)
  })

  it('zwraca pustą tablicę dla pustego/brakującego wejścia', () => {
    expect(sortujFeed([])).toEqual([])
    expect(sortujFeed(undefined)).toEqual([])
  })
})

describe('wczytajFiltr / zapiszFiltr', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('bez zapisu w localStorage domyślnie zaznacza wszystkie dostępne klucze, sort najnowsze', () => {
    const wynik = wczytajFiltr(['Zestaw', 'Umowa'])
    expect(wynik).toEqual({ zaznaczone: ['Zestaw', 'Umowa'], kierunek: KIERUNKI_SORTU.NAJNOWSZE })
  })

  it('zapiszFiltr, potem wczytajFiltr odzyskuje ten sam wybór (przeżywa "przeładowanie")', () => {
    zapiszFiltr(['Umowa'], KIERUNKI_SORTU.NAJSTARSZE)
    const wynik = wczytajFiltr(['Zestaw', 'Umowa', 'Audyt'])
    expect(wynik).toEqual({ zaznaczone: ['Umowa'], kierunek: KIERUNKI_SORTU.NAJSTARSZE })
  })

  it('przycina zapisane zaznaczenie do kluczy nadal dostępnych', () => {
    zapiszFiltr(['Umowa', 'ZnikleZrodlo'], KIERUNKI_SORTU.NAJNOWSZE)
    const wynik = wczytajFiltr(['Zestaw', 'Umowa'])
    expect(wynik.zaznaczone).toEqual(['Umowa'])
  })

  it('zapisane zaznaczenie puste po przycięciu spada na "wszystko zaznaczone"', () => {
    zapiszFiltr(['TylkoZnikleZrodlo'], KIERUNKI_SORTU.NAJNOWSZE)
    const wynik = wczytajFiltr(['Zestaw', 'Umowa'])
    expect(wynik.zaznaczone).toEqual(['Zestaw', 'Umowa'])
  })

  it('JSON uszkodzony w localStorage nie rzuca, spada na domyślny stan', () => {
    localStorage.setItem('notatki-filtr', '{niepoprawny json')
    const wynik = wczytajFiltr(['Zestaw'])
    expect(wynik).toEqual({ zaznaczone: ['Zestaw'], kierunek: KIERUNKI_SORTU.NAJNOWSZE })
  })

  it('nieznana wartość kierunku spada na domyślne "najnowsze"', () => {
    zapiszFiltr(['Zestaw'], 'cos-nieznanego')
    const wynik = wczytajFiltr(['Zestaw'])
    expect(wynik.kierunek).toBe(KIERUNKI_SORTU.NAJNOWSZE)
  })
})
