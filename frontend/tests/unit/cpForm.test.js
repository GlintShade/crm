import {
  POZIOMY,
  STANDARDY,
  ZRODLA,
  PRACE_M2,
  GOSPODARSTWA,
  PROGI_DOCHODU,
  PROGI_KWOTY,
  pustyFormularz,
  wyliczPoziom,
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
      expect(GOSPODARSTWA).toEqual(['jednoosobowe', 'wieloosobowe'])
      expect(PROGI_DOCHODU).toEqual(['niski', 'sredni', 'wysoki'])
    })

    it('pins the income thresholds to the program figures', () => {
      expect(PROGI_KWOTY).toEqual({
        jednoosobowe: { niski: 1800, sredni: 3150 },
        wieloosobowe: { niski: 1300, sredni: 2250 },
      })
    })
  })

  describe('wyliczPoziom', () => {
    it.each([
      ['do80', 'jednoosobowe', 'wysoki', 'podstawowy'],
      ['od80do140', 'jednoosobowe', 'wysoki', 'podstawowy'],
      ['powyzej140', 'jednoosobowe', 'wysoki', 'podstawowy'],
      ['do80', 'wieloosobowe', 'wysoki', 'podstawowy'],
      ['od80do140', 'wieloosobowe', 'wysoki', 'podstawowy'],
      ['powyzej140', 'wieloosobowe', 'wysoki', 'podstawowy'],
      ['do80', 'jednoosobowe', 'sredni', 'podwyzszony'],
      ['od80do140', 'jednoosobowe', 'sredni', 'podwyzszony'],
      ['powyzej140', 'jednoosobowe', 'sredni', 'podwyzszony'],
      ['do80', 'wieloosobowe', 'sredni', 'podwyzszony'],
      ['od80do140', 'wieloosobowe', 'sredni', 'podwyzszony'],
      ['powyzej140', 'wieloosobowe', 'sredni', 'podwyzszony'],
      ['do80', 'jednoosobowe', 'niski', 'podwyzszony'],
      ['od80do140', 'jednoosobowe', 'niski', 'podwyzszony'],
      ['powyzej140', 'jednoosobowe', 'niski', 'najwyzszy'],
      ['do80', 'wieloosobowe', 'niski', 'podwyzszony'],
      ['od80do140', 'wieloosobowe', 'niski', 'podwyzszony'],
      ['powyzej140', 'wieloosobowe', 'niski', 'najwyzszy'],
    ])(
      'derives %s / %s / %s -> %s',
      (standard, gospodarstwo, progDochodu, expected) => {
        expect(wyliczPoziom(standard, gospodarstwo, progDochodu)).toBe(expected)
      },
    )

    it('returns null when the household is missing', () => {
      expect(wyliczPoziom('powyzej140', null, 'niski')).toBeNull()
    })

    it('returns null when the income bracket is missing', () => {
      expect(wyliczPoziom('powyzej140', 'jednoosobowe', null)).toBeNull()
    })

    it('returns null for niski with no standard selected', () => {
      expect(wyliczPoziom(null, 'jednoosobowe', 'niski')).toBeNull()
    })

    it('returns null for an unrecognised income bracket', () => {
      expect(wyliczPoziom('powyzej140', 'jednoosobowe', 'unknown')).toBeNull()
    })

    it('never yields najwyzszy for a standard other than powyzej140', () => {
      const standardy = [...STANDARDY, null, 'unknown']
      const gospodarstwa = [...GOSPODARSTWA, null]
      const progi = [...PROGI_DOCHODU, null, 'unknown']

      for (const standard of standardy) {
        for (const gospodarstwo of gospodarstwa) {
          for (const prog of progi) {
            const poziom = wyliczPoziom(standard, gospodarstwo, prog)
            if (poziom === 'najwyzszy') {
              expect(standard).toBe('powyzej140')
            }
          }
        }
      }
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
      expect(autoM2('dach', '123', { dach: 0.15 })).toBe(18.45)
    })

    it('accepts a numeric string multiplier', () => {
      expect(autoM2('dach', '100', { dach: '0.9' })).toBe(90)
    })

    it('returns null for a null or missing multiplier', () => {
      expect(autoM2('strop', '100', { strop: null })).toBeNull()
      expect(autoM2('strop', '100', {})).toBeNull()
    })

    it('derives windows from the facade area, never from the building area directly', () => {
      // 100 m² of floor area -> facade = 100 * 1.3 = 130 m² -> windows = 130 * 0.10 = 13 m²
      expect(
        autoM2('okna', '100', { elewacja: 1.3, okna_od_elewacji: 0.1 }),
      ).toBe(13)
    })

    it('rounds the derived windows area to two decimal places', () => {
      expect(
        autoM2('okna', '123', { elewacja: 1.35, okna_od_elewacji: 0.111 }),
      ).toBe(18.43)
    })

    it('returns null for okna when the facade multiplier is missing', () => {
      expect(autoM2('okna', '100', { okna_od_elewacji: 0.1 })).toBeNull()
    })

    it('returns null for okna when okna_od_elewacji is missing', () => {
      expect(autoM2('okna', '100', { elewacja: 1.3 })).toBeNull()
    })

    it('does not use the obsolete mnozniki.okna key for windows', () => {
      expect(autoM2('okna', '100', { okna: 0.15 })).toBeNull()
    })

    it('leaves elewacja/strop/dach on the plain powierzchnia × mnoznik rule', () => {
      expect(autoM2('elewacja', '100', { elewacja: 1.3 })).toBe(130)
      expect(autoM2('strop', '100', { strop: 1 })).toBe(100)
      expect(autoM2('dach', '100', { dach: 1.05 })).toBe(105)
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
        standard: null,
        gospodarstwo: null,
        progDochodu: null,
        zrodlo: null,
        zrodloWlaczone: false,
        cwu: false,
        typGrzejnikow: null,
        iloscGrzejnikow: 0,
        powierzchnia: '',
        termoWlaczone: false,
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
      first.gospodarstwo = 'jednoosobowe'
      first.prace.elewacja.wybrana = true
      first.prace.drzwi.ilosc = '2'

      expect(second.gospodarstwo).toBeNull()
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
        form.termoWlaczone = true
        form.prace.elewacja = { wybrana: true, reczne, m2 }

        expect(buildWejscie(form).prace.elewacja).toEqual({
          wybrana: true,
          m2: expected,
        })
      },
    )

    it('passes permitted heat-pump radiators through when the source scope is on', () => {
      const form = pustyFormularz()
      form.zrodloWlaczone = true
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
      form.zrodloWlaczone = true
      form.zrodlo = 'pellet'
      form.typGrzejnikow = 'grzejnik'
      form.iloscGrzejnikow = '4'

      expect(buildWejscie(form)).toMatchObject({
        typ_grzejnikow: null,
        ilosc_grzejnikow: 0,
      })
    })

    it.each([
      ['pellet', true],
      ['zgazowujacy', true],
      ['pompa_ciepla', false],
    ])(
      'derives cwu from the source (%s -> %s) regardless of form.cwu',
      (zrodlo, expected) => {
        const form = pustyFormularz()
        form.zrodloWlaczone = true
        form.zrodlo = zrodlo
        form.cwu = false

        expect(buildWejscie(form).cwu).toBe(expected)
      },
    )

    it('cwu is false while the source scope is off, even for pellet', () => {
      const form = pustyFormularz()
      form.zrodloWlaczone = false
      form.zrodlo = 'pellet'
      form.cwu = true

      expect(buildWejscie(form).cwu).toBe(false)
    })

    it('coerces invalid and fractional counts to non-negative integers', () => {
      const form = pustyFormularz()
      form.zrodloWlaczone = true
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
      form.standard = 'powyzej140'
      form.gospodarstwo = 'wieloosobowe'
      form.progDochodu = 'sredni'
      form.zrodloWlaczone = true
      form.zrodlo = 'pellet'
      form.cwu = true
      form.termoWlaczone = true
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
        gospodarstwo: 'wieloosobowe',
        prog_dochodu: 'sredni',
        zrodlo_ciepla: 'pellet',
        cwu: true,
        typ_grzejnikow: null,
        ilosc_grzejnikow: 0,
        powierzchnia_m2: 120,
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

    describe('scope toggles', () => {
      function skonfigurowanyFormularz() {
        const form = pustyFormularz()
        form.standard = 'od80do140'
        form.gospodarstwo = 'jednoosobowe'
        form.progDochodu = 'wysoki'
        form.zrodlo = 'pellet'
        form.cwu = false
        form.typGrzejnikow = null
        form.iloscGrzejnikow = 0
        form.powierzchnia = '100'
        form.prace.elewacja = { wybrana: true, reczne: false, m2: '' }
        form.prace.strop = { wybrana: true, reczne: true, m2: '50' }
        form.prace.dach = { wybrana: false, reczne: false, m2: '' }
        form.prace.okna = { wybrana: true, reczne: false, m2: '' }
        form.prace.drzwi = { wybrana: true, ilosc: '2' }
        return form
      }

      it('emits both scopes when both toggles are on', () => {
        const form = skonfigurowanyFormularz()
        form.zrodloWlaczone = true
        form.termoWlaczone = true
        const before = JSON.parse(JSON.stringify(form))

        const result = buildWejscie(form)

        expect(result.zrodlo_ciepla).toBe('pellet')
        expect(result.cwu).toBe(true)
        expect(result.prace.elewacja.wybrana).toBe(true)
        expect(result.prace.strop.wybrana).toBe(true)
        expect(result.prace.strop.m2).toBe('50')
        expect(result.prace.okna.wybrana).toBe(true)
        expect(result.prace.drzwi).toEqual({ wybrana: true, ilosc: 2 })
        expect(form).toEqual(before)
      })

      it('emits only the source scope when termo is off, keeping typed work values', () => {
        const form = skonfigurowanyFormularz()
        form.zrodloWlaczone = true
        form.termoWlaczone = false
        const before = JSON.parse(JSON.stringify(form))

        const result = buildWejscie(form)

        expect(result.zrodlo_ciepla).toBe('pellet')
        expect(result.cwu).toBe(true)
        expect(result.prace.elewacja.wybrana).toBe(false)
        expect(result.prace.strop.wybrana).toBe(false)
        // The typed m2 survives even though the scope is off, so switching
        // back to TAK does not require the rep to re-enter anything.
        expect(result.prace.strop.m2).toBe('50')
        expect(result.prace.okna.wybrana).toBe(false)
        expect(result.prace.drzwi).toEqual({ wybrana: false, ilosc: 2 })
        expect(form).toEqual(before)
      })

      it('emits only the termo scope when the source is off', () => {
        const form = skonfigurowanyFormularz()
        form.zrodloWlaczone = false
        form.termoWlaczone = true
        const before = JSON.parse(JSON.stringify(form))

        const result = buildWejscie(form)

        expect(result.zrodlo_ciepla).toBeNull()
        expect(result.cwu).toBe(false)
        expect(result.typ_grzejnikow).toBeNull()
        expect(result.ilosc_grzejnikow).toBe(0)
        expect(result.prace.elewacja.wybrana).toBe(true)
        expect(result.prace.strop.wybrana).toBe(true)
        expect(result.prace.okna.wybrana).toBe(true)
        expect(result.prace.drzwi).toEqual({ wybrana: true, ilosc: 2 })
        expect(form).toEqual(before)
      })

      it('emits neither scope when both toggles are off', () => {
        const form = skonfigurowanyFormularz()
        form.zrodloWlaczone = false
        form.termoWlaczone = false
        const before = JSON.parse(JSON.stringify(form))

        const result = buildWejscie(form)

        expect(result.zrodlo_ciepla).toBeNull()
        expect(result.cwu).toBe(false)
        expect(result.prace.elewacja.wybrana).toBe(false)
        expect(result.prace.strop.wybrana).toBe(false)
        expect(result.prace.strop.m2).toBe('50')
        expect(result.prace.drzwi).toEqual({ wybrana: false, ilosc: 2 })
        expect(form).toEqual(before)
      })
    })

    it('derives the subsidy level from household and income when building the payload', () => {
      const form = pustyFormularz()
      form.standard = 'powyzej140'
      form.gospodarstwo = 'wieloosobowe'
      form.progDochodu = 'niski'

      expect(buildWejscie(form)).toMatchObject({
        poziom: 'najwyzszy',
        gospodarstwo: 'wieloosobowe',
        prog_dochodu: 'niski',
      })
    })

    describe('powierzchnia_m2 coercion', () => {
      it('sends 0, not a blank string, for a freshly created form', () => {
        const form = pustyFormularz()
        expect(buildWejscie(form).powierzchnia_m2).toBe(0)
      })

      it('sends 0 for a source-only quote (termo off) with a blank area — the reported bug', () => {
        const form = pustyFormularz()
        form.zrodloWlaczone = true
        form.zrodlo = 'pompa_ciepla'
        form.termoWlaczone = false
        const before = JSON.parse(JSON.stringify(form))

        const result = buildWejscie(form)

        expect(result.powierzchnia_m2).toBe(0)
        expect(result.zrodlo_ciepla).toBe('pompa_ciepla')
        expect(form).toEqual(before)
      })

      it('sends 0 with both scopes off', () => {
        const form = pustyFormularz()
        expect(buildWejscie(form).powierzchnia_m2).toBe(0)
      })

      it('preserves a typed decimal area without flooring it', () => {
        const form = pustyFormularz()
        form.powierzchnia = '120.5'
        expect(buildWejscie(form).powierzchnia_m2).toBe(120.5)
      })

      it('coerces a whitespace-only area to 0', () => {
        const form = pustyFormularz()
        form.powierzchnia = '   '
        expect(buildWejscie(form).powierzchnia_m2).toBe(0)
      })

      it('coerces a non-numeric area to 0', () => {
        const form = pustyFormularz()
        form.powierzchnia = 'abc'
        expect(buildWejscie(form).powierzchnia_m2).toBe(0)
      })

      it('coerces a negative area to 0', () => {
        const form = pustyFormularz()
        form.powierzchnia = '-15.5'
        expect(buildWejscie(form).powierzchnia_m2).toBe(0)
      })

      it('does not mutate the form for any of the above inputs', () => {
        for (const powierzchnia of ['', '   ', 'abc', '-15.5', '120.5']) {
          const form = pustyFormularz()
          form.powierzchnia = powierzchnia
          const before = JSON.parse(JSON.stringify(form))
          deepFreeze(form)

          buildWejscie(form)

          expect(form).toEqual(before)
        }
      })
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
