import { grupujBreakdown } from '@/utils/pvBreakdown'

const pelnyBreakdown = {
  k_falownik: 100,
  k_bateria: 200,
  k_panele: 300,
  k_konstrukcja: 400,
  k_sterownik: 500,
  k_spoldzielnia: 600,
  kilometrowka: 700,
  k_montaz_pv: 800,
  k_montaz_mag: 900,
  k_akcesoria: 1000,
  k_kabel: 1100,
  marza_proenergy: 1200,
  marza_sps: 1300,
  bonus_liderki: 1400,
  net_base: 99999,
}

const kluczeGrup = ['hurtownia', 'montaz', 'marze']
const kluczePozycji = [
  ['k_falownik', 'k_bateria', 'k_panele', 'k_konstrukcja', 'k_sterownik', 'k_spoldzielnia'],
  ['kilometrowka', 'k_montaz_pv', 'k_montaz_mag', 'k_akcesoria', 'k_kabel'],
  ['marza_proenergy', 'marza_sps', 'bonus_liderki'],
]

function wszystkiePozycje(grupy) {
  return grupy.flatMap((grupa) => grupa.pozycje)
}

describe('grupujBreakdown', () => {
  it('buduje trzy grupy i zachowuje kolejność pozycji oraz sumy', () => {
    const grupy = grupujBreakdown(pelnyBreakdown)

    expect(grupy.map((grupa) => grupa.klucz)).toEqual(kluczeGrup)
    expect(grupy.map((grupa) => grupa.pozycje.map((pozycja) => pozycja.klucz))).toEqual(kluczePozycji)
    expect(grupy.map((grupa) => grupa.suma)).toEqual([2100, 4500, 3900])
    expect(wszystkiePozycje(grupy).map((pozycja) => pozycja.kwota)).toEqual([
      100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400,
    ])
  })

  it('suma grup obejmuje dokładnie 14 wartości, bez net_base', () => {
    const grupy = grupujBreakdown(pelnyBreakdown)
    const sumaWejscia = Object.entries(pelnyBreakdown)
      .filter(([klucz]) => klucz !== 'net_base')
      .reduce((suma, [, kwota]) => suma + kwota, 0)

    expect(grupy.reduce((suma, grupa) => suma + grupa.suma, 0)).toBe(sumaWejscia)
    expect(wszystkiePozycje(grupy)).toHaveLength(14)
  })

  it('umieszcza kilometrowke w montazu, a spoldzielnie w hurtowni', () => {
    const grupy = grupujBreakdown(pelnyBreakdown)

    expect(grupy[1].pozycje[0].klucz).toBe('kilometrowka')
    expect(grupy[0].pozycje.at(-1).klucz).toBe('k_spoldzielnia')
  })

  it('zamienia brakujące i niepoprawne wartości na zero', () => {
    const grupy = grupujBreakdown({ k_falownik: null, k_bateria: 'abc', k_panele: NaN, k_konstrukcja: Infinity })
    const pozycje = wszystkiePozycje(grupy)

    expect(pozycje.find((pozycja) => pozycja.klucz === 'k_falownik').kwota).toBe(0)
    expect(pozycje.find((pozycja) => pozycja.klucz === 'k_bateria').kwota).toBe(0)
    expect(pozycje.find((pozycja) => pozycja.klucz === 'k_panele').kwota).toBe(0)
    expect(pozycje.find((pozycja) => pozycja.klucz === 'k_konstrukcja').kwota).toBe(0)
    expect(grupy.every((grupa) => Number.isFinite(grupa.suma))).toBe(true)
  })

  it.each([null, undefined])('dla %p zwraca pełną strukturę zerową', (breakdown) => {
    const grupy = grupujBreakdown(breakdown)

    expect(grupy.map((grupa) => grupa.klucz)).toEqual(kluczeGrup)
    expect(grupy.every((grupa) => grupa.pozycje.every((pozycja) => pozycja.kwota === 0))).toBe(true)
    expect(grupy.every((grupa) => grupa.suma === 0)).toBe(true)
  })

  it('nie mutuje wejścia i zwraca nowe obiekty', () => {
    const wejscie = structuredClone(pelnyBreakdown)
    const przed = structuredClone(wejscie)
    const wynik = grupujBreakdown(wejscie)

    expect(wejscie).toEqual(przed)
    expect(wynik).not.toBe(wejscie)
    expect(wynik[0]).not.toBe(wynik[1])
    expect(wynik[0].pozycje).not.toBe(wynik[1].pozycje)
  })

  it('zachowuje wartości ujemne i uwzględnia je w sumie', () => {
    const grupy = grupujBreakdown({ k_falownik: -100, k_bateria: -50 })

    expect(grupy[0].pozycje[0].kwota).toBe(-100)
    expect(grupy[0].suma).toBe(-150)
  })
})
