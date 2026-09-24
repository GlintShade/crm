import { describe, it, expect } from 'vitest'
import { opcjeUzytkownikow, etykietaWartosciUzytkownika } from './etykietaUzytkownika'

function stworzGetUser(baza) {
  return (email) => baza[email]
}

describe('opcjeUzytkownikow', () => {
  it('uzywa full_name ze sklepu jako etykiety, description zostaje e-mailem', () => {
    const getUser = stworzGetUser({
      'jan.kowalski@proenergy.pro': { full_name: 'Jan Kowalski' },
    })
    const wynik = opcjeUzytkownikow(
      [{ value: 'jan.kowalski@proenergy.pro', description: '<b>Jan Kowalski</b>' }],
      getUser,
    )
    expect(wynik).toEqual([
      {
        label: 'Jan Kowalski',
        value: 'jan.kowalski@proenergy.pro',
        description: 'jan.kowalski@proenergy.pro',
      },
    ])
  })

  it('gdy sklep nie zna uzytkownika, spada do description oczyszczonego z HTML', () => {
    const getUser = stworzGetUser({})
    const wynik = opcjeUzytkownikow(
      [
        {
          value: 'anna.nowak@proenergy.pro',
          description: '<div>Anna&nbsp;Nowak</div>',
        },
      ],
      getUser,
    )
    expect(wynik[0].label).toBe('Anna Nowak')
    expect(wynik[0].description).toBe('anna.nowak@proenergy.pro')
  })

  it('gdy brak i sklepu, i description, spada do samej wartosci (e-mail)', () => {
    const getUser = stworzGetUser({})
    const wynik = opcjeUzytkownikow([{ value: 'x@proenergy.pro' }], getUser)
    expect(wynik[0].label).toBe('x@proenergy.pro')
  })

  it('getUser zwracajacy pusty obiekt (nieznany uzytkownik z wlasnym getterem) spada do description', () => {
    const getUser = () => ({})
    const wynik = opcjeUzytkownikow(
      [{ value: 'ktos@proenergy.pro', description: 'Ktos Inny' }],
      getUser,
    )
    expect(wynik[0].label).toBe('Ktos Inny')
  })

  it('full_name skladajacy sie z samych bialych znakow traktowany jak pusty, spada dalej', () => {
    const getUser = stworzGetUser({
      'pusty@proenergy.pro': { full_name: '   ' },
    })
    const wynik = opcjeUzytkownikow(
      [{ value: 'pusty@proenergy.pro', description: 'Opis Zastepczy' }],
      getUser,
    )
    expect(wynik[0].label).toBe('Opis Zastepczy')
  })

  it('nie mutuje wejsciowej tablicy ani jej elementow', () => {
    const getUser = stworzGetUser({
      'jan.kowalski@proenergy.pro': { full_name: 'Jan Kowalski' },
    })
    const wejscie = [{ value: 'jan.kowalski@proenergy.pro', description: 'x' }]
    const kopiaWejscia = JSON.parse(JSON.stringify(wejscie))
    const wynik = opcjeUzytkownikow(wejscie, getUser)
    expect(wejscie).toEqual(kopiaWejscia)
    expect(wynik).not.toBe(wejscie)
    expect(wynik[0]).not.toBe(wejscie[0])
  })

  it('zachowuje kolejnosc wierszy i nie pomija zadnego', () => {
    const getUser = stworzGetUser({
      'a@proenergy.pro': { full_name: 'A A' },
      'c@proenergy.pro': { full_name: 'C C' },
    })
    const wynik = opcjeUzytkownikow(
      [
        { value: 'a@proenergy.pro' },
        { value: 'b@proenergy.pro', description: 'B B' },
        { value: 'c@proenergy.pro' },
      ],
      getUser,
    )
    expect(wynik.map((o) => o.value)).toEqual([
      'a@proenergy.pro',
      'b@proenergy.pro',
      'c@proenergy.pro',
    ])
    expect(wynik.map((o) => o.label)).toEqual(['A A', 'B B', 'C C'])
  })

  it('dla pustej lub brakujacej tablicy zwraca pusta tablice', () => {
    expect(opcjeUzytkownikow([], stworzGetUser({}))).toEqual([])
    expect(opcjeUzytkownikow(null, stworzGetUser({}))).toEqual([])
    expect(opcjeUzytkownikow(undefined, stworzGetUser({}))).toEqual([])
  })
})

describe('etykietaWartosciUzytkownika', () => {
  it('zwraca full_name ze sklepu dla zwyklej wartosci', () => {
    const getUser = stworzGetUser({
      'jan.kowalski@proenergy.pro': { full_name: 'Jan Kowalski' },
    })
    expect(
      etykietaWartosciUzytkownika('jan.kowalski@proenergy.pro', getUser, 'Moje leady'),
    ).toBe('Jan Kowalski')
  })

  it('zwraca meLabel dla wartosci @me, bez pytania getUser', () => {
    let wolane = false
    const getUser = () => {
      wolane = true
      return { full_name: 'Nie powinno sie uzyc' }
    }
    expect(etykietaWartosciUzytkownika('@me', getUser, 'Moje leady')).toBe('Moje leady')
    expect(wolane).toBe(false)
  })

  it('zwraca pusty string dla pustej lub nullowej wartosci', () => {
    const getUser = stworzGetUser({})
    expect(etykietaWartosciUzytkownika('', getUser, 'Moje leady')).toBe('')
    expect(etykietaWartosciUzytkownika(null, getUser, 'Moje leady')).toBe('')
    expect(etykietaWartosciUzytkownika(undefined, getUser, 'Moje leady')).toBe('')
  })

  it('nieznany uzytkownik (getUser zwraca pusty obiekt) spada do wartosci', () => {
    const getUser = () => ({})
    expect(etykietaWartosciUzytkownika('nieznany@proenergy.pro', getUser, 'Moje leady')).toBe(
      'nieznany@proenergy.pro',
    )
  })

  it('full_name skladajacy sie z samych bialych znakow spada do wartosci', () => {
    const getUser = stworzGetUser({
      'pusty@proenergy.pro': { full_name: '   ' },
    })
    expect(etykietaWartosciUzytkownika('pusty@proenergy.pro', getUser, 'Moje leady')).toBe(
      'pusty@proenergy.pro',
    )
  })
})
