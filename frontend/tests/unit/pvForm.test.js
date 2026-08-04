import {
  VARIANT_PV,
  VARIANT_PV_BAT,
  VARIANT_BAT,
  VARIANTS,
  MOC_MIN_KW,
  MOC_MAX_KW,
  roundHalf,
  clamp,
  variantHasPv,
  variantHasBattery,
  producentOptionsFor,
  buildMocOptions,
  suggestedKwp,
  suggestedStorageKwh,
  pickBySpec,
  pickMounting,
} from '@/utils/pvForm'

describe('PV form logic', () => {
  describe('domain constants', () => {
    it('exports the supported variants', () => {
      expect(VARIANTS).toEqual([VARIANT_PV, VARIANT_PV_BAT, VARIANT_BAT])
      expect(VARIANT_PV).toBe('Fotowoltaika')
      expect(VARIANT_PV_BAT).toBe('Fotowoltaika + Magazyn')
      expect(VARIANT_BAT).toBe('Magazyn energii')
    })
  })

  describe('roundHalf / clamp', () => {
    it('rounds to the nearest half', () => {
      expect(roundHalf(4.48)).toBe(4.5)
      expect(roundHalf(4.2)).toBe(4)
      expect(roundHalf(4.26)).toBe(4.5)
    })

    it('clamps a value to a range', () => {
      expect(clamp(1, 3, 20)).toBe(3)
      expect(clamp(25, 3, 20)).toBe(20)
      expect(clamp(10, 3, 20)).toBe(10)
    })
  })

  describe('variantHasPv / variantHasBattery', () => {
    it.each([
      [VARIANT_PV, true, false],
      [VARIANT_PV_BAT, true, true],
      [VARIANT_BAT, false, true],
    ])('%s -> hasPv=%s hasBattery=%s', (variant, hasPv, hasBattery) => {
      expect(variantHasPv(variant)).toBe(hasPv)
      expect(variantHasBattery(variant)).toBe(hasBattery)
    })
  })

  describe('producentOptionsFor', () => {
    it('forces FoxESS for PV-only', () => {
      expect(producentOptionsFor(VARIANT_PV)).toEqual(['FoxESS'])
    })

    it('offers Sigenergy/Deye for PV+Magazyn and Magazyn-only', () => {
      expect(producentOptionsFor(VARIANT_PV_BAT)).toEqual(['Sigenergy', 'Deye'])
      expect(producentOptionsFor(VARIANT_BAT)).toEqual(['Sigenergy', 'Deye'])
    })
  })

  describe('buildMocOptions', () => {
    it('returns 35 entries from 3 kW to 20 kW in 0.5 kW steps', () => {
      const options = buildMocOptions()
      expect(options).toHaveLength(35)
      expect(options[0]).toEqual({ value: 3, label: '3 kW (6 paneli)' })
      expect(options[options.length - 1].value).toBe(20)
    })

    it('tracks the grid endpoints from MOC_MIN_KW / MOC_MAX_KW, not hardcoded literals', () => {
      const options = buildMocOptions()
      expect(options[0].value).toBe(MOC_MIN_KW)
      expect(options[options.length - 1].value).toBe(MOC_MAX_KW)
    })
  })

  describe('suggestedKwp', () => {
    it('applies the 1.4x oversize ratio for PV-only', () => {
      expect(suggestedKwp(5000, VARIANT_PV)).toBe(7)
    })

    it('applies a 1x ratio for PV+Magazyn', () => {
      expect(suggestedKwp(5000, VARIANT_PV_BAT)).toBe(5)
    })

    it('returns 0 for Magazyn-only (no PV)', () => {
      expect(suggestedKwp(5000, VARIANT_BAT)).toBe(0)
    })

    it('snaps to the 0.5 kW grid', () => {
      expect(suggestedKwp(3200, VARIANT_PV)).toBe(4.5)
    })

    it('respects the lower bound', () => {
      expect(suggestedKwp(1000, VARIANT_PV)).toBe(3)
    })

    it('respects the upper bound', () => {
      expect(suggestedKwp(20000, VARIANT_PV)).toBe(20)
    })

    it.each([0, null, '', 'abc', -100, NaN])(
      'returns 0 (never NaN) for invalid consumption %s',
      (consumption) => {
        const result = suggestedKwp(consumption, VARIANT_PV)
        expect(result).toBe(0)
        expect(Number.isNaN(result)).toBe(false)
      },
    )

    it('grid invariant: every suggestion is either 0 or a valid moc option', () => {
      const validValues = new Set(buildMocOptions().map((o) => o.value))
      for (let c = 0; c <= 25000; c += 100) {
        const kwp = suggestedKwp(c, VARIANT_PV)
        expect(kwp === 0 || validValues.has(kwp)).toBe(true)
      }
    })
  })

  describe('suggestedStorageKwh', () => {
    it('is the regression anchor for the pre-change value', () => {
      expect(suggestedStorageKwh(5000, 5)).toBe(10)
    })

    it('returns 0 for non-positive consumption or kwp', () => {
      expect(suggestedStorageKwh(0, 5)).toBe(0)
      expect(suggestedStorageKwh(5000, 0)).toBe(0)
    })

    it('is not affected by the PV-only 1.4x oversize ratio', () => {
      const anchor = suggestedStorageKwh(5000, 5)
      const baseKwp = suggestedKwp(5000, VARIANT_PV_BAT)
      expect(suggestedStorageKwh(5000, baseKwp)).toBe(anchor)
    })
  })

  describe('pickBySpec', () => {
    const list = [
      { name: 'a', moc_kw: 10 },
      { name: 'b', moc_kw: 5 },
      { name: 'c', moc_kw: 15 },
    ]

    it('picks the smallest value >= minValue', () => {
      expect(pickBySpec(list, 'moc_kw', 7).name).toBe('a')
    })

    it('picks the exact match when present', () => {
      expect(pickBySpec(list, 'moc_kw', 10).name).toBe('a')
    })

    it('falls back to the largest value when nothing qualifies', () => {
      expect(pickBySpec(list, 'moc_kw', 100).name).toBe('c')
    })

    it('returns undefined for an empty list', () => {
      expect(pickBySpec([], 'moc_kw', 5)).toBeUndefined()
    })

    it('returns undefined for a nullish list', () => {
      expect(pickBySpec(null, 'moc_kw', 5)).toBeUndefined()
      expect(pickBySpec(undefined, 'moc_kw', 5)).toBeUndefined()
    })

    it('does not mutate the input array', () => {
      const original = [
        { name: 'a', moc_kw: 10 },
        { name: 'b', moc_kw: 5 },
        { name: 'c', moc_kw: 15 },
      ]
      const before = original.map((x) => x.name)
      pickBySpec(original, 'moc_kw', 7)
      expect(original.map((x) => x.name)).toEqual(before)
    })
  })

  describe('pickMounting', () => {
    it('prefers a name containing "blacha" (case-insensitive)', () => {
      const list = [
        { name: 'a', nazwa: 'Dachówka' },
        { name: 'b', nazwa: 'BLACHA trapezowa' },
        { name: 'c', nazwa: 'Grunt' },
      ]
      expect(pickMounting(list).name).toBe('b')
    })

    it('falls back to the first item when no name contains "blacha"', () => {
      const list = [
        { name: 'a', nazwa: 'Dachówka' },
        { name: 'c', nazwa: 'Grunt' },
      ]
      expect(pickMounting(list).name).toBe('a')
    })

    it('returns undefined for an empty list', () => {
      expect(pickMounting([])).toBeUndefined()
    })
  })
})
