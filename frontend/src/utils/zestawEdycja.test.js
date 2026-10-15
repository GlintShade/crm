import {
  POLA_CENY_WEJSCIE,
  POLA_KONFIGURACJI,
  cenaDoWywolania,
  czyBladWersji,
  czyTypInny,
  czyZmieniony,
  dodajWiersz,
  doWywolania,
  doZapisu,
  etykietaTypu,
  komunikatBledu,
  konfiguracjaDoWywolania,
  opisOstatniejEdycji,
  przesunWiersz,
  pustyWiersz,
  roznicaDoOkna,
  stanZOdpowiedzi,
  usunWiersz,
  zastosujPropozycje,
  zmienPoleCeny,
  zmienPoleKonfiguracji,
  zmienPoleWiersza,
} from '@/utils/zestawEdycja'

const KONF = {
  custom_falownik: 'Deye 5K',
  custom_bateria: 'Deye BOS',
  custom_pojemnosc_kwh: 5.12,
  custom_panel: 'JA Solar',
  custom_panele: 12,
  custom_konstrukcja: 'Dach skosny',
  custom_kabel_m: 30,
  custom_licznik_dodatkowy: 'Nie',
  custom_dod_klima: '',
  custom_dod_panele: 0,
  custom_dod_panele_mikro: 0,
  custom_ems_breeze: 'Tak',
  custom_pstryk: 'Nie',
  custom_ev_ladowarka: '',
}

function odp() {
  return {
    wiersze: [
      { name: 'a1', idx: 1, typ: 'Falownik', nazwa: 'Deye 5K', ilosc: 1, jednostka: 'szt.', netto: 0, brutto: 0 },
      { name: 'a2', idx: 2, typ: 'Kabel', nazwa: 'Kabel AC', ilosc: 30, jednostka: 'm', netto: 0, brutto: 0 },
    ],
    cena: { netto: 45000, vat_pct: 8, dotacja: 16000, ulga_pct: '12', okres_lat: 10, wplata_wlasna: 0, dodatki_bez_ulgi_brutto: 0, brutto: 48600 },
    konfiguracja: KONF,
  }
}

describe('stanZOdpowiedzi', () => {
  it('buduje wiersze z kluczem name i polami tekstowymi', () => {
    const s = stanZOdpowiedzi(odp())
    expect(s.wiersze).toHaveLength(2)
    expect(s.wiersze[0]).toMatchObject({ klucz: 'a1', name: 'a1', typ: 'Falownik', ilosc: '1' })
  })
  it('bierze tylko pola wejsciowe ceny', () => {
    const s = stanZOdpowiedzi(odp())
    expect(Object.keys(s.cena)).toEqual(POLA_CENY_WEJSCIE)
    expect(s.cena.netto).toBe('45000')
  })
  it('ma wszystkie 14 pol konfiguracji', () => {
    const s = stanZOdpowiedzi(odp())
    expect(Object.keys(s.konfiguracja)).toEqual(POLA_KONFIGURACJI)
    expect(POLA_KONFIGURACJI).toHaveLength(14)
  })
  it('obsluguje pusta odpowiedz', () => {
    const s = stanZOdpowiedzi(null)
    expect(s.wiersze).toEqual([])
    expect(s.reczne).toEqual([])
  })
})

describe('operacje niemutowalne', () => {
  it('dodajWiersz zwraca nowy stan i nie rusza starego', () => {
    const s = stanZOdpowiedzi(odp())
    const n = dodajWiersz(s, pustyWiersz('Magazyn energii'))
    expect(n).not.toBe(s)
    expect(s.wiersze).toHaveLength(2)
    expect(n.wiersze).toHaveLength(3)
    expect(n.wiersze[2].name).toBeNull()
  })
  it('nowe wiersze maja unikalne klucze', () => {
    expect(pustyWiersz().klucz).not.toBe(pustyWiersz().klucz)
  })
  it('usunWiersz usuwa i nie rusza starego', () => {
    const s = stanZOdpowiedzi(odp())
    const n = usunWiersz(s, 1)
    expect(n.wiersze.map((w) => w.name)).toEqual(['a1'])
    expect(s.wiersze).toHaveLength(2)
  })
  it('usunWiersz poza zakresem zwraca ten sam stan', () => {
    const s = stanZOdpowiedzi(odp())
    expect(usunWiersz(s, 5)).toBe(s)
  })
  it('przesunWiersz w dol i w gore', () => {
    const s = stanZOdpowiedzi(odp())
    const d = przesunWiersz(s, 0, 1)
    expect(d.wiersze.map((w) => w.name)).toEqual(['a2', 'a1'])
    expect(przesunWiersz(d, 1, -1).wiersze.map((w) => w.name)).toEqual(['a1', 'a2'])
    expect(s.wiersze.map((w) => w.name)).toEqual(['a1', 'a2'])
  })
  it('przesunWiersz poza krawedz nic nie robi', () => {
    const s = stanZOdpowiedzi(odp())
    expect(przesunWiersz(s, 0, -1)).toBe(s)
    expect(przesunWiersz(s, 1, 1)).toBe(s)
  })
  it('zmienPoleWiersza zmienia tylko wskazany wiersz', () => {
    const s = stanZOdpowiedzi(odp())
    const n = zmienPoleWiersza(s, 1, 'ilosc', '40')
    expect(n.wiersze[1].ilosc).toBe('40')
    expect(n.wiersze[0]).toBe(s.wiersze[0])
    expect(s.wiersze[1].ilosc).toBe('30')
  })
  it('zmienPoleCeny nie mutuje', () => {
    const s = stanZOdpowiedzi(odp())
    const n = zmienPoleCeny(s, 'netto', '50000')
    expect(n.cena.netto).toBe('50000')
    expect(s.cena.netto).toBe('45000')
  })
  it('zmienPoleKonfiguracji oznacza pole jako reczne', () => {
    const s = stanZOdpowiedzi(odp())
    const n = zmienPoleKonfiguracji(s, 'custom_falownik', 'Deye 6K')
    expect(n.konfiguracja.custom_falownik).toBe('Deye 6K')
    expect(n.reczne).toEqual(['custom_falownik'])
    expect(zmienPoleKonfiguracji(n, 'custom_falownik', 'X').reczne).toEqual(['custom_falownik'])
    expect(s.reczne).toEqual([])
  })
})

