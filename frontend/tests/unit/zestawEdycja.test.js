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
  opcjeProducenta,
  roznicaDoOkna,
  stanZOdpowiedzi,
  zastosujPropozycje,
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
