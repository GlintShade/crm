import { describe, expect, it } from 'vitest'
import { ETYKIETY, KOLORY, STATUSY, etykietaStatusu, kolorStatusu } from '@/utils/osdDotacja'

describe('osdDotacja', () => {
  describe('STATUSY', () => {
    it('declares exactly OSD and Dotacja', () => {
      expect(Object.keys(STATUSY).sort()).toEqual(['Dotacja', 'OSD'])
    })

    it('OSD has the 6 owner-specified statuses in order', () => {
      expect(STATUSY.OSD).toEqual([
        'Nie rozpoczęto',
        'Zgłoszenie wysłane',
        'Uwagi OSD',
        'Umowa przyłączeniowa',
        'Licznik wymieniony',
        'Zakończone',
      ])
    })

    it('Dotacja has the 6 owner-specified statuses in order', () => {
      expect(STATUSY.Dotacja).toEqual([
        'Nie rozpoczęto',
        'Wniosek złożony',
        'Uzupełnienie',
        'Decyzja pozytywna',
        'Wypłacona',
        'Odrzucona',
      ])
    })

    it('every tab starts with Nie rozpoczęto', () => {
      for (const zakladka of Object.keys(STATUSY)) {
        expect(STATUSY[zakladka][0]).toBe('Nie rozpoczęto')
      }
    })

    it('an empty string is never a member of any tuple', () => {
      for (const zakladka of Object.keys(STATUSY)) {
        expect(STATUSY[zakladka]).not.toContain('')
      }
    })
  })

  describe('KOLORY', () => {
    it('has a color for every declared status and nothing else', () => {
      for (const zakladka of Object.keys(STATUSY)) {
        expect(Object.keys(KOLORY[zakladka]).sort()).toEqual([...STATUSY[zakladka]].sort())
      }
    })

    it('Nie rozpoczęto is always gray', () => {
      for (const zakladka of Object.keys(STATUSY)) {
        expect(KOLORY[zakladka]['Nie rozpoczęto']).toBe('gray')
      }
    })

    it('in-progress OSD statuses are blue (owner rule: in-progress is always blue)', () => {
      for (const status of [
        'Zgłoszenie wysłane',
        'Uwagi OSD',
        'Umowa przyłączeniowa',
        'Licznik wymieniony',
      ]) {
        expect(KOLORY.OSD[status]).toBe('blue')
      }
    })

    it('in-progress Dotacja statuses are blue', () => {
      for (const status of ['Wniosek złożony', 'Uzupełnienie']) {
        expect(KOLORY.Dotacja[status]).toBe('blue')
      }
    })

    it('terminal success statuses are green', () => {
      expect(KOLORY.OSD['Zakończone']).toBe('green')
      expect(KOLORY.Dotacja['Wypłacona']).toBe('green')
    })

    it('Decyzja pozytywna is lime', () => {
      expect(KOLORY.Dotacja['Decyzja pozytywna']).toBe('lime')
    })

    it('Odrzucona is red', () => {
      expect(KOLORY.Dotacja['Odrzucona']).toBe('red')
    })
  })

  describe('ETYKIETY', () => {
    it('has the card label for each tab', () => {
      expect(ETYKIETY).toEqual({ OSD: 'Status OSD', Dotacja: 'Status dotacji' })
    })
  })

  describe('kolorStatusu', () => {
    it.each([
      ['OSD', 'Zgłoszenie wysłane', 'blue'],
      ['OSD', 'Zakończone', 'green'],
      ['Dotacja', 'Decyzja pozytywna', 'lime'],
      ['Dotacja', 'Odrzucona', 'red'],
    ])('%s / %s -> %s', (zakladka, wartosc, oczekiwany) => {
      expect(kolorStatusu(zakladka, wartosc)).toBe(oczekiwany)
    })

    it.each([[''], [null], [undefined], ['Coś nieznanego']])(
      'empty/unknown value (%p) falls back to gray',
      (wartosc) => {
        expect(kolorStatusu('OSD', wartosc)).toBe('gray')
        expect(kolorStatusu('Dotacja', wartosc)).toBe('gray')
      },
    )
  })

  describe('etykietaStatusu', () => {
    it('returns the value itself when it is a known status', () => {
      expect(etykietaStatusu('OSD', 'Zakończone')).toBe('Zakończone')
      expect(etykietaStatusu('Dotacja', 'Wypłacona')).toBe('Wypłacona')
    })

    it.each([[''], [null], [undefined], ['Coś nieznanego']])(
      'empty/unknown value (%p) returns Nie rozpoczęto',
      (wartosc) => {
        expect(etykietaStatusu('OSD', wartosc)).toBe('Nie rozpoczęto')
        expect(etykietaStatusu('Dotacja', wartosc)).toBe('Nie rozpoczęto')
      },
    )
  })
})
