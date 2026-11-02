import { describe, expect, it } from 'vitest'
import { TYPY_ALIASOWANE_DO_LISTY, typWidokuDoZapisu } from './widokLeady'

describe('typWidokuDoZapisu', () => {
  it('mapuje "mapa" na "list", bo CRM View Settings.type nie zna "mapa"', () => {
    expect(typWidokuDoZapisu('mapa')).toBe('list')
  })

  it('mapuje "kalendarz" na "list" (ops#318), żeby nigdy nie zapisać go jako typu widoku', () => {
    expect(typWidokuDoZapisu('kalendarz')).toBe('list')
    expect(TYPY_ALIASOWANE_DO_LISTY).toEqual(['mapa', 'kalendarz'])
  })

  it('zostawia pozostałe typy widoku bez zmian', () => {
    expect(typWidokuDoZapisu('list')).toBe('list')
    expect(typWidokuDoZapisu('group_by')).toBe('group_by')
    expect(typWidokuDoZapisu('kanban')).toBe('kanban')
  })

  it('przepuszcza pusty/nieznany typ bez zmian (wołający sam dobiera wartość domyślną)', () => {
    expect(typWidokuDoZapisu('')).toBe('')
    expect(typWidokuDoZapisu(undefined)).toBe(undefined)
    expect(typWidokuDoZapisu(null)).toBe(null)
  })
})
