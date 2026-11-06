import { describe, it, expect } from 'vitest'
import {
  SZABLONY,
  POLA_SZABLONOW,
  formularzZeStanu,
  zmienionePola,
  czySaZmiany,
  walidujSzablon,
  walidujLimit,
  sortujHandlowcow,
  stanNumeru,
  liczBezNumeru,
  odmianaCzesci,
  opisCzesci,
  ostrzezenieCzesci,
  opisCiszyNocnej,
  opisLicznikaDnia,
  listaPlaceholderow,
  wynikTestu,
  komunikatBledu,
} from '@/utils/smsHandlowiec'

const PLACEHOLDERY = [
  'termin',
  'stary_termin',
  'data',
  'godzina',
  'klient',
  'adres',
  'miejscowosc',
]

const STAN = {
  handlowiec_wlaczone: 0,
  handlowiec_odwolanie_wlaczone: 1,
  tresc_handlowiec_nowe:
    'Nowe spotkanie {termin}: {klient}, {adres}. Szczegóły w CRM.',
  tresc_handlowiec_zmiana: 'Zmiana {termin}',
  tresc_handlowiec_odwolanie: 'Odwołane {stary_termin}',
  limit_dzienny_handlowiec: 100,
  tryb_testowy: 0,
  token_ustawiony: true,
}

describe('SZABLONY', () => {
  it('trzy typy zgodne z API (typ testu i pole zapisu)', () => {
    expect(SZABLONY.map((s) => s.typ)).toEqual(['nowe', 'zmiana', 'odwolanie'])
    expect(POLA_SZABLONOW).toEqual([
      'tresc_handlowiec_nowe',
      'tresc_handlowiec_zmiana',
      'tresc_handlowiec_odwolanie',
    ])
  })
})

describe('formularzZeStanu', () => {
  it('bierze tylko szablony i limit', () => {
    const f = formularzZeStanu(STAN)
    expect(Object.keys(f).sort()).toEqual(
      [...POLA_SZABLONOW, 'limit_dzienny_handlowiec'].sort(),
    )
    expect(f.limit_dzienny_handlowiec).toBe(100)
    expect(f.tresc_handlowiec_zmiana).toBe('Zmiana {termin}')
  })
  it('pusty stan nie rzuca', () => {
    const f = formularzZeStanu(null)
    expect(f.tresc_handlowiec_nowe).toBe('')
    expect(f.limit_dzienny_handlowiec).toBe(0)
  })
})

describe('zmienionePola', () => {
  it('bez zmian daje pusty ladunek', () => {
    expect(zmienionePola(formularzZeStanu(STAN), STAN)).toEqual({})
    expect(czySaZmiany(formularzZeStanu(STAN), STAN)).toBe(false)
  })
  it('tylko zmieniony szablon', () => {
    const f = {
      ...formularzZeStanu(STAN),
      tresc_handlowiec_zmiana: 'Inna {termin}',
    }
    expect(zmienionePola(f, STAN)).toEqual({
      tresc_handlowiec_zmiana: 'Inna {termin}',
    })
    expect(czySaZmiany(f, STAN)).toBe(true)
  })
  it('limit jako liczba, tekst z pola number tez', () => {
    const f = { ...formularzZeStanu(STAN), limit_dzienny_handlowiec: '150' }
    expect(zmienionePola(f, STAN)).toEqual({ limit_dzienny_handlowiec: 150 })
    const tenSam = {
      ...formularzZeStanu(STAN),
      limit_dzienny_handlowiec: '100',
    }
    expect(zmienionePola(tenSam, STAN)).toEqual({})
  })
  it('limit 0 jest zmiana', () => {
    const f = { ...formularzZeStanu(STAN), limit_dzienny_handlowiec: 0 }
    expect(zmienionePola(f, STAN)).toEqual({ limit_dzienny_handlowiec: 0 })
  })
  it('flagi jako 0/1, tylko gdy podane i rozne', () => {
    expect(zmienionePola({ handlowiec_wlaczone: true }, STAN)).toEqual({
      handlowiec_wlaczone: 1,
    })
    expect(
      zmienionePola({ handlowiec_odwolanie_wlaczone: false }, STAN),
    ).toEqual({
      handlowiec_odwolanie_wlaczone: 0,
    })
    expect(zmienionePola({ handlowiec_odwolanie_wlaczone: 1 }, STAN)).toEqual(
      {},
    )
  })
  it('wyczyszczony szablon trafia do ladunku (serwer go odrzuci walidacja)', () => {
    const f = { ...formularzZeStanu(STAN), tresc_handlowiec_nowe: '' }
    expect(zmienionePola(f, STAN)).toEqual({ tresc_handlowiec_nowe: '' })
  })
})

