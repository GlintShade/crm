import {
  KOLUMNY_INLINE,
  czyKolumnaInline,
  surowaWartoscKomorki,
  nowaListaZPodmienionymPolem,
} from './leadyInline'

describe('KOLUMNY_INLINE / czyKolumnaInline', () => {
  it('zawiera dokladnie cztery kolumny inline', () => {
    expect([...KOLUMNY_INLINE].sort()).toEqual(
      [
        'custom_kolejny_kontakt',
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
