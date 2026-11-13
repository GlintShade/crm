import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  ETYKIETY_KONFIGURACJI,
  MSG_NOTA_PRODUCENTA,
  POLA_KONFIGURACJI,
  POLA_KONFIGURACJI_TEKSTOWE,
  POLE_PRODUCENT,
  doPodgladu,
  doWywolania,
  doZapisu,
  konfiguracjaDoWywolania,
  nowyZestawTyp,
  opcjeProducenta,
  roznicaDoOkna,
  stanZOdpowiedzi,
  zastosujPropozycje,
  wierszeKomunikatow,
  zestawDlaProducenta,
  zmienPoleKonfiguracji,
  czyZmieniony,
} from '@/utils/zestawEdycja'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// POLA_KONFIGURACJI po stronie serwera czytamy jako TEKST (nigdy jako moduł).
function polaKonfiguracjiZSerwera() {
  const zrodlo = fs.readFileSync(path.resolve(__dirname, '../../../crm/api/zestaw.py'), 'utf8')
  const blok = /POLA_KONFIGURACJI: tuple\[str, \.\.\.\] = \(([\s\S]*?)\n\)/.exec(zrodlo)
  expect(blok).not.toBeNull()
  return [...blok[1].matchAll(/"(custom_[a-z_]+)"/g)].map((m) => m[1])
}

function odpowiedz(nad = {}) {
  return {
    linia: 'oze',
    rodzaj: 'Fotowoltaika + Magazyn',
    wiersze: [
      { name: 'a1', idx: 1, typ: 'Falownik', nazwa: 'Hoymiles HIT-15L-G3S 15 kW', ilosc: 1, jednostka: 'szt.', netto: '0.00', brutto: '0.00' },
    ],
    cena: { netto: '40000.00', vat_pct: '8', dotacja: '0', ulga_pct: '12', okres_lat: 10, wplata_wlasna: '0', dodatki_bez_ulgi_brutto: '0' },
    konfiguracja: { custom_producent: 'Sigenergy', custom_falownik: 'Hoymiles HIT-15L-G3S 15 kW', custom_panele: 12 },
    zestaw_typ: 'PREMIUM +',
    ...nad,
  }
}

describe('POLA_KONFIGURACJI', () => {
  it('jest w lockstepie z crm/api/zestaw.py (skład i kolejność)', () => {
    expect(POLA_KONFIGURACJI).toEqual(polaKonfiguracjiZSerwera())
  })

  it('zaczyna się od producenta i ma 15 pól', () => {
    expect(POLA_KONFIGURACJI[0]).toBe('custom_producent')
    expect(POLA_KONFIGURACJI).toHaveLength(15)
  })

  it('nie zawiera zestawu (wyliczany na serwerze)', () => {
    expect(POLA_KONFIGURACJI).not.toContain('custom_zestaw_typ')
  })

  it('każde pole ma etykietę, a Producent i Zestaw mają polskie etykiety', () => {
    for (const pole of POLA_KONFIGURACJI) expect(ETYKIETY_KONFIGURACJI[pole]).toBeTruthy()
    expect(ETYKIETY_KONFIGURACJI.custom_producent).toBe('Producent')
    expect(ETYKIETY_KONFIGURACJI.custom_zestaw_typ).toBe('Zestaw')
  })

  it('tabela tekstowa pomija producenta', () => {
    expect(POLA_KONFIGURACJI_TEKSTOWE).not.toContain(POLE_PRODUCENT)
    expect(POLA_KONFIGURACJI_TEKSTOWE).toHaveLength(14)
  })
})

