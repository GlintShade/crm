import { podzielNazwe, zlozNazwe, sprawdzTrzon, MAKS_DLUGOSC } from '@/utils/zalaczniki'

describe('Edycja nazwy pliku przed wysłaniem załącznika (zalaczniki)', () => {
  describe('podzielNazwe', () => {
    it.each([
      ['a.b.pdf', { trzon: 'a.b', rozszerzenie: '.pdf' }],
      ['bez', { trzon: 'bez', rozszerzenie: '' }],
      ['.gitignore', { trzon: '.gitignore', rozszerzenie: '' }],
      ['plik.PDF', { trzon: 'plik', rozszerzenie: '.PDF' }],
      ['', { trzon: '', rozszerzenie: '' }],
      [null, { trzon: '', rozszerzenie: '' }],
      [undefined, { trzon: '', rozszerzenie: '' }],
    ])('podzielNazwe(%p) === %p', (nazwa, expected) => {
      expect(podzielNazwe(nazwa)).toEqual(expected)
    })
  })

  describe('zlozNazwe', () => {
    it('łączy trzon i rozszerzenie', () => {
      expect(zlozNazwe('Formularz kredytowy', '.pdf')).toBe('Formularz kredytowy.pdf')
    })

    it('obcina białe znaki na brzegach trzonu', () => {
      expect(zlozNazwe('  Umowa  ', '.pdf')).toBe('Umowa.pdf')
    })

    it('działa bez rozszerzenia', () => {
      expect(zlozNazwe('bez_rozszerzenia')).toBe('bez_rozszerzenia')
    })
  })

  describe('sprawdzTrzon', () => {
    it('akceptuje poprawny trzon', () => {
      expect(sprawdzTrzon('Formularz kredytowy', '.pdf')).toBeNull()
    })

    it('odrzuca pusty trzon', () => {
      expect(sprawdzTrzon('', '.pdf')).toBe('Nazwa pliku nie może być pusta.')
    })

    it('odrzuca trzon z samych białych znaków', () => {
      expect(sprawdzTrzon('   ', '.pdf')).toBe('Nazwa pliku nie może być pusta.')
    })

    it('odrzuca ukośnik', () => {
      expect(sprawdzTrzon('folder/plik', '.pdf')).toBe(
        'Nazwa pliku nie może zawierać ukośników ani znaków sterujących.',
      )
    })

    it('odrzuca wsteczny ukośnik', () => {
      expect(sprawdzTrzon('folder\\plik', '.pdf')).toBe(
        'Nazwa pliku nie może zawierać ukośników ani znaków sterujących.',
      )
    })

    it('odrzuca tabulator (znak sterujący)', () => {
      expect(sprawdzTrzon('plik\tnazwa', '.pdf')).toBe(
        'Nazwa pliku nie może zawierać ukośników ani znaków sterujących.',
      )
    })

    it('odrzuca znak nowej linii (znak sterujący)', () => {
      expect(sprawdzTrzon('plik\nnazwa', '.pdf')).toBe(
        'Nazwa pliku nie może zawierać ukośników ani znaków sterujących.',
      )
    })

    it('akceptuje trzon dający dokładnie 140 znaków łącznie', () => {
      const trzon = 'a'.repeat(MAKS_DLUGOSC - '.pdf'.length)
      expect(zlozNazwe(trzon, '.pdf')).toHaveLength(MAKS_DLUGOSC)
      expect(sprawdzTrzon(trzon, '.pdf')).toBeNull()
    })

    it('odrzuca trzon dający 141 znaków łącznie', () => {
      const trzon = 'a'.repeat(MAKS_DLUGOSC - '.pdf'.length + 1)
      expect(sprawdzTrzon(trzon, '.pdf')).toBe(
        `Nazwa pliku może mieć najwyżej ${MAKS_DLUGOSC} znaków.`,
      )
    })

    it('obsługuje wiele kropek w trzonie', () => {
      expect(sprawdzTrzon('a.b.c', '.pdf')).toBeNull()
    })

    it('działa bez rozszerzenia (parametr domyślny)', () => {
      expect(sprawdzTrzon('bez_rozszerzenia')).toBeNull()
    })

    it('odrzuca pusty trzon nawet bez rozszerzenia', () => {
      expect(sprawdzTrzon('')).toBe('Nazwa pliku nie może być pusta.')
    })
  })
})
