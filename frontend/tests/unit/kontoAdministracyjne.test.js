import {
  czyKontoAdministracyjne,
  tekstOstrzezenia,
} from '@/utils/kontoAdministracyjne'

describe('kontoAdministracyjne', () => {
  beforeAll(() => {
    globalThis.__ = (s) => s
  })

  it('admin lub backoffice to konto administracyjne', () => {
    expect(czyKontoAdministracyjne(true, false)).toBe(true)
    expect(czyKontoAdministracyjne(false, true)).toBe(true)
    expect(czyKontoAdministracyjne(true, true)).toBe(true)
  })

  it('handlowiec i CC nie', () => {
    expect(czyKontoAdministracyjne(false, false)).toBe(false)
    expect(czyKontoAdministracyjne(undefined, undefined)).toBe(false)
  })

  it('tekst szansy wspomina doradce', () => {
    expect(tekstOstrzezenia('szansa')).toContain('ustaw doradcę')
    expect(tekstOstrzezenia()).toContain('Szansa zostanie zapisana')
  })

  it('tekst klienta nie wspomina doradcy', () => {
    const t = tekstOstrzezenia('klient')
    expect(t).toContain('Klient zostanie zapisany')
    expect(t).not.toContain('doradc')
  })

  it('bez myslnikow em i en', () => {
    for (const r of ['szansa', 'klient']) {
      expect([8211, 8212].some((k) => tekstOstrzezenia(r).includes(String.fromCharCode(k)))).toBe(false)
    }
  })
})
