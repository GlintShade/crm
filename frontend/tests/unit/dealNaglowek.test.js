import { describe, it, expect } from 'vitest'
import {
  skrotProduktu,
  metaSzansy,
  etapyLiczba,
  poczatekEtapu,
  dniWEtapie,
  formatCzasWEtapie,
  czasWEtapie,
  etykietaStatusu,
} from '@/utils/dealNaglowek'
import {
  procesDlaRodzaju,
  nastepnyKrok,
  podpowiedzEtapu,
  rodzajZmianyEtapu,
  pominieteEtapy,
  terminalneStatusy,
} from '@/utils/dealPipeline'

describe('skrotProduktu', () => {
  it('skraca znane rodzaje', () => {
    expect(skrotProduktu('Fotowoltaika')).toBe('PV')
    expect(skrotProduktu('Fotowoltaika + Magazyn')).toBe('PV + ME')
    expect(skrotProduktu('Magazyn energii')).toBe('ME')
    expect(skrotProduktu('Czyste Powietrze')).toBe('Czyste Powietrze')
  })
  it('zostawia inne i puste', () => {
    expect(skrotProduktu('Pompa ciepła')).toBe('Pompa ciepła')
    expect(skrotProduktu('')).toBe('')
    expect(skrotProduktu(null)).toBe('')
  })
})

describe('metaSzansy', () => {
  it('buduje pełną linię', () => {
    expect(
      metaSzansy({
        custom_rodzaj_umowy: 'Fotowoltaika + Magazyn',
        custom_pv_power_kwp: 5.5,
        custom_pojemnosc_kwh: 33,
        custom_install_city: 'Suchy Las',
      }),
    ).toBe('PV + ME · 5,5 kWp · 33 kWh · Suchy Las')
  })
  it('pomija puste i zerowe części', () => {
    expect(
      metaSzansy({
        custom_rodzaj_umowy: 'Fotowoltaika',
        custom_pv_power_kwp: '8.2',
        custom_pojemnosc_kwh: 0,
        custom_install_city: '  ',
      }),
    ).toBe('PV · 8,2 kWp')
  })
  it('puste dla braku dokumentu', () => {
    expect(metaSzansy(null)).toBe('')
    expect(metaSzansy({})).toBe('')
  })
})

describe('etapyLiczba', () => {
  it('odmienia po polsku', () => {
    expect(etapyLiczba(1)).toBe('1 etap')
    expect(etapyLiczba(2)).toBe('2 etapy')
    expect(etapyLiczba(4)).toBe('4 etapy')
    expect(etapyLiczba(5)).toBe('5 etapów')
    expect(etapyLiczba(11)).toBe('11 etapów')
    expect(etapyLiczba(12)).toBe('12 etapów')
    expect(etapyLiczba(22)).toBe('22 etapy')
  })
})

describe('czas w etapie', () => {
  const log = [
    { from: 'Lead', from_date: '2026-11-01 10:00:00' },
    { from: 'Umowa Wygenerowana', from_date: '2026-11-02 09:30:00' },
  ]
  const teraz = new Date(2026, 10, 4, 8, 0, 0)
  it('znajduje początek ostatniego wejścia w status', () => {
    expect(poczatekEtapu(log, 'Umowa Wygenerowana').getDate()).toBe(2)
    expect(poczatekEtapu(log, 'Finansowanie')).toBeNull()
    expect(poczatekEtapu(null, 'Lead')).toBeNull()
  })
  it('liczy dni kalendarzowe', () => {
    expect(dniWEtapie(new Date(2026, 10, 2, 23, 0), teraz)).toBe(2)
    expect(dniWEtapie(new Date(2026, 10, 4, 1, 0), teraz)).toBe(0)
    expect(dniWEtapie(null, teraz)).toBeNull()
  })
  it('formatuje', () => {
    expect(formatCzasWEtapie(0)).toBe('dziś')
    expect(formatCzasWEtapie(1)).toBe('1 dzień')
    expect(formatCzasWEtapie(2)).toBe('2 dni')
    expect(formatCzasWEtapie(null)).toBeNull()
  })
  it('składa całość', () => {
    expect(czasWEtapie(log, 'Umowa Wygenerowana', teraz)).toBe('2 dni')
    expect(czasWEtapie(log, 'Lead', teraz)).toBe('3 dni')
    expect(czasWEtapie([], 'Lead', teraz)).toBeNull()
  })
})

