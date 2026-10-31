import {
  KOLUMNY_INLINE,
  czyKolumnaInline,
  surowaWartoscKomorki,
  probyKontaktuDoWyswietlenia,
  nowaListaZPodmienionymPolem,
  MIN_SZEROKOSC_KOLUMNY_PX,
  ograniczSzerokoscKolumny,
  szerokoscKolumnyZMinimum,
} from './leadyInline'

describe('KOLUMNY_INLINE / czyKolumnaInline', () => {
  it('zawiera dokladnie szesc kolumn inline', () => {
    expect([...KOLUMNY_INLINE].sort()).toEqual(
      [
        'custom_czas_do_kontaktu',
        'custom_kolejny_kontakt',
        'custom_proby_kontaktu',
        'custom_status_handlowy',
        'custom_termin_spotkania',
        'status',
      ].sort(),
    )
  })

  it('rozpoznaje kolumne inline i nie-inline', () => {
    expect(czyKolumnaInline({ key: 'status' })).toBe(true)
    expect(czyKolumnaInline({ key: 'custom_cc' })).toBe(false)
    expect(czyKolumnaInline({ key: 'lead_owner' })).toBe(false)
    expect(czyKolumnaInline(null)).toBe(false)
  })
})

describe('surowaWartoscKomorki', () => {
  it('status: wyciaga label z obiektu {label, color}', () => {
    const column = { key: 'status', type: 'Link' }
    expect(surowaWartoscKomorki(column, { label: 'Nowy', color: 'gray' })).toBe(
      'Nowy',
    )
  })

  it('status: przepuszcza goly string bez zmian', () => {
    const column = { key: 'status', type: 'Link' }
    expect(surowaWartoscKomorki(column, 'Nowy')).toBe('Nowy')
  })

  it('status: pusty item daje pusty string, nie undefined', () => {
    const column = { key: 'status', type: 'Link' }
    expect(surowaWartoscKomorki(column, null)).toBe('')
  })

  it('Date/Datetime: wyciaga value z obiektu {label, value}', () => {
    const column = { key: 'custom_kolejny_kontakt', type: 'Date' }
    expect(
      surowaWartoscKomorki(column, { label: '10-09-2026', value: '2026-09-10' }),
    ).toBe('2026-09-10')
  })

  it('Date/Datetime: brak wartosci daje null, nie pusty string', () => {
    const column = { key: 'custom_termin_spotkania', type: 'Datetime' }
    expect(surowaWartoscKomorki(column, null)).toBe(null)
    expect(surowaWartoscKomorki(column, { label: '', value: null })).toBe(null)
  })

  it('Select (custom_status_handlowy): goly string przechodzi bez zmian', () => {
    const column = { key: 'custom_status_handlowy', type: 'Select' }
    expect(surowaWartoscKomorki(column, 'Umowa')).toBe('Umowa')
    expect(surowaWartoscKomorki(column, null)).toBe('')
  })
})

describe('nowaListaZPodmienionymPolem', () => {
  const oryginal = [
    { name: 'CRM-LEAD-1', status: 'Nowy', custom_status_handlowy: '' },
    { name: 'CRM-LEAD-2', status: 'Otwarty', custom_status_handlowy: 'Decyzja' },
  ]

  it('podmienia pole tylko w docelowym wierszu', () => {
    const wynik = nowaListaZPodmienionymPolem(
      oryginal,
      'CRM-LEAD-1',
      'status',
      'Odrzucony',
    )
    expect(wynik[0].status).toBe('Odrzucony')
    expect(wynik[1]).toEqual(oryginal[1])
  })

  it('nie mutuje wejsciowej tablicy ani wejsciowych obiektow', () => {
    const kopiaOryginalu = JSON.parse(JSON.stringify(oryginal))
    nowaListaZPodmienionymPolem(oryginal, 'CRM-LEAD-2', 'custom_status_handlowy', 'Umowa')
    expect(oryginal).toEqual(kopiaOryginalu)
  })

  it('docelowy wiersz to nowy obiekt (inna referencja), niezmieniony wiersz to ta sama referencja', () => {
    const wynik = nowaListaZPodmienionymPolem(
      oryginal,
      'CRM-LEAD-1',
      'status',
      'Odrzucony',
    )
    expect(wynik[0]).not.toBe(oryginal[0])
    expect(wynik[1]).toBe(oryginal[1])
  })

  it('brak dopasowania nazwy zwraca liste rownowazna wejsciowej', () => {
    const wynik = nowaListaZPodmienionymPolem(
      oryginal,
      'CRM-LEAD-NIEISTNIEJACY',
      'status',
      'Odrzucony',
    )
    expect(wynik).toEqual(oryginal)
  })
})

