import { describe, it, expect, vi } from 'vitest'
import {
  BRAK_WYNIKU,
  czyKodPocztowy,
  czyPokazacListe,
  latkaAdresuZKodu,
  listaMiejscowosci,
  utworzLookup,
  uzupelnijAdresZKodu,
} from './kodPocztowy'

const WYNIK = {
  found: true,
  wojewodztwo: 'wielkopolskie',
  powiat: 'kościański',
  gmina: 'Kościan',
  miejscowosc: 'Kościan',
  cities: ['Kościan', 'Racot'],
}

describe('czyKodPocztowy', () => {
  it('tylko XX-XXX', () => {
    expect(czyKodPocztowy('64-000')).toBe(true)
    expect(czyKodPocztowy(' 64-000 ')).toBe(true)
    for (const v of ['64000', '64-00', '6-4000', '', null, undefined]) {
      expect(czyKodPocztowy(v)).toBe(false)
    }
  })
})

describe('listaMiejscowosci', () => {
  it('cities bez duplikatow i pustych', () => {
    expect(
      listaMiejscowosci({ found: true, cities: ['A', '', ' A ', 'B', null] }),
    ).toEqual(['A', 'B'])
  })
  it('bez listy nie zgaduje z miejscowosc GeoNames', () => {
    expect(
      listaMiejscowosci({ found: true, miejscowosc: 'X', cities: [] }),
    ).toEqual([])
    expect(listaMiejscowosci({ found: false, cities: ['A'] })).toEqual([])
    expect(listaMiejscowosci(null)).toEqual([])
  })
})

describe('czyPokazacListe', () => {
  it('lista z wyborem', () => {
    expect(czyPokazacListe(['A', 'B'], 'A')).toBe(true)
    expect(czyPokazacListe(['A'], '')).toBe(true)
    expect(czyPokazacListe(['A'], 'Inna')).toBe(true)
  })
  it('nic do wyboru', () => {
    expect(czyPokazacListe([], '')).toBe(false)
    expect(czyPokazacListe(['A'], 'A')).toBe(false)
  })
})

describe('latkaAdresuZKodu', () => {
  it('wojewodztwo i powiat nadpisane, gmina tylko gdy pole istnieje', () => {
    const doc = { custom_voivodeship: 'śląskie', custom_powiat: '' }
    expect(latkaAdresuZKodu(doc, WYNIK)).toEqual({
      custom_voivodeship: 'wielkopolskie',
      custom_powiat: 'kościański',
    })
    expect(
      latkaAdresuZKodu({ ...doc, custom_gmina: null }, WYNIK),
    ).toMatchObject({
      custom_gmina: 'Kościan',
    })
  })

  it('wiele miejscowosci: pole miejscowosci nietkniete', () => {
    expect(
      latkaAdresuZKodu({ custom_install_city: '' }, WYNIK),
    ).not.toHaveProperty('custom_install_city')
  })

  it('jedna miejscowosc: wpisana tylko do pustego pola', () => {
    const jedna = { ...WYNIK, cities: ['Racot'] }
    expect(latkaAdresuZKodu({ custom_install_city: '' }, jedna)).toMatchObject({
      custom_install_city: 'Racot',
    })
    expect(
      latkaAdresuZKodu({ custom_install_city: 'Wpisana' }, jedna),
    ).not.toHaveProperty('custom_install_city')
  })

  it('bez zmian i bez wyniku: pusta latka', () => {
    const doc = {
      custom_voivodeship: 'wielkopolskie',
      custom_powiat: 'kościański',
    }
    expect(latkaAdresuZKodu(doc, { ...WYNIK, cities: [] })).toEqual({})
    expect(latkaAdresuZKodu(doc, BRAK_WYNIKU)).toEqual({})
    expect(
      latkaAdresuZKodu(doc, {
        ...WYNIK,
        wojewodztwo: '',
        powiat: '',
        cities: [],
      }),
    ).toEqual({})
  })
})

describe('utworzLookup', () => {
  it('jedno zapytanie na kod', async () => {
    const wywolaj = vi.fn().mockResolvedValue(WYNIK)
    const pobierz = utworzLookup(wywolaj)
    const [a, b] = await Promise.all([pobierz('64-000'), pobierz(' 64-000')])
    expect(a).toBe(WYNIK)
    expect(b).toBe(WYNIK)
    expect(wywolaj).toHaveBeenCalledTimes(1)
    expect(wywolaj).toHaveBeenCalledWith('64-000')
  })

  it('zly kod bez zapytania', async () => {
    const wywolaj = vi.fn()
    expect(await utworzLookup(wywolaj)('64000')).toBe(BRAK_WYNIKU)
    expect(wywolaj).not.toHaveBeenCalled()
  })

  it('blad nie zostaje w pamieci i nie wychodzi', async () => {
    const wywolaj = vi
      .fn()
      .mockRejectedValueOnce(new Error('siec'))
      .mockResolvedValueOnce(WYNIK)
    const pobierz = utworzLookup(wywolaj)
    expect(await pobierz('64-000')).toBe(BRAK_WYNIKU)
    expect(await pobierz('64-000')).toBe(WYNIK)
    expect(wywolaj).toHaveBeenCalledTimes(2)
  })

  it('wyjatek synchroniczny tez cichy', async () => {
    const pobierz = utworzLookup(() => {
      throw new Error('x')
    })
    expect(await pobierz('64-000')).toBe(BRAK_WYNIKU)
  })
})

describe('uzupelnijAdresZKodu', () => {
  it('uzupelnia dokument w miejscu', async () => {
    const doc = {
      custom_install_postal_code: '64-000',
      custom_install_city: '',
    }
    const latka = await uzupelnijAdresZKodu(doc, async () => ({
      ...WYNIK,
      cities: ['Kościan'],
    }))
    expect(doc).toMatchObject({
      custom_voivodeship: 'wielkopolskie',
      custom_powiat: 'kościański',
      custom_install_city: 'Kościan',
    })
    expect(latka.custom_install_city).toBe('Kościan')
  })

  it('kod zmieniony w trakcie zapytania: bez zmian', async () => {
    const doc = { custom_install_postal_code: '64-000' }
    await uzupelnijAdresZKodu(doc, async () => {
      doc.custom_install_postal_code = '00-001'
      return WYNIK
    })
    expect(doc).not.toHaveProperty('custom_voivodeship')
  })

  it('niepelny kod: bez zapytania', async () => {
    const pobierz = vi.fn()
    expect(
      await uzupelnijAdresZKodu(
        { custom_install_postal_code: '64-0' },
        pobierz,
      ),
    ).toEqual({})
    expect(pobierz).not.toHaveBeenCalled()
  })
})