describe('walidujSzablon', () => {
  it('poprawny szablon', () => {
    expect(walidujSzablon(STAN.tresc_handlowiec_nowe, PLACEHOLDERY)).toBeNull()
  })
  it('pusty', () => {
    expect(walidujSzablon('   ', PLACEHOLDERY)).toBe(
      'Treść SMS nie może być pusta.',
    )
    expect(walidujSzablon(null, PLACEHOLDERY)).toBe(
      'Treść SMS nie może być pusta.',
    )
  })
  it('telefon i link nie sa juz dozwolone', () => {
    expect(walidujSzablon('tel. {telefon}', PLACEHOLDERY)).toMatch(
      /^Nieznany placeholder \{telefon\}/,
    )
    expect(walidujSzablon('{link}', PLACEHOLDERY)).toMatch(
      /^Nieznany placeholder \{link\}/,
    )
  })
  it('komunikat jak w Pythonie', () => {
    expect(walidujSzablon('{x}', ['termin', 'klient'])).toBe(
      'Nieznany placeholder {x}. Dozwolone: {termin}, {klient}.',
    )
  })
})

describe('walidujLimit', () => {
  it('zakres 0..1000', () => {
    expect(walidujLimit(0)).toBeNull()
    expect(walidujLimit('100')).toBeNull()
    expect(walidujLimit(1000)).toBeNull()
    for (const v of [-1, 1001, '', null, 'abc', 1.5])
      expect(walidujLimit(v)).toMatch(/^Limit dzienny/)
  })
})

describe('sortujHandlowcow', () => {
  it('najpierw bez poprawnego numeru, potem z linia Leady, potem po nazwie', () => {
    const lista = [
      {
        uzytkownik: 'a',
        imie_nazwisko: 'Adam',
        linia_leady: 1,
        mobile_no: '+48500100200',
        numer_ok: true,
      },
      {
        uzytkownik: 'z',
        imie_nazwisko: 'Żaneta',
        linia_leady: 0,
        mobile_no: '',
        numer_ok: false,
      },
      {
        uzytkownik: 'b',
        imie_nazwisko: 'Bartek',
        linia_leady: 0,
        mobile_no: '+48500100201',
        numer_ok: true,
      },
      {
        uzytkownik: 'c',
        imie_nazwisko: 'Celina',
        linia_leady: 1,
        mobile_no: '123',
        numer_ok: false,
      },
      {
        uzytkownik: 'd',
        imie_nazwisko: 'ania',
        linia_leady: 1,
        mobile_no: '+48500100202',
        numer_ok: true,
      },
    ]
    expect(sortujHandlowcow(lista).map((h) => h.uzytkownik)).toEqual([
      'c',
      'z',
      'a',
      'd',
      'b',
    ])
  })
  it('nie zmienia wejscia i znosi null', () => {
    const lista = [
      { uzytkownik: 'b', numer_ok: true },
      { uzytkownik: 'a', numer_ok: false },
    ]
    const kopia = [...lista]
    sortujHandlowcow(lista)
    expect(lista).toEqual(kopia)
    expect(sortujHandlowcow(null)).toEqual([])
  })
})

describe('stanNumeru', () => {
  it('brak, niepoprawny, poprawny', () => {
    expect(stanNumeru({ mobile_no: '', numer_ok: false })).toEqual({
      kod: 'brak',
      etykieta: 'Brak numeru',
      blad: true,
    })
    expect(stanNumeru({ mobile_no: '  ', numer_ok: false }).kod).toBe('brak')
    expect(stanNumeru({ mobile_no: null }).kod).toBe('brak')
    expect(stanNumeru({ mobile_no: '12345', numer_ok: false })).toEqual({
      kod: 'niepoprawny',
      etykieta: 'Niepoprawny numer',
      blad: true,
    })
    expect(stanNumeru({ mobile_no: '+48500100200', numer_ok: true }).blad).toBe(
      false,
    )
  })
  it('liczBezNumeru', () => {
    expect(
      liczBezNumeru([
        { mobile_no: '', numer_ok: false },
        { mobile_no: 'x', numer_ok: false },
        { mobile_no: '+48500100200', numer_ok: true },
      ]),
    ).toBe(2)
    expect(liczBezNumeru(undefined)).toBe(0)
  })
})

