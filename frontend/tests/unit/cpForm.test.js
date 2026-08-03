import {
  POZIOMY,
  STANDARDY,
  ZRODLA,
  PRACE_M2,
  pustyFormularz,
  dostepnePoziomy,
  dozwoloneDodatki,
  autoM2,
  drzwiM2,
  buildWejscie,
  opisBledu,
} from '@/utils/cpForm'

function deepFreeze(value) {
  Object.freeze(value)
  for (const child of Object.values(value)) {
    if (child && typeof child === 'object' && !Object.isFrozen(child)) {
      deepFreeze(child)
    }
  }
  return value
}

describe('Czyste Powietrze form logic', () => {
  describe('domain constants', () => {
    it('exports the supported form values', () => {
      expect(POZIOMY).toEqual(['podstawowy', 'podwyzszony', 'najwyzszy'])
      expect(STANDARDY).toEqual(['do80', 'od80do140', 'powyzej140'])
      expect(ZRODLA).toEqual(['pompa_ciepla', 'pellet', 'zgazowujacy'])
      expect(PRACE_M2).toEqual(['elewacja', 'strop', 'dach', 'okna'])
    })
  })

  describe('dostepnePoziomy', () => {
    it.each([
      ['do80', ['podstawowy', 'podwyzszony']],
      ['od80do140', ['podstawowy', 'podwyzszony']],
      ['powyzej140', ['podstawowy', 'podwyzszony', 'najwyzszy']],
      [null, ['podstawowy', 'podwyzszony', 'najwyzszy']],
    ])('returns the right levels for %s', (standard, expected) => {
      expect(dostepnePoziomy(standard)).toEqual(expected)
    })

    it('does not offer najwyzszy below the above-140 standard', () => {
      expect(dostepnePoziomy('do80')).not.toContain('najwyzszy')
      expect(dostepnePoziomy('od80do140')).not.toContain('najwyzszy')
    })

    it('does not lock the levels for an unknown standard', () => {
      expect(dostepnePoziomy('unknown')).toEqual(POZIOMY)
    })
  })

  describe('dozwoloneDodatki', () => {
    it.each([
      ['pompa_ciepla', { grzejniki: true, cwu: false }],
      ['pellet', { grzejniki: false, cwu: true }],
      ['zgazowujacy', { grzejniki: false, cwu: true }],
      [null, { grzejniki: false, cwu: false }],
    ])('returns the right add-ons for %s', (zrodlo, expected) => {
      expect(dozwoloneDodatki(zrodlo)).toEqual(expected)
    })

    it('returns no add-ons for an unknown source', () => {
      expect(dozwoloneDodatki('unknown')).toEqual({
        grzejniki: false,
        cwu: false,
      })
    })
  })

  describe('autoM2', () => {
    it('calculates an area from the building area and multiplier', () => {
      expect(autoM2('elewacja', '100', { elewacja: 1.4 })).toBe(140)
    })

    it('rounds the displayed area to two decimal places', () => {
      expect(autoM2('okna', '123', { okna: 0.15 })).toBe(18.45)
    })

    it('accepts a numeric string multiplier', () => {
      expect(autoM2('dach', '100', { dach: '0.9' })).toBe(90)
    })

    it('returns null for a null or missing multiplier', () => {
      expect(autoM2('strop', '100', { strop: null })).toBeNull()
      expect(autoM2('strop', '100', {})).toBeNull()
    })

    it.each(['', '   ', 'zero', '0', '-5'])(
      'returns null for invalid building area %s',
      (powierzchnia) => {
        expect(autoM2('elewacja', powierzchnia, { elewacja: 1.4 })).toBeNull()
      },
    )

    it('returns null for a non-numeric multiplier', () => {
      expect(autoM2('elewacja', '100', { elewacja: 'not-a-number' })).toBeNull()
    })

    it('returns null when the work code is not in the multipliers', () => {
      expect(autoM2('drzwi', '100', { elewacja: 1.4 })).toBeNull()
    })
  })

  describe('drzwiM2', () => {
    it('calculates the area for a whole door count', () => {
      expect(drzwiM2('2', 2)).toBe(4)
    })

    it('rounds the displayed door area and accepts a string multiplier', () => {
      expect(drzwiM2('3', '0.15')).toBe(0.45)
    })

    it('rounds fractional door input down because doors are counted', () => {
      expect(drzwiM2('2.5', 2)).toBe(4)
    })

    it('returns null when the area per door is null', () => {
      expect(drzwiM2('2', null)).toBeNull()
    })

    it.each(['', '0', '-1', 'not-a-number'])(
      'returns null for an invalid door count %s',
      (ilosc) => {
        expect(drzwiM2(ilosc, 2)).toBeNull()
      },
    )
  })

  describe('pustyFormularz', () => {
    it('returns the complete initial form shape', () => {
      expect(pustyFormularz()).toEqual({
        poziom: null,
        standard: null,
        zrodlo: null,
        cwu: false,
        typGrzejnikow: null,
        iloscGrzejnikow: 0,
        powierzchnia: '',
        prace: {
          elewacja: { wybrana: false, reczne: false, m2: '' },
          strop: { wybrana: false, reczne: false, m2: '' },
          dach: { wybrana: false, reczne: false, m2: '' },
          okna: { wybrana: false, reczne: false, m2: '' },
          drzwi: { wybrana: false, ilosc: '' },
        },
      })
    })

    it('returns independent copies, including nested work state', () => {
      const first = pustyFormularz()
      const second = pustyFormularz()
      first.poziom = 'podstawowy'
      first.prace.elewacja.wybrana = true
      first.prace.drzwi.ilosc = '2'

      expect(second.poziom).toBeNull()
      expect(second.prace.elewacja.wybrana).toBe(false)
      expect(second.prace.drzwi.ilosc).toBe('')
      expect(first).not.toBe(second)
      expect(first.prace).not.toBe(second.prace)
    })
  })

  describe('buildWejscie', () => {
    it.each([
      [false, '', null],
      [false, '12.50', null],
      [true, '', null],
      [true, '12.50', '12.50'],
    ])(
      'uses manual m2 only for reczne=%s and m2=%s',
      (reczne, m2, expected) => {
        const form = pustyFormularz()
        form.prace.elewacja = { wybrana: true, reczne, m2 }

        expect(buildWejscie(form).prace.elewacja).toEqual({
          wybrana: true,
          m2: expected,
        })
      },
    )

    it('passes permitted heat-pump radiators through', () => {
      const form = pustyFormularz()
      form.zrodlo = 'pompa_ciepla'
      form.typGrzejnikow = 'grzejnik_co'
      form.iloscGrzejnikow = '3'

      expect(buildWejscie(form)).toMatchObject({
        zrodlo_ciepla: 'pompa_ciepla',
        typ_grzejnikow: 'grzejnik_co',
        ilosc_grzejnikow: 3,
      })
    })

    it('removes stale radiators after switching to pellet', () => {
      const form = pustyFormularz()
      form.zrodlo = 'pellet'
      form.typGrzejnikow = 'grzejnik'
      form.iloscGrzejnikow = '4'

      expect(buildWejscie(form)).toMatchObject({
        typ_grzejnikow: null,
        ilosc_grzejnikow: 0,
      })
    })

    it('passes pellet cwu through', () => {
      const form = pustyFormularz()
      form.zrodlo = 'pellet'
      form.cwu = true

      expect(buildWejscie(form).cwu).toBe(true)
    })

    it('removes stale cwu after switching to a heat pump', () => {
      const form = pustyFormularz()
      form.zrodlo = 'pompa_ciepla'
      form.cwu = true

      expect(buildWejscie(form).cwu).toBe(false)
    })

    it('coerces invalid and fractional counts to non-negative integers', () => {
      const form = pustyFormularz()
      form.zrodlo = 'pompa_ciepla'
      form.iloscGrzejnikow = '2.9'
      form.prace.drzwi.ilosc = '-1.5'

      expect(buildWejscie(form)).toMatchObject({
        ilosc_grzejnikow: 2,
        prace: { drzwi: { ilosc: 0 } },
      })

      form.iloscGrzejnikow = 'invalid'
      form.prace.drzwi.ilosc = ''
      expect(buildWejscie(form)).toMatchObject({
        ilosc_grzejnikow: 0,
        prace: { drzwi: { ilosc: 0 } },
      })
    })

    it('builds the payload without mutating a deeply frozen form', () => {
      const form = pustyFormularz()
      form.poziom = 'podwyzszony'
      form.standard = 'powyzej140'
      form.zrodlo = 'pellet'
      form.cwu = true
      form.powierzchnia = '120'
      form.prace.elewacja = { wybrana: true, reczne: true, m2: '123.45' }
      form.prace.strop = { wybrana: true, reczne: false, m2: '999' }
      form.prace.drzwi = { wybrana: true, ilosc: '2.7' }
      const before = JSON.parse(JSON.stringify(form))

      deepFreeze(form)
      const result = buildWejscie(form)

      expect(result).toEqual({
        poziom: 'podwyzszony',
        standard: 'powyzej140',
        zrodlo_ciepla: 'pellet',
        cwu: true,
        typ_grzejnikow: null,
        ilosc_grzejnikow: 0,
        powierzchnia_m2: '120',
        prace: {
          elewacja: { wybrana: true, m2: '123.45' },
          strop: { wybrana: true, m2: null },
          dach: { wybrana: false, m2: null },
          okna: { wybrana: false, m2: null },
          drzwi: { wybrana: true, ilosc: 2 },
        },
      })
      expect(form).toEqual(before)
    })

    it('returns a fresh payload tree', () => {
      const form = pustyFormularz()
      const first = buildWejscie(form)
      const second = buildWejscie(form)

      first.prace.elewacja.m2 = '10'
      expect(second.prace.elewacja.m2).toBeNull()
      expect(first).not.toBe(second)
      expect(first.prace).not.toBe(second.prace)
    })
  })

  describe('opisBledu', () => {
    it('prefers the first server message', () => {
      expect(opisBledu({ messages: ['Serwerowy komunikat', 'Drugi'] })).toBe(
        'Serwerowy komunikat',
      )
    })

    it('uses a plain error message when there are no server messages', () => {
      expect(opisBledu({ message: 'Błąd połączenia' })).toBe('Błąd połączenia')
    })

    it('falls back for empty or garbage errors', () => {
      const fallback = 'Nie udało się obliczyć oferty.'
      expect(opisBledu({ messages: [], message: '' })).toBe(fallback)
      expect(opisBledu(null)).toBe(fallback)
      expect(opisBledu('garbage')).toBe(fallback)
    })
  })
})