describe('opcjeProducenta', () => {
  const wartosci = (opcje) => opcje.map((o) => o.value)

  it('sama fotowoltaika: tylko FoxESS', () => {
    expect(wartosci(opcjeProducenta('Fotowoltaika', 'FoxESS'))).toEqual(['FoxESS'])
  })

  it('rodzaje z magazynem: cztery producenci', () => {
    for (const rodzaj of ['Fotowoltaika + Magazyn', 'Magazyn energii']) {
      const opcje = opcjeProducenta(rodzaj, 'Sigenergy')
      expect(wartosci(opcje)).toEqual(['FoxESS', 'Sigenergy', 'Hoymiles', 'Solax'])
      expect(opcje.every((o) => !o.disabled)).toBe(true)
    }
  })

  it('Deye jest tylko wartością bieżącą, zdezaktywowaną', () => {
    const opcje = opcjeProducenta('Fotowoltaika + Magazyn', 'Deye')
    expect(opcje[0]).toEqual({ value: 'Deye', label: 'Deye', disabled: true })
    expect(wartosci(opcje).filter((v) => v === 'Deye')).toHaveLength(1)
    expect(opcje.slice(1).every((o) => !o.disabled)).toBe(true)
  })

  it('Deye nie pojawia się, gdy nie jest wartością bieżącą', () => {
    expect(wartosci(opcjeProducenta('Magazyn energii', 'Hoymiles'))).not.toContain('Deye')
  })

  it('pusty producent bieżący: zdezaktywowana opcja "(nie ustawiono)"', () => {
    const opcje = opcjeProducenta('Magazyn energii', '')
    expect(opcje[0]).toEqual({ value: '', label: '(nie ustawiono)', disabled: true })
  })

  it('PV z historycznym producentem innym niż FoxESS pokazuje go jako zdezaktywowanego', () => {
    const opcje = opcjeProducenta('Fotowoltaika', 'Sigenergy')
    expect(opcje[0]).toEqual({ value: 'Sigenergy', label: 'Sigenergy', disabled: true })
    expect(wartosci(opcje)).toEqual(['Sigenergy', 'FoxESS'])
  })
})

describe('zestawDlaProducenta', () => {
  it('mapuje producenta na zestaw przy magazynie', () => {
    expect(zestawDlaProducenta('Hoymiles', 'Fotowoltaika + Magazyn')).toBe('COMFORT')
    expect(zestawDlaProducenta('Solax', 'Magazyn energii')).toBe('COMFORT PREMIUM')
    expect(zestawDlaProducenta('Sigenergy', 'Magazyn energii')).toBe('PREMIUM +')
  })

  it('FoxESS, Deye, brak producenta i sama PV dają pusty zestaw', () => {
    expect(zestawDlaProducenta('FoxESS', 'Fotowoltaika + Magazyn')).toBe('')
    expect(zestawDlaProducenta('Deye', 'Fotowoltaika + Magazyn')).toBe('')
    expect(zestawDlaProducenta('', 'Fotowoltaika + Magazyn')).toBe('')
    expect(zestawDlaProducenta('Sigenergy', 'Fotowoltaika')).toBe('')
    expect(zestawDlaProducenta('Hoymiles', 'Rozbudowa PV/ME')).toBe('')
  })
})

describe('nowyZestawTyp', () => {
  const MAG = 'Fotowoltaika + Magazyn'
  it('przy zmianie producenta wylicza zestaw', () => {
    expect(nowyZestawTyp('Sigenergy', 'Hoymiles', 'PREMIUM +', MAG)).toBe('COMFORT')
    expect(nowyZestawTyp('Hoymiles', 'FoxESS', 'COMFORT', MAG)).toBe('')
  })
  it('bez zmiany producenta zwraca zestaw zapisany na szansie', () => {
    expect(nowyZestawTyp('Sigenergy', 'Sigenergy', '', MAG)).toBe('')
    expect(nowyZestawTyp('Sigenergy', 'Sigenergy', undefined, MAG)).toBe('')
    expect(nowyZestawTyp('Hoymiles', 'Hoymiles', 'COMFORT +', MAG)).toBe('COMFORT +')
  })
})

