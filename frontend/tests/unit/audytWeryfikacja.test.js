import {
  FIELD_PREFIX,
  PHOTO_PREFIX,
  VERDICT_META,
  aggregate,
  depOk,
  fieldKey,
  parseWeryfikacja,
  photoKey,
  verdictFor,
  visibleElements,
} from '@/utils/audytWeryfikacja'

describe('Audyt — weryfikacja elementów', () => {
  const variant = {
    label: 'Fotowoltaika + Magazyn',
    sections: [
      {
        label: 'Instalacja',
        fields: [
          { fieldname: 'moc_umowna_kw', label: 'Moc umowna', type: 'Float', required: true },
          { fieldname: 'istniejaca_pv', label: 'Istniejąca PV?', type: 'Select', options: 'Tak\nNie' },
        ],
      },
      {
        label: 'Magazyn',
        fields: [
          {
            fieldname: 'pojemnosc_magazynu_kwh',
            label: 'Pojemność magazynu',
            type: 'Float',
            required: false,
            depends_on: { fieldname: 'istniejaca_pv', value: 'Tak' },
          },
          {
            fieldname: 'rok_pv',
            label: 'Rok PV',
            type: 'Int',
            required: false,
            depends_on: { fieldname: 'istniejaca_pv', value: 'Tak' },
          },
        ],
      },
      { label: 'Formalności', fields: [{ fieldname: 'uwagi', label: 'Uwagi', type: 'Small Text' }] },
      { label: 'Pomiary', fields: [] },
      { label: 'Podsumowanie', fields: [{ fieldname: 'wynik', label: 'Wynik', type: 'Select', required: false }] },
    ],
    photo_slots: [
      { key: 'rozdzielnica', label: 'Rozdzielnica', required: true },
      { key: 'dach', label: 'Dach', required: true },
      {
        key: 'istniejaca_pv',
        label: 'Istniejąca instalacja PV',
        depends_on: { fieldname: 'istniejaca_pv', value: 'Tak' },
      },
      { key: 'licznik', label: 'Licznik', required: false, pdf: true },
    ],
  }

  describe('klucze i stałe', () => {
    it('używa zamrożonych prefiksów', () => {
      expect(FIELD_PREFIX).toBe('pole:')
      expect(PHOTO_PREFIX).toBe('foto:')
      expect(fieldKey('moc_umowna_kw')).toBe('pole:moc_umowna_kw')
      expect(photoKey('rozdzielnica')).toBe('foto:rozdzielnica')
    })
  })

  describe('parseWeryfikacja', () => {
    it.each([null, undefined, '', '{broken', 'null', '[]', '"not a map"', 42])(
      'zwraca pustą mapę dla niepoprawnego wejścia: %p',
      (raw) => expect(parseWeryfikacja(raw)).toEqual({}),
    )

    it('parsuje mapę JSON oraz zachowuje poprawne wpisy', () => {
      const entry = { status: 'error', note: 'Nie pasuje', by: 'user@x.pl' }
      expect(parseWeryfikacja(JSON.stringify({ 'pole:moc': entry }))).toEqual({ 'pole:moc': entry })
      expect(parseWeryfikacja({ 'foto:dach': { status: 'accepted' } })).toEqual({
        'foto:dach': { status: 'accepted' },
      })
    })

    it('obsługuje podwójnie zakodowany JSON', () => {
      const map = { 'foto:licznik': { status: 'accepted', at: '2026-08-14 10:13:01' } }
      expect(parseWeryfikacja(JSON.stringify(JSON.stringify(map)))).toEqual(map)
    })

    it('odrzuca wpisy niebędące obiektami i wpisy z nieprawidłowym statusem', () => {
      expect(
        parseWeryfikacja({
          good: { status: 'accepted' },
          badStatus: { status: 'waiting' },
          number: 1,
          list: [],
          nil: null,
        }),
      ).toEqual({ good: { status: 'accepted' } })
    })
  })

  describe('depOk', () => {
    it('pokazuje element bez depends_on', () => {
      expect(depOk({ fieldname: 'x' }, {})).toBe(true)
      expect(depOk({}, {})).toBe(true)
    })

    it.each([
      [{ fieldname: 'x', depends_on: { fieldname: 'switch', value: 'Tak' } }, { switch: 'Tak' }, true],
      [{ fieldname: 'x', depends_on: { fieldname: 'switch', value: 'Tak' } }, { switch: 'Nie' }, false],
    ])('sprawdza wartość zależności', (item, values, expected) => {
      expect(depOk(item, values)).toBe(expected)
    })
  })

  describe('visibleElements', () => {
    it('zwraca wszystkie pola w kolejności sekcji, a potem zdjęcia', () => {
      const result = visibleElements(variant, { istniejaca_pv: 'Tak' })
      expect(result.map((element) => element.key)).toEqual([
        'pole:moc_umowna_kw',
        'pole:istniejaca_pv',
        'pole:pojemnosc_magazynu_kwh',
        'pole:rok_pv',
        'pole:uwagi',
        'pole:wynik',
        'foto:rozdzielnica',
        'foto:dach',
        'foto:istniejaca_pv',
        'foto:licznik',
      ])
      expect(result[0]).toEqual({
        key: 'pole:moc_umowna_kw',
        kind: 'field',
        label: 'Moc umowna',
        fieldname: 'moc_umowna_kw',
      })
      expect(result.at(-1)).toEqual({
        key: 'foto:licznik',
        kind: 'photo',
        label: 'Licznik',
        slotKey: 'licznik',
      })
    })

    it('ukrywa pola i zdjęcie zależne od przełącznika', () => {
      const result = visibleElements(variant, { istniejaca_pv: 'Nie' })
      expect(result.map((element) => element.key)).not.toContain('pole:pojemnosc_magazynu_kwh')
      expect(result.map((element) => element.key)).not.toContain('pole:rok_pv')
      expect(result.map((element) => element.key)).not.toContain('foto:istniejaca_pv')
      expect(result).toHaveLength(7)
    })

    it.each([[null], [undefined]])('zwraca pustą listę dla wariantu %p', (definition) => {
      expect(visibleElements(definition, {})).toEqual([])
    })

    it('zachowuje kolejność i obsługuje puste sekcje', () => {
      const result = visibleElements({ sections: [{ fields: [] }, { fields: [{ fieldname: 'a', label: 'A' }] }] }, {})
      expect(result).toEqual([{ key: 'pole:a', kind: 'field', label: 'A', fieldname: 'a' }])
    })
  })

  describe('verdictFor', () => {
    it('brak wpisu oznacza oczekiwanie', () => {
      expect(verdictFor({}, 'pole:x')).toEqual({ status: 'waiting' })
      expect(verdictFor(null, 'pole:x')).toEqual({ status: 'waiting' })
    })

    it('przekazuje zaakceptowany i błędny werdykt wraz z notatką', () => {
      expect(verdictFor({ x: { status: 'accepted', by: 'u', at: 't' } }, 'x')).toEqual({
        status: 'accepted',
        by: 'u',
        at: 't',
      })
      expect(verdictFor({ x: { status: 'error', note: 'Poprawić' } }, 'x')).toEqual({
        status: 'error',
        note: 'Poprawić',
      })
      expect(verdictFor({ x: { status: 'waiting' } }, 'x')).toEqual({ status: 'waiting' })
    })
  })

  describe('aggregate', () => {
    const elements = [{ key: 'a' }, { key: 'b' }, { key: 'c' }, { key: 'd' }]

    it('liczy oczekujące elementy i nie uznaje pustej listy za ukończoną', () => {
      expect(aggregate({}, elements)).toEqual({ accepted: 0, errors: 0, waiting: 4, total: 4, allAccepted: false })
      expect(aggregate({}, [])).toEqual({ accepted: 0, errors: 0, waiting: 0, total: 0, allAccepted: false })
    })

    it('zwraca mieszane liczniki', () => {
      expect(aggregate({ a: { status: 'accepted' }, b: { status: 'error' } }, elements)).toEqual({
        accepted: 1,
        errors: 1,
        waiting: 2,
        total: 4,
        allAccepted: false,
      })
    })

    it('uznaje wszystkie elementy za zaakceptowane tylko gdy każdy ma werdykt', () => {
      expect(aggregate({ a: { status: 'accepted' }, b: { status: 'accepted' } }, elements.slice(0, 2))).toMatchObject({
        accepted: 2,
        errors: 0,
        waiting: 0,
        total: 2,
        allAccepted: true,
      })
    })

    it('ignoruje zapisany werdykt dla ukrytego elementu', () => {
      expect(aggregate({ hidden: { status: 'accepted' }, a: { status: 'accepted' } }, [{ key: 'a' }])).toEqual({
        accepted: 1,
        errors: 0,
        waiting: 0,
        total: 1,
        allAccepted: true,
      })
    })

    it('element opcjonalny bez werdyktu nadal blokuje ukończenie', () => {
      expect(aggregate({ required: { status: 'accepted' } }, [{ key: 'required' }, { key: 'optional' }]).allAccepted).toBe(false)
    })
  })

  describe('VERDICT_META', () => {
    it('zawiera polskie etykiety, kolory i ring dla wszystkich stanów', () => {
      expect(VERDICT_META.waiting).toEqual({ theme: 'blue', label: 'Oczekuje', ring: 'ring-outline-blue-2' })
      expect(VERDICT_META.accepted).toEqual({ theme: 'green', label: 'Zaakceptowano', ring: 'ring-outline-green-2' })
      expect(VERDICT_META.error).toEqual({ theme: 'red', label: 'Błąd', ring: 'ring-outline-red-3' })
    })
  })
})
