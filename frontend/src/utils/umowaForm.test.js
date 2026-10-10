import { describe, expect, it } from 'vitest'
import {
  dodatkiDoPokazania,
  etykietaFinansowania,
  opisWzoru,
  pokazPojemnoscMe,
  sekcjeFormularza,
  wszystkiePola,
  zakresRozbudowy,
} from './umowaForm'

const klucze = (sekcje) => sekcje.map((s) => s.key)
const pola = (sekcje) => sekcje.flatMap((s) => s.fields.map((f) => f.fieldname))

describe('sekcjeFormularza', () => {
  it('PV/PVME/ME dostaja pelny zestaw sekcji', () => {
    for (const r of ['Fotowoltaika', 'Fotowoltaika + Magazyn', 'Magazyn energii']) {
      expect(klucze(sekcjeFormularza(r))).toEqual([
        'adres', 'budynek', 'finansowanie', 'warunki', 'istniejaca_pv', 'zgody',
      ])
    }
  })

  it('rodzaj pusty lub nieznany ma zestaw domyslny', () => {
    expect(klucze(sekcjeFormularza(''))).toContain('warunki')
    expect(klucze(sekcjeFormularza(undefined))).toContain('istniejaca_pv')
  })

  it('Rozbudowa ma skrocony formularz bez warunkow instalacyjnych PV', () => {
    const s = sekcjeFormularza('Rozbudowa PV/ME')
    expect(klucze(s)).toEqual(['adres', 'budynek', 'finansowanie', 'osd', 'zakres_rozbudowy', 'zgody'])
    const p = pola(s)
    expect(p).toContain('osd')
    expect(p).not.toContain('internet')
    expect(p).not.toContain('przekop_gruntowy')
    expect(p).not.toContain('liczba_faz')
  })

  it('pojemnosc magazynu tylko gdy bateria > 0', () => {
    expect(pola(sekcjeFormularza('Rozbudowa PV/ME', {}))).not.toContain('istniejacy_me_pojemnosc_kwh')
    expect(
      pola(sekcjeFormularza('Rozbudowa PV/ME', { custom_oze_rozbudowa_bateria: 2 })),
    ).toContain('istniejacy_me_pojemnosc_kwh')
  })

  it('nie mutuje definicji sekcji', () => {
    sekcjeFormularza('Rozbudowa PV/ME', { custom_oze_rozbudowa_bateria: 1 })
    const bez = sekcjeFormularza('Rozbudowa PV/ME', {})
    expect(bez.find((s) => s.key === 'zakres_rozbudowy').fields).toEqual([])
  })

  it('select finansowania niesie wartosci bez zmian i etykiety UI', () => {
    const f = sekcjeFormularza('Fotowoltaika')
      .find((s) => s.key === 'finansowanie')
      .fields.find((x) => x.fieldname === 'finansowanie')
    expect(f.options.map((o) => o.value)).toEqual(['', 'Kredyt 100%', 'Gotówka 100%', 'Kredyt + gotówka'])
    expect(f.options.find((o) => o.value === 'Kredyt + gotówka').label).toBe('Kredyt z wkładem własnym')
    expect(f.options.find((o) => o.value === 'Gotówka 100%').label).toBe('Gotówka / przelew')
  })
})

describe('wszystkiePola', () => {
  it('bez duplikatow i z polem pojemnosci oraz osd', () => {
    const n = wszystkiePola().map((f) => f.fieldname)
    expect(new Set(n).size).toBe(n.length)
    expect(n).toContain('istniejacy_me_pojemnosc_kwh')
    expect(n).toContain('osd')
  })
})