describe('stan, wywołania i zmiana producenta', () => {
  it('stan niesie producenta z konfiguracji', () => {
    expect(stanZOdpowiedzi(odpowiedz()).konfiguracja.custom_producent).toBe('Sigenergy')
  })

  it('podgląd OZE dostaje wybranego producenta, zapis ma go w konfiguracji', () => {
    let stan = stanZOdpowiedzi(odpowiedz())
    stan = zmienPoleKonfiguracji(stan, POLE_PRODUCENT, 'Hoymiles')
    expect(doPodgladu(stan).producent).toBe('Hoymiles')
    expect(doZapisu(stan).konfiguracja.custom_producent).toBe('Hoymiles')
    expect(doZapisu(stan).konfiguracja).not.toHaveProperty('custom_zestaw_typ')
    expect(konfiguracjaDoWywolania(stan).custom_producent).toBe('Hoymiles')
  })

  it('doWywolania nie niesie producenta (to argumenty zapisu)', () => {
    expect(doWywolania(stanZOdpowiedzi(odpowiedz()))).not.toHaveProperty('producent')
  })

  it('podgląd CP nie niesie producenta', () => {
    const stan = stanZOdpowiedzi({ linia: 'cp', wiersze: [], cena_cp: {}, konfiguracja: {} })
    expect(doPodgladu(stan)).not.toHaveProperty('producent')
  })

  it('sama zmiana producenta liczy się jako zmiana formularza', () => {
    const poczatkowy = stanZOdpowiedzi(odpowiedz())
    expect(czyZmieniony(poczatkowy, poczatkowy)).toBe(false)
    expect(czyZmieniony(poczatkowy, zmienPoleKonfiguracji(poczatkowy, POLE_PRODUCENT, 'Hoymiles'))).toBe(true)
  })

  it('propozycja z podglądu nie nadpisuje producenta', () => {
    const stan = zmienPoleKonfiguracji(stanZOdpowiedzi(odpowiedz()), POLE_PRODUCENT, 'Hoymiles')
    const po = zastosujPropozycje(stan, { custom_falownik: 'Inny', custom_producent: 'Solax' })
    expect(po.konfiguracja.custom_producent).toBe('Hoymiles')
    expect(po.konfiguracja.custom_falownik).toBe('Inny')
  })
})

describe('roznicaDoOkna: producent i zestaw', () => {
  it('pokazuje Producent i Zestaw na początku listy konfiguracji', () => {
    const przed = { custom_producent: 'Sigenergy', custom_zestaw_typ: 'PREMIUM +', custom_falownik: 'A' }
    const po = { custom_producent: 'Hoymiles', custom_zestaw_typ: 'COMFORT', custom_falownik: 'B' }
    const okno = roznicaDoOkna({}, {}, {}, przed, po)
    expect(okno.konfiguracja.map((k) => k.etykieta)).toEqual(['Producent', 'Zestaw', 'Falownik'])
    expect(okno.konfiguracja[0]).toEqual({ etykieta: 'Producent', przed: 'Sigenergy', po: 'Hoymiles' })
    expect(okno.konfiguracja[1]).toEqual({ etykieta: 'Zestaw', przed: 'PREMIUM +', po: 'COMFORT' })
  })

  it('zestaw wyliczony na pusty pokazuje myślnik', () => {
    const okno = roznicaDoOkna({}, {}, {}, { custom_zestaw_typ: 'COMFORT' }, { custom_zestaw_typ: '' })
    expect(okno.konfiguracja).toEqual([{ etykieta: 'Zestaw', przed: 'COMFORT', po: '-' }])
  })

  it('bez zmiany producenta i zestawu nie ma ich w oknie', () => {
    const k = { custom_producent: 'Solax', custom_zestaw_typ: 'COMFORT PREMIUM' }
    expect(roznicaDoOkna({}, {}, {}, k, { ...k }).konfiguracja).toEqual([])
  })
})

describe('nota o cenie', () => {
  it('ma ustalony tekst bez pauz', () => {
    expect(MSG_NOTA_PRODUCENTA).toBe('Zmiana producenta nie przelicza ceny ani kosztów, ustaw netto ręcznie.')
    expect(MSG_NOTA_PRODUCENTA).not.toMatch(/[\u2013\u2014]/)
  })
})

describe('wierszeKomunikatow', () => {
  it('rozbija komunikaty po nowej linii i wyciąga typ pozycji', () => {
    const t =
      'Pozycja Falownik "Sigenergy TP2 6 kW" jest producenta Sigenergy, a wybrany producent to Hoymiles. Zmień producenta albo pozycję.\n' +
      'Pozycja Magazyn energii "Sigenergy 12 kWh (6+6)" jest producenta Sigenergy, a wybrany producent to Hoymiles. Zmień producenta albo pozycję.'
    expect(wierszeKomunikatow(t)).toEqual([
      { typ: 'Falownik', tresc: '"Sigenergy TP2 6 kW" jest producenta Sigenergy, a wybrany producent to Hoymiles. Zmień producenta albo pozycję.' },
      { typ: 'Magazyn energii', tresc: '"Sigenergy 12 kWh (6+6)" jest producenta Sigenergy, a wybrany producent to Hoymiles. Zmień producenta albo pozycję.' },
    ])
  })
  it('przycina, pomija puste i zostawia inne komunikaty bez typu', () => {
    expect(wierszeKomunikatow('  Zly VAT \r\n\n  \nProducent jest wymagany.')).toEqual([
      { typ: '', tresc: 'Zly VAT' },
      { typ: '', tresc: 'Producent jest wymagany.' },
    ])
  })
  it('przyjmuje tablicę i puste wejście', () => {
    expect(wierszeKomunikatow(['A', 'B\nC'])).toHaveLength(3)
    expect(wierszeKomunikatow('')).toEqual([])
    expect(wierszeKomunikatow(null)).toEqual([])
  })
})

