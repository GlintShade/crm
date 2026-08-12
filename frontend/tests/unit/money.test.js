import { roundPln, formatPln, formatPlnAmount } from '@/utils/money'

describe('Formatowanie kwot pieniężnych (money)', () => {
  describe('formatPln — wartości domyślne / puste / nieprawidłowe', () => {
    it.each([
      [0, '0,00 zł'],
      [null, '0,00 zł'],
      [undefined, '0,00 zł'],
      ['', '0,00 zł'],
      [NaN, '0,00 zł'],
      ['abc', '0,00 zł'],
    ])('formatPln(%p) === %p', (wartosc, expected) => {
      expect(formatPln(wartosc)).toBe(expected)
    })
  })

  describe('formatPln — zawsze dokładnie dwa miejsca po przecinku', () => {
    it('liczba całkowita dostaje dwa zera', () => {
      expect(formatPln(5)).toBe('5,00 zł')
    })

    it('jedno miejsce dziesiętne dopełnia się do dwóch', () => {
      expect(formatPln(5.5)).toBe('5,50 zł')
    })
  })

  describe('formatPln — grupowanie tysięcy', () => {
    it('grupuje tysiące twardą spacją nierozdzielającą', () => {
      expect(formatPln(52018.2)).toBe('52 018,20 zł')
    })

    it('grupuje wielokrotnie przy większej liczbie cyfr', () => {
      expect(formatPln(1234567.89)).toBe('1 234 567,89 zł')
    })

    it('dokładnie 4 cyfry grupują się raz', () => {
      expect(formatPln(1234)).toBe('1 234,00 zł')
    })

    it('3 cyfry nie grupują się wcale', () => {
      expect(formatPln(123)).toBe('123,00 zł')
    })
  })

  describe('formatPln — separator dziesiętny', () => {
    it('używa przecinka, nigdy kropki', () => {
      const wynik = formatPln(1234.56)
      expect(wynik).toContain(',')
      expect(wynik).not.toContain('.')
    })
  })

  describe('formatPln — wartości ujemne', () => {
    it('minus stoi przed cyframi, grupowanie dotyczy tylko cyfr', () => {
      expect(formatPln(-1234.5)).toBe('-1 234,50 zł')
    })
  })

  describe('formatPln — wejście tekstowe', () => {
    it('przyjmuje liczbę zapisaną jako string', () => {
      expect(formatPln('1234.56')).toBe('1 234,56 zł')
    })
  })

  describe('formatPln — duże kwoty bez notacji naukowej', () => {
    it('nie generuje zapisu wykładniczego dla dużej kwoty', () => {
      const wynik = formatPln(12345678.91)
      expect(wynik).not.toMatch(/e/i)
      expect(wynik).toBe('12 345 678,91 zł')
    })
  })

  describe('formatPlnAmount — bez sufiksu " zł"', () => {
    it('zwraca ten sam napis co formatPln, ale bez " zł"', () => {
      expect(formatPlnAmount(52018.2)).toBe('52 018,20')
      expect(formatPlnAmount(0)).toBe('0,00')
      expect(formatPlnAmount(-1234.5)).toBe('-1 234,50')
    })

    it('nie zawiera sufiksu zł', () => {
      expect(formatPlnAmount(100)).not.toContain('zł')
    })
  })

  describe('roundPln — zaokrąglanie w połówkę od zera (half-away-from-zero)', () => {
    it('zaokrągla do dwóch miejsc po przecinku', () => {
      expect(roundPln(2.345)).toBeCloseTo(2.35, 10)
      expect(roundPln(1.005)).toBeCloseTo(1.01, 10)
      expect(roundPln(0.125)).toBeCloseTo(0.13, 10)
    })

    it('ujemne lustro jest dokładną negacją dodatniego przypadku (zapobiega błędowi Math.round(-0.5) === -0)', () => {
      expect(roundPln(-2.345)).toBe(-roundPln(2.345))
      expect(roundPln(-1.005)).toBe(-roundPln(1.005))
      expect(roundPln(-0.125)).toBe(-roundPln(0.125))
    })

    it('puste / nieprawidłowe wejście daje 0', () => {
      expect(roundPln(null)).toBe(0)
      expect(roundPln(undefined)).toBe(0)
      expect(roundPln('')).toBe(0)
      expect(roundPln(NaN)).toBe(0)
      expect(roundPln(Infinity)).toBe(0)
      expect(roundPln(-Infinity)).toBe(0)
    })

    it('przyjmuje wejście tekstowe', () => {
      expect(roundPln('1234.567')).toBeCloseTo(1234.57, 10)
    })

    it('zwraca Number, nigdy String', () => {
      expect(typeof roundPln(2.345)).toBe('number')
      expect(typeof roundPln('abc')).toBe('number')
    })
  })

  describe('roundPln — wartości, dla których String() używa notacji wykładniczej', () => {
    // Przesunięcie przecinka przez sklejenie tekstu ("${abs}e2") zawodzi,
    // gdy String(abs) sam już jest w notacji wykładniczej (|x| < 1e-6 albo
    // |x| >= 1e21) — powstałby zniekształcony literał typu "1e-7e2", a
    // Number(...) z niego dałoby NaN. To właśnie ten przypadek naprawia
    // fallback na zwykłe mnożenie w roundPln.

    it('resztka zmiennoprzecinkowa z odejmowania w cpMarza (netto - koszt - prowizja) zaokrągla się do zera, nie do NaN', () => {
      // 0.1 + 0.2 - 0.3 === 5.551115123125783e-17 w IEEE-754 — dokładnie
      // taka resztka może zostać po odjęciu bliskich sobie kwot w
      // przeliczPodzial (pula/zysk), więc roundPln musi ją bezpiecznie
      // sprowadzić do 0, a nie do NaN.
      expect(roundPln(0.1 + 0.2 - 0.3)).toBe(0)
      expect(roundPln(5.551115123125783e-17)).toBe(0)
    })

    it('bardzo małe wartości (poniżej progu notacji wykładniczej) zaokrąglają się do zera', () => {
      expect(roundPln(1e-7)).toBe(0)
      expect(roundPln(-1e-7)).toBe(0)
    })

    it('liczba zdenormalizowana (najmniejsza możliwa dodatnia double) zaokrągla się do zera', () => {
      expect(roundPln(5e-324)).toBe(0)
    })

    it('bardzo duża wartość (notacja wykładnicza od String()) pozostaje skończoną liczbą, nie NaN', () => {
      expect(roundPln(1e21)).toBe(1e21)
      expect(Number.isFinite(roundPln(1e21))).toBe(true)
    })
  })

  describe('formatPlnAmount / formatPln — nigdy nie renderują NaN ani undefined', () => {
    // Zabezpieczenie dwupoziomowe: roundPln nie powinien już zwracać NaN dla
    // tych wejść, ale formatPlnAmount ma też własną osłonę na wypadek, gdyby
    // jakiś przyszły wywołujący ominął roundPln — jej wyjście trafia wprost
    // do DOM, więc "NaN,undefined" na ekranie jest niedopuszczalne.
    it.each([
      [0.1 + 0.2 - 0.3],
      [5.551115123125783e-17],
      [1e-7],
      [-1e-7],
      [5e-324],
      [1e21],
      [NaN],
      [Infinity],
      [-Infinity],
    ])('formatPlnAmount(%p) i formatPln(%p) nie zawierają "NaN" ani "undefined"', (wartosc) => {
      expect(formatPlnAmount(wartosc)).not.toMatch(/NaN/)
      expect(formatPlnAmount(wartosc)).not.toMatch(/undefined/)
      expect(formatPln(wartosc)).not.toMatch(/NaN/)
      expect(formatPln(wartosc)).not.toMatch(/undefined/)
    })
  })
})