describe('opisCzesci i ostrzezenie', () => {
  it('odmiana', () => {
    expect(odmianaCzesci(1)).toBe('część')
    expect(odmianaCzesci(2)).toBe('części')
    expect(odmianaCzesci(5)).toBe('części')
  })
  it('opis licznika czesci', () => {
    expect(opisCzesci(98, 1)).toBe('98 znaków GSM-7, 1 część SMS')
    expect(opisCzesci(170, 2)).toBe('170 znaków GSM-7, 2 części SMS')
    expect(opisCzesci(undefined, undefined)).toBe('0 znaków GSM-7, 1 część SMS')
  })
  it('ostrzezenie od 2 czesci', () => {
    expect(ostrzezenieCzesci(1)).toBeNull()
    expect(ostrzezenieCzesci(2)).toBe(
      'Treść zajmie 2 części SMS, SMSAPI policzy ją jak 2 wiadomości.',
    )
  })
})

describe('opisCiszyNocnej', () => {
  it('okno wysylki z cisza_od i cisza_do', () => {
    expect(opisCiszyNocnej('21:00', '08:00')).toBe(
      'SMS-y wychodzą od 08:00 do 21:00, później czekają do rana.',
    )
  })
  it('brak danych', () => {
    expect(opisCiszyNocnej('', '08:00')).toBeNull()
    expect(opisCiszyNocnej(undefined, undefined)).toBeNull()
  })
})

describe('opisLicznikaDnia', () => {
  it('licznik, limit 0, Redis niedostepny', () => {
    expect(opisLicznikaDnia(3, 100)).toBe('Dziś wysłano 3 z 100.')
    expect(opisLicznikaDnia(0, 100)).toBe('Dziś wysłano 0 z 100.')
    expect(opisLicznikaDnia(5, 0)).toBe(
      'Limit 0: wysyłka SMS do handlowców zablokowana.',
    )
    expect(opisLicznikaDnia(null, 100)).toBe(
      'Dziś wysłano: brak danych (licznik niedostępny). Limit: 100.',
    )
  })
})

describe('listaPlaceholderow', () => {
  it('z przykladem z serwera', () => {
    expect(
      listaPlaceholderow(['termin', 'inne'], { termin: 'pt. 07.11 14:30' }),
    ).toEqual(['{termin} (np. pt. 07.11 14:30)', '{inne}'])
    expect(listaPlaceholderow(null, null)).toEqual([])
  })
})

describe('wynikTestu', () => {
  it('wyslany, tryb testowy, odmowa z powodem', () => {
    expect(wynikTestu({ ok: true, tryb_testowy: 0 })).toEqual({
      ok: true,
      tekst: 'SMS testowy wysłany na Twój numer.',
    })
    expect(wynikTestu({ ok: true, tryb_testowy: 1 }).tekst).toMatch(
      /^Tryb testowy SMSAPI/,
    )
    expect(
      wynikTestu({
        ok: false,
        powod: 'Wyczerpany dzienny limit SMS do handlowców (100).',
      }),
    ).toEqual({
      ok: false,
      tekst: 'Wyczerpany dzienny limit SMS do handlowców (100).',
    })
    expect(wynikTestu({ ok: false })).toEqual({
      ok: false,
      tekst: 'Nie udało się wysłać SMS testowego.',
    })
    expect(wynikTestu(null).ok).toBe(false)
  })
})

describe('komunikatBledu', () => {
  it('pierwszy komunikat serwera albo domyslny, nigdy surowe err.message', () => {
    expect(komunikatBledu({ messages: ['Brak tokenu SMSAPI.'] }, 'x')).toBe(
      'Brak tokenu SMSAPI.',
    )
    expect(
      komunikatBledu(
        { message: 'crm.api...\nValidationError', messages: [] },
        'Domyślny',
      ),
    ).toBe('Domyślny')
    expect(komunikatBledu(undefined, 'Domyślny')).toBe('Domyślny')
  })
})
