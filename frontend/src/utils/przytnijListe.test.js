import { describe, it, expect } from 'vitest'
import { przytnijZapisanaListe } from './przytnijListe'

const rows = (k) => Array.from({ length: k }, (_, i) => ({ name: i }))

describe('przytnijZapisanaListe', () => {
  it('przycina 300 wierszy do wybranego rozmiaru i nie mutuje wejscia', () => {
    const d = { data: rows(300), page_length: 300, page_length_count: 100, row_count: 300 }
    const r = przytnijZapisanaListe(d)
    expect(r.data).toHaveLength(100)
    expect(r.page_length).toBe(100)
    expect(r.row_count).toBe(100)
    expect(d.data).toHaveLength(300)
  })
  it('zostawia mala liste bez zmian', () => {
    const d = { data: rows(20), page_length: 20, page_length_count: 20 }
    expect(przytnijZapisanaListe(d)).toBe(d)
  })
  it('nie rusza kanbana ani braku danych', () => {
    const k = { data: rows(3), page_length: 300, page_length_count: 20, view_type: 'kanban' }
    expect(przytnijZapisanaListe(k)).toBe(k)
    expect(przytnijZapisanaListe(null)).toBe(null)
  })
})
