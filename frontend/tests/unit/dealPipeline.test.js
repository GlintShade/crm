import {
  currentIndexFor,
  bandMode,
  nodeState,
  nodeStateForMode,
  stepNumber,
  nextStepNote,
  offPipelineBadge,
  grupaForRodzaj,
  filterKnown,
} from '@/utils/dealPipeline'

const stepsPvMe = [
  { status: 'Nowy', index: 0 },
  { status: 'Kalkulacja', index: 1 },
  { status: 'Umowa', index: 2 },
]

function shapePayload(overrides = {}) {
  return {
    rodzaj: 'Fotowoltaika + Magazyn',
    steps: stepsPvMe,
    notes: { Kalkulacja: 'Uzupełnij dane techniczne' },
    // Migawkowe pola z backendu — CELOWO rozjechane z tym, co niesie `status`
    // przekazywany osobno w testach niżej, żeby dowieść, że funkcje ich nie czytają.
    current_index: 99,
    off_pipeline: true,
    off_pipeline_type: 'Lost',
    note: 'TA WARTOŚĆ NIE POWINNA NIGDY WYCIEC DO WYNIKU',
    ...overrides,
  }
}

describe('Pipeline dealu — logika węzłów paska etapów (dealPipeline)', () => {
  describe('currentIndexFor', () => {
    it('zwraca indeks statusu dopasowanego po step.status', () => {
      expect(currentIndexFor(stepsPvMe, 'Nowy')).toBe(0)
      expect(currentIndexFor(stepsPvMe, 'Kalkulacja')).toBe(1)
      expect(currentIndexFor(stepsPvMe, 'Umowa')).toBe(2)
    })

    it.each([
      [stepsPvMe, 'Nieznany status'],
      [stepsPvMe, null],
      [stepsPvMe, undefined],
      [stepsPvMe, ''],
      [[], 'Nowy'],
      [undefined, 'Nowy'],
      [null, 'Nowy'],
    ])('zwraca -1 dla steps=%p, status=%p', (steps, status) => {
      expect(currentIndexFor(steps, status)).toBe(-1)
    })
  })

  describe('bandMode — hidden', () => {
    it.each([
      [null, 'brak payloadu'],
      [undefined, 'undefined zamiast payloadu'],
      [{ ...shapePayload(), steps: [] }, 'puste steps'],
      [{ ...shapePayload(), steps: undefined }, 'brak pola steps'],
      [{ notes: {} }, 'payload bez steps w ogóle'],
    ])('zwraca "hidden" dla: %s (%s)', (payload) => {
      expect(bandMode(payload, 'Nowy', undefined)).toBe('hidden')
    })
  })

  describe('bandMode — progress ignoruje migawkę payloadu (payload.current_index/off_pipeline* rozjechane z props.status)', () => {
    it('zwraca "progress", gdy status jest w steps, mimo że payload.off_pipeline=true/current_index=99', () => {
      const payload = shapePayload()
      expect(bandMode(payload, 'Kalkulacja', undefined)).toBe('progress')
    })

    it('indeks bieżącego kroku liczy się z currentIndexFor(props.status), NIE z payload.current_index', () => {
      const payload = shapePayload()
      expect(currentIndexFor(payload.steps, 'Kalkulacja')).toBe(1)
      expect(payload.current_index).toBe(99) // migawka rozjechana — dowód, że jest nieużywana
    })
  })

  describe('bandMode — lost / won / unknown liczone z statusType, nie z payload.off_pipeline_type', () => {
    it('zwraca "lost" gdy status poza steps i statusType==="Lost"', () => {
      const payload = shapePayload({ off_pipeline_type: 'Won' }) // migawka celowo mówi co innego
      expect(bandMode(payload, 'Utracona', 'Lost')).toBe('lost')
    })

    it('zwraca "won" gdy status poza steps i statusType==="Won"', () => {
      const payload = shapePayload({ off_pipeline_type: 'Lost' })
      expect(bandMode(payload, 'Wygrana', 'Won')).toBe('won')
    })

    it.each([[null], [undefined], ['CośInnego'], ['']])(
      'zwraca "unknown" gdy status poza steps i statusType=%p',
      (statusType) => {
        const payload = shapePayload()
        expect(bandMode(payload, 'Jakiś obcy status', statusType)).toBe('unknown')
      },
    )

    it('undefined statusType (store jeszcze nie załadowany) daje "unknown" dla statusu spoza rurociągu', () => {
      const payload = shapePayload()
      expect(bandMode(payload, 'Przegrana', undefined)).toBe('unknown')
    })
  })

  describe('nodeState', () => {
    it.each([
      [0, 1, 'done'],
      [1, 1, 'current'],
      [2, 1, 'future'],
      [0, 0, 'current'],
      [4, 0, 'future'],
    ])('nodeState(%p, %p) === %p', (index, currentIndex, expected) => {
      expect(nodeState(index, currentIndex)).toBe(expected)
    })
  })

  describe('nodeState — pełny przebieg przez wszystkie węzły (pierwszy/środkowy/ostatni krok)', () => {
    const indeksy = [0, 1, 2]

    it('pierwszy krok (current_index=0): węzeł 0 current, reszta future', () => {
      const currentIndex = 0
      const wynik = indeksy.map((i) => nodeState(i, currentIndex))
      expect(wynik).toEqual(['current', 'future', 'future'])
    })

    it('środkowy krok (current_index=1): węzeł 0 done, 1 current, 2 future', () => {
      const currentIndex = 1
      const wynik = indeksy.map((i) => nodeState(i, currentIndex))
      expect(wynik).toEqual(['done', 'current', 'future'])
    })

    it('ostatni krok (current_index=2): węzły 0 i 1 done, 2 current', () => {
      const currentIndex = 2
      const wynik = indeksy.map((i) => nodeState(i, currentIndex))
      expect(wynik).toEqual(['done', 'done', 'current'])
    })
  })

  describe('nodeStateForMode', () => {
    it('tryb "won" — każdy węzeł, niezależnie od indeksu, jest "done"', () => {
      expect(nodeStateForMode('won', 0, 1)).toBe('done')
      expect(nodeStateForMode('won', 5, 0)).toBe('done')
      expect(nodeStateForMode('won', 0, 0)).toBe('done')
    })

    it.each([['lost'], ['unknown']])(
      'tryb "%s" — każdy węzeł jest wyciszony ("muted"), niezależnie od indeksu',
      (mode) => {
        expect(nodeStateForMode(mode, 0, 1)).toBe('muted')
        expect(nodeStateForMode(mode, 5, 0)).toBe('muted')
        expect(nodeStateForMode(mode, 2, 2)).toBe('muted')
      },
    )

    it('tryb "progress" — deleguje do nodeState', () => {
      expect(nodeStateForMode('progress', 0, 1)).toBe('done')
      expect(nodeStateForMode('progress', 1, 1)).toBe('current')
      expect(nodeStateForMode('progress', 2, 1)).toBe('future')
    })

    it('tryb "hidden" — traktowany jak "muted" (nieużywane w UI, ale bez wyjątku)', () => {
      expect(nodeStateForMode('hidden', 0, 0)).toBe('muted')
    })
  })

  describe('stepNumber', () => {
    it.each([
      [0, 1],
      [1, 2],
      [2, 3],
      [9, 10],
    ])('stepNumber(%p) === %p', (index, expected) => {
      expect(stepNumber(index)).toBe(expected)
    })
  })

  describe('nextStepNote', () => {
    it('zwraca notatkę z payload.notes[status] w trybie progress', () => {
      const payload = shapePayload({ notes: { Kalkulacja: 'Uzupełnij dane techniczne' } })
      expect(nextStepNote(payload, 'Kalkulacja', undefined)).toBe('Uzupełnij dane techniczne')
    })

    it('nigdy nie czyta migawkowego payload.note', () => {
      const payload = shapePayload({
        notes: { Kalkulacja: 'Notatka właściwa' },
        note: 'Notatka migawkowa — nie powinna się pokazać',
      })
      expect(nextStepNote(payload, 'Kalkulacja', undefined)).toBe('Notatka właściwa')
    })

    it.each([[''], ['   '], [undefined], [null]])(
      'zwraca null dla pustej/białoznakowej/brakującej notatki (%p) w trybie progress',
      (note) => {
        const payload = shapePayload({ notes: { Kalkulacja: note } })
        expect(nextStepNote(payload, 'Kalkulacja', undefined)).toBeNull()
      },
    )

    it('zwraca null, gdy status nie ma wpisu w notes (brak notatki dla tego kroku)', () => {
      const payload = shapePayload({ notes: {} })
      expect(nextStepNote(payload, 'Kalkulacja', undefined)).toBeNull()
    })

    it('zwraca null w trybie "lost" nawet gdy notes ma wpis dla statusu', () => {
      const payload = shapePayload({ notes: { Utracona: 'Ta notatka nie powinna się pokazać' } })
      expect(nextStepNote(payload, 'Utracona', 'Lost')).toBeNull()
    })

    it('zwraca null w trybie "won" nawet gdy notes ma wpis dla statusu', () => {
      const payload = shapePayload({ notes: { Wygrana: 'Ta notatka nie powinna się pokazać' } })
      expect(nextStepNote(payload, 'Wygrana', 'Won')).toBeNull()
    })

    it('zwraca null w trybie "unknown" nawet gdy notes ma wpis dla statusu', () => {
      const payload = shapePayload({ notes: { 'Obcy status': 'Ta notatka nie powinna się pokazać' } })
      expect(nextStepNote(payload, 'Obcy status', 'Recycled')).toBeNull()
    })

    it('zwraca null w trybie "hidden" (brak payloadu)', () => {
      expect(nextStepNote(null, 'Nowy', undefined)).toBeNull()
      expect(nextStepNote({ steps: [] }, 'Nowy', undefined)).toBeNull()
    })
  })

  describe('offPipelineBadge', () => {
    it('zwraca null w trybie "progress"', () => {
      expect(offPipelineBadge(shapePayload(), 'Kalkulacja', undefined)).toBeNull()
    })

    it('zwraca null w trybie "hidden"', () => {
      expect(offPipelineBadge(null, 'Nowy', undefined)).toBeNull()
      expect(offPipelineBadge({ steps: [] }, 'Nowy', undefined)).toBeNull()
    })

    it('zwraca surowy status (props.status) w trybie "lost", NIE payload.status', () => {
      const payload = shapePayload()
      expect(offPipelineBadge(payload, 'Utracona — cena', 'Lost')).toBe('Utracona — cena')
    })

    it('zwraca surowy status w trybie "won"', () => {
      const payload = shapePayload()
      expect(offPipelineBadge(payload, 'Wygrana', 'Won')).toBe('Wygrana')
    })

    it('zwraca surowy status w trybie "unknown"', () => {
      const payload = shapePayload()
      expect(offPipelineBadge(payload, 'Status spoza znanych typów', 'Recycled')).toBe(
        'Status spoza znanych typów',
      )
    })
  })

  describe('grupaForRodzaj', () => {
    const config = {
      Fotowoltaika: ['Nowy', 'Kalkulacja', 'Umowa', 'Wygrana – montaż', 'Przegrana'],
      'Czyste Powietrze': ['Nowy', 'Wniosek', 'Wygrana', 'Przegrana'],
    }

    it('zwraca grupę statusów dla rozpoznanego rodzaju (trafienie)', () => {
      expect(grupaForRodzaj(config, 'Fotowoltaika')).toEqual([
        'Nowy',
        'Kalkulacja',
        'Umowa',
        'Wygrana – montaż',
        'Przegrana',
      ])
    })

    it('zwraca [] dla rodzaju nieobecnego w configu (nietrafienie)', () => {
      expect(grupaForRodzaj(config, 'Magazyn energii')).toEqual([])
    })

    it.each([[null], [undefined]])(
      'zwraca [] dla config=%p (null-safe względem configu)',
      (badConfig) => {
        expect(grupaForRodzaj(badConfig, 'Fotowoltaika')).toEqual([])
      },
    )

    it.each([[null], [undefined], ['']])(
      'zwraca [] dla rodzaj=%p (null-safe względem rodzaju)',
      (rodzaj) => {
        expect(grupaForRodzaj(config, rodzaj)).toEqual([])
      },
    )
  })

  describe('filterKnown', () => {
    const isKnown = (name) => ['Nowy', 'Kalkulacja', 'Umowa'].includes(name)

    it('filtruje do nazw znanych store\'owi', () => {
      expect(filterKnown(['Nowy', 'Widmo', 'Umowa'], isKnown)).toEqual([
        'Nowy',
        'Umowa',
      ])
    })

    it('zwraca [] gdy żadna nazwa nie jest znana', () => {
      expect(filterKnown(['Widmo1', 'Widmo2'], isKnown)).toEqual([])
    })

    it.each([[null], [undefined], [[]]])(
      'zwraca [] dla names=%p (null-safe)',
      (names) => {
        expect(filterKnown(names, isKnown)).toEqual([])
      },
    )

    it('nie mutuje przekazanej tablicy names', () => {
      const names = ['Nowy', 'Widmo', 'Umowa']
      const kopia = [...names]
      filterKnown(names, isKnown)
      expect(names).toEqual(kopia)
    })
  })

  describe('brak mutacji payloadu', () => {
    it('żadna funkcja nie modyfikuje przekazanego obiektu payload', () => {
      const payload = shapePayload({ off_pipeline: false, off_pipeline_type: null })
      const kopia = JSON.parse(JSON.stringify(payload))

      currentIndexFor(payload.steps, 'Kalkulacja')
      bandMode(payload, 'Kalkulacja', undefined)
      nextStepNote(payload, 'Kalkulacja', undefined)
      offPipelineBadge(payload, 'Kalkulacja', undefined)
      nodeState(1, currentIndexFor(payload.steps, 'Kalkulacja'))
      nodeStateForMode(bandMode(payload, 'Kalkulacja', undefined), 1, 1)
      stepNumber(1)

      expect(payload).toEqual(kopia)
    })
  })
})
