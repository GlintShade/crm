import {
  opisZestawu,
  grupujMocePv,
  grupujMagazyny,
  udzialyCeny,
  podsumowanieMontazu,
  podsumowanieFinansowania,
  podsumowanieDodatkow,
  VARIANT_PV,
  VARIANT_PV_BAT,
  VARIANT_BAT,
  VARIANTS,
  MOC_MIN_KW,
  MIN_PANELI,
  paneleDlaZestawu,
  MOC_MAX_KW,
  roundHalf,
  clamp,
  variantHasPv,
  variantHasBattery,
  producentOptionsFor,
  ZESTAWY,
  DOMYSLNY_ZESTAW,
  zestawProducent,
  licznikDostepny,
  buildMocOptions,
  panelLabel,
  buildMocOptionsForPanel,
  snapMocToPanel,
  pickMocForTarget,
  suggestedKwp,
  suggestedStorageKwh,
  pickBySpec,
  pickMounting,
  PROG_PPOZ_KW,
  ppozWymagane,
  ppozWymuszonyProgiem,
  RODZAJE_KLIMY_DODATKU,
  RODZAJ_KLIMY_CHLODZENIE,
  RODZAJ_KLIMY_DOGRZEWANIE,
  RODZAJ_KLIMY_GRZANIE,
  POWIERZCHNIA_KLIMY,
  modeleDodatkuKlimy,
  domyslnyStanEms,
  klimaDodatekDostepna,
  dodatekPaneleDostepny,
  emsDostepny,
  emsWymuszony,
  pstrykDostepny,
  evDostepne,
  moceDodatkuKlimy,
  evOpcje,
  sanitizujDodatki,
  celKwpComfortPremium,
  celKwhComfortPremium,
  dobierzMocComfortPremium,
  dobierzMagazynComfortPremium,
  czyAutodobor,
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

    it('offers only the producer of the chosen zestaw for variants with storage', () => {
      expect(producentOptionsFor(VARIANT_PV_BAT, 'COMFORT')).toEqual(['Hoymiles'])
      expect(producentOptionsFor(VARIANT_BAT, 'COMFORT PREMIUM')).toEqual(['Solax'])
      expect(producentOptionsFor(VARIANT_BAT, 'PREMIUM +')).toEqual(['Sigenergy'])
    })

    it('falls back to the default zestaw producer when zestaw is missing or unknown', () => {
      expect(producentOptionsFor(VARIANT_PV_BAT)).toEqual(['Sigenergy'])
      expect(producentOptionsFor(VARIANT_BAT, 'nope')).toEqual(['Sigenergy'])
    })

    it('ignores the zestaw for PV-only', () => {
      expect(producentOptionsFor(VARIANT_PV, 'COMFORT')).toEqual(['FoxESS'])
    })
  })

  describe('ZESTAWY', () => {
    it('maps the three zestawy to their producers, default is PREMIUM +', () => {
      expect(ZESTAWY.map((z) => [z.kod, z.producent])).toEqual([
        ['COMFORT', 'Hoymiles'],
        ['COMFORT PREMIUM', 'Solax'],
        ['PREMIUM +', 'Sigenergy'],
      ])
      expect(DOMYSLNY_ZESTAW).toBe('PREMIUM +')
    })

    it('carries the bill-guarantee note only as text on COMFORT PREMIUM', () => {
      const premium = ZESTAWY.find((z) => z.kod === 'COMFORT PREMIUM')
      expect(premium.opis).toBe('Solax, Abonament 49 zł/mies.')
      expect(ZESTAWY.filter((z) => z.opis.includes('49'))).toHaveLength(1)
    })

    it('contains no em or en dashes', () => {
      expect(JSON.stringify(ZESTAWY)).not.toMatch(/[\u2013\u2014]/)
    })

    it('zestawProducent resolves known codes and returns empty for unknown', () => {
      expect(zestawProducent('COMFORT')).toBe('Hoymiles')
      expect(zestawProducent('')).toBe('')
      expect(zestawProducent('x')).toBe('')
    })
  })

  describe('licznikDostepny', () => {
    it('is false for FoxESS', () => {
      expect(licznikDostepny('FoxESS')).toBe(false)
    })

    it('is false for an empty or unset producent', () => {
      expect(licznikDostepny('')).toBe(false)
      expect(licznikDostepny(undefined)).toBe(false)
    })

    it('is true for every hybrid inverter producer', () => {
      expect(licznikDostepny('Sigenergy')).toBe(true)
      expect(licznikDostepny('Deye')).toBe(true)
      expect(licznikDostepny('Hoymiles')).toBe(true)
      expect(licznikDostepny('Solax')).toBe(true)
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

  describe('panelLabel', () => {
    it('joins panel name and model and appends positive finite power', () => {
      expect(panelLabel({ nazwa: 'AIKO', model: 'Neostar 2S+', moc_wp: 500 })).toBe(
        'AIKO Neostar 2S+ (500 Wp)',
      )
      expect(panelLabel({ nazwa: 'AIKO' })).toBe('AIKO')
      expect(panelLabel({})).toBe('')
      expect(panelLabel(null)).toBe('')
      expect(panelLabel({ nazwa: 'AIKO', moc_wp: 0 })).toBe('AIKO')
    })
  })

  describe('buildMocOptionsForPanel', () => {
    it('matches the legacy grid for 500 Wp panels', () => {
      expect(buildMocOptionsForPanel(500).map((o) => o.value)).toEqual(
        buildMocOptions().map((o) => o.value),
      )
      expect(buildMocOptionsForPanel(500)[0]).toEqual({
        panele: 6,
        value: 3,
        label: '6 paneli, 3.00 kWp',
      })
      expect(buildMocOptionsForPanel(500).at(-1)).toMatchObject({
        panele: 40,
        value: 20,
      })
    })

    it('starts at MIN_PANELI panels, also for 475 Wp panels', () => {
      expect(MIN_PANELI).toBe(6)
      expect(buildMocOptionsForPanel(475)[0]).toEqual({
        panele: 6,
        value: 2.85,
        label: '6 paneli, 2.85 kWp',
      })
      expect(buildMocOptionsForPanel(475).at(-1).value).toBeLessThanOrEqual(MOC_MAX_KW)
    })

    it('builds integer panel counts for 450 Wp panels', () => {
      const options = buildMocOptionsForPanel(450)
      expect(options[0]).toEqual({ panele: 6, value: 2.7, label: '6 paneli, 2.70 kWp' })
      expect(options.at(-1)).toEqual({
        panele: 44,
        value: 19.8,
        label: '44 paneli, 19.80 kWp',
      })
    })

    it.each([0, -1, null, undefined, NaN, '500'])(
      'returns an empty list for invalid panel power %s',
      (wp) => {
        expect(buildMocOptionsForPanel(wp)).toEqual([])
      },
    )
  })

  describe('paneleDlaZestawu', () => {
    const aiko = { name: 'a', zestaw_typ: '' }
    const sun = { name: 's', zestaw_typ: 'COMFORT' }
    const tcl = { name: 't', zestaw_typ: 'COMFORT PREMIUM' }
    const karty = [aiko, sun, tcl]

    it('shows only own cards for a zestaw that has them', () => {
      expect(paneleDlaZestawu(karty, 'COMFORT')).toEqual([sun])
      expect(paneleDlaZestawu(karty, 'COMFORT PREMIUM')).toEqual([tcl])
    })

    it('falls back to universal cards for zestaw without own cards', () => {
      expect(paneleDlaZestawu(karty, 'PREMIUM +')).toEqual([aiko])
    })

    it('shows universal cards for plain PV (empty zestaw)', () => {
      expect(paneleDlaZestawu(karty, '')).toEqual([aiko])
    })

    it('treats missing zestaw_typ as universal and tolerates bad input', () => {
      expect(paneleDlaZestawu([{ name: 'x' }], 'COMFORT')).toEqual([{ name: 'x' }])
      expect(paneleDlaZestawu(null, 'COMFORT')).toEqual([])
    })
  })

  describe('snapMocToPanel', () => {
    it('snaps to the nearest panel-compatible power', () => {
      expect(snapMocToPanel(10, 450)).toBe(9.9)
      expect(snapMocToPanel(3.25, 500)).toBe(3)
      expect(snapMocToPanel(1, 500)).toBe(3)
      expect(snapMocToPanel(25, 500)).toBe(20)
    })

    it('returns null for invalid input or empty options', () => {
      expect(snapMocToPanel(10, 0)).toBeNull()
      expect(snapMocToPanel(null, 500)).toBeNull()
    })
  })

  describe('pickMocForTarget', () => {
    it('picks the first power meeting the target and clamps to the range', () => {
      expect(pickMocForTarget(9.95, 450)).toBe(10.35)
      expect(pickMocForTarget(3.0, 500)).toBe(3)
      expect(pickMocForTarget(25, 450)).toBe(19.8)
    })

    it('returns null for empty options', () => {
      expect(pickMocForTarget(10, 0)).toBeNull()
    })
  })

  describe('ppozWymagane', () => {
    it('is false at exactly the threshold (strict greater-than)', () => {
      expect(ppozWymagane({ mocNowaKw: PROG_PPOZ_KW, istniejacaPv: 'Nie', mocIstniejacaKwp: 0 })).toBe(false)
      expect(ppozWymagane({ mocNowaKw: 6.5, istniejacaPv: 'Nie', mocIstniejacaKwp: 0 })).toBe(false)
    })

    it('is false below the threshold', () => {
      expect(ppozWymagane({ mocNowaKw: 5, istniejacaPv: 'Nie', mocIstniejacaKwp: 0 })).toBe(false)
    })

    it('is true above the threshold on new power alone', () => {
      expect(ppozWymagane({ mocNowaKw: 7, istniejacaPv: 'Nie', mocIstniejacaKwp: 0 })).toBe(true)
    })

    it('is true when new plus existing power exceeds the threshold', () => {
      expect(ppozWymagane({ mocNowaKw: 3, istniejacaPv: 'Tak', mocIstniejacaKwp: 5 })).toBe(true)
    })

    it('ignores the existing power when istniejacaPv is "Nie"', () => {
      expect(ppozWymagane({ mocNowaKw: 3, istniejacaPv: 'Nie', mocIstniejacaKwp: 5 })).toBe(false)
    })

    it('wins via ppozKalkulator even below the threshold', () => {
      expect(ppozWymagane({ mocNowaKw: 1, istniejacaPv: 'Nie', mocIstniejacaKwp: 0, ppozKalkulator: 'Tak' })).toBe(true)
    })

    it('does not change the rule when ppozKalkulator is "Nie" or undefined', () => {
      expect(ppozWymagane({ mocNowaKw: 3, istniejacaPv: 'Nie', mocIstniejacaKwp: 0, ppozKalkulator: 'Nie' })).toBe(false)
      expect(ppozWymagane({ mocNowaKw: 7, istniejacaPv: 'Nie', mocIstniejacaKwp: 0, ppozKalkulator: 'Nie' })).toBe(true)
      expect(ppozWymagane({ mocNowaKw: 7, istniejacaPv: 'Nie', mocIstniejacaKwp: 0, ppozKalkulator: undefined })).toBe(true)
    })

    it('treats empty, null and undefined inputs as zero', () => {
      expect(ppozWymagane({ mocNowaKw: null, istniejacaPv: 'Nie', mocIstniejacaKwp: null })).toBe(false)
      expect(ppozWymagane({ mocNowaKw: undefined, istniejacaPv: 'Tak', mocIstniejacaKwp: undefined })).toBe(false)
      expect(ppozWymagane({ mocNowaKw: '', istniejacaPv: 'Tak', mocIstniejacaKwp: '' })).toBe(false)
      expect(ppozWymagane({ mocNowaKw: 7, istniejacaPv: 'Tak', mocIstniejacaKwp: NaN })).toBe(true)
    })

    it('accepts string numbers from number inputs', () => {
      expect(ppozWymagane({ mocNowaKw: '5', istniejacaPv: 'Tak', mocIstniejacaKwp: '3.5' })).toBe(true)
      expect(ppozWymagane({ mocNowaKw: '3', istniejacaPv: 'Tak', mocIstniejacaKwp: '3' })).toBe(false)
    })

    it('wins via ppozRecznie even below the threshold', () => {
      expect(ppozWymagane({ mocNowaKw: 1, istniejacaPv: 'Nie', mocIstniejacaKwp: 0, ppozRecznie: 'Tak' })).toBe(true)
    })

    it('does not change the rule when ppozRecznie is "Nie" or undefined', () => {
      expect(ppozWymagane({ mocNowaKw: 3, istniejacaPv: 'Nie', mocIstniejacaKwp: 0, ppozRecznie: 'Nie' })).toBe(false)
      expect(ppozWymagane({ mocNowaKw: 7, istniejacaPv: 'Nie', mocIstniejacaKwp: 0, ppozRecznie: 'Nie' })).toBe(true)
      expect(ppozWymagane({ mocNowaKw: 7, istniejacaPv: 'Nie', mocIstniejacaKwp: 0, ppozRecznie: undefined })).toBe(true)
    })

    it('does not accept case or whitespace variants of "Tak" for ppozRecznie', () => {
      expect(ppozWymagane({ mocNowaKw: 1, istniejacaPv: 'Nie', mocIstniejacaKwp: 0, ppozRecznie: ' Tak' })).toBe(false)
      expect(ppozWymagane({ mocNowaKw: 1, istniejacaPv: 'Nie', mocIstniejacaKwp: 0, ppozRecznie: 'tak' })).toBe(false)
    })
  })

  describe('ppozWymuszonyProgiem', () => {
    it('is false at exactly the threshold (strict greater-than)', () => {
      expect(ppozWymuszonyProgiem({ mocNowaKw: PROG_PPOZ_KW, istniejacaPv: 'Nie', mocIstniejacaKwp: 0 })).toBe(false)
    })

    it('is true just above the threshold', () => {
      expect(ppozWymuszonyProgiem({ mocNowaKw: PROG_PPOZ_KW + 0.1, istniejacaPv: 'Nie', mocIstniejacaKwp: 0 })).toBe(true)
    })

    it('is false below the threshold', () => {
      expect(ppozWymuszonyProgiem({ mocNowaKw: 5, istniejacaPv: 'Nie', mocIstniejacaKwp: 0 })).toBe(false)
    })

    it('sums new and existing power', () => {
      expect(ppozWymuszonyProgiem({ mocNowaKw: 3, istniejacaPv: 'Tak', mocIstniejacaKwp: 5 })).toBe(true)
    })

    it('ignores the existing power when istniejacaPv is "Nie"', () => {
      expect(ppozWymuszonyProgiem({ mocNowaKw: 3, istniejacaPv: 'Nie', mocIstniejacaKwp: 5 })).toBe(false)
    })
  })

  // --- Opcje dodatkowe PV / PV+ME / ME (ops#225) ------------------------
  describe('RODZAJE_KLIMY_DODATKU', () => {
    it('exports exactly three rodzaje, each with a grupa', () => {
      expect(RODZAJE_KLIMY_DODATKU).toHaveLength(3)
      expect(RODZAJE_KLIMY_DODATKU.map((r) => r.value)).toEqual([
        RODZAJ_KLIMY_CHLODZENIE,
        RODZAJ_KLIMY_DOGRZEWANIE,
        RODZAJ_KLIMY_GRZANIE,
      ])
    })

    it('maps each rodzaj to a standalone klima grupa (no fixed model)', () => {
      expect(RODZAJE_KLIMY_DODATKU.map((r) => r.grupa)).toEqual(['klima_chlodzenie', 'klima_dogrzewanie', 'klima_grzanie'])
      expect(RODZAJE_KLIMY_DODATKU.every((r) => r.model === undefined)).toBe(true)
    })
  })

  describe('POWIERZCHNIA_KLIMY', () => {
    it('has an entry for every catalog power', () => {
      expect(POWIERZCHNIA_KLIMY['2.6']).toBe('do 25 m2')
      expect(POWIERZCHNIA_KLIMY['3.5']).toBe('25-40 m2')
      expect(POWIERZCHNIA_KLIMY['5.1']).toBe('40-55 m2')
      expect(POWIERZCHNIA_KLIMY['6.8']).toBe('55-75 m2')
    })
  })

  describe('klimaDodatekDostepna', () => {
    it('is available for all three variants', () => {
      expect(klimaDodatekDostepna(VARIANT_PV)).toBe(true)
      expect(klimaDodatekDostepna(VARIANT_PV_BAT)).toBe(true)
      expect(klimaDodatekDostepna(VARIANT_BAT)).toBe(true)
    })

    it('is false for an unknown variant', () => {
      expect(klimaDodatekDostepna('')).toBe(false)
      expect(klimaDodatekDostepna('Cos innego')).toBe(false)
    })
  })

  describe('dodatekPaneleDostepny', () => {
    it('is true only for Magazyn energii', () => {
      expect(dodatekPaneleDostepny(VARIANT_BAT)).toBe(true)
    })

    it('is false for PV and PV+Magazyn', () => {
      expect(dodatekPaneleDostepny(VARIANT_PV)).toBe(false)
      expect(dodatekPaneleDostepny(VARIANT_PV_BAT)).toBe(false)
    })
  })

  describe('emsDostepny', () => {
    it('is true only for Deye with a battery variant', () => {
      expect(emsDostepny({ producent: 'Deye', variant: VARIANT_PV_BAT })).toBe(true)
      expect(emsDostepny({ producent: 'Deye', variant: VARIANT_BAT })).toBe(true)
    })

    it('is false for Deye without a battery variant', () => {
      expect(emsDostepny({ producent: 'Deye', variant: VARIANT_PV })).toBe(false)
    })

    it('is false for other producents', () => {
      expect(emsDostepny({ producent: 'Sigenergy', variant: VARIANT_PV_BAT })).toBe(false)
      expect(emsDostepny({ producent: 'FoxESS', variant: VARIANT_PV })).toBe(false)
    })

    it('handles missing arguments', () => {
      expect(emsDostepny()).toBe(false)
      expect(emsDostepny({})).toBe(false)
    })
  })

  describe('pstrykDostepny', () => {
    it('is true only for Sigenergy with a battery variant', () => {
      expect(pstrykDostepny({ producent: 'Sigenergy', variant: VARIANT_PV_BAT })).toBe(true)
      expect(pstrykDostepny({ producent: 'Sigenergy', variant: VARIANT_BAT })).toBe(true)
    })

    it('is false for Sigenergy without a battery variant', () => {
      expect(pstrykDostepny({ producent: 'Sigenergy', variant: VARIANT_PV })).toBe(false)
    })

    it('is false for other producents', () => {
      expect(pstrykDostepny({ producent: 'Deye', variant: VARIANT_PV_BAT })).toBe(false)
    })
  })

  describe('evDostepne', () => {
    it('is true only for Sigenergy with a battery variant', () => {
      expect(evDostepne({ producent: 'Sigenergy', variant: VARIANT_PV_BAT })).toBe(true)
      expect(evDostepne({ producent: 'Sigenergy', variant: VARIANT_BAT })).toBe(true)
    })

    it('is false for Sigenergy without a battery variant', () => {
      expect(evDostepne({ producent: 'Sigenergy', variant: VARIANT_PV })).toBe(false)
    })

    it('is false for other producents', () => {
      expect(evDostepne({ producent: 'Deye', variant: VARIANT_PV_BAT })).toBe(false)
    })
  })

  describe('moceDodatkuKlimy', () => {
    const katalog = [
      { kod: 'dod_klima_elis_x_2_6', grupa: 'dod_klima', model: 'Elis X', moc_kw: 2.6, cena: 4900 },
      { kod: 'dod_klima_elis_x_3_5', grupa: 'dod_klima', model: 'Elis X', moc_kw: 3.5, cena: 5000 },
      { kod: 'dod_klima_elis_x_5_1', grupa: 'dod_klima', model: 'Elis X', moc_kw: 5.1, cena: 5600 },
      { kod: 'dod_klima_elis_x_6_8', grupa: 'dod_klima', model: 'Elis X', moc_kw: 6.8, cena: 6300 },
      { kod: 'dod_klima_teta_x_3_5', grupa: 'dod_klima', model: 'Teta X', moc_kw: 3.5, cena: 5400 },
      { kod: 'dod_klima_teta_x_5_1', grupa: 'dod_klima', model: 'Teta X', moc_kw: 5.1, cena: 6200 },
      { kod: 'dod_klima_mira_x_3_5', grupa: 'dod_klima', model: 'Mira X', moc_kw: 3.5, cena: 6600 },
      { kod: 'dod_panele_1', grupa: 'dod_panele', model: '', moc_kw: 0, cena: 3600 },
    ]

    it('filters by model and sorts ascending by moc_kw', () => {
      const opcje = moceDodatkuKlimy(katalog, 'Elis X')
      expect(opcje.map((o) => o.kod)).toEqual([
        'dod_klima_elis_x_2_6', 'dod_klima_elis_x_3_5', 'dod_klima_elis_x_5_1', 'dod_klima_elis_x_6_8',
      ])
      expect(opcje.map((o) => o.moc_kw)).toEqual([2.6, 3.5, 5.1, 6.8])
    })

    it('builds the label with the comma decimal and the m2 hint', () => {
      const opcje = moceDodatkuKlimy(katalog, 'Teta X')
      expect(opcje).toEqual([
        { kod: 'dod_klima_teta_x_3_5', moc_kw: 3.5, label: '3,5 kW (25-40 m2)', cena: 5400 },
        { kod: 'dod_klima_teta_x_5_1', moc_kw: 5.1, label: '5,1 kW (40-55 m2)', cena: 6200 },
      ])
    })

    it('returns a single option for a rodzaj with one power (Mira X)', () => {
      const opcje = moceDodatkuKlimy(katalog, 'Mira X')
      expect(opcje).toEqual([{ kod: 'dod_klima_mira_x_3_5', moc_kw: 3.5, label: '3,5 kW (25-40 m2)', cena: 6600 }])
    })

    it('never leaks other grupy (dod_panele) into the result', () => {
      const opcje = moceDodatkuKlimy(katalog, 'Elis X')
      expect(opcje.every((o) => !o.kod.startsWith('dod_panele'))).toBe(true)
    })

    it('returns an empty list for an unknown model or a non-array catalog', () => {
      expect(moceDodatkuKlimy(katalog, '')).toEqual([])
      expect(moceDodatkuKlimy(katalog, 'nieznany')).toEqual([])
      expect(moceDodatkuKlimy(null, 'Elis X')).toEqual([])
      expect(moceDodatkuKlimy(undefined, 'Elis X')).toEqual([])
    })
  })

  describe('evOpcje', () => {
    const katalog = [
      { kod: 'ev_ac_7', nazwa: 'Ładowarka EV AC 7 kW', grupa: 'ev_ac', moc_kw: 7, cena: 4100 },
      { kod: 'ev_ac_11', nazwa: 'Ładowarka EV AC 11 kW', grupa: 'ev_ac', moc_kw: 11, cena: 4300 },
      { kod: 'ev_ac_22', nazwa: 'Ładowarka EV AC 22 kW', grupa: 'ev_ac', moc_kw: 22, cena: 4500 },
      { kod: 'ev_dc_12_7_5', nazwa: 'Ładowarka EV DC 12 kW (kabel 7,5m)', grupa: 'ev_dc', moc_kw: 12, cena: 6900 },
      { kod: 'ev_dc_25_10', nazwa: 'Ładowarka EV DC 25 kW (kabel 10m)', grupa: 'ev_dc', moc_kw: 25, cena: 9100 },
      { kod: 'dod_panele_1', nazwa: 'Panele PV x 1 (dodatek)', grupa: 'dod_panele', moc_kw: 0, cena: 3600 },
    ]

    it('returns only AC options for a TP2 falownik', () => {
      const opcje = evOpcje(katalog, { producent: 'Sigenergy', variant: VARIANT_PV_BAT, sigenTyp: 'TP2' })
      expect(opcje.map((o) => o.kod)).toEqual(['ev_ac_7', 'ev_ac_11', 'ev_ac_22'])
    })

    it('returns AC and DC options for an AIO falownik, AC first then by moc', () => {
      const opcje = evOpcje(katalog, { producent: 'Sigenergy', variant: VARIANT_PV_BAT, sigenTyp: 'AIO' })
      expect(opcje.map((o) => o.kod)).toEqual(['ev_ac_7', 'ev_ac_11', 'ev_ac_22', 'ev_dc_12_7_5', 'ev_dc_25_10'])
    })

    it('returns nothing when the ladowarka is not available at all', () => {
      expect(evOpcje(katalog, { producent: 'Deye', variant: VARIANT_PV_BAT, sigenTyp: 'AIO' })).toEqual([])
      expect(evOpcje(katalog, { producent: 'Sigenergy', variant: VARIANT_PV, sigenTyp: 'AIO' })).toEqual([])
    })

    it('never leaks other grupy (dod_panele) into the result', () => {
      const opcje = evOpcje(katalog, { producent: 'Sigenergy', variant: VARIANT_PV_BAT, sigenTyp: 'AIO' })
      expect(opcje.every((o) => o.grupa === 'ev_ac' || o.grupa === 'ev_dc')).toBe(true)
    })

    it('returns an empty list for a non-array catalog', () => {
      expect(evOpcje(null, { producent: 'Sigenergy', variant: VARIANT_PV_BAT, sigenTyp: 'AIO' })).toEqual([])
    })
  })

  describe('sanitizujDodatki', () => {
    const pelnyWybor = () => ({
      klimaKod: 'dod_klima_elis_x_2_6',
      panele: 3,
      paneleMikro: 2,
      emsBreeze: 'Tak',
      pstryk: 'Tak',
      evKod: 'ev_ac_7',
    })

    it('keeps every field when everything stays available (PV+Magazyn, Deye, AIO-equivalent)', () => {
      // EMS/pstryk/EV need Deye or Sigenergy specifically; this case only
      // exercises klima + panele(which stay 0 for a non-Magazyn variant, see
      // next test) staying untouched when their own gate is satisfied.
      const wybor = { klimaKod: 'dod_klima_elis_x_2_6', panele: 0, paneleMikro: 0, emsBreeze: 'Nie', pstryk: 'Nie', evKod: '' }
      const wynik = sanitizujDodatki(wybor, { variant: VARIANT_PV_BAT, producent: 'Deye', sigenTyp: '' })
      expect(wynik.klimaKod).toBe('dod_klima_elis_x_2_6')
    })

    it('clears klimaKod when the variant no longer supports it', () => {
      const wynik = sanitizujDodatki(pelnyWybor(), { variant: '', producent: 'Sigenergy', sigenTyp: 'AIO' })
      expect(wynik.klimaKod).toBe('')
    })

    it('clears panele and paneleMikro outside Magazyn energii', () => {
      const wynik = sanitizujDodatki(pelnyWybor(), { variant: VARIANT_PV_BAT, producent: 'Sigenergy', sigenTyp: 'AIO' })
      expect(wynik.panele).toBe(0)
      expect(wynik.paneleMikro).toBe(0)
    })

    it('keeps panele and paneleMikro for Magazyn energii', () => {
      const wynik = sanitizujDodatki(pelnyWybor(), { variant: VARIANT_BAT, producent: 'Sigenergy', sigenTyp: 'AIO' })
      expect(wynik.panele).toBe(3)
      expect(wynik.paneleMikro).toBe(2)
    })

    it('clears emsBreeze for Sigenergy, forces Tak for Solax, keeps choice for Hoymiles', () => {
      const soli = sanitizujDodatki({ ...pelnyWybor(), emsBreeze: 'Nie' }, { variant: VARIANT_PV_BAT, producent: 'Solax', sigenTyp: '' })
      expect(soli.emsBreeze).toBe('Tak')
      const hoy = sanitizujDodatki({ ...pelnyWybor(), emsBreeze: 'Nie' }, { variant: VARIANT_PV_BAT, producent: 'Hoymiles', sigenTyp: '' })
      expect(hoy.emsBreeze).toBe('Nie')
    })

    it('clears emsBreeze when the producent is not Deye', () => {
      const wynik = sanitizujDodatki(pelnyWybor(), { variant: VARIANT_PV_BAT, producent: 'Sigenergy', sigenTyp: 'AIO' })
      expect(wynik.emsBreeze).toBe('Nie')
    })

    it('keeps emsBreeze for Deye with a battery variant', () => {
      const wynik = sanitizujDodatki(pelnyWybor(), { variant: VARIANT_PV_BAT, producent: 'Deye', sigenTyp: '' })
      expect(wynik.emsBreeze).toBe('Tak')
    })

    it('clears pstryk and evKod when the producent is not Sigenergy', () => {
      const wynik = sanitizujDodatki(pelnyWybor(), { variant: VARIANT_PV_BAT, producent: 'Deye', sigenTyp: '' })
      expect(wynik.pstryk).toBe('Nie')
      expect(wynik.evKod).toBe('')
    })

    it('clears an ev_dc selection when the falownik is not AIO, keeps an ev_ac one', () => {
      const wyborDc = { ...pelnyWybor(), evKod: 'ev_dc_12_7_5' }
      const wynikDc = sanitizujDodatki(wyborDc, { variant: VARIANT_PV_BAT, producent: 'Sigenergy', sigenTyp: 'TP2' })
      expect(wynikDc.evKod).toBe('')

      const wyborAc = { ...pelnyWybor(), evKod: 'ev_ac_7' }
      const wynikAc = sanitizujDodatki(wyborAc, { variant: VARIANT_PV_BAT, producent: 'Sigenergy', sigenTyp: 'TP2' })
      expect(wynikAc.evKod).toBe('ev_ac_7')
    })

    it('keeps an ev_dc selection when the falownik is AIO', () => {
      const wybor = { ...pelnyWybor(), evKod: 'ev_dc_12_7_5' }
      const wynik = sanitizujDodatki(wybor, { variant: VARIANT_PV_BAT, producent: 'Sigenergy', sigenTyp: 'AIO' })
      expect(wynik.evKod).toBe('ev_dc_12_7_5')
    })

    it('never enables a field that started cleared', () => {
      const wybor = { klimaKod: '', panele: 0, paneleMikro: 0, emsBreeze: 'Nie', pstryk: 'Nie', evKod: '' }
      const wynik = sanitizujDodatki(wybor, { variant: VARIANT_BAT, producent: 'Sigenergy', sigenTyp: 'AIO' })
      expect(wynik).toEqual(wybor)
    })

    it('does not mutate the input object and returns a new one', () => {
      const wybor = pelnyWybor()
      const przed = { ...wybor }
      const wynik = sanitizujDodatki(wybor, { variant: '', producent: '', sigenTyp: '' })
      expect(wybor).toEqual(przed)
      expect(wynik).not.toBe(wybor)
    })

    it('handles a missing kontekst as "nothing available"', () => {
      const wynik = sanitizujDodatki(pelnyWybor())
      expect(wynik).toEqual({ klimaKod: '', panele: 0, paneleMikro: 0, emsBreeze: 'Nie', pstryk: 'Nie', evKod: '' })
    })
  })
})

// --- b69 (#237): model klimatyzacji w dodatku, EMS domyslnie Tak ---
const dod = (model, kolor, moc, kod) => ({ kod, grupa: 'dod_klima', model, kolor, moc_kw: moc, cena: 5000 })
const DODATKI = [
  dod('Elis X', 'Czarny', 3.5, 'dod_klima_elis_x_3_5'),
  dod('Elis X', 'Czarny', 2.6, 'dod_klima_elis_x_2_6'),
  dod('Roni X', 'Biały', 3.5, 'dod_klima_roni_x_3_5'),
  dod('Teta Mirror X', 'Czarny', 3.5, 'dod_klima_teta_mirror_x_3_5'),
  dod('Teta X', 'Biały', 3.5, 'dod_klima_teta_x_3_5'),
  dod('Mira X', 'Biały', 3.5, 'dod_klima_mira_x_3_5'),
  { kod: 'ems_breeze', grupa: 'dod_ems', cena: 1 },
]
const SAMODZIELNE = [
  { grupa: 'klima_chlodzenie', model: 'Elis X' },
  { grupa: 'klima_chlodzenie', model: 'Roni X' },
  { grupa: 'klima_dogrzewanie', model: 'Teta X' },
  { grupa: 'klima_dogrzewanie', model: 'Teta Mirror X' },
  { grupa: 'klima_grzanie', model: 'Mira X' },
]

describe('modeleDodatkuKlimy', () => {
  it('chlodzenie: Elis X i Roni X z kolorem', () => {
    const m = modeleDodatkuKlimy(DODATKI, SAMODZIELNE, 'chlodzenie')
    expect(m.map((x) => x.model)).toEqual(['Elis X', 'Roni X'])
    expect(m[0].label).toBe('Elis X (Czarny)')
  })
  it('dogrzewanie: Teta Mirror X i Teta X', () => {
    const m = modeleDodatkuKlimy(DODATKI, SAMODZIELNE, 'dogrzewanie')
    expect(m.map((x) => x.model).sort()).toEqual(['Teta Mirror X', 'Teta X'])
  })
  it('grzanie: Mira X', () => {
    expect(modeleDodatkuKlimy(DODATKI, SAMODZIELNE, 'grzanie').map((x) => x.model)).toEqual(['Mira X'])
  })
  it('model bez pozycji dod_klima jest pomijany', () => {
    const bezRoni = DODATKI.filter((d) => d.model !== 'Roni X')
    expect(modeleDodatkuKlimy(bezRoni, SAMODZIELNE, 'chlodzenie').map((x) => x.model)).toEqual(['Elis X'])
  })
  it('model dod_klima bez pozycji samodzielnej nie trafia do rodzaju', () => {
    const bezMira = SAMODZIELNE.filter((p) => p.model !== 'Mira X')
    expect(modeleDodatkuKlimy(DODATKI, bezMira, 'grzanie')).toEqual([])
  })
  it('kazdy model tylko raz mimo wielu mocy', () => {
    expect(modeleDodatkuKlimy(DODATKI, SAMODZIELNE, 'chlodzenie').filter((x) => x.model === 'Elis X')).toHaveLength(1)
  })
  it('nieznany rodzaj lub brak danych daje pusta liste', () => {
    expect(modeleDodatkuKlimy(DODATKI, SAMODZIELNE, 'x')).toEqual([])
    expect(modeleDodatkuKlimy(DODATKI, null, 'chlodzenie')).toEqual([])
    expect(modeleDodatkuKlimy(null, SAMODZIELNE, 'chlodzenie')).toEqual([])
  })
  it('trzy rodzaje zdefiniowane z grupami', () => {
    expect(RODZAJE_KLIMY_DODATKU.map((r) => r.grupa)).toEqual(['klima_chlodzenie', 'klima_dogrzewanie', 'klima_grzanie'])
  })
})

describe('moceDodatkuKlimy', () => {
  it('zwraca moce wybranego modelu rosnaco z kodem pozycji', () => {
    const o = moceDodatkuKlimy(DODATKI, 'Elis X')
    expect(o.map((x) => x.moc_kw)).toEqual([2.6, 3.5])
    expect(o[1].kod).toBe('dod_klima_elis_x_3_5')
  })
  it('pusty model lub nieznany daje pusta liste', () => {
    expect(moceDodatkuKlimy(DODATKI, '')).toEqual([])
    expect(moceDodatkuKlimy(DODATKI, 'Nieznany')).toEqual([])
  })
  it('nie myli modeli Teta X i Teta Mirror X', () => {
    expect(moceDodatkuKlimy(DODATKI, 'Teta X')).toHaveLength(1)
  })
})

describe('EMS Zeronest: dostepnosc i wymuszenie (ops#294)', () => {
  const pvme = 'Fotowoltaika + Magazyn'
  it('dostepny dla Hoymiles, Solax, Deye z magazynem; nie dla Sigenergy ani bez magazynu', () => {
    for (const producent of ['Hoymiles', 'Solax', 'Deye']) {
      expect(emsDostepny({ producent, variant: pvme })).toBe(true)
      expect(emsDostepny({ producent, variant: 'Magazyn energii' })).toBe(true)
      expect(emsDostepny({ producent, variant: 'Fotowoltaika' })).toBe(false)
    }
    expect(emsDostepny({ producent: 'Sigenergy', variant: pvme })).toBe(false)
  })
  it('wymuszony tylko dla Solax z magazynem', () => {
    expect(emsWymuszony({ producent: 'Solax', variant: pvme })).toBe(true)
    expect(emsWymuszony({ producent: 'Solax', variant: 'Fotowoltaika' })).toBe(false)
    expect(emsWymuszony({ producent: 'Hoymiles', variant: pvme })).toBe(false)
    expect(emsWymuszony({ producent: 'Deye', variant: pvme })).toBe(false)
  })
  it('Solax: stan Tak, reczne Nie ignorowane', () => {
    expect(domyslnyStanEms({ producent: 'Solax', variant: pvme, wyborReczny: false })).toBe(true)
    expect(domyslnyStanEms({ producent: 'Solax', variant: pvme })).toBe(true)
  })
  it('Hoymiles: domyslnie Tak, trwaly wybor reczny', () => {
    expect(domyslnyStanEms({ producent: 'Hoymiles', variant: pvme })).toBe(true)
    expect(domyslnyStanEms({ producent: 'Hoymiles', variant: pvme, wyborReczny: false })).toBe(false)
  })
  it('Sigenergy: zawsze false', () => {
    expect(domyslnyStanEms({ producent: 'Sigenergy', variant: pvme, wyborReczny: true })).toBe(false)
  })
})

describe('EMS Zeronest domyslnie Tak', () => {
  const dost = { producent: 'Deye', variant: 'Fotowoltaika + Magazyn' }
  it('dostepny i bez recznego wyboru: Tak', () => {
    expect(emsDostepny(dost)).toBe(true)
    expect(domyslnyStanEms({ ...dost })).toBe(true)
  })
  it('niedostepny (producent lub wariant): Nie', () => {
    expect(domyslnyStanEms({ producent: 'Sigenergy', variant: 'Fotowoltaika + Magazyn' })).toBe(false)
    expect(domyslnyStanEms({ producent: 'Deye', variant: 'Fotowoltaika' })).toBe(false)
  })
  it('reczne Nie + dostepny: Nie', () => {
    expect(domyslnyStanEms({ ...dost, wyborReczny: false })).toBe(false)
  })
  it('reczne Nie + niedostepny: Nie', () => {
    expect(domyslnyStanEms({ producent: 'Sigenergy', variant: 'Fotowoltaika + Magazyn', wyborReczny: false })).toBe(false)
  })
  it('reczne Nie + z powrotem dostepny: Nie', () => {
    expect(domyslnyStanEms({ ...dost, wyborReczny: false })).toBe(false)
  })
  it('reczne Tak + z powrotem dostepny: Tak', () => {
    expect(domyslnyStanEms({ ...dost, wyborReczny: true })).toBe(true)
  })
  it('niedostepny wygrywa nad recznym Tak', () => {
    expect(domyslnyStanEms({ producent: 'Deye', variant: 'Fotowoltaika', wyborReczny: true })).toBe(false)
  })
  it('brak wyboru + dostepny: Tak', () => {
    expect(domyslnyStanEms({ ...dost, wyborReczny: null })).toBe(true)
  })
  it('sanitizujDodatki nigdy nie wlacza EMS, tylko wylacza', () => {
    expect(sanitizujDodatki({ emsBreeze: 'Nie' }, { ...dost }).emsBreeze).toBe('Nie')
    expect(sanitizujDodatki({ emsBreeze: 'Tak' }, { producent: 'Sigenergy', variant: 'Fotowoltaika' }).emsBreeze).toBe('Nie')
  })
})

describe('autodobor COMFORT PREMIUM (ops#295)', () => {
  const mag = [
    { name: 'a', pojemnosc_kwh: 21.2 },
    { name: 'b', pojemnosc_kwh: 14.3 },
    { name: 'c', pojemnosc_kwh: 7.2 },
  ]
  it('cele dla 5000 i 8000 kWh', () => {
    expect(celKwpComfortPremium(5000)).toBe(5.7)
    expect(celKwhComfortPremium(5000)).toBe(12.83)
    expect(celKwpComfortPremium(8000)).toBe(9.12)
    expect(celKwhComfortPremium(8000)).toBe(20.52)
    expect(celKwpComfortPremium(0)).toBe(0)
    expect(celKwhComfortPremium('abc')).toBe(0)
  })
  it('dobor mocy: pierwsza opcja >= cel', () => {
    expect(dobierzMocComfortPremium(5000, 500)).toBe(6)
    expect(dobierzMocComfortPremium(8000, 500)).toBe(9.5)
  })
  it('moc: cel ponizej minimum daje pierwsza, powyzej maksimum ostatnia, rowny opcji ta opcja', () => {
    const opcje = buildMocOptionsForPanel(500)
    expect(dobierzMocComfortPremium(1000, 500)).toBe(opcje[0].value)
    expect(dobierzMocComfortPremium(1e6, 500)).toBe(opcje[opcje.length - 1].value)
    // 6.0 kWp / (1.2 * 0.95) = 5263.157..: cel 6,00 dokladnie (po zaokragleniu) to 12 paneli
    expect(dobierzMocComfortPremium(5264, 500)).toBe(6)
    expect(dobierzMocComfortPremium(0, 500)).toBeNull()
  })
  it('dobor magazynu', () => {
    expect(dobierzMagazynComfortPremium(5000, mag).name).toBe('b')
    expect(dobierzMagazynComfortPremium(8000, mag).name).toBe('a')
    expect(dobierzMagazynComfortPremium(50000, mag).name).toBe('a')
    expect(dobierzMagazynComfortPremium(5000, [])).toBeUndefined()
    const kopia = JSON.stringify(mag)
    dobierzMagazynComfortPremium(5000, mag)
    expect(JSON.stringify(mag)).toBe(kopia)
  })
  it('magazyn: cel rowny pojemnosci wybiera te pojemnosc', () => {
    // 14.3 / (2.7 * 0.95) * 1000 = 5575.2 -> cel 14.30 przy 5575
    expect(celKwhComfortPremium(5575)).toBe(14.3)
    expect(dobierzMagazynComfortPremium(5575, mag).name).toBe('b')
  })
  it('czyAutodobor tylko PV+ME i COMFORT PREMIUM', () => {
    expect(czyAutodobor({ variant: 'Fotowoltaika + Magazyn', zestaw: 'COMFORT PREMIUM' })).toBe(true)
    expect(czyAutodobor({ variant: 'Fotowoltaika + Magazyn', zestaw: 'COMFORT' })).toBe(false)
    expect(czyAutodobor({ variant: 'Fotowoltaika', zestaw: 'COMFORT PREMIUM' })).toBe(false)
    expect(czyAutodobor({ variant: 'Magazyn energii', zestaw: 'COMFORT PREMIUM' })).toBe(false)
    expect(czyAutodobor()).toBe(false)
  })
})

describe('grupujMocePv', () => {
  const o = (v) => ({ value: v, label: String(v) })
  it('dzieli na do progu i powyzej, prog 6.5 wlacznie w pierwszej grupie', () => {
    const g = grupujMocePv([o(6), o(6.5), o(7)], { etykietaPowyzej: 'X' })
    expect(g.map((x) => x.naglowek)).toEqual(['Do 6,5 kW', 'X'])
    expect(g[0].opcje.map((x) => x.value)).toEqual([6, 6.5])
    expect(g[1].opcje.map((x) => x.value)).toEqual([7])
  })
  it('istniejaca PV przesuwa opcje powyzej progu', () => {
    const g = grupujMocePv([o(3), o(4)], { istniejacaKwp: 3 })
    expect(g).toHaveLength(2)
    expect(g[0].opcje.map((x) => x.value)).toEqual([3])
  })
  it('jedna niepusta grupa i pusta lista', () => {
    expect(grupujMocePv([o(3), o(4)])).toHaveLength(1)
    expect(grupujMocePv([])).toEqual([])
    expect(grupujMocePv(null)).toEqual([])
  })
})

describe('grupujMagazyny', () => {
  const m = (k) => ({ pojemnosc_kwh: k })
  it('dzieli po progach 30/50/70, prog liczony dopiero powyzej (ops#301)', () => {
    const g = grupujMagazyny([m(10), m(29.9), m(30), m(30.1), m(49), m(50), m(50.1), m(70), m(70.1), m(90)])
    expect(g.map((x) => x.naglowek)).toEqual(['Do 30 kWh', 'Powyżej 30 do 50 kWh', 'Powyżej 50 do 70 kWh', 'Powyżej 70 kWh'])
    expect(g.map((x) => x.opcje.length)).toEqual([3, 3, 2, 2])
  })
  it('wartosci rowne progom ladują w nizszej grupie', () => {
    const g = grupujMagazyny([m(30), m(50), m(70)])
    expect(g.map((x) => x.naglowek)).toEqual(['Do 30 kWh', 'Powyżej 30 do 50 kWh', 'Powyżej 50 do 70 kWh'])
  })
  it('brak pojemnosci laduje w pierwszej grupie, puste grupy pomijane', () => {
    const g = grupujMagazyny([{}, m(0)])
    expect(g).toHaveLength(1)
    expect(g[0].naglowek).toBe('Do 30 kWh')
    expect(grupujMagazyny([])).toEqual([])
  })
})

describe('udzialyCeny', () => {
  it('liczy procenty z brutto', () => {
    expect(udzialyCeny({ brutto: 1000, dotacja: 200, ulga: 100 })).toEqual({ klient: 70, dotacja: 20, ulga: 10 })
  })
  it('brutto 0 lub brak daje zera', () => {
    expect(udzialyCeny({ brutto: 0, dotacja: 5, ulga: 5 })).toEqual({ klient: 0, dotacja: 0, ulga: 0 })
    expect(udzialyCeny(null)).toEqual({ klient: 0, dotacja: 0, ulga: 0 })
  })
  it('nie schodzi ponizej zera', () => {
    const r = udzialyCeny({ brutto: 100, dotacja: 80, ulga: 80 })
    expect(r.klient).toBe(0)
    expect(r.dotacja + r.ulga + r.klient).toBe(100)
  })
})

describe('podsumowania sekcji (pigulki)', () => {
  const fmt = (n) => `${n} zł`
  const sel = { kabelM: 0, spoldzielnia: 'Nie', licznik: 'Nie', istniejacaPv: 'Nie', istniejacaPvMocKwp: 0, operator: '', kierunek: '' }
  const teksty = (r) => r.map((p) => p.tekst)
  it('montaz: wszystko domyslne daje jedna pigulke muted', () => {
    expect(podsumowanieMontazu(sel, { formatPln: fmt })).toEqual([{ tekst: 'Ustawienia domyślne', ton: 'muted' }])
  })
  it('montaz: kazda niedomyslna wartosc', () => {
    expect(teksty(podsumowanieMontazu({ ...sel, kabelM: 5 }, { formatPln: fmt }))).toEqual(['Kabel 5 m'])
    expect(teksty(podsumowanieMontazu({ ...sel, spoldzielnia: 'Tak' }, { formatPln: fmt }))).toEqual(['Spółdzielnia'])
    expect(teksty(podsumowanieMontazu({ ...sel, licznik: 'Tak' }, { formatPln: fmt, licznikDostepny: true }))).toEqual(['Dodatkowy licznik'])
    expect(podsumowanieMontazu({ ...sel, licznik: 'Tak' }, { formatPln: fmt, licznikDostepny: false })).toEqual([
      { tekst: 'Ustawienia domyślne', ton: 'muted' },
    ])
    expect(teksty(podsumowanieMontazu({ ...sel, istniejacaPv: 'Tak', istniejacaPvMocKwp: 4.5 }, { formatPln: fmt }))).toEqual(['Istniejąca PV 4,5 kWp'])
    expect(teksty(podsumowanieMontazu({ ...sel, istniejacaPv: 'Tak' }, { formatPln: fmt }))).toEqual(['Istniejąca PV'])
    expect(teksty(podsumowanieMontazu({ ...sel, operator: 'Tauron', kierunek: 'Południe' }, { formatPln: fmt }))).toEqual(['Tauron', 'Południe'])
    expect(teksty(podsumowanieMontazu({ ...sel, kierunek: 'Południe' }, { formatPln: fmt, hasPv: false }))).toEqual(['Ustawienia domyślne'])
  })
  it('montaz: PPOŻ z cena i bez', () => {
    expect(podsumowanieMontazu(sel, { formatPln: fmt, ppozWymagane: true, ppozCena: 1000 })).toEqual([
      { tekst: 'PPOŻ wymagane +1000 zł', ton: 'info' },
    ])
    expect(podsumowanieMontazu(sel, { formatPln: fmt, ppozWymagane: true })).toEqual([{ tekst: 'PPOŻ wymagane', ton: 'info' }])
  })
  it('finansowanie: trzy pigulki i polska odmiana lat', () => {
    const r = (lat) => podsumowanieFinansowania({ ulgaPct: 12, okresLat: lat, wplataWlasna: 0 }, { formatPln: fmt })
    expect(teksty(r(10))).toEqual(['Ulga 12%', '10 lat', 'Wpłata własna 0 zł'])
    expect(teksty(r(1))[1]).toBe('1 rok')
    expect(teksty(r(3))[1]).toBe('3 lata')
    expect(teksty(r(12))[1]).toBe('12 lat')
    expect(r(10).every((p) => p.ton === 'neutral')).toBe(true)
  })
  it('dodatki: brak, jeden, kilka z kwota z serwera', () => {
    expect(podsumowanieDodatkow({ formatPln: fmt })).toEqual([{ tekst: 'Brak dodatków', ton: 'muted' }])
    expect(podsumowanieDodatkow({ wybrane: ['licznik Pstryk'], dodatkiNetto: 0, formatPln: fmt })).toEqual([
      { tekst: 'Licznik Pstryk', ton: 'neutral' },
    ])
    expect(podsumowanieDodatkow({ wybrane: ['EMS Zeronest', 'ładowarka EV'], dodatkiNetto: 1850, formatPln: fmt })).toEqual([
      { tekst: 'EMS Zeronest', ton: 'neutral' },
      { tekst: 'Ładowarka EV', ton: 'neutral' },
      { tekst: '+1850 zł netto', ton: 'info' },
    ])
  })
})
