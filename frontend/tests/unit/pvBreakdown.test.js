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
  k_licznik: 150,
  k_ppoz: 250,
  // ops#225: koszty + marże opcji dodatkowych PV/PV+ME/ME.
  k_dod_klima: 2900,
  m_dod_klima: 2000,
  k_dod_panele: 2100,
  m_dod_panele: 1500,
  k_dod_panele_mikro: 2600,
  m_dod_panele_mikro: 1500,
  k_ems_breeze: 1250,
  m_ems_breeze: 250,
  k_ev: 2100,
  m_ev: 1000,
  marza_proenergy: 1200,
  marza_sps: 1300,
  bonus_liderki: 1400,
  net_base: 99999,
}

const kluczeGrup = ['hurtownia', 'montaz', 'dodatki', 'marze']
const kluczePozycji = [
  ['k_falownik', 'k_bateria', 'k_panele', 'k_konstrukcja', 'k_sterownik', 'k_spoldzielnia'],
  ['kilometrowka', 'k_montaz_pv', 'k_montaz_mag', 'k_akcesoria', 'k_kabel', 'k_licznik', 'k_ppoz'],
  ['k_dod_klima', 'k_dod_panele', 'k_dod_panele_mikro', 'k_ems_breeze', 'k_ev'],
  ['marza_proenergy', 'marza_sps', 'bonus_liderki', 'marza_dodatki'],
]

// Suma m_dod_* - jedyna pozycja (marza_dodatki) liczona przez grupujBreakdown
// jako SUMA kilku pól wejścia, nie odczyt jednego klucza wprost.
const SUMA_MARZA_DODATKI = 2000 + 1500 + 1500 + 250 + 1000

function wszystkiePozycje(grupy) {
  return grupy.flatMap((grupa) => grupa.pozycje)
}

describe('grupujBreakdown', () => {
  it('buduje cztery grupy i zachowuje kolejność pozycji oraz sumy', () => {
    const grupy = grupujBreakdown(pelnyBreakdown)

    expect(grupy.map((grupa) => grupa.klucz)).toEqual(kluczeGrup)
    expect(grupy.map((grupa) => grupa.pozycje.map((pozycja) => pozycja.klucz))).toEqual(kluczePozycji)
    expect(grupy.map((grupa) => grupa.suma)).toEqual([2100, 4900, 10950, 3900 + SUMA_MARZA_DODATKI])
    expect(wszystkiePozycje(grupy).map((pozycja) => pozycja.kwota)).toEqual([
      100, 200, 300, 400, 500, 600,
      700, 800, 900, 1000, 1100, 150, 250,
      2900, 2100, 2600, 1250, 2100,
      1200, 1300, 1400, SUMA_MARZA_DODATKI,
    ])
  })

  it('suma grup obejmuje dokładnie 22 pozycje (16 bazowych + 5 dodatków + marza_dodatki), bez net_base', () => {
    const grupy = grupujBreakdown(pelnyBreakdown)
    const sumaWejscia = Object.entries(pelnyBreakdown)
      .filter(([klucz]) => klucz !== 'net_base')
      .reduce((suma, [, kwota]) => suma + kwota, 0)

    expect(grupy.reduce((suma, grupa) => suma + grupa.suma, 0)).toBe(sumaWejscia)
    expect(wszystkiePozycje(grupy)).toHaveLength(22)
  })

  it('marza_dodatki sumuje m_dod_klima + m_dod_panele + m_dod_panele_mikro + m_ems_breeze + m_ev', () => {
    const grupy = grupujBreakdown(pelnyBreakdown)
    const marzaDodatki = grupy[3].pozycje.find((pozycja) => pozycja.klucz === 'marza_dodatki')

    expect(marzaDodatki.kwota).toBe(SUMA_MARZA_DODATKI)
  })

  it('traktuje brakujące skladowe marzy dodatkow jako zero, bez rzucania bledu', () => {
    const grupy = grupujBreakdown({ k_dod_klima: 2900 })
    const marzaDodatki = grupy[3].pozycje.find((pozycja) => pozycja.klucz === 'marza_dodatki')
    const kDodKlima = grupy[2].pozycje.find((pozycja) => pozycja.klucz === 'k_dod_klima')

    expect(marzaDodatki.kwota).toBe(0)
    expect(kDodKlima.kwota).toBe(2900)
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

  it('ops#293: adnotacja progu magazynu tylko w grupie marz i tylko gdy prog > 0', () => {
    const z = grupujBreakdown({ prog_mag_kwh: 50 })
    expect(z.find((g) => g.klucz === 'marze').adnotacja).toBe('Próg magazynu: powyżej 50 kWh')
    expect(z.filter((g) => g.klucz !== 'marze').every((g) => g.adnotacja === '')).toBe(true)
    expect(grupujBreakdown({ prog_mag_kwh: 0 }).every((g) => g.adnotacja === '')).toBe(true)
    expect(grupujBreakdown({}).every((g) => g.adnotacja === '')).toBe(true)
  })
})
