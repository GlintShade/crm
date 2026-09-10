import { czyWidokDozwolony } from './widokiDozwolone'
import { KLUCZ_GRUP } from './grupyFiltrow'

describe('czyWidokDozwolony', () => {
  it('brak dozwolonePola (null) → zawsze dozwolony', () => {
    const widok = { filters: JSON.stringify({ custom_cc: 'me@example.com' }) }
    expect(czyWidokDozwolony(widok, null)).toBe(true)
  })

  it('dozwolonePola puste → zawsze dozwolony', () => {
    const widok = { filters: JSON.stringify({ custom_cc: 'me@example.com' }) }
    expect(czyWidokDozwolony(widok, [])).toBe(true)
  })

  it('wszystkie klucze filtrow na liście dozwolonych → dozwolony', () => {
    const widok = { filters: JSON.stringify({ status: 'Nowy', lead_owner: '@me' }) }
    expect(czyWidokDozwolony(widok, ['status', 'lead_owner', 'name'])).toBe(true)
  })

  it('klucz spoza listy dozwolonych (custom_cc) → niedozwolony', () => {
    const widok = { filters: JSON.stringify({ status: 'Nowy', custom_cc: '@me' }) }
    expect(czyWidokDozwolony(widok, ['status', 'name'])).toBe(false)
  })

  it('klucz niedozwolony wewnatrz grupy volteo_grupy → niedozwolony', () => {
    const widok = {
      filters: JSON.stringify({
        status: 'Nowy',
        [KLUCZ_GRUP]: [{ custom_cc: '@me' }, { lead_owner: 'x@proenergy.pro' }],
      }),
    }
    expect(czyWidokDozwolony(widok, ['status', 'lead_owner'])).toBe(false)
  })

  it('wszystkie klucze grup dozwolone → dozwolony', () => {
    const widok = {
      filters: JSON.stringify({
        status: 'Nowy',
        [KLUCZ_GRUP]: [{ lead_owner: '@me' }, { custom_kolejny_kontakt: ['<=', '@dzis'] }],
      }),
    }
    expect(
      czyWidokDozwolony(widok, ['status', 'lead_owner', 'custom_kolejny_kontakt']),
    ).toBe(true)
  })

  it('filters jako juz sparsowany obiekt (nie string) działa identycznie', () => {
    const widok = { filters: { custom_cc: '@me' } }
    expect(czyWidokDozwolony(widok, ['status'])).toBe(false)
    expect(czyWidokDozwolony(widok, ['custom_cc'])).toBe(true)
  })

  it('filters puste/brak → dozwolony niezaleznie od listy', () => {
    expect(czyWidokDozwolony({ filters: '' }, ['status'])).toBe(true)
    expect(czyWidokDozwolony({ filters: null }, ['status'])).toBe(true)
    expect(czyWidokDozwolony({}, ['status'])).toBe(true)
  })

  it('filters JSON niepoprawny → dozwolony (fail-open, nie jest to bezpiecznik)', () => {
    expect(czyWidokDozwolony({ filters: '{niepoprawny' }, ['status'])).toBe(true)
  })

  it('widok bez view (undefined) → dozwolony', () => {
    expect(czyWidokDozwolony(undefined, ['status'])).toBe(true)
  })

  it('@me/@dzis sa wartosciami, nie kluczami - nie wplywaja na wynik', () => {
    const widok = { filters: JSON.stringify({ lead_owner: '@me', modified: ['<=', '@dzis'] }) }
    expect(czyWidokDozwolony(widok, ['lead_owner', 'modified'])).toBe(true)
    expect(czyWidokDozwolony(widok, ['lead_owner'])).toBe(false)
  })
})
