import {
  KOLUMNY_INLINE,
  czyKolumnaInline,
  surowaWartoscKomorki,
  probyKontaktuDoWyswietlenia,
  nowaListaZPodmienionymPolem,
  MIN_SZEROKOSC_KOLUMNY_PX,
  ograniczSzerokoscKolumny,
  szerokoscKolumnyZMinimum,
  KOLUMNY_TEKSTOWE_INLINE,
  WOJEWODZTWA,
  ROLE_BYPASS_HANDLOWCA,
  ROLA_CC,
  mozePrzypisywacHandlowca,
  emailUzytkownikaZKomorki,
  normalizujKodPocztowy,
  wartoscTekstuDoZapisu,
  czyWartoscSieZmienila,
} from './leadyInline'

describe('KOLUMNY_INLINE / czyKolumnaInline', () => {
  it('zawiera dokladnie trzynascie kolumn inline (szesc CC + siedem z b83)', () => {
    expect([...KOLUMNY_INLINE].sort()).toEqual(
      [
        'custom_czas_do_kontaktu',
        'custom_install_address',
        'custom_install_city',
        'custom_install_postal_code',
        'custom_nr_domu',
        'custom_powiat',
        'custom_voivodeship',
        'lead_owner',
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
    expect(czyKolumnaInline({ key: 'lead_owner' })).toBe(true)
    expect(czyKolumnaInline({ key: 'custom_powiat' })).toBe(true)
    expect(czyKolumnaInline({ key: 'mobile_no' })).toBe(false)
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

describe('b83: kolumny adresu i handlowca', () => {
  it('kolumny tekstowe to piec pol adresu, bez wojewodztwa i handlowca', () => {
    expect([...KOLUMNY_TEKSTOWE_INLINE].sort()).toEqual(
      [
        'custom_install_address',
        'custom_install_city',
        'custom_install_postal_code',
        'custom_nr_domu',
        'custom_powiat',
      ].sort(),
    )
    for (const key of KOLUMNY_TEKSTOWE_INLINE) {
      expect(KOLUMNY_INLINE.has(key)).toBe(true)
    }
    expect(KOLUMNY_TEKSTOWE_INLINE.has('custom_voivodeship')).toBe(false)
    expect(KOLUMNY_TEKSTOWE_INLINE.has('lead_owner')).toBe(false)
  })

  it('16 wojewodztw, malymi literami, bez duplikatow', () => {
    expect(WOJEWODZTWA).toHaveLength(16)
    expect(new Set(WOJEWODZTWA).size).toBe(16)
    for (const w of WOJEWODZTWA) {
      expect(w).toBe(w.toLowerCase())
      expect(w).toBe(w.trim())
    }
    expect(WOJEWODZTWA).toContain('dolnośląskie')
    expect(WOJEWODZTWA).toContain('zachodniopomorskie')
  })

  it('surowaWartoscKomorki: lead_owner wyciaga e-mail z obiektu uzytkownika', () => {
    const column = { key: 'lead_owner', type: 'Link', options: 'User' }
    expect(
      surowaWartoscKomorki(column, {
        label: 'Jan Kowalski',
        name: 'jan@volteo.pl',
        full_name: 'Jan Kowalski',
      }),
    ).toBe('jan@volteo.pl')
    expect(surowaWartoscKomorki(column, { label: '' })).toBe('')
    expect(surowaWartoscKomorki(column, null)).toBe('')
    expect(surowaWartoscKomorki(column, 'jan@volteo.pl')).toBe('jan@volteo.pl')
  })

  it('surowaWartoscKomorki: pola adresu i wojewodztwo to gole stringi', () => {
    expect(surowaWartoscKomorki({ key: 'custom_install_city', type: 'Data' }, 'Opole')).toBe(
      'Opole',
    )
    expect(surowaWartoscKomorki({ key: 'custom_voivodeship', type: 'Select' }, null)).toBe('')
  })
})

describe('mozePrzypisywacHandlowca (ta sama bramka co przekaz_handlowcowi)', () => {
  const CC = 'cc@volteo.pl'
  const INNY_CC = 'inny.cc@volteo.pl'

  it('Administrator zawsze, nawet bez rol', () => {
    expect(mozePrzypisywacHandlowca({ uzytkownik: 'Administrator', role: [] })).toBe(true)
  })

  it('role BYPASS zawsze, bez wzgledu na custom_cc leada', () => {
    for (const rola of ['System Manager', 'Volteo Core Admin', 'Volteo Backend']) {
      expect(
        mozePrzypisywacHandlowca({ uzytkownik: 'a@volteo.pl', role: [rola], ccLeada: '' }),
      ).toBe(true)
      expect(
        mozePrzypisywacHandlowca({ uzytkownik: 'a@volteo.pl', role: [rola], ccLeada: INNY_CC }),
      ).toBe(true)
    }
  })

  it('CC tylko na leadzie z wlasnym custom_cc', () => {
    expect(mozePrzypisywacHandlowca({ uzytkownik: CC, role: [ROLA_CC], ccLeada: CC })).toBe(true)
    expect(mozePrzypisywacHandlowca({ uzytkownik: CC, role: [ROLA_CC], ccLeada: INNY_CC })).toBe(
      false,
    )
    expect(mozePrzypisywacHandlowca({ uzytkownik: CC, role: [ROLA_CC], ccLeada: '' })).toBe(false)
    expect(mozePrzypisywacHandlowca({ uzytkownik: CC, role: [ROLA_CC] })).toBe(false)
  })

  it('custom_cc rowny uzytkownikowi bez roli CC nie wystarcza', () => {
    expect(
      mozePrzypisywacHandlowca({ uzytkownik: CC, role: ['Volteo D2D Sales'], ccLeada: CC }),
    ).toBe(false)
  })

  it('handlowiec D2D nigdy', () => {
    const rep = 'rep@volteo.pl'
    expect(mozePrzypisywacHandlowca({ uzytkownik: rep, role: ['Volteo D2D Sales'] })).toBe(false)
    expect(
      mozePrzypisywacHandlowca({ uzytkownik: rep, role: ['Volteo D2D Sales'], ccLeada: CC }),
    ).toBe(false)
    expect(mozePrzypisywacHandlowca({ uzytkownik: rep, role: ['Sales User'] })).toBe(false)
  })

  it('brak danych albo zly typ rol daje false', () => {
    expect(mozePrzypisywacHandlowca()).toBe(false)
    expect(mozePrzypisywacHandlowca({ uzytkownik: CC, role: null, ccLeada: CC })).toBe(false)
    expect(mozePrzypisywacHandlowca({ uzytkownik: CC, role: 'System Manager' })).toBe(false)
    expect(mozePrzypisywacHandlowca({ uzytkownik: '', role: [ROLA_CC], ccLeada: '' })).toBe(false)
  })

  it('lista BYPASS zgadza sie z serwerem i nie zawiera CC ani D2D', () => {
    expect([...ROLE_BYPASS_HANDLOWCA].sort()).toEqual(
      ['System Manager', 'Volteo Backend', 'Volteo Core Admin'].sort(),
    )
    expect(ROLE_BYPASS_HANDLOWCA).not.toContain(ROLA_CC)
    expect(ROLE_BYPASS_HANDLOWCA).not.toContain('Volteo D2D Sales')
  })
})

describe('emailUzytkownikaZKomorki', () => {
  it('obiekt z parseRows, goly e-mail i pustka', () => {
    expect(emailUzytkownikaZKomorki({ label: 'CC', name: 'cc@volteo.pl' })).toBe('cc@volteo.pl')
    expect(emailUzytkownikaZKomorki({ label: '' })).toBe('')
    expect(emailUzytkownikaZKomorki('cc@volteo.pl')).toBe('cc@volteo.pl')
    expect(emailUzytkownikaZKomorki(null)).toBe('')
    expect(emailUzytkownikaZKomorki(undefined)).toBe('')
  })
})

describe('normalizujKodPocztowy', () => {
  it('przepuszcza poprawny format NN-NNN', () => {
    expect(normalizujKodPocztowy('00-950')).toEqual({ ok: true, wartosc: '00-950' })
  })

  it('obcina spacje', () => {
    expect(normalizujKodPocztowy('  45-001 ')).toEqual({ ok: true, wartosc: '45-001' })
    expect(normalizujKodPocztowy('45 - 001')).toEqual({ ok: true, wartosc: '45-001' })
  })

  it('dopelnia piec cyfr do NN-NNN', () => {
    expect(normalizujKodPocztowy('45001')).toEqual({ ok: true, wartosc: '45-001' })
  })

  it('pusty wpis czysci pole', () => {
    expect(normalizujKodPocztowy('')).toEqual({ ok: true, wartosc: '' })
    expect(normalizujKodPocztowy('   ')).toEqual({ ok: true, wartosc: '' })
    expect(normalizujKodPocztowy(null)).toEqual({ ok: true, wartosc: '' })
  })

  it('zly format daje blad z czytelnym komunikatem', () => {
    for (const zly of ['4500', '450011', '4-5001', 'ab-cde', '45_001', '45-0011']) {
      const wynik = normalizujKodPocztowy(zly)
      expect(wynik.ok).toBe(false)
      expect(wynik.blad).toMatch(/NN-NNN/)
    }
  })
})

describe('wartoscTekstuDoZapisu', () => {
  it('pola tekstowe: obcina spacje, pusty wpis to pusty string', () => {
    expect(wartoscTekstuDoZapisu('custom_install_city', '  Opole ')).toEqual({
      ok: true,
      wartosc: 'Opole',
    })
    expect(wartoscTekstuDoZapisu('custom_nr_domu', '')).toEqual({ ok: true, wartosc: '' })
    expect(wartoscTekstuDoZapisu('custom_powiat', undefined)).toEqual({ ok: true, wartosc: '' })
  })

  it('nr domu z ukosnikiem i litera zostaje bez zmian', () => {
    expect(wartoscTekstuDoZapisu('custom_nr_domu', '12A/3')).toEqual({
      ok: true,
      wartosc: '12A/3',
    })
  })

  it('kod pocztowy idzie przez walidacje', () => {
    expect(wartoscTekstuDoZapisu('custom_install_postal_code', '45001')).toEqual({
      ok: true,
      wartosc: '45-001',
    })
    expect(wartoscTekstuDoZapisu('custom_install_postal_code', '450').ok).toBe(false)
  })
})

describe('czyWartoscSieZmienila', () => {
  it('null, undefined i pusty string to ta sama pusta wartosc', () => {
    expect(czyWartoscSieZmienila(null, '')).toBe(false)
    expect(czyWartoscSieZmienila(undefined, '')).toBe(false)
    expect(czyWartoscSieZmienila('', null)).toBe(false)
  })

  it('rozne teksty to zmiana, takie same nie', () => {
    expect(czyWartoscSieZmienila('Opole', 'Opole')).toBe(false)
    expect(czyWartoscSieZmienila('Opole', 'Nysa')).toBe(true)
    expect(czyWartoscSieZmienila('', 'Nysa')).toBe(true)
    expect(czyWartoscSieZmienila('Nysa', '')).toBe(true)
  })
})
