import { describe, expect, it } from 'vitest'
import { kwotaKredytuPodglad } from '@/utils/kwotaKredytu'

describe('kwotaKredytuPodglad (lustro crm.volteo_umowa.kwota_kredytu)', () => {
  it('Kredyt 100% to cała cena brutto, wpłata ignorowana', () => {
    expect(kwotaKredytuPodglad(40843.44, 6000, 'Kredyt 100%')).toBe(40843.44)
    expect(kwotaKredytuPodglad('40843.44', '', 'Kredyt 100%')).toBe(40843.44)
  })

  it('Kredyt + gotówka to brutto minus wpłata', () => {
    expect(kwotaKredytuPodglad(60000, 10000, 'Kredyt + gotówka')).toBe(50000)
    expect(kwotaKredytuPodglad('60000', '15000', 'Kredyt + gotówka')).toBe(45000)
  })

  it('wpłata większa od ceny daje 0, nigdy ujemną kwotę', () => {
    expect(kwotaKredytuPodglad(1000, 5000, 'Kredyt + gotówka')).toBe(0)
  })

  it('Gotówka 100%, puste i nieznane finansowanie dają 0', () => {
    expect(kwotaKredytuPodglad(60000, 10000, 'Gotówka 100%')).toBe(0)
    expect(kwotaKredytuPodglad(60000, 10000, '')).toBe(0)
    expect(kwotaKredytuPodglad(60000, 10000, undefined)).toBe(0)
  })

  it('niepoprawne liczby traktuje jak zero', () => {
    expect(kwotaKredytuPodglad(null, 'abc', 'Kredyt + gotówka')).toBe(0)
    expect(kwotaKredytuPodglad(60000, 'abc', 'Kredyt + gotówka')).toBe(60000)
  })
})