describe('etykietaStatusu', () => {
  it('zamienia typograficzny myślnik na łącznik', () => {
    expect(etykietaStatusu('Wygrana \u2013 montaż')).toBe('Wygrana - montaż')
    expect(etykietaStatusu(null)).toBe('')
  })
})

describe('nastepnyKrok', () => {
  it('OZE: etykieta i zakładka z jednego wpisu', () => {
    expect(nastepnyKrok('OZE', 'Lead')).toEqual({ etykieta: 'Wygeneruj umowę', zakladka: 'Umowa' })
    expect(nastepnyKrok('OZE', 'Umowa Wygenerowana')).toEqual({
      etykieta: 'Wyślij do podpisu',
      zakladka: 'Umowa',
    })
    expect(nastepnyKrok('OZE', 'Umowa Podpisana').zakladka).toBe('Kredyt')
    expect(nastepnyKrok('OZE', 'Finansowanie')).toEqual({
      etykieta: 'Prześlij audyt',
      zakladka: 'Audyt',
    })
  })
  it('OZE: weryfikacja to tekst bez przycisku', () => {
    const k = nastepnyKrok('OZE', 'Weryfikacja Backoffice')
    expect(k.tekst).toBe('Czeka na weryfikację backoffice')
    expect(k.zakladka).toBeUndefined()
  })
  it('OZE: status terminalny i nieznany dają null', () => {
    expect(nastepnyKrok('OZE', 'Przegrana')).toBeNull()
    expect(nastepnyKrok('OZE', 'toString')).toBeNull()
  })
  it('CP: tylko notatka serwera', () => {
    const notes = { Dokumentacja: 'Umowa na obsługę dotacji, GOPS, pełnomocnictwo' }
    expect(nastepnyKrok('CP', 'Dokumentacja', notes)).toEqual({ tekst: notes.Dokumentacja })
    expect(nastepnyKrok('CP', 'Lead', notes)).toBeNull()
    expect(nastepnyKrok('CP', 'Dokumentacja', { Dokumentacja: ' ' })).toBeNull()
  })
  it('brak procesu lub statusu daje null', () => {
    expect(nastepnyKrok(null, 'Lead')).toBeNull()
    expect(nastepnyKrok('OZE', '')).toBeNull()
  })
})

describe('procesDlaRodzaju', () => {
  it('rozpoznaje procesy', () => {
    expect(procesDlaRodzaju('Fotowoltaika')).toBe('OZE')
    expect(procesDlaRodzaju('Czyste Powietrze')).toBe('CP')
    expect(procesDlaRodzaju('')).toBeNull()
    expect(procesDlaRodzaju('Inne')).toBeNull()
  })
})

describe('menu etapu', () => {
  it('podpowiedzi automatycznych etapów', () => {
    expect(podpowiedzEtapu('OZE', 'Umowa Podpisana')).toBe('zwykle sam, po podpisie w Autenti')
    expect(podpowiedzEtapu('OZE', 'Weryfikacja Backoffice')).toBe('sam, po przesłaniu audytu')
    expect(podpowiedzEtapu('OZE', 'Lead')).toBeNull()
    expect(podpowiedzEtapu('CP', 'Lead')).toBeNull()
  })
  it('rodzaj zmiany', () => {
    expect(rodzajZmianyEtapu(1, 2)).toBe('dalej')
    expect(rodzajZmianyEtapu(1, 3)).toBe('przeskok')
    expect(rodzajZmianyEtapu(2, 0)).toBe('wstecz')
    expect(rodzajZmianyEtapu(2, 2)).toBe('ten-sam')
    expect(rodzajZmianyEtapu(2, null)).toBe('terminal')
    expect(rodzajZmianyEtapu(-1, 1)).toBe('przeskok')
  })
  it('pominięte etapy', () => {
    const steps = ['A', 'B', 'C', 'D'].map((status, index) => ({ status, index }))
    expect(pominieteEtapy(steps, 0, 3)).toEqual(['B', 'C'])
    expect(pominieteEtapy(steps, 0, 1)).toEqual([])
  })
  it('terminalne statusy z grupy', () => {
    const payload = {
      steps: [{ status: 'Lead', index: 0 }],
      group: ['Lead', 'Wygrana', 'Przegrana'],
    }
    expect(terminalneStatusy(payload)).toEqual(['Wygrana', 'Przegrana'])
    expect(terminalneStatusy(null)).toEqual([])
  })
})