// ---- koszty i marże (ops#341) ----
import {
  bilans,
  bledyKoszty,
  dodajSamKoszt,
  dodajWiersz,
  kosztPozycji,
  kosztyDoWywolania,
  liczbaPustychKosztow,
  linieBezPozycjiWidoczne,
  marzaBylo,
  przelaczPusteKoszty,
  przesunWiersz,
  roznicaKosztowDoOkna,
  usunLinieKosztu,
  usunWiersz,
  zmienKosztPozycji,
  zmienLinieKosztu,
  zmienMarze,
  zmienPoleCeny,
  MSG_PROWIZJA_NALICZONA,
} from '@/utils/zestawEdycja'

function odpKoszty(nad = {}) {
  return odpowiedz({
    wiersze: [
      { name: 'a1', typ: 'Falownik', nazwa: 'F', ilosc: 1, jednostka: 'szt.', netto: '0', brutto: '0' },
      { name: 'a2', typ: 'Panele PV', nazwa: 'P', ilosc: 11, jednostka: 'szt.', netto: '0', brutto: '0' },
      { name: 'a3', typ: 'Licznik', nazwa: 'L', ilosc: 1, jednostka: 'szt.', netto: '0', brutto: '0' },
    ],
    cena: { netto: '83921.00', vat_pct: '8', dotacja: '0', ulga_pct: '12', okres_lat: 10, wplata_wlasna: '0', dodatki_bez_ulgi_brutto: '0', podstawa: 'netto' },
    koszty: {
      linie: [
        { klucz: 'k_falownik', etykieta: 'Falownik', koszt_plan: '3251.00', wiersz: 0, reczna: false, korekta: false },
        { klucz: 'k_panele', etykieta: 'Panele', koszt_plan: '3960.00', wiersz: 1, reczna: false, korekta: false },
        { klucz: 'k_sterownik', etykieta: 'Sterownik', koszt_plan: '969.00', wiersz: null, reczna: false, korekta: false },
        { klucz: 'k_kilometrowka', etykieta: 'Kilometrówka', koszt_plan: '0.00', wiersz: null, reczna: false, korekta: false },
      ],
      skladniki_marzy: [
        { klucz: 'narzut', etykieta: 'Narzut handlowca', kwota: '10000.00', kwota_pierwotna: null },
        { klucz: 'marza_proenergy', etykieta: 'Marża ProEnergy', kwota: '5000.00', kwota_pierwotna: null },
      ],
      podsumowanie: { netto: '83921.00', koszt_plan: '8180.00', marza_plan: '15000.00' },
      rozliczenie_handlowca: { naliczone: false },
    },
    ...nad,
  })
}

describe('koszty: brak snapshotu i CP', () => {
  it('koszty null: stan.koszty null i brak parametru koszty', () => {
    const s = stanZOdpowiedzi(odpowiedz())
    expect(s.koszty).toBeNull()
    expect('koszty' in doPodgladu(s)).toBe(false)
    expect('koszty' in doZapisu(s)).toBe(false)
    expect(bilans(s, '1')).toBeNull()
    expect(roznicaKosztowDoOkna(s, 0, false)).toBeNull()
  })
  it('CP ignoruje koszty', () => {
    const s = stanZOdpowiedzi({ ...odpKoszty(), linia: 'cp', cena_cp: {} })
    expect(s.koszty).toBeNull()
  })
})

