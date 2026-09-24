import {
  KLUCZ,
  czyPustaWartosc,
  czyUkrycPole,
  wczytajUkryjPuste,
  zapiszUkryjPuste,
} from '@/utils/panelPuste'

beforeEach(() => {
  localStorage.clear()
})

describe('czyPustaWartosc', () => {
  it('null i undefined sa zawsze puste, niezaleznie od fieldtype', () => {
    expect(czyPustaWartosc(null, 'Data')).toBe(true)
    expect(czyPustaWartosc(undefined, 'Data')).toBe(true)
    expect(czyPustaWartosc(null, 'Currency')).toBe(true)
    expect(czyPustaWartosc(undefined, 'Check')).toBe(true)
  })

  it('Check: 0/false/"0" sa puste, 1/true/"1" nie sa', () => {
    expect(czyPustaWartosc(0, 'Check')).toBe(true)
    expect(czyPustaWartosc(false, 'Check')).toBe(true)
    expect(czyPustaWartosc('0', 'Check')).toBe(true)
    expect(czyPustaWartosc(1, 'Check')).toBe(false)
    expect(czyPustaWartosc(true, 'Check')).toBe(false)
    expect(czyPustaWartosc('1', 'Check')).toBe(false)
  })

  it.each(['Int', 'Float', 'Currency', 'Percent'])(
    '%s: liczbowe zero jest puste, niezerowe nie',
    (fieldtype) => {
      expect(czyPustaWartosc(0, fieldtype)).toBe(true)
      expect(czyPustaWartosc('0', fieldtype)).toBe(true)
      expect(czyPustaWartosc(0.0, fieldtype)).toBe(true)
      expect(czyPustaWartosc(5, fieldtype)).toBe(false)
      expect(czyPustaWartosc('5', fieldtype)).toBe(false)
      expect(czyPustaWartosc(-1, fieldtype)).toBe(false)
    },
  )

  it('pozostale typy: pusty/bialy string jest pusty', () => {
    expect(czyPustaWartosc('', 'Data')).toBe(true)
    expect(czyPustaWartosc(' ', 'Select')).toBe(true)
    expect(czyPustaWartosc('   ', 'Small Text')).toBe(true)
  })

  it('pozostale typy: niepusty string nie jest pusty', () => {
    expect(czyPustaWartosc('Warszawa', 'Data')).toBe(false)
    expect(czyPustaWartosc('Nowe zasady', 'Select')).toBe(false)
  })

  it('tablica pusta jest pusta, niepusta nie (pola tagow)', () => {
    expect(czyPustaWartosc([], 'Data')).toBe(true)
    expect(czyPustaWartosc(['PV'], 'Data')).toBe(false)
  })

  it('pola tagow produktowych jako pusty string sa puste', () => {
    expect(czyPustaWartosc('', 'Data')).toBe(true)
    expect(czyPustaWartosc('PV+ME', 'Data')).toBe(false)
  })
})

describe('czyUkrycPole', () => {
  const poleZwykle = { fieldname: 'custom_kolejny_kontakt', fieldtype: 'Date' }
  const poleWymagane = { fieldname: 'custom_status_cc', fieldtype: 'Select', reqd: 1 }
  const poleButton = { fieldname: 'wygeneruj_pdf', fieldtype: 'Button' }

  it('przelacznik wylaczony -- nic nie jest ukrywane, nawet puste', () => {
    expect(czyUkrycPole(poleZwykle, '', false)).toBe(false)
    expect(czyUkrycPole(poleZwykle, null, false)).toBe(false)
  })

  it('pole wymagane (reqd) nigdy nie jest ukrywane', () => {
    expect(czyUkrycPole(poleWymagane, '', true)).toBe(false)
    expect(czyUkrycPole(poleWymagane, null, true)).toBe(false)
  })

  it('Button nigdy nie jest ukrywany', () => {
    expect(czyUkrycPole(poleButton, null, true)).toBe(false)
    expect(czyUkrycPole(poleButton, '', true)).toBe(false)
  })

  it('przelacznik wlaczony i pole puste -- ukryte', () => {
    expect(czyUkrycPole(poleZwykle, '', true)).toBe(true)
    expect(czyUkrycPole(poleZwykle, null, true)).toBe(true)
  })

  it('przelacznik wlaczony i pole wypelnione -- widoczne', () => {
    expect(czyUkrycPole(poleZwykle, '2026-09-24', true)).toBe(false)
  })

  it('respektuje fieldtype przy sprawdzaniu pustki (Currency zero)', () => {
    const poleKwoty = { fieldname: 'custom_cp_wplata_gotowka', fieldtype: 'Currency' }
    expect(czyUkrycPole(poleKwoty, 0, true)).toBe(true)
    expect(czyUkrycPole(poleKwoty, 1500, true)).toBe(false)
  })
})

describe('trwalosc ustawienia (localStorage)', () => {
  it('odczyt bez wczesniejszego zapisu -- domyslnie false', () => {
    expect(wczytajUkryjPuste()).toBe(false)
  })

  it('zapis true, potem odczyt -- true', () => {
    zapiszUkryjPuste(true)
    expect(wczytajUkryjPuste()).toBe(true)
    expect(localStorage.getItem(KLUCZ)).toBe('1')
  })

  it('zapis false, potem odczyt -- false', () => {
    zapiszUkryjPuste(true)
    zapiszUkryjPuste(false)
    expect(wczytajUkryjPuste()).toBe(false)
    expect(localStorage.getItem(KLUCZ)).toBe('0')
  })

  it('nieoczekiwana wartosc w localStorage -- traktowana jako wylaczone', () => {
    localStorage.setItem(KLUCZ, 'cokolwiek')
    expect(wczytajUkryjPuste()).toBe(false)
  })
})
