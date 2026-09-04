import { MONTAZ, TRIFY, tekstPusty } from '@/utils/aktualizacje'

function bezDuplikatow(arr) {
  return new Set(arr).size === arr.length
}

describe('konfiguracje strumieni aktualizacji', () => {
  it.each([
    ['MONTAZ', MONTAZ],
    ['TRIFY', TRIFY],
  ])('%s ma name, doctype, typy i html', (_, konfig) => {
    expect(typeof konfig.name).toBe('string')
    expect(konfig.name.length).toBeGreaterThan(0)
    expect(typeof konfig.doctype).toBe('string')
    expect(konfig.doctype.length).toBeGreaterThan(0)
    expect(Array.isArray(konfig.typy)).toBe(true)
    expect(konfig.typy.length).toBeGreaterThan(0)
    expect(bezDuplikatow(konfig.typy)).toBe(true)
    expect(typeof konfig.html).toBe('boolean')
  })

  it('MONTAZ.typy ma 5 pozycji jak dziś', () => {
    expect(MONTAZ.typy).toHaveLength(5)
    expect(MONTAZ.typy).toEqual(['Notatka', 'Telefon', 'Wizyta', 'Termin montażu', 'Problem'])
  })

  it('MONTAZ.html jest false (tekst zwykły)', () => {
    expect(MONTAZ.html).toBe(false)
  })

  it('TRIFY.typy ma 6 pozycji i zaczyna się od "Notatka"', () => {
    expect(TRIFY.typy).toHaveLength(6)
    expect(TRIFY.typy[0]).toBe('Notatka')
  })

  it('TRIFY.html jest true (edytor HTML ze wzmiankami)', () => {
    expect(TRIFY.html).toBe(true)
  })

  it('doctype odpowiada oczekiwanym Frappe doctype', () => {
    expect(MONTAZ.doctype).toBe('Volteo Montaz Update')
    expect(TRIFY.doctype).toBe('Volteo Trify Update')
  })
})

describe('tekstPusty', () => {
  it.each([
    ['', ''],
    ['undefined', undefined],
    ['<p></p>', '<p></p>'],
    ['<p>&nbsp;</p>', '<p>&nbsp;</p>'],
    ['<p><br></p>', '<p><br></p>'],
  ])('zwraca true dla %s', (_, html) => {
    expect(tekstPusty(html)).toBe(true)
  })

  it.each([
    ['<p>x</p>', '<p>x</p>'],
    ['tekst ze wzmianką (span)', '<p>Cześć <span data-type="mention">@Jan Kowalski</span></p>'],
  ])('zwraca false dla %s', (_, html) => {
    expect(tekstPusty(html)).toBe(false)
  })
})
