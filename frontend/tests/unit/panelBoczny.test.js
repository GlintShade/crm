import { describe, it, expect, beforeEach } from 'vitest'
import {
  formatLiczba,
  formatKwota,
  formatData,
  formatDataCzas,
  formatTelefon,
  rozbijUwagi,
  kluczSekcji,
  wczytajOtwartaSekcje,
  zapiszOtwartaSekcje,
  podsumowanieSekcji,
  podsumowanieZadan,
} from '@/utils/panelBoczny'

const sek = (label, fields, name = 'x') => ({
  label,
  name,
  columns: [{ fields: fields.map((f) => ({ visible: true, ...f })) }],
})

describe('formaty', () => {
  it('kwota z grupowaniem i przecinkiem', () => {
    expect(formatKwota(63093.6).replace(' ', ' ')).toBe('63 093,60 zł')
    expect(formatKwota(0).replace(' ', ' ')).toBe('0,00 zł')
    expect(formatKwota(null)).toBe('')
    expect(formatKwota(1234567.891, { jednostka: false })).toBe('1 234 567,89')
  })
  it('liczba obcina zbedne zera', () => {
    expect(formatLiczba(8.5)).toBe('8,5')
    expect(formatLiczba(8)).toBe('8')
    expect(formatLiczba('abc')).toBe('')
  })
  it('daty', () => {
    expect(formatData('2026-11-03')).toBe('03.11.2026')
    expect(formatData('2026-11-03 14:30:00')).toBe('03.11.2026')
    expect(formatDataCzas('2026-11-03 14:30:00')).toBe('03.11.2026, 14:30')
    expect(formatDataCzas('2026-11-03')).toBe('03.11.2026')
    expect(formatData('')).toBe('')
    expect(formatData('bzdura')).toBe('')
  })
  it('telefon tylko grupuje', () => {
    expect(formatTelefon('+48600123456')).toBe('+48 600 123 456')
    expect(formatTelefon('600123456')).toBe('600 123 456')
    expect(formatTelefon('+48 600 123 456')).toBe('+48 600 123 456')
    expect(formatTelefon('(22) 123 45 67')).toBe('(22) 123 45 67')
    expect(formatTelefon(null)).toBe('')
  })
})

describe('rozbijUwagi', () => {
  it('rozbija po " | " i pierwszym dwukropku', () => {
    expect(
      rozbijUwagi('Zrodlo: Facebook | System rozliczen: net-billing | Inne: a: b'),
    ).toEqual([
      { klucz: 'Źródło', wartosc: 'Facebook' },
      { klucz: 'System rozliczeń', wartosc: 'net-billing' },
      { klucz: 'Inne', wartosc: 'a: b' },
    ])
  })
  it('segment bez klucza i puste wejscia', () => {
    expect(rozbijUwagi('sama notatka')).toEqual([
      { klucz: '', wartosc: 'sama notatka' },
    ])
    expect(rozbijUwagi('')).toEqual([])
    expect(rozbijUwagi(null)).toEqual([])
  })
})

describe('pamiec sekcji', () => {
  beforeEach(() => localStorage.clear())
  it('klucz per doctype i sekcja', () => {
    expect(kluczSekcji('CRM Deal', 'a')).not.toBe(kluczSekcji('CRM Lead', 'a'))
  })
  it('zapis i odczyt, null gdy brak', () => {
    expect(wczytajOtwartaSekcje('CRM Deal', 's')).toBeNull()
    zapiszOtwartaSekcje('CRM Deal', 's', true)
    expect(wczytajOtwartaSekcje('CRM Deal', 's')).toBe(true)
    zapiszOtwartaSekcje('CRM Deal', 's', false)
    expect(wczytajOtwartaSekcje('CRM Deal', 's')).toBe(false)
  })
})

