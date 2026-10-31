import {
  DNI_TYGODNIA,
  formatujGodzine,
  grupujPoDniach,
  naSekundy,
  walidujWiersz,
} from '@/utils/dyzury'

describe('dyzury: dni i godziny', () => {
  it('ma 7 dni w kolejnosci tygodnia', () => {
    expect(DNI_TYGODNIA).toHaveLength(7)
    expect(DNI_TYGODNIA[0]).toBe('Poniedziałek')
    expect(DNI_TYGODNIA[6]).toBe('Niedziela')
  })

  it('formatujGodzine skraca sekundy', () => {
    expect(formatujGodzine('08:00:00')).toBe('08:00')
    expect(formatujGodzine('8:5')).toBe('08:05')
    expect(formatujGodzine('18:30')).toBe('18:30')
  })

  it('formatujGodzine zostawia smieci i puste', () => {
    expect(formatujGodzine('abc')).toBe('abc')
    expect(formatujGodzine(null)).toBe('')
  })

  it('naSekundy dopisuje sekundy', () => {
    expect(naSekundy('08:00')).toBe('08:00:00')
    expect(naSekundy('8:30')).toBe('08:30:00')
    expect(naSekundy('08:00:15')).toBe('08:00:15')
    expect(naSekundy('xx')).toBe('xx')
  })
})

describe('dyzury: walidujWiersz', () => {
  it('akceptuje poprawny wiersz', () => {
    expect(walidujWiersz('Wtorek', '08:00', '18:00')).toBeNull()
    expect(walidujWiersz('Wtorek', '08:00:00', '18:00:00')).toBeNull()
  })

  it('odrzuca zly dzien', () => {
    expect(walidujWiersz('Monday', '08:00', '18:00')).toContain('Dzień tygodnia')
  })

  it('odrzuca od rowne do i od pozniejsze niz do', () => {
    expect(walidujWiersz('Wtorek', '08:00', '08:00')).toContain('wcześniejsza')
    expect(walidujWiersz('Wtorek', '19:00', '08:00')).toContain('wcześniejsza')
  })

  it('odrzuca zly format i godziny poza zakresem', () => {
    expect(walidujWiersz('Wtorek', 'xx', '08:00')).toContain('GG:MM')
    expect(walidujWiersz('Wtorek', '08:00', '25:00')).toContain('GG:MM')
  })
})

describe('dyzury: grupujPoDniach', () => {
  it('zwraca zawsze 7 kluczy, nawet bez wierszy', () => {
    const g = grupujPoDniach([])
    expect(Object.keys(g)).toEqual(DNI_TYGODNIA)
    expect(g['Sobota']).toEqual([])
  })

  it('grupuje i sortuje po godzinie od', () => {
    const g = grupujPoDniach([
      { dzien_tygodnia: 'Środa', od: '12:00:00', uzytkownik: 'b' },
      { dzien_tygodnia: 'Środa', od: '08:00:00', uzytkownik: 'a' },
      { dzien_tygodnia: 'Piątek', od: '08:00:00', uzytkownik: 'c' },
    ])
    expect(g['Środa'].map((w) => w.uzytkownik)).toEqual(['a', 'b'])
    expect(g['Piątek']).toHaveLength(1)
  })

  it('ignoruje wiersz z nieznanym dniem', () => {
    const g = grupujPoDniach([{ dzien_tygodnia: 'x', od: '08:00', uzytkownik: 'a' }])
    expect(Object.values(g).flat()).toHaveLength(0)
  })
})