describe('zastosujPropozycje', () => {
  it('nadpisuje pola nieruszone i zachowuje reczne', () => {
    let s = stanZOdpowiedzi(odp())
    s = zmienPoleKonfiguracji(s, 'custom_falownik', 'Reczny')
    const n = zastosujPropozycje(s, { ...KONF, custom_falownik: 'Z podgladu', custom_kabel_m: 40, _ostrzezenia: ['x'] })
    expect(n.konfiguracja.custom_falownik).toBe('Reczny')
    expect(n.konfiguracja.custom_kabel_m).toBe(40)
    expect(n.konfiguracja._ostrzezenia).toBeUndefined()
  })
  it('null propozycja zwraca ten sam stan', () => {
    const s = stanZOdpowiedzi(odp())
    expect(zastosujPropozycje(s, null)).toBe(s)
  })
})

describe('serializacja', () => {
  it('doWywolania: name tylko dla istniejacych, ilosc jako liczba', () => {
    let s = stanZOdpowiedzi(odp())
    s = dodajWiersz(s, { ...pustyWiersz('Magazyn energii'), nazwa: ' Deye BOS ', ilosc: '2,5' })
    const w = doWywolania(s).wiersze
    expect(w[0]).toEqual({ name: 'a1', typ: 'Falownik', nazwa: 'Deye 5K', ilosc: 1, jednostka: 'szt.' })
    expect(w[2]).toEqual({ typ: 'Magazyn energii', nazwa: 'Deye BOS', ilosc: 2.5, jednostka: 'szt.' })
    expect('name' in w[2]).toBe(false)
  })
  it('puste i smieciowe ilosci daja 0', () => {
    let s = stanZOdpowiedzi(odp())
    s = zmienPoleWiersza(s, 0, 'ilosc', '')
    s = zmienPoleWiersza(s, 1, 'ilosc', 'abc')
    expect(doWywolania(s).wiersze.map((w) => w.ilosc)).toEqual([0, 0])
  })
  it('cena: tylko pola wejsciowe, liczby, ulga jako tekst', () => {
    const c = cenaDoWywolania(stanZOdpowiedzi(odp()))
    expect(Object.keys(c)).toEqual(POLA_CENY_WEJSCIE)
    expect(c.netto).toBe(45000)
    expect(c.ulga_pct).toBe('12')
    expect(c.brutto).toBeUndefined()
  })
  it('ulga z przecinkiem i pusta', () => {
    let s = zmienPoleCeny(stanZOdpowiedzi(odp()), 'ulga_pct', '8,5')
    expect(cenaDoWywolania(s).ulga_pct).toBe('8.5')
    s = zmienPoleCeny(s, 'ulga_pct', '')
    expect(cenaDoWywolania(s).ulga_pct).toBe('0')
  })
  it('konfiguracja: liczbowe jako liczby, reszta tekst', () => {
    const k = konfiguracjaDoWywolania(zmienPoleKonfiguracji(stanZOdpowiedzi(odp()), 'custom_kabel_m', '45'))
    expect(k.custom_kabel_m).toBe(45)
    expect(k.custom_falownik).toBe('Deye 5K')
    expect(Object.keys(k)).toEqual(POLA_KONFIGURACJI)
  })
  it('doZapisu przycina powod do 500 znakow', () => {
    const z = doZapisu(stanZOdpowiedzi(odp()), `  ${'a'.repeat(600)}`)
    expect(z.powod).toHaveLength(500)
    expect(Object.keys(z).sort()).toEqual(['cena', 'konfiguracja', 'powod', 'wiersze'])
  })
})