describe('podsumowanieSekcji', () => {
  it('Dane instalacji', () => {
    const s = sek('Dane instalacji', [])
    const r = podsumowanieSekcji(s, { custom_pv_power_kwp: 8.5, deal_value: 63093.6 })
    expect(r.replace(' ', ' ')).toBe('8,5 kWp · 63 093,60 zł brutto')
  })
  it('Nieruchomosc i Adres', () => {
    const doc = {
      custom_install_address: 'Polna',
      custom_nr_domu: '12',
      custom_install_postal_code: '00-001',
      custom_install_city: 'Warszawa',
    }
    expect(podsumowanieSekcji(sek('Adres', []), doc)).toBe('Polna 12, 00-001 Warszawa')
    expect(podsumowanieSekcji(sek('Nieruchomość', []), { custom_install_address: 'Polna 3' })).toBe('Polna 3')
  })
  it('Spotkanie z rozwiazaniem uzytkownika', () => {
    const s = sek('Spotkanie', [{ fieldname: 'lead_owner', fieldtype: 'Link' }])
    const r = podsumowanieSekcji(
      s,
      { custom_termin_spotkania: '2026-11-03 14:30:00', lead_owner: 'a@b.pl' },
      { rozwiaz: () => 'Anna Nowak' },
    )
    expect(r).toBe('03.11.2026, 14:30 · Anna Nowak')
  })
  it('Zrodlo', () => {
    expect(
      podsumowanieSekcji(sek('Źródło', []), {
        custom_import_source: 'FB',
        custom_import_date: '2026-11-01',
      }),
    ).toBe('FB · 01.11.2026')
  })
  it('Dane klienta nie powtarza naglowka', () => {
    expect(podsumowanieSekcji(sek('Dane klienta', []), {})).toBe('Imię, nazwisko, telefon')
  })
  it('Klient liczy kontakty z odmiana', () => {
    const k = (n) => podsumowanieSekcji(sek('Klient', [], 'contacts_section'), {}, { liczbaKontaktow: n })
    expect(k(1)).toBe('1 kontakt')
    expect(k(3)).toBe('3 kontakty')
    expect(k(5)).toBe('5 kontaktów')
    expect(k(12)).toBe('12 kontaktów')
    expect(k(22)).toBe('22 kontakty')
    expect(k(0)).toBe('Brak kontaktów')
  })
  it('ogolna: do trzech wartosci, pomija puste i ukryte', () => {
    const s = sek('Call center', [
      { fieldname: 'a', fieldtype: 'Data' },
      { fieldname: 'b', fieldtype: 'Data' },
      { fieldname: 'c', fieldtype: 'Check', label: 'Tak' },
      { fieldname: 'd', fieldtype: 'Data' },
      { fieldname: 'e', fieldtype: 'Data' },
      { fieldname: 'h', fieldtype: 'Data', visible: false },
    ])
    expect(podsumowanieSekcji(s, { a: 'x', b: '', c: 1, d: 'y', e: 'z', h: 'q' })).toBe('x · Tak · y')
  })
  it('puste: Brak danych', () => {
    expect(podsumowanieSekcji(sek('Inna', [{ fieldname: 'a', fieldtype: 'Data' }]), {})).toBe('Brak danych')
  })
  it('Dane instalacji bez mocy i kwoty spada do ogolnej', () => {
    const s = sek('Dane instalacji', [{ fieldname: 'a', fieldtype: 'Data' }])
    expect(podsumowanieSekcji(s, { a: 'abc', deal_value: 0 })).toBe('abc')
  })
})

describe('podsumowanieZadan', () => {
  it('odmiana i licznik otwartych', () => {
    expect(podsumowanieZadan(0)).toBe('Brak zadań')
    expect(podsumowanieZadan(1)).toBe('1 zadanie')
    expect(podsumowanieZadan(3, 2)).toBe('3 zadania, otwartych: 2')
    expect(podsumowanieZadan(5)).toBe('5 zadań')
    expect(podsumowanieZadan(12)).toBe('12 zadań')
  })
})
