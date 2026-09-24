import { czyPoleTekstowe, liczWierszeTekstu } from '@/utils/panelTekst'

describe('czyPoleTekstowe', () => {
  it('true dla Small Text, Text, Long Text', () => {
    expect(czyPoleTekstowe({ fieldtype: 'Small Text' })).toBe(true)
    expect(czyPoleTekstowe({ fieldtype: 'Text' })).toBe(true)
    expect(czyPoleTekstowe({ fieldtype: 'Long Text' })).toBe(true)
  })

  it('false dla Code (zostaje w dotychczasowej galezi)', () => {
    expect(czyPoleTekstowe({ fieldtype: 'Code' })).toBe(false)
  })

  it('false dla innych typow pol', () => {
    expect(czyPoleTekstowe({ fieldtype: 'Select' })).toBe(false)
    expect(czyPoleTekstowe({ fieldtype: 'Data' })).toBe(false)
    expect(czyPoleTekstowe({ fieldtype: 'Link' })).toBe(false)
  })

  it('nie wybucha na brakujacym polu/fieldtype', () => {
    expect(czyPoleTekstowe(undefined)).toBe(false)
    expect(czyPoleTekstowe({})).toBe(false)
  })
})

describe('liczWierszeTekstu', () => {
  it('puste wejscie daje minimum wierszy', () => {
    expect(liczWierszeTekstu('')).toBe(4)
  })

  it('null/undefined daje minimum wierszy', () => {
    expect(liczWierszeTekstu(null)).toBe(4)
    expect(liczWierszeTekstu(undefined)).toBe(4)
  })

  it('jedna krotka linia daje minimum wierszy', () => {
    expect(liczWierszeTekstu('Krotki tekst')).toBe(4)
  })

  it('jedna dluga linia liczy sie proporcjonalnie do znakowNaWiersz', () => {
    const tekst = 'a'.repeat(500)
    // ceil(500 / 48) = 11
    expect(liczWierszeTekstu(tekst)).toBe(11)
  })

  it('wiele linii sumuje sie', () => {
    const tekst = Array(6).fill('krotka linia').join('\n')
    // 6 linii, kazda ceil(<=48/48) = 1 -> suma 6
    expect(liczWierszeTekstu(tekst)).toBe(6)
  })

  it('przyciecie do max', () => {
    const tekst = 'a'.repeat(48 * 100)
    expect(liczWierszeTekstu(tekst)).toBe(40)
  })

  it('respektuje niestandardowe znakowNaWiersz/min/max', () => {
    const tekst = 'a'.repeat(20)
    expect(liczWierszeTekstu(tekst, 10, 1, 40)).toBe(2)
    expect(liczWierszeTekstu(tekst, 10, 1, 1)).toBe(1)
  })

  it('wartosc niebedaca stringiem nie wybucha, jest konwertowana', () => {
    expect(liczWierszeTekstu(12345)).toBe(4)
    expect(liczWierszeTekstu(true)).toBe(4)
    expect(liczWierszeTekstu({})).toBe(4)
    expect(liczWierszeTekstu([])).toBe(4)
  })
})
