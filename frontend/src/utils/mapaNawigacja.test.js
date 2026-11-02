import {
  modelPrzyciskuTrasy,
  czyLokalizacjaPrzyblizona,
  linkTrasyGoogle,
} from '@/utils/mapaNawigacja'

const PREFIX = 'https://www.google.com/maps/dir/?api=1&destination='
const SUFIX = '&travelmode=driving'

describe('linkTrasyGoogle', () => {
  it('buduje link z liczb', () => {
    expect(linkTrasyGoogle(52.1, 21.5)).toBe(`${PREFIX}52.1,21.5${SUFIX}`)
  })

  it('przyjmuje liczby jako stringi', () => {
    expect(linkTrasyGoogle('52.1', '21.5')).toBe(`${PREFIX}52.1,21.5${SUFIX}`)
  })

  it('zaokrągla do 6 miejsc po kropce', () => {
    expect(linkTrasyGoogle(52.12345678, 21.98765432)).toBe(
      `${PREFIX}52.123457,21.987654${SUFIX}`,
    )
  })

  it('obsługuje ujemne współrzędne i granice zakresu', () => {
    expect(linkTrasyGoogle(-90, 180)).toBe(`${PREFIX}-90,180${SUFIX}`)
    expect(linkTrasyGoogle(90, -180)).toBe(`${PREFIX}90,-180${SUFIX}`)
  })

  it('nie dodaje dir_action=navigate', () => {
    expect(linkTrasyGoogle(52, 21)).not.toContain('dir_action')
  })

  it('null dla braku wartości i nieliczb', () => {
    expect(linkTrasyGoogle(null, 21)).toBeNull()
    expect(linkTrasyGoogle(52, undefined)).toBeNull()
    expect(linkTrasyGoogle('', 21)).toBeNull()
    expect(linkTrasyGoogle(52, 'abc')).toBeNull()
    expect(linkTrasyGoogle(NaN, 21)).toBeNull()
    expect(linkTrasyGoogle(52, Infinity)).toBeNull()
    expect(linkTrasyGoogle({}, [])).toBeNull()
  })

  it('null dla 0/0', () => {
    expect(linkTrasyGoogle(0, 0)).toBeNull()
    expect(linkTrasyGoogle('0', '0')).toBeNull()
  })

  it('null poza zakresem', () => {
    expect(linkTrasyGoogle(90.1, 21)).toBeNull()
    expect(linkTrasyGoogle(-91, 21)).toBeNull()
    expect(linkTrasyGoogle(52, 180.5)).toBeNull()
    expect(linkTrasyGoogle(52, -181)).toBeNull()
  })
})

describe('czyLokalizacjaPrzyblizona', () => {
  it('true dla miejscowosc i kod', () => {
    expect(czyLokalizacjaPrzyblizona('miejscowosc')).toBe(true)
    expect(czyLokalizacjaPrzyblizona('kod')).toBe(true)
  })

  it('false dla pozostałych', () => {
    for (const v of ['adres', 'ulica', 'brak', '', null, undefined]) {
      expect(czyLokalizacjaPrzyblizona(v)).toBe(false)
    }
  })
})

describe('modelPrzyciskuTrasy', () => {
  const TEKST = 'Lokalizacja przybliżona'

  it('zwraca href z prawdziwych współrzędnych i pusty title dla adresu', () => {
    const m = modelPrzyciskuTrasy(
      { custom_lat: 53.372662, custom_lng: 17.314668, custom_geo_dokladnosc: 'adres' },
      TEKST,
    )
    expect(m.href).toContain('destination=53.372662,17.314668')
    expect(m.title).toBe('')
  })

  it('dla lokalizacji przybliżonej ustawia title', () => {
    for (const d of ['miejscowosc', 'kod']) {
      const m = modelPrzyciskuTrasy(
        { custom_lat: 52.1, custom_lng: 21.0, custom_geo_dokladnosc: d },
        TEKST,
      )
      expect(m.title).toBe(TEKST)
    }
  })

  it('zwraca null bez współrzędnych albo bez leada', () => {
    expect(modelPrzyciskuTrasy(null, TEKST)).toBeNull()
    expect(modelPrzyciskuTrasy({ custom_lat: 0, custom_lng: 0 }, TEKST)).toBeNull()
    expect(modelPrzyciskuTrasy({ custom_lat: '', custom_lng: null }, TEKST)).toBeNull()
  })
})