describe('czyZmieniony', () => {
  it('false dla identycznego stanu', () => {
    const s = stanZOdpowiedzi(odp())
    expect(czyZmieniony(s, stanZOdpowiedzi(odp()))).toBe(false)
  })
  it('true po zmianie wiersza, ceny, konfiguracji i kolejnosci', () => {
    const s = stanZOdpowiedzi(odp())
    expect(czyZmieniony(s, zmienPoleWiersza(s, 0, 'nazwa', 'Inny'))).toBe(true)
    expect(czyZmieniony(s, zmienPoleCeny(s, 'netto', '1'))).toBe(true)
    expect(czyZmieniony(s, zmienPoleKonfiguracji(s, 'custom_panele', '13'))).toBe(true)
    expect(czyZmieniony(s, przesunWiersz(s, 0, 1))).toBe(true)
  })
  it('false gdy zmiana tylko formatu liczby (30 vs 30,0)', () => {
    const s = stanZOdpowiedzi(odp())
    expect(czyZmieniony(s, zmienPoleWiersza(s, 1, 'ilosc', '30,0'))).toBe(false)
  })
})

describe('typy', () => {
  it('etykietaTypu', () => {
    expect(etykietaTypu('Kabel')).toBe('Kabel')
    expect(etykietaTypu('  ')).toBe('-')
  })
  it('czyTypInny', () => {
    expect(czyTypInny('Kabel', ['Kabel'])).toBe(false)
    expect(czyTypInny('Cos', ['Kabel'])).toBe(true)
    expect(czyTypInny('', ['Kabel'])).toBe(false)
  })
})

describe('roznicaDoOkna', () => {
  it('puste sekcje dla braku zmian', () => {
    const r = roznicaDoOkna({}, { netto: 1 }, { netto: 1 }, KONF, KONF)
    expect(r).toEqual({ dodane: [], usuniete: [], zmienione: [], cena: [], konfiguracja: [] })
  })
  it('obsluguje null we wszystkich argumentach', () => {
    const r = roznicaDoOkna(null, null, null, null, null)
    expect(r.dodane).toEqual([])
    expect(r.cena).toEqual([])
  })
  it('pelne sekcje', () => {
    const roznice = {
      dodane: [{ typ: 'Magazyn energii', nazwa: 'Deye BOS', ilosc: 2, jednostka: 'szt.' }],
      usuniete: [{ typ: 'Kabel', nazwa: '', ilosc: 30, jednostka: 'm' }],
      zmienione: [{ stary: { typ: 'Panele PV', ilosc: 12 }, nowy: { typ: 'Panele PV', ilosc: 14 }, pola: ['ilosc'] }],
    }
    const r = roznicaDoOkna(
      roznice,
      { netto: 45000, brutto: 48600, dotacja: 16000 },
      { netto: 48200, brutto: 52056, dotacja: 16000 },
      KONF,
      { ...KONF, custom_kabel_m: 0 },
    )
    expect(r.dodane).toEqual(['Magazyn energii "Deye BOS" x 2 szt.'])
    expect(r.usuniete).toEqual(['Kabel x 30 m'])
    expect(r.zmienione).toEqual(['Panele PV: ilość 12 -> 14'])
    expect(r.cena.map((c) => c.etykieta)).toEqual(['Netto', 'Brutto'])
    expect(r.cena[0].przed).toContain('45')
    expect(r.cena[0].po).toContain('zł')
    expect(r.konfiguracja).toEqual([{ etykieta: 'Dodatkowy kabel (m)', przed: '30', po: '0' }])
  })
  it('w tekstach nie ma myslnikow em ani en', () => {
    const r = roznicaDoOkna(
      { zmienione: [{ stary: { typ: 'A', nazwa: 'x' }, nowy: { typ: 'A', nazwa: 'y' }, pola: ['nazwa'] }] },
      null,
      null,
      null,
      null,
    )
    expect(r.zmienione[0]).not.toMatch(/[\u2013\u2014]/)
  })
})

describe('bledy i opis edycji', () => {
  it('komunikatBledu', () => {
    expect(komunikatBledu({ messages: ['Zly VAT'] }, 'x')).toBe('Zly VAT')
    expect(komunikatBledu({ message: 'boom' }, 'x')).toBe('boom')
    expect(komunikatBledu(null, 'x')).toBe('x')
  })
  it('czyBladWersji', () => {
    expect(czyBladWersji('Dokument został zmodyfikowany po otwarciu')).toBe(true)
    expect(czyBladWersji('Niepoprawny VAT')).toBe(false)
  })
  it('opisOstatniejEdycji z powodem i bez', () => {
    const e = { kiedy: '2026-10-15 09:05:00', kto: 'Jan Kowalski', powod: 'aneks 1' }
    expect(opisOstatniejEdycji(e)).toBe('15.10.2026 09:05, Jan Kowalski, powód: aneks 1')
    expect(opisOstatniejEdycji({ ...e, powod: '' })).toBe('15.10.2026 09:05, Jan Kowalski')
    expect(opisOstatniejEdycji(null)).toBe('')
  })
})
