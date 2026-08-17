import {
  TAK_NIE_OPCJE,
  WYKSZTALCENIE_OPCJE,
  RODZAJ_DOKUMENTU_OPCJE,
  STAN_CYWILNY_OPCJE,
  PRACA_FORMA_OPCJE,
  PRACA_OKRES_OPCJE,
  DZIALALNOSC_FORMA_OPCJE,
  PREFILL_KEYS,
  BASE_FIELDS,
  GRUPY,
  defaultForm,
  buildDane,
  hydrateFrom,
  normalizujKwote,
  formatujNumerRachunku,
  formatujNumerRachunkuZKursorem,
} from '@/utils/kredytForm'

function deepFreeze(value) {
  Object.freeze(value)
  for (const child of Object.values(value)) {
    if (child && typeof child === 'object' && !Object.isFrozen(child)) {
      deepFreeze(child)
    }
  }
  return value
}

describe('Kredyt form logic', () => {
  describe('option constants', () => {
    it('pins the authoritative option wording (PDF transcription, except STAN_CYWILNY_OPCJE which is an owner override)', () => {
      expect(TAK_NIE_OPCJE).toEqual(['', 'Tak', 'Nie'])
      expect(WYKSZTALCENIE_OPCJE).toEqual([
        '',
        'wyższe',
        'średnie',
        'zawodowe',
        'podstawowe/gimnazjalne',
      ])
      expect(RODZAJ_DOKUMENTU_OPCJE).toEqual(['', 'Dowód osobisty', 'Paszport', 'Karta pobytu'])
      expect(STAN_CYWILNY_OPCJE).toEqual([
        '',
        'Kawaler/panna',
        'Rozwiedziony/a',
        'Małżeństwo - rozdzielność majątkowa',
        'Małżeństwo - wspólnota majątkowa',
        'Wdowiec/wdowa',
        'Separacja',
      ])
      expect(PRACA_FORMA_OPCJE).toEqual(['', 'Umowa o pracę', 'Umowa zlecenie', 'Umowa o dzieło'])
      expect(PRACA_OKRES_OPCJE).toEqual(['', 'Czas określony', 'Czas nieokreślony'])
      expect(DZIALALNOSC_FORMA_OPCJE).toEqual([
        '',
        'ryczałt',
        'księga przychodów i rozchodów (KPiR)',
        'inne',
      ])
    })

    it('uses the lowercase "inne" value, not "Inne"', () => {
      expect(DZIALALNOSC_FORMA_OPCJE).toContain('inne')
      expect(DZIALALNOSC_FORMA_OPCJE).not.toContain('Inne')
    })

    it('exports the 10 read-only prefill keys', () => {
      expect(PREFILL_KEYS).toEqual([
        'pesel',
        'imiona',
        'nazwisko',
        'telefon',
        'email',
        'kod_pocztowy',
        'miejscowosc',
        'ulica',
        'nr_domu',
        'nr_lokalu',
      ])
    })
  })

  describe('GRUPY', () => {
    it('declares six income groups', () => {
      expect(GRUPY).toHaveLength(6)
      expect(GRUPY.map((g) => g.key)).toEqual([
        'praca',
        'emerytura',
        'renta',
        'dzialalnosc',
        'gospodarstwo',
        'inne',
      ])
    })

    it('every group fieldname (toggle + fields) exists as a key in defaultForm()', () => {
      const form = defaultForm()
      GRUPY.forEach((grupa) => {
        expect(form).toHaveProperty(grupa.wlaczone)
        grupa.fields.forEach((fn) => {
          expect(form).toHaveProperty(fn)
        })
      })
    })

    it('every base field exists as a key in defaultForm()', () => {
      const form = defaultForm()
      BASE_FIELDS.forEach((fn) => {
        expect(form).toHaveProperty(fn)
      })
    })
  })

  describe('defaultForm', () => {
    it('sets every toggle to false and every other field to the empty string', () => {
      const form = defaultForm()
      GRUPY.forEach((grupa) => {
        expect(form[grupa.wlaczone]).toBe(false)
        grupa.fields.forEach((fn) => {
          expect(form[fn]).toBe('')
        })
      })
      BASE_FIELDS.forEach((fn) => {
        expect(form[fn]).toBe('')
      })
    })

    it('returns independent copies on each call', () => {
      const first = defaultForm()
      const second = defaultForm()
      first.miejsce_urodzenia = 'Warszawa'
      first.praca_wlaczone = true
      expect(second.miejsce_urodzenia).toBe('')
      expect(second.praca_wlaczone).toBe(false)
      expect(first).not.toBe(second)
    })
  })

  describe('buildDane', () => {
    it('passes base fields through unchanged', () => {
      const form = defaultForm()
      form.miejsce_urodzenia = 'Kraków'
      form.wyksztalcenie = 'wyższe'
      form.liczba_osob_na_utrzymaniu = '2'

      const dane = buildDane(form)
      expect(dane.miejsce_urodzenia).toBe('Kraków')
      expect(dane.wyksztalcenie).toBe('wyższe')
      expect(dane.liczba_osob_na_utrzymaniu).toBe('2')
    })

    it('never mutates a deeply frozen form', () => {
      const form = defaultForm()
      form.praca_wlaczone = true
      form.praca_forma = 'Umowa o pracę'
      form.praca_kwota_dochodu = '5000'
      form.miejsce_urodzenia = 'Poznań'
      const before = JSON.parse(JSON.stringify(form))

      deepFreeze(form)
      buildDane(form)

      expect(form).toEqual(before)
    })

    it('sends null for every field of a group whose toggle is off', () => {
      const form = defaultForm()
      form.praca_forma = 'Umowa zlecenie'
      form.praca_kwota_dochodu = '4200'
      form.praca_wlaczone = false

      const dane = buildDane(form)
      expect(dane.praca_wlaczone).toBe(false)
      expect(dane.praca_forma).toBeNull()
      expect(dane.praca_data_zatrudnienia).toBeNull()
      expect(dane.praca_okres).toBeNull()
      expect(dane.praca_okres_od).toBeNull()
      expect(dane.praca_okres_do).toBeNull()
      expect(dane.praca_nip).toBeNull()
      expect(dane.praca_nazwa_zakladu).toBeNull()
      expect(dane.praca_adres_telefon).toBeNull()
      expect(dane.praca_kwota_dochodu).toBeNull()
    })

    it('passes through every field of a group whose toggle is on', () => {
      const form = defaultForm()
      form.praca_wlaczone = true
      form.praca_forma = 'Umowa o pracę'
      form.praca_data_zatrudnienia = '2020-01-15'
      form.praca_okres = 'Czas określony'
      form.praca_okres_od = '2020-01-15'
      form.praca_okres_do = '2028-01-15'
      form.praca_nip = '1234567890'
      form.praca_nazwa_zakladu = 'ACME sp. z o.o.'
      form.praca_adres_telefon = 'ul. Testowa 1, 500600700'
      form.praca_kwota_dochodu = '6500'

      const dane = buildDane(form)
      expect(dane).toMatchObject({
        praca_wlaczone: true,
        praca_forma: 'Umowa o pracę',
        praca_data_zatrudnienia: '2020-01-15',
        praca_okres: 'Czas określony',
        praca_okres_od: '2020-01-15',
        praca_okres_do: '2028-01-15',
        praca_nip: '1234567890',
        praca_nazwa_zakladu: 'ACME sp. z o.o.',
        praca_adres_telefon: 'ul. Testowa 1, 500600700',
        praca_kwota_dochodu: '6500',
      })
    })

    it('all-off toggle matrix: every group nulled, every toggle false', () => {
      const form = defaultForm()
      GRUPY.forEach((grupa) => {
        grupa.fields.forEach((fn, i) => {
          form[fn] = `wartosc-${i}`
        })
      })

      const dane = buildDane(form)
      GRUPY.forEach((grupa) => {
        expect(dane[grupa.wlaczone]).toBe(false)
        grupa.fields.forEach((fn) => {
          expect(dane[fn]).toBeNull()
        })
      })
    })

    it('all-on toggle matrix: every group passed through, every toggle true', () => {
      const form = defaultForm()
      GRUPY.forEach((grupa) => {
        form[grupa.wlaczone] = true
        grupa.fields.forEach((fn, i) => {
          form[fn] = `wartosc-${i}`
        })
      })

      const dane = buildDane(form)
      GRUPY.forEach((grupa) => {
        expect(dane[grupa.wlaczone]).toBe(true)
        grupa.fields.forEach((fn, i) => {
          expect(dane[fn]).toBe(`wartosc-${i}`)
        })
      })
    })

    it('mixed matrix: only the toggled-off groups are nulled', () => {
      const form = defaultForm()
      form.emerytura_wlaczone = true
      form.emerytura_numer_swiadczenia = 'EMR-1'
      form.emerytura_od_kiedy = '2018-05-01'
      form.emerytura_kwota_dochodu = '3200'

      form.dzialalnosc_wlaczone = true
      form.dzialalnosc_forma_opodatkowania = 'ryczałt'
      form.dzialalnosc_nip = '9998887776'
      form.dzialalnosc_nazwa = 'Firma X'
      form.dzialalnosc_kwota_dochodu = '9000'

      // renta and inne stay off
      form.renta_numer_swiadczenia = 'stale'
      form.inne_1_typ = 'stypendium'
      form.inne_1_kwota = '400'

      const dane = buildDane(form)

      expect(dane.emerytura_wlaczone).toBe(true)
      expect(dane.emerytura_numer_swiadczenia).toBe('EMR-1')
      expect(dane.emerytura_od_kiedy).toBe('2018-05-01')
      expect(dane.emerytura_kwota_dochodu).toBe('3200')

      expect(dane.dzialalnosc_wlaczone).toBe(true)
      expect(dane.dzialalnosc_forma_opodatkowania).toBe('ryczałt')
      expect(dane.dzialalnosc_nip).toBe('9998887776')
      expect(dane.dzialalnosc_nazwa).toBe('Firma X')
      expect(dane.dzialalnosc_kwota_dochodu).toBe('9000')
      // Group is ON but this field was never typed — passed through as the
      // untouched default '', NOT nulled (nulling only happens when the
      // group's own toggle is off).
      expect(dane.dzialalnosc_forma_inna).toBe('')

      expect(dane.renta_wlaczone).toBe(false)
      expect(dane.renta_numer_swiadczenia).toBeNull()

      expect(dane.inne_wlaczone).toBe(false)
      expect(dane.inne_1_typ).toBeNull()
      expect(dane.inne_1_kwota).toBeNull()
    })

    it('returns a fresh object every call', () => {
      const form = defaultForm()
      const first = buildDane(form)
      const second = buildDane(form)
      first.miejsce_urodzenia = 'zmienione'
      expect(second.miejsce_urodzenia).toBe('')
      expect(first).not.toBe(second)
    })
  })

  describe('hydrateFrom', () => {
    it('coerces every toggle to a real boolean', () => {
      const record = {
        praca_wlaczone: 1,
        emerytura_wlaczone: 0,
        renta_wlaczone: null,
        dzialalnosc_wlaczone: true,
        gospodarstwo_wlaczone: false,
        inne_wlaczone: undefined,
      }
      const form = hydrateFrom(record)
      expect(form.praca_wlaczone).toBe(true)
      expect(form.emerytura_wlaczone).toBe(false)
      expect(form.renta_wlaczone).toBe(false)
      expect(form.dzialalnosc_wlaczone).toBe(true)
      expect(form.gospodarstwo_wlaczone).toBe(false)
      expect(form.inne_wlaczone).toBe(false)
    })

    it('coerces null/undefined non-toggle fields to the empty string', () => {
      const record = {
        miejsce_urodzenia: null,
        wyksztalcenie: undefined,
        praca_forma: null,
      }
      const form = hydrateFrom(record)
      expect(form.miejsce_urodzenia).toBe('')
      expect(form.wyksztalcenie).toBe('')
      expect(form.praca_forma).toBe('')
    })

    it('preserves real values, including falsy-but-meaningful strings and numbers', () => {
      const record = {
        miejsce_urodzenia: 'Gdańsk',
        liczba_osob_na_utrzymaniu: 0,
        praca_wlaczone: true,
        praca_kwota_dochodu: '0',
      }
      const form = hydrateFrom(record)
      expect(form.miejsce_urodzenia).toBe('Gdańsk')
      expect(form.liczba_osob_na_utrzymaniu).toBe(0)
      expect(form.praca_wlaczone).toBe(true)
      expect(form.praca_kwota_dochodu).toBe('0')
    })

    it('treats a null record like an empty one, returning defaultForm()', () => {
      expect(hydrateFrom(null)).toEqual(defaultForm())
      expect(hydrateFrom(undefined)).toEqual(defaultForm())
    })

    it('never mutates the source record', () => {
      const record = deepFreeze({ praca_wlaczone: true, praca_forma: 'Umowa o pracę' })
      expect(() => hydrateFrom(record)).not.toThrow()
      expect(record.praca_wlaczone).toBe(true)
    })

    it('returns a fresh object every call', () => {
      const record = { miejsce_urodzenia: 'Łódź' }
      const first = hydrateFrom(record)
      const second = hydrateFrom(record)
      first.miejsce_urodzenia = 'zmienione'
      expect(second.miejsce_urodzenia).toBe('Łódź')
      expect(first).not.toBe(second)
    })
  })

  describe('normalizujKwote', () => {
    it('appends ",00" to a bare integer', () => {
      expect(normalizujKwote('123')).toBe('123,00')
    })

    it('pads a single decimal digit to two', () => {
      expect(normalizujKwote('123,4')).toBe('123,40')
    })

    it('leaves an already-two-decimal-digit amount unchanged', () => {
      expect(normalizujKwote('123,90')).toBe('123,90')
    })

    it('treats a trailing comma with no digits as zero decimals', () => {
      expect(normalizujKwote('123,')).toBe('123,00')
    })

    it('converts a dot decimal separator to a comma and pads it', () => {
      expect(normalizujKwote('123.4')).toBe('123,40')
    })

    it('treats a trailing dot with no digits as zero decimals', () => {
      expect(normalizujKwote('123.')).toBe('123,00')
    })

    it('preserves user-typed thousands-space grouping, touching only the decimal part', () => {
      expect(normalizujKwote('12 300')).toBe('12 300,00')
      expect(normalizujKwote('12 300,5')).toBe('12 300,50')
      expect(normalizujKwote('1 234 567')).toBe('1 234 567,00')
    })

    it('returns empty or whitespace-only text unchanged', () => {
      expect(normalizujKwote('')).toBe('')
      expect(normalizujKwote('   ')).toBe('   ')
    })

    it('returns text unchanged when it fails a Decimal-like parse', () => {
      expect(normalizujKwote('abc')).toBe('abc')
      expect(normalizujKwote('1,2,3')).toBe('1,2,3')
      expect(normalizujKwote(',123')).toBe(',123')
      expect(normalizujKwote('1.2.3')).toBe('1.2.3')
    })

    it('leaves more than 2 decimal digits unchanged rather than rounding', () => {
      expect(normalizujKwote('123,456')).toBe('123,456')
      expect(normalizujKwote('123.4567')).toBe('123.4567')
    })

    it('never mutates its argument and never throws on non-string input', () => {
      const tekst = '123'
      const wynik = normalizujKwote(tekst)
      expect(tekst).toBe('123')
      expect(wynik).toBe('123,00')
      expect(() => normalizujKwote(null)).not.toThrow()
      expect(() => normalizujKwote(undefined)).not.toThrow()
    })
  })

  describe('formatujNumerRachunku', () => {
    it('groups a full 26-digit NRB as 2 digits then groups of 4', () => {
      expect(formatujNumerRachunku('61109010140000071219812874')).toBe(
        '61 1090 1014 0000 0712 1981 2874',
      )
    })

    it('formats progressively as digits accumulate (partial input)', () => {
      expect(formatujNumerRachunku('6')).toBe('6')
      expect(formatujNumerRachunku('61')).toBe('61')
      expect(formatujNumerRachunku('611')).toBe('61 1')
      expect(formatujNumerRachunku('611090')).toBe('61 1090')
    })

    it('is idempotent — formatting an already-formatted value is a no-op', () => {
      const raz = formatujNumerRachunku('61109010140000071219812874')
      expect(formatujNumerRachunku(raz)).toBe(raz)
    })

    it('regroups a value with misplaced spaces, keying only off the digits', () => {
      expect(formatujNumerRachunku('61 10 9010')).toBe('61 1090 10')
    })

    it('strips a non-breaking space and regroups from the digits underneath', () => {
      expect(formatujNumerRachunku('61 1090')).toBe('61 1090')
    })

    it('returns empty and whitespace-only input as empty string', () => {
      expect(formatujNumerRachunku('')).toBe('')
      expect(formatujNumerRachunku('   ')).toBe('')
    })

    it('returns non-digit content verbatim — server has no format validation for this field', () => {
      expect(formatujNumerRachunku('PL61109010140000071219812874')).toBe(
        'PL61109010140000071219812874',
      )
      expect(formatujNumerRachunku('61-1090')).toBe('61-1090')
      expect(formatujNumerRachunku('abc')).toBe('abc')
    })

    it('groups more than 26 digits too — this is a display mask, not a length validator', () => {
      expect(formatujNumerRachunku('6110901014000007121981287499')).toBe(
        '61 1090 1014 0000 0712 1981 2874 99',
      )
    })

    it('returns non-string input unchanged and never throws', () => {
      expect(formatujNumerRachunku(null)).toBeNull()
      expect(formatujNumerRachunku(undefined)).toBeUndefined()
      expect(formatujNumerRachunku(123)).toBe(123)
    })
  })

  describe('formatujNumerRachunkuZKursorem', () => {
    it('keeps the caret at the end when it starts at the end', () => {
      // '611090' (6 digits) -> '61 1090' (7 chars); caret was after all 6
      // digits, so it lands after all digits in the formatted string too.
      expect(formatujNumerRachunkuZKursorem('611090', 6)).toEqual({
        tekst: '61 1090',
        kursor: 7,
      })
    })

    it('lands the caret right after a digit just typed mid-string', () => {
      // Rep had '61 1090' and typed '5' after '61 1', producing raw
      // '61 15090' with the caret at index 5 (right after the new '5').
      // That's the 4th digit in the raw text (6,1,1,5); the formatted
      // string '61 1509 0' has its 4th digit ('5') at index 4, so the
      // caret goes to index 5 — still immediately after that same '5'.
      expect(formatujNumerRachunkuZKursorem('61 15090', 5)).toEqual({
        tekst: '61 1509 0',
        kursor: 5,
      })
    })

    it('keeps caret 0 at 0', () => {
      expect(formatujNumerRachunkuZKursorem('611090', 0)).toEqual({
        tekst: '61 1090',
        kursor: 0,
      })
    })

    it('deleting a digit just after a space keeps the caret stable', () => {
      // Raw '6110914' (7 digits) with the caret at index 5 — 5 digits
      // precede it (6,1,1,0,9). The formatted string '61 1091 4' has its
      // 5th digit ('9') at index 5, so the caret goes to index 6,
      // immediately after that digit rather than jumping to the end.
      expect(formatujNumerRachunkuZKursorem('6110914', 5)).toEqual({
        tekst: '61 1091 4',
        kursor: 6,
      })
    })

    it('pasting a full 26-digit number with the caret at the end lands the caret at the end', () => {
      const surowy = '61109010140000071219812874'
      const sformatowany = '61 1090 1014 0000 0712 1981 2874'
      expect(formatujNumerRachunkuZKursorem(surowy, surowy.length)).toEqual({
        tekst: sformatowany,
        kursor: sformatowany.length,
      })
    })

    it('keeps the original caret untouched for verbatim (non-digit) passthrough', () => {
      expect(formatujNumerRachunkuZKursorem('61-1090', 3)).toEqual({
        tekst: '61-1090',
        kursor: 3,
      })
      expect(formatujNumerRachunkuZKursorem('abc', 2)).toEqual({ tekst: 'abc', kursor: 2 })
    })
  })
})