describe('koszty: ładunek', () => {
  it('pełna lista linii z indeksami wiersz, marze tylko zmienione', () => {
    let s = stanZOdpowiedzi(odpKoszty())
    expect(kosztyDoWywolania(s)).toEqual({
      linie: [
        { klucz: 'k_falownik', etykieta: 'Falownik', koszt_plan: '3251.00', wiersz: 0 },
        { klucz: 'k_panele', etykieta: 'Panele', koszt_plan: '3960.00', wiersz: 1 },
        { klucz: 'k_sterownik', etykieta: 'Sterownik', koszt_plan: '969.00', wiersz: null },
        { klucz: 'k_kilometrowka', etykieta: 'Kilometrówka', koszt_plan: '0.00', wiersz: null },
      ],
      marze: {},
    })
    s = zmienMarze(s, 'narzut', '7000')
    expect(doPodgladu(s).koszty.marze).toEqual({ narzut: '7000.00' })
    expect(doZapisu(s).koszty.marze).toEqual({ narzut: '7000.00' })
  })

  it('nowa pozycja z kosztem: linia z kluczem null i indeksem nowego wiersza', () => {
    let s = stanZOdpowiedzi(odpKoszty())
    s = dodajWiersz(s, { ...s.wiersze[0], klucz: 'nowy', name: null, typ: 'EMS', nazwa: 'EMS z integratorem' })
    s = zmienKosztPozycji(s, 'nowy', '3000')
    const linie = kosztyDoWywolania(s).linie
    expect(linie[linie.length - 1]).toEqual({ klucz: null, etykieta: 'EMS z integratorem', koszt_plan: '3000.00', wiersz: 3 })
  })

  it('indeksy wiersz po usunięciu i przesunięciu pozycji', () => {
    let s = stanZOdpowiedzi(odpKoszty())
    s = przesunWiersz(s, 1, -1)
    let linie = kosztyDoWywolania(s).linie
    expect(linie.find((l) => l.klucz === 'k_panele').wiersz).toBe(0)
    expect(linie.find((l) => l.klucz === 'k_falownik').wiersz).toBe(1)
    s = usunWiersz(s, 0) // panele
    linie = kosztyDoWywolania(s).linie
    expect(linie.find((l) => l.klucz === 'k_panele')).toBeUndefined()
    expect(linie.find((l) => l.klucz === 'k_falownik').wiersz).toBe(0)
    expect(s.koszty.linie.some((l) => l.klucz === 'k_panele')).toBe(false)
  })

  it('puste pole kosztu pozycji usuwa linię, wpisanie tworzy', () => {
    let s = stanZOdpowiedzi(odpKoszty())
    expect(kosztPozycji(s, s.wiersze[0].klucz)).toBe('3251.00')
    s = zmienKosztPozycji(s, s.wiersze[0].klucz, '')
    expect(kosztPozycji(s, s.wiersze[0].klucz)).toBe('')
    expect(kosztyDoWywolania(s).linie.some((l) => l.klucz === 'k_falownik')).toBe(false)
    s = zmienKosztPozycji(s, s.wiersze[2].klucz, '12,5')
    expect(kosztyDoWywolania(s).linie.at(-1)).toMatchObject({ klucz: null, koszt_plan: '12.50', wiersz: 2 })
  })

  it('dodaj sam koszt: linia reczna z kluczem null i wiersz null; bez nazwy blokuje zapis', () => {
    let s = dodajSamKoszt(stanZOdpowiedzi(odpKoszty()))
    expect(bledyKoszty(s)).toHaveLength(1)
    const lid = s.koszty.linie.at(-1).lid
    s = zmienLinieKosztu(s, lid, 'etykieta', 'Dojazd')
    s = zmienLinieKosztu(s, lid, 'koszt', '250')
    expect(bledyKoszty(s)).toHaveLength(0)
    expect(kosztyDoWywolania(s).linie.at(-1)).toEqual({ klucz: null, etykieta: 'Dojazd', koszt_plan: '250.00', wiersz: null })
    s = usunLinieKosztu(s, lid)
    expect(kosztyDoWywolania(s).linie).toHaveLength(4)
  })
})

describe('koszty: ukrywanie pustych', () => {
  it('zero bez pozycji schowane, przełącznik w obie strony, świeżo dodana widoczna', () => {
    let s = stanZOdpowiedzi(odpKoszty())
    expect(liczbaPustychKosztow(s)).toBe(1)
    expect(linieBezPozycjiWidoczne(s).map((l) => l.klucz)).toEqual(['k_sterownik'])
    s = przelaczPusteKoszty(s)
    expect(linieBezPozycjiWidoczne(s)).toHaveLength(2)
    s = przelaczPusteKoszty(s)
    expect(linieBezPozycjiWidoczne(s)).toHaveLength(1)
    s = dodajSamKoszt(s)
    expect(linieBezPozycjiWidoczne(s)).toHaveLength(2)
  })
  it('schowana linia nadal idzie w ładunku', () => {
    const s = stanZOdpowiedzi(odpKoszty())
    expect(kosztyDoWywolania(s).linie.some((l) => l.klucz === 'k_kilometrowka')).toBe(true)
  })
})

