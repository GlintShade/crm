import {
  DNI_TYGODNIA,
  dzienZDaty,
  formatujDate,
  formatujGodzine,
  grupujPoDniach,
  naSekundy,
  sortujWyjatki,
  walidujLimit,
  walidujTresc,
  walidujWiersz,
  walidujWyjatek,
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

describe('dyzury: walidujTresc', () => {
  it('akceptuje znane placeholdery', () => {
    expect(walidujTresc('Lead {klient}, {telefon}, {kod}, {miejscowosc}. {link}')).toBeNull()
  })

  it('odrzuca pusta tresc', () => {
    expect(walidujTresc('   ')).toBe('Treść SMS nie może być pusta.')
    expect(walidujTresc(null)).toBe('Treść SMS nie może być pusta.')
  })

  it('odrzuca nieznany placeholder', () => {
    expect(walidujTresc('Lead {xxx}')).toContain('Nieznany placeholder {xxx}')
  })
})

describe('dyzury: walidujLimit', () => {
  it('akceptuje 0 i 1000', () => {
    expect(walidujLimit(0)).toBeNull()
    expect(walidujLimit('100')).toBeNull()
    expect(walidujLimit(1000)).toBeNull()
  })

  it('odrzuca poza zakresem, puste i niecalkowite', () => {
    expect(walidujLimit(1001)).toContain('od 0 do 1000')
    expect(walidujLimit(-1)).toContain('od 0 do 1000')
    expect(walidujLimit('')).toContain('od 0 do 1000')
    expect(walidujLimit(1.5)).toContain('od 0 do 1000')
  })
})

describe('dyzury: wyjatki', () => {
  it('grupujPoDniach pomija wyjatki z data', () => {
    const g = grupujPoDniach([
      { dzien_tygodnia: 'Wtorek', od: '08:00', uzytkownik: 'a', data: '' },
      { dzien_tygodnia: 'Wtorek', od: '09:00', uzytkownik: 'b', data: '2026-11-03' },
    ])
    expect(g['Wtorek'].map((w) => w.uzytkownik)).toEqual(['a'])
  })

  it('formatujDate daje skrot dnia i date', () => {
    expect(formatujDate('2026-11-03')).toBe('wt 03.11.2026')
    expect(formatujDate('2026-11-01')).toBe('nd 01.11.2026')
    expect(formatujDate('2026-11-02')).toBe('pn 02.11.2026')
    expect(formatujDate('2026-11-07')).toBe('sob 07.11.2026')
    expect(formatujDate('2026-11-04')).toBe('śr 04.11.2026')
    expect(formatujDate('xx')).toBe('xx')
  })

  it('dzienZDaty zwraca nazwe z DNI_TYGODNIA', () => {
    expect(dzienZDaty('2026-11-03')).toBe('Wtorek')
    expect(dzienZDaty('2026-11-01')).toBe('Niedziela')
    expect(dzienZDaty('2026-11-02')).toBe('Poniedziałek')
    expect(dzienZDaty('2026-02-30')).toBeNull()
  })

  it('sortujWyjatki bierze tylko wiersze z data i sortuje', () => {
    const w = sortujWyjatki([
      { data: '2026-11-05', od: '08:00' },
      { data: '', od: '07:00' },
      { data: '2026-11-03', od: '12:00' },
      { data: '2026-11-03', od: '08:00' },
    ])
    expect(w.map((x) => `${x.data} ${x.od}`)).toEqual([
      '2026-11-03 08:00',
      '2026-11-03 12:00',
      '2026-11-05 08:00',
    ])
  })

  it('walidujWyjatek: data, bez dyzuru, godziny, uzytkownik', () => {
    expect(walidujWyjatek('', '', '', true, '')).toContain('datę')
    expect(walidujWyjatek('03.11.2026', '', '', true, '')).toContain('RRRR-MM-DD')
    expect(walidujWyjatek('2026-11-03', '', '', true, '')).toBeNull()
    expect(walidujWyjatek('2026-11-03', 'xx', '10:00', false, 'a')).toContain('GG:MM')
    expect(walidujWyjatek('2026-11-03', '12:00', '10:00', false, 'a')).toContain('wcześniejsza')
    expect(walidujWyjatek('2026-11-03', '09:00', '10:00', false, '')).toContain('użytkownika')
    expect(walidujWyjatek('2026-11-03', '09:00', '10:00', false, 'a')).toBeNull()
  })
})
