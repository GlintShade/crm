import { describe, it, expect } from 'vitest'
import { pipelineOnly, liczbaSegmentow, segmentyWypelnione } from '@/utils/pasekEtapu'

// Lustro crm.volteo_pipeline.PIPELINE_OZE / PIPELINE_CP / TERMINALE (5 + 2
// kroki OZE, 12 + 1 krok CP; grupa_for = pipeline + terminale).
const GRUPA_OZE = [
  'Lead',
  'Umowa Wygenerowana',
  'Umowa Podpisana',
  'Finansowanie',
  'Weryfikacja Backoffice',
  'Wygrana – montaż',
  'Przegrana',
]

const GRUPA_CP = [
  'Lead',
  'Dokumentacja',
  'Audyt Energetyczny',
  'Umowa na realizację',
  'Wniosek o dotację',
  'Dyspozycja wypłaty zaliczki',
  'I transza',
  'Finansowanie Trify',
  'Realizacja',
  'Wniosek o płatność końcową',
  '2 transza',
  'Projekt rozliczony',
  'Przegrana',
]

const GRUPY = {
  Fotowoltaika: GRUPA_OZE,
  'Czyste Powietrze': GRUPA_CP,
}

describe('pipelineOnly', () => {
  it('odcina oba statusy terminalne OZE, zostaje 5 krokow procesu', () => {
    expect(pipelineOnly(GRUPA_OZE)).toEqual([
      'Lead',
      'Umowa Wygenerowana',
      'Umowa Podpisana',
      'Finansowanie',
      'Weryfikacja Backoffice',
    ])
  })

  it('odcina tylko "Przegrana" dla CP, "Projekt rozliczony" (Won) zostaje w procesie - 12 krokow', () => {
    const wynik = pipelineOnly(GRUPA_CP)
    expect(wynik).toHaveLength(12)
    expect(wynik[wynik.length - 1]).toBe('Projekt rozliczony')
    expect(wynik).not.toContain('Przegrana')
  })

  it('zwraca [] dla nie-tablicy', () => {
    expect(pipelineOnly(null)).toEqual([])
    expect(pipelineOnly(undefined)).toEqual([])
    expect(pipelineOnly('cos')).toEqual([])
  })

  it('nie mutuje wejscia', () => {
    const wejscie = [...GRUPA_OZE]
    pipelineOnly(wejscie)
    expect(wejscie).toEqual(GRUPA_OZE)
  })
})

describe('liczbaSegmentow', () => {
  it('5 dla OZE, 12 dla CP - liczone z danych, nie hardkodowane', () => {
    expect(liczbaSegmentow(GRUPY, 'Fotowoltaika')).toBe(5)
    expect(liczbaSegmentow(GRUPY, 'Czyste Powietrze')).toBe(12)
  })

  it('0 dla braku grupy/rodzaju (deal bez rodzaju - "XX")', () => {
    expect(liczbaSegmentow(GRUPY, '')).toBe(0)
    expect(liczbaSegmentow(GRUPY, null)).toBe(0)
    expect(liczbaSegmentow(GRUPY, undefined)).toBe(0)
    expect(liczbaSegmentow(GRUPY, 'Nieznany rodzaj')).toBe(0)
    expect(liczbaSegmentow(null, 'Fotowoltaika')).toBe(0)
    expect(liczbaSegmentow(undefined, 'Fotowoltaika')).toBe(0)
  })
})

describe('segmentyWypelnione', () => {
  it('status w srodku procesu OZE -> pozycja 1-based', () => {
    expect(segmentyWypelnione(GRUPY, 'Fotowoltaika', 'Lead', 'Open')).toBe(1)
    expect(segmentyWypelnione(GRUPY, 'Fotowoltaika', 'Umowa Podpisana', 'Ongoing')).toBe(3)
    expect(
      segmentyWypelnione(GRUPY, 'Fotowoltaika', 'Weryfikacja Backoffice', 'Ongoing'),
    ).toBe(5)
  })

  it('OZE "Wygrana – montaż" (poza procesem, Won) -> pelny pasek', () => {
    expect(segmentyWypelnione(GRUPY, 'Fotowoltaika', 'Wygrana – montaż', 'Won')).toBe(5)
  })

  it('OZE "Przegrana" (poza procesem, Lost) -> pusty pasek', () => {
    expect(segmentyWypelnione(GRUPY, 'Fotowoltaika', 'Przegrana', 'Lost')).toBe(0)
  })

  it('CP "Projekt rozliczony" (W procesie, 12. krok, typ Won) -> pelny pasek przez indeks, nie przez galaz Won', () => {
    expect(segmentyWypelnione(GRUPY, 'Czyste Powietrze', 'Projekt rozliczony', 'Won')).toBe(12)
  })

  it('CP "Przegrana" (poza procesem, Lost) -> pusty pasek', () => {
    expect(segmentyWypelnione(GRUPY, 'Czyste Powietrze', 'Przegrana', 'Lost')).toBe(0)
  })

  it('CP w srodku procesu -> pozycja 1-based', () => {
    expect(segmentyWypelnione(GRUPY, 'Czyste Powietrze', 'I transza', 'Ongoing')).toBe(7)
  })

  it('rodzaj bez procesu ("XX"/pusty/nieznany) -> 0', () => {
    expect(segmentyWypelnione(GRUPY, '', 'Lead', 'Open')).toBe(0)
    expect(segmentyWypelnione(GRUPY, null, 'Lead', 'Open')).toBe(0)
    expect(segmentyWypelnione(GRUPY, 'Nieznany rodzaj', 'Lead', 'Open')).toBe(0)
  })

  it('status nieznany, nie-terminalny, nie w procesie -> 0', () => {
    expect(segmentyWypelnione(GRUPY, 'Fotowoltaika', 'Cos obcego', undefined)).toBe(0)
  })
})
