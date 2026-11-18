import { describe, it, expect } from 'vitest'
import {
  MAKS_ETAPOW_BEZ_ZWARCIA,
  czyZwarty,
  czasOd,
  tekstEtapu,
  tekstDalej,
  normalizujWariant,
  segmentKlasa,
  tekstNumeruEtapu,
  liczbaRzedowPaska,
  podzielNaRzedy,
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
  const STEPS_OZE = [
    'Lead',
    'Umowa Wygenerowana',
    'Umowa Podpisana',
    'Finansowanie',
    'Weryfikacja Backoffice',
    'Montaż',
    'Obsługa pomontażowa',
    'Wygrana - zakończona',
  ].map((status, index) => ({ status, index }))

  it('OZE: etapy 1 i 2 mają etykietę i zakładkę z jednego wpisu (bez steps)', () => {
    expect(nastepnyKrok('OZE', 'Lead')).toEqual({ etykieta: 'Wygeneruj umowę', zakladka: 'Umowa' })
    expect(nastepnyKrok('OZE', 'Umowa Wygenerowana')).toEqual({
      etykieta: 'Wyślij do podpisu',
      zakladka: 'Umowa',
    })
    expect(nastepnyKrok('OZE', 'Lead', null, STEPS_OZE).zakladka).toBe('Umowa')
  })
  it('OZE: od etapu 3 wpis powstaje z następnego kroku w steps', () => {
    const oczekiwane = {
      'Umowa Podpisana': 'Finansowanie',
      Finansowanie: 'Weryfikacja Backoffice',
      'Weryfikacja Backoffice': 'Montaż',
      Montaż: 'Obsługa pomontażowa',
      'Obsługa pomontażowa': 'Wygrana - zakończona',
    }
    Object.entries(oczekiwane).forEach(([status, nast]) => {
      expect(nastepnyKrok('OZE', status, null, STEPS_OZE)).toEqual({
        etykieta: `Następny etap: ${nast}`,
        etap: nast,
      })
    })
  })
  it('OZE: bez steps etapy od 3 dają null, ostatni etap też', () => {
    ;['Umowa Podpisana', 'Finansowanie', 'Weryfikacja Backoffice', 'Montaż', 'Obsługa pomontażowa'].forEach(
      (status) => expect(nastepnyKrok('OZE', status)).toBeNull(),
    )
    expect(nastepnyKrok('OZE', 'Wygrana - zakończona', null, STEPS_OZE)).toBeNull()
  })
  it('OZE: status poza procesem i nieznany dają null', () => {
    expect(nastepnyKrok('OZE', 'Przegrana', null, STEPS_OZE)).toBeNull()
    expect(nastepnyKrok('OZE', 'toString', null, STEPS_OZE)).toBeNull()
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
    expect(podpowiedzEtapu('OZE', 'Weryfikacja Backoffice')).toBeNull()
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

describe('pasek etapów', () => {
  it('forma zwarta dla długich procesów i wąskiego okna', () => {
    expect(czyZwarty(12, 2000)).toBe(true)
    expect(czyZwarty(5, 800)).toBe(false)
    expect(czyZwarty(5, 400)).toBe(true)
    expect(czyZwarty(5, 0)).toBe(false)
  })
  it('procesy powyżej 6 etapów (OZE 8, CP 12) używają formy zwartej', () => {
    expect(MAKS_ETAPOW_BEZ_ZWARCIA).toBe(6)
    expect(czyZwarty(8, 1200)).toBe(true)
    expect(czyZwarty(9, 2000)).toBe(true)
    expect(czyZwarty(12, 2000)).toBe(true)
    expect(czyZwarty(5, 800)).toBe(false)
  })
  it('numer etapu OZE', () => {
    expect(tekstNumeruEtapu(2, 8)).toBe('Etap 3 z 8')
  })
  it('teksty stanu', () => {
    expect(czasOd('dziś')).toBe('od dziś')
    expect(czasOd('1 dzień')).toBe('od 1 dnia')
    expect(czasOd('6 dni')).toBe('od 6 dni')
    expect(czasOd(null)).toBe('')
    expect(tekstEtapu(4, 12, 'Wniosek o dotację', '6 dni')).toBe(
      'Etap 5 z 12: Wniosek o dotację \u00b7 od 6 dni',
    )
    expect(tekstEtapu(0, 5, 'Lead', null)).toBe('Etap 1 z 5: Lead')
    const steps = [{ status: 'A', index: 0 }, { status: 'B', index: 1 }]
    expect(tekstDalej(steps, 0)).toBe('Dalej: B')
    expect(tekstDalej(steps, 1)).toBe('')
  })
})

describe('wariant paska', () => {
  it('normalizuje wariant widoku etapów', () => {
    expect(normalizujWariant('kroki')).toBe('kroki')
    expect(normalizujWariant('pasek')).toBe('pasek')
    expect(normalizujWariant('x')).toBe('pasek')
    expect(normalizujWariant(null)).toBe('pasek')
  })
  it('klasy segmentów i numer etapu', () => {
    expect(segmentKlasa('done')).toBe('bg-green-500')
    expect(segmentKlasa('current')).toBe('bg-blue-500')
    expect(segmentKlasa('future')).toBe('bg-surface-gray-3')
    expect(segmentKlasa('muted')).toBe('bg-surface-gray-3')
    expect(tekstNumeruEtapu(2, 5)).toBe('Etap 3 z 5')
  })
})

describe('rzędy paska', () => {
  it('jeden rząd tylko gdy nieaktywny segment ma dość miejsca', () => {
    expect(liczbaRzedowPaska(5, 100)).toBe(1)
    expect(liczbaRzedowPaska(6, 100)).toBe(1)
    expect(liczbaRzedowPaska(6, 50)).toBe(1)
    expect(liczbaRzedowPaska(8, 1000)).toBe(1)
    expect(liczbaRzedowPaska(8, 500)).toBe(2)
    expect(liczbaRzedowPaska(12, 1400)).toBe(1)
    expect(liczbaRzedowPaska(12, 790)).toBe(2)
    expect(liczbaRzedowPaska(12, 0)).toBe(1)
  })
  it('dzieli na połowy', () => {
    expect(podzielNaRzedy([1, 2, 3, 4], 1)).toEqual([[1, 2, 3, 4]])
    expect(podzielNaRzedy([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], 2).map((r) => r.length)).toEqual([6, 6])
    expect(podzielNaRzedy([1, 2, 3], 2)).toEqual([[1, 2], [3]])
  })
})