describe('koszty: bilans w groszach', () => {
  it('zgadza, do pokrycia, nadwyżka', () => {
    let s = stanZOdpowiedzi(odpKoszty())
    // koszty 8180 + marze 15000 = 23180 przy netto 83921: nadwyzka
    let b = bilans(s)
    expect(b).toMatchObject({ netto: 8392100, koszty: 818000, marze: 1500000, roznica: 8392100 - 818000 - 1500000, status: 'nadwyzka' })
    s = zmienPoleCeny(s, 'netto', '23180')
    expect(bilans(s).status).toBe('zgadza')
    s = zmienKosztPozycji(s, s.wiersze[2].klucz, '3000')
    b = bilans(s)
    expect(b.status).toBe('do_pokrycia')
    expect(b.roznica).toBe(-300000)
  })
  it('podstawa brutto: netto z podgladu serwera', () => {
    let s = stanZOdpowiedzi(odpKoszty())
    s = zmienPoleCeny(s, 'brutto', '90635.88')
    expect(s.cena.podstawa).toBe('brutto')
    expect(bilans(s, '83921.00').netto).toBe(8392100)
  })
  it('bez zaokragleń zmiennoprzecinkowych', () => {
    let s = stanZOdpowiedzi(odpKoszty())
    s = zmienKosztPozycji(s, s.wiersze[0].klucz, '0.1')
    s = zmienKosztPozycji(s, s.wiersze[1].klucz, '0.2')
    expect(bilans(s).koszty).toBe(10 + 20 + 96900)
  })
})

describe('koszty: marza i okno', () => {
  it('bylo tylko dla zmienionych; pierwotna z serwera ma pierwszenstwo', () => {
    let s = stanZOdpowiedzi(odpKoszty())
    expect(marzaBylo(s.koszty.marze[0])).toBe('')
    s = zmienMarze(s, 'narzut', '7000')
    expect(marzaBylo(s.koszty.marze[0])).toBe('10000.00')
    const s2 = stanZOdpowiedzi(
      odpKoszty({ koszty: { ...odpKoszty().koszty, skladniki_marzy: [{ klucz: 'narzut', etykieta: 'N', kwota: '7000.00', kwota_pierwotna: '10000.00' }] } }),
    )
    expect(marzaBylo(s2.koszty.marze[0])).toBe('10000.00')
  })

  it('okno: koszty przed i po, marze, ostrzezenie prowizji tylko gdy naliczona i narzut', () => {
    let s = stanZOdpowiedzi(odpKoszty())
    expect(roznicaKosztowDoOkna(s, 818000, true)).toMatchObject({ koszty: null, marze: [], ostrzezenie: '' })
    s = zmienKosztPozycji(s, s.wiersze[2].klucz, '3000')
    s = zmienMarze(s, 'marza_proenergy', '4000')
    let r = roznicaKosztowDoOkna(s, 818000, true)
    expect(r.koszty.przed).toContain('8')
    expect(r.marze).toHaveLength(1)
    expect(r.ostrzezenie).toBe('')
    s = zmienMarze(s, 'narzut', '7000')
    r = roznicaKosztowDoOkna(s, 818000, true)
    expect(r.ostrzezenie).toBe(MSG_PROWIZJA_NALICZONA)
    expect(roznicaKosztowDoOkna(s, 818000, false).ostrzezenie).toBe('')
  })

  it('czyZmieniony widzi zmianę kosztu i marzy, nie samo ukrycie pustych', () => {
    const p = stanZOdpowiedzi(odpKoszty())
    expect(czyZmieniony(p, przelaczPusteKoszty(p))).toBe(false)
    expect(czyZmieniony(p, zmienMarze(p, 'narzut', '7000'))).toBe(true)
    expect(czyZmieniony(p, zmienKosztPozycji(p, p.wiersze[0].klucz, '1'))).toBe(true)
  })
})