describe('probyKontaktuDoWyswietlenia', () => {
  it('puste wartosci daja "0"', () => {
    expect(probyKontaktuDoWyswietlenia('')).toBe('0')
    expect(probyKontaktuDoWyswietlenia(null)).toBe('0')
    expect(probyKontaktuDoWyswietlenia(undefined)).toBe('0')
    expect(probyKontaktuDoWyswietlenia('  ')).toBe('0')
  })
  it('zachowuje liczby jako tekst', () => {
    expect(probyKontaktuDoWyswietlenia('3')).toBe('3')
    expect(probyKontaktuDoWyswietlenia(5)).toBe('5')
    expect(probyKontaktuDoWyswietlenia(0)).toBe('0')
  })
  it('surowaWartoscKomorki dla kolumny prob uzywa fallbacku', () => {
    expect(surowaWartoscKomorki({ key: 'custom_proby_kontaktu' }, '')).toBe('0')
  })
})

describe('ograniczSzerokoscKolumny', () => {
  it('stosuje minimum per kolumna', () => {
    expect(ograniczSzerokoscKolumny('custom_czas_do_kontaktu', 40)).toBe(72)
    expect(ograniczSzerokoscKolumny('custom_proby_kontaktu', 50)).toBe(64)
    expect(ograniczSzerokoscKolumny('_comment_count', 20)).toBe(32)
  })
  it('nie zmienia szerokosci powyzej minimum ani innych kolumn', () => {
    expect(ograniczSzerokoscKolumny('custom_czas_do_kontaktu', 120)).toBe(120)
    expect(ograniczSzerokoscKolumny('lead_name', 10)).toBe(10)
  })
  it('nieliczbowa wartosc daje minimum', () => {
    expect(ograniczSzerokoscKolumny('_comment_count', NaN)).toBe(32)
    expect(MIN_SZEROKOSC_KOLUMNY_PX._comment_count).toBe(32)
  })
})

describe('szerokoscKolumnyZMinimum', () => {
  const k = 'custom_czas_do_kontaktu'
  it('px ponizej minimum -> minimum w px, nowy obiekt', () => {
    const c = { key: k, width: '63px' }
    const r = szerokoscKolumnyZMinimum(c)
    expect(r.width).toBe('72px')
    expect(r).not.toBe(c)
    expect(c.width).toBe('63px')
  })
  it('rem ponizej minimum', () => {
    expect(szerokoscKolumnyZMinimum({ key: k, width: '4rem' }).width).toBe('72px')
  })
  it('px i rem powyzej minimum bez zmian', () => {
    const a = { key: k, width: '80px' }
    const b = { key: k, width: '4.5rem' }
    expect(szerokoscKolumnyZMinimum(a)).toBe(a)
    expect(szerokoscKolumnyZMinimum(b)).toBe(b)
  })
  it('nieznany klucz i brak szerokosci bez zmian', () => {
    const a = { key: 'lead_name', width: '10px' }
    const b = { key: k }
    expect(szerokoscKolumnyZMinimum(a)).toBe(a)
    expect(szerokoscKolumnyZMinimum(b)).toBe(b)
  })
})
