import { describe, expect, it } from 'vitest'
import { leadDozwolony, opcjeLeadow } from '@/utils/kalendarzLeady'

describe('opcjeLeadow', () => {
  it('buduje opcje z wierszy endpointu', () => {
    const opcje = opcjeLeadow([
      {
        name: 'CRM-LEAD-1',
        lead_name: 'Jan Kowalski',
        mobile_no: '+48600111222',
        lead_owner: 'h@x.pl',
      },
      { name: 'CRM-LEAD-2', lead_name: '', mobile_no: null, lead_owner: null },
    ])
    expect(opcje).toEqual([
      {
        label: 'Jan Kowalski',
        value: 'CRM-LEAD-1',
        description: '+48600111222 · CRM-LEAD-1',
        lead_owner: 'h@x.pl',
      },
      {
        label: 'CRM-LEAD-2',
        value: 'CRM-LEAD-2',
        description: '',
        lead_owner: '',
      },
    ])
  })

  it('pomija puste i niepoprawne wiersze', () => {
    expect(opcjeLeadow(null)).toEqual([])
    expect(opcjeLeadow([null, {}, { name: '' }])).toEqual([])
  })

  it('zachowuje wybranego leada spoza wyniku na gorze', () => {
    const wybrany = {
      label: 'Anna',
      value: 'L9',
      description: '',
      lead_owner: '',
    }
    const opcje = opcjeLeadow([{ name: 'L1', lead_name: 'Ola' }], wybrany)
    expect(opcje.map((o) => o.value)).toEqual(['L9', 'L1'])
  })

  it('nie dubluje wybranego leada obecnego w wyniku', () => {
    const wybrany = {
      label: 'Ola',
      value: 'L1',
      description: '',
      lead_owner: '',
    }
    const opcje = opcjeLeadow([{ name: 'L1', lead_name: 'Ola' }], wybrany)
    expect(opcje).toHaveLength(1)
  })
})

describe('leadDozwolony', () => {
  it('pusty wlasciciel albo ten sam handlowiec', () => {
    expect(leadDozwolony('', 'h@x.pl')).toBe(true)
    expect(leadDozwolony(null, 'h@x.pl')).toBe(true)
    expect(leadDozwolony('h@x.pl', 'h@x.pl')).toBe(true)
  })

  it('cudzy lead niedozwolony', () => {
    expect(leadDozwolony('inny@x.pl', 'h@x.pl')).toBe(false)
  })

  it('bez handlowca kazdy lead', () => {
    expect(leadDozwolony('inny@x.pl', '')).toBe(true)
  })
})
