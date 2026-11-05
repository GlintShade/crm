import { describe, expect, it } from 'vitest'
import {
  czySekcjaSpotkanie,
  hashWskazujeKomentarze,
} from '../../src/utils/komentarzeSekcja'

describe('komentarzeSekcja', () => {
  it('rozpoznaje sekcje Spotkanie po nazwie i etykiecie', () => {
    expect(czySekcjaSpotkanie({ name: 'spotkanie_section' })).toBe(true)
    expect(czySekcjaSpotkanie({ name: 'x', label: 'Spotkanie' })).toBe(true)
    expect(czySekcjaSpotkanie({ name: 'cc_section', label: 'Call center' })).toBe(false)
    expect(czySekcjaSpotkanie(null)).toBe(false)
  })
  it('hash komentarza lub #comments wskazuje komentarze, nazwa zakladki nie', () => {
    const z = ['Details', 'Activity', 'Emails']
    expect(hashWskazujeKomentarze('#comments', z)).toBe(true)
    expect(hashWskazujeKomentarze('#a1b2c3d4e5', z)).toBe(true)
    expect(hashWskazujeKomentarze('#details', z)).toBe(false)
    expect(hashWskazujeKomentarze('', z)).toBe(false)
  })
})
