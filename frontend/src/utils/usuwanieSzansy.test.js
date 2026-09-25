import { odmianaSzansy, trescOstrzezenia } from '@/utils/usuwanieSzansy'

const MYSLNIK_EN = '\u2013'
const MYSLNIK_EM = '\u2014'

function zawieraMyslnik(tekst) {
  return tekst.includes(MYSLNIK_EN) || tekst.includes(MYSLNIK_EM)
}

describe('odmianaSzansy', () => {
  it('1 daje biernik liczby pojedynczej', () => {
    expect(odmianaSzansy(1)).toBe('szansę')
  })

  it('2 daje mianownik/biernik liczby mnogiej', () => {
    expect(odmianaSzansy(2)).toBe('szanse')
  })

  it('5 daje dopełniacz liczby mnogiej', () => {
    expect(odmianaSzansy(5)).toBe('szans')
  })

  it('12 to wyjątek nastolatkowy mimo końcówki 2', () => {
    expect(odmianaSzansy(12)).toBe('szans')
  })

  it('22 wraca do formy 2-4 (poza zakresem 12-14)', () => {
    expect(odmianaSzansy(22)).toBe('szanse')
  })

  it('25 daje dopełniacz jak każda inna piątka i więcej', () => {
    expect(odmianaSzansy(25)).toBe('szans')
  })
})

describe('trescOstrzezenia, tytul i przycisk', () => {
  it('dla 1 nazwy: "Usuń szansę" bez liczby', () => {
    const wynik = trescOstrzezenia(['PRO/PV/26/1060'])
    expect(wynik.tytul).toBe('Usuń szansę')
    expect(wynik.etykietaPrzycisku).toBe('Usuń szansę')
  })

  it('dla 3 nazw: "Usuń 3 szanse"', () => {
    const wynik = trescOstrzezenia(['A', 'B', 'C'])
    expect(wynik.tytul).toBe('Usuń 3 szanse')
    expect(wynik.etykietaPrzycisku).toBe('Usuń 3 szanse')
  })
})

describe('trescOstrzezenia, akapit 1', () => {
  it('1 nazwa: zdanie z nazwą wprost, bez listy', () => {
    const wynik = trescOstrzezenia(['PRO/PV/26/1060'])
    expect(wynik.akapity[0]).toBe('Usuwasz szansę PRO/PV/26/1060.')
  })

  it('5 nazw: lista po przecinku z prefiksem "Usuwasz szanse:"', () => {
    const nazwy = ['A', 'B', 'C', 'D', 'E']
    const wynik = trescOstrzezenia(nazwy)
    expect(wynik.akapity[0]).toBe('Usuwasz szanse: A, B, C, D, E.')
  })

  it('6 nazw: przełącza się na podsumowanie liczbowe', () => {
    const nazwy = ['A', 'B', 'C', 'D', 'E', 'F']
    const wynik = trescOstrzezenia(nazwy)
    expect(wynik.akapity[0]).toBe('Usuwasz 6 zaznaczonych szans.')
  })
})

describe('trescOstrzezenia, tresc stala', () => {
  it('akapit 2 wspomina kaskadę dokumentów i nieodwracalność', () => {
    const wynik = trescOstrzezenia(['PRO/PV/26/1060'])
    expect(wynik.akapity[1]).toContain('nieodwracalna')
    expect(wynik.akapity[1]).toContain('umowy')
    expect(wynik.akapity[1]).toContain('Trify')
  })

  it('akapit 3 wspomina blokadę statusu podpisu i audytu', () => {
    const wynik = trescOstrzezenia(['PRO/PV/26/1060'])
    expect(wynik.akapity[2]).toContain('nie da się usunąć')
    expect(wynik.akapity[2]).toContain('audytem specjalnym CP')
  })
})

describe('trescOstrzezenia, bez myslnikow em/en', () => {
  it('żaden zwrócony tekst nie zawiera U+2014 ani U+2013, dla wielu n', () => {
    for (const n of [1, 2, 3, 5, 6, 12, 22, 25]) {
      const nazwy = Array.from({ length: n }, (_, i) => `PRO/PV/26/${1000 + i}`)
      const wynik = trescOstrzezenia(nazwy)
      expect(zawieraMyslnik(wynik.tytul)).toBe(false)
      expect(zawieraMyslnik(wynik.etykietaPrzycisku)).toBe(false)
      for (const akapit of wynik.akapity) {
        expect(zawieraMyslnik(akapit)).toBe(false)
      }
    }
  })
})

describe('trescOstrzezenia, immutability', () => {
  it('nie mutuje wejściowej tablicy nazw', () => {
    const nazwy = ['A', 'B', 'C']
    const kopia = [...nazwy]
    trescOstrzezenia(nazwy)
    expect(nazwy).toEqual(kopia)
  })

  it('zwraca nową tablicę akapitów przy każdym wywołaniu', () => {
    const nazwy = ['A']
    const pierwszy = trescOstrzezenia(nazwy)
    const drugi = trescOstrzezenia(nazwy)
    expect(pierwszy.akapity).not.toBe(drugi.akapity)
  })
})
