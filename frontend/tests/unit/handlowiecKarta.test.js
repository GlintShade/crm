import { describe, it, expect } from 'vitest'
import { czyPobracKontakt } from '@/utils/handlowiecKarta'

describe('czyPobracKontakt', () => {
  it('odrzuca puste, Administrator i Guest', () => {
    for (const v of ['', '  ', null, undefined, 'Administrator', 'Guest']) {
      expect(czyPobracKontakt(v)).toBe(false)
    }
  })
  it('odrzuca wartosci bez ksztaltu e-mail', () => {
    for (const v of ['jan', '@x.pl', 'a@', 'a@b@c']) {
      expect(czyPobracKontakt(v)).toBe(false)
    }
  })
  it('przyjmuje e-mail', () => {
    expect(czyPobracKontakt('a.b@proenergy.pro')).toBe(true)
  })
})