describe('etykietaFinansowania', () => {
  it('mapuje trzy wartosci', () => {
    expect(etykietaFinansowania('Kredyt 100%')).toBe('Kredyt 100%')
    expect(etykietaFinansowania('Kredyt + gotówka')).toBe('Kredyt z wkładem własnym')
    expect(etykietaFinansowania('Gotówka 100%')).toBe('Gotówka / przelew')
  })
  it('puste i nieznane', () => {
    expect(etykietaFinansowania('')).toBe('')
    expect(etykietaFinansowania(null)).toBe('')
    expect(etykietaFinansowania('Inne')).toBe('Inne')
  })
})

describe('opisWzoru', () => {
  it('dostepny to badge z nazwa', () => {
    expect(opisWzoru({ kod: 'PV', nazwa: 'Umowa PV', dostepny: true })).toEqual({
      tekst: 'Wzór: Umowa PV', dostepny: true, powod: '',
    })
  })
  it('niedostepny niesie powod dosłownie', () => {
    const o = opisWzoru({ dostepny: false, powod: 'Brak wzoru umowy dla konfiguracji: X.' })
    expect(o.dostepny).toBe(false)
    expect(o.tekst).toBe('Brak wzoru umowy dla konfiguracji: X.')
    expect(o.powod).toBe('Brak wzoru umowy dla konfiguracji: X.')
  })
  it('brak wzoru daje null', () => {
    expect(opisWzoru(null)).toBeNull()
    expect(opisWzoru(undefined)).toBeNull()
  })
})

describe('dodatkiDoPokazania', () => {
  it('pusty gdy nic nie ma', () => {
    expect(dodatkiDoPokazania({})).toEqual([])
    expect(dodatkiDoPokazania(null)).toEqual([])
    expect(dodatkiDoPokazania({ custom_dod_klima: '  ', custom_dod_panele: 0, custom_ems_breeze: 'Nie' })).toEqual([])
  })
  it('klimatyzacja, ladowarka i panele jako wiersze drukowane', () => {
    const w = dodatkiDoPokazania({
      custom_dod_klima: 'Elis X 3,5 kW (Czarny)',
      custom_ev_ladowarka: 'Wallbox AC',
      custom_dod_panele: '3',
      custom_dod_panele_mikro: 2,
    })
    expect(w.map((x) => x.key)).toEqual(['klima', 'ev', 'panele', 'panele_mikro'])
    expect(w[0].value).toBe('Elis X 3,5 kW (Czarny)')
    expect(w[2].value).toBe('3 szt.')
    expect(w.every((x) => !x.info)).toBe(true)
  })
  it('EMS i Pstryk jako informacja nie drukowana', () => {
    const w = dodatkiDoPokazania({ custom_ems_breeze: 'Tak', custom_pstryk: 'Tak' })
    expect(w.map((x) => x.key)).toEqual(['ems', 'pstryk'])
    expect(w.every((x) => x.info)).toBe(true)
  })
})

describe('zakresRozbudowy i pokazPojemnoscMe', () => {
  it('cztery wiersze, kreska dla zera', () => {
    const z = zakresRozbudowy({})
    expect(z.map((x) => x.key)).toEqual(['panele', 'panele_mikro', 'bateria', 'istniejaca_pv'])
    expect(z.every((x) => x.value === '-')).toBe(true)
  })
  it('wartosci z szansy', () => {
    const z = zakresRozbudowy({
      custom_oze_rozbudowa_panele: 10,
      custom_oze_rozbudowa_bateria: 2,
      custom_istniejaca_pv_moc_kwp: 5.5,
    })
    expect(z.find((x) => x.key === 'panele').value).toBe('10 szt.')
    expect(z.find((x) => x.key === 'bateria').value).toBe('2 szt.')
    expect(z.find((x) => x.key === 'istniejaca_pv').value).toBe('5.5 kWp')
  })
  it('pokazPojemnoscMe', () => {
    expect(pokazPojemnoscMe({ custom_oze_rozbudowa_bateria: '1' })).toBe(true)
    expect(pokazPojemnoscMe({ custom_oze_rozbudowa_bateria: 0 })).toBe(false)
    expect(pokazPojemnoscMe(undefined)).toBe(false)
  })
})
