import {
  bandMode,
  nodeState,
  nodeStateForMode,
  stepNumber,
  nextStepNote,
  offPipelineBadge,
} from '@/utils/dealPipeline'

const stepsPvMe = [
  { status: 'Nowy', index: 0 },
  { status: 'Kalkulacja', index: 1 },
  { status: 'Umowa', index: 2 },
]

function progressPayload(overrides = {}) {
  return {
    rodzaj: 'Fotowoltaika + Magazyn',
    status: 'Kalkulacja',
    steps: stepsPvMe,
    current_index: 1,
    off_pipeline: false,
    off_pipeline_type: null,
    note: 'Uzupełnij dane techniczne',
    ...overrides,
  }
}

describe('Pipeline dealu — logika węzłów paska etapów (dealPipeline)', () => {
  describe('bandMode — hidden', () => {
    it.each([
      [null, 'brak payloadu'],
      [undefined, 'undefined zamiast payloadu'],
      [{ ...progressPayload(), steps: [] }, 'puste steps'],
      [{ ...progressPayload(), steps: undefined }, 'brak pola steps'],
      [{ status: 'Nowy' }, 'payload bez steps w ogóle'],
    ])('zwraca "hidden" dla: %s (%s)', (payload) => {
      expect(bandMode(payload)).toBe('hidden')
    })
  })

  describe('bandMode — progress / won / lost / unknown', () => {
    it('zwraca "progress" dla dealu wewnątrz pipeline\'u', () => {
      expect(bandMode(progressPayload())).toBe('progress')
    })

    it('zwraca "lost" gdy off_pipeline=true i off_pipeline_type="Lost"', () => {
      const payload = progressPayload({
        off_pipeline: true,
        off_pipeline_type: 'Lost',
        status: 'Utracona',
      })
      expect(bandMode(payload)).toBe('lost')
    })

    it('zwraca "won" gdy off_pipeline=true i off_pipeline_type="Won"', () => {
      const payload = progressPayload({
        off_pipeline: true,
        off_pipeline_type: 'Won',
        status: 'Wygrana',
      })
      expect(bandMode(payload)).toBe('won')
    })

    it.each([[null], [undefined], ['CośInnego'], [''], ['Recycled']])(
      'zwraca "unknown" gdy off_pipeline=true i off_pipeline_type=%p (obcy status)',
      (offPipelineType) => {
        const payload = progressPayload({
          off_pipeline: true,
          off_pipeline_type: offPipelineType,
          status: 'Jakiś obcy status',
        })
        expect(bandMode(payload)).toBe('unknown')
      },
    )
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
    it('zwraca notatkę w trybie progress', () => {
      expect(nextStepNote(progressPayload({ note: 'Uzupełnij dane techniczne' }))).toBe(
        'Uzupełnij dane techniczne',
      )
    })

    it.each([[''], ['   '], [undefined], [null]])(
      'zwraca null dla pustej/białoznakowej/brakującej notatki (%p) w trybie progress',
      (note) => {
        expect(nextStepNote(progressPayload({ note }))).toBeNull()
      },
    )

    it('zwraca null w trybie "lost" nawet gdy note jest ustawione', () => {
      const payload = progressPayload({
        off_pipeline: true,
        off_pipeline_type: 'Lost',
        status: 'Utracona',
        note: 'Ta notatka nie powinna się pokazać',
      })
      expect(nextStepNote(payload)).toBeNull()
    })

    it('zwraca null w trybie "won" nawet gdy note jest ustawione', () => {
      const payload = progressPayload({
        off_pipeline: true,
        off_pipeline_type: 'Won',
        status: 'Wygrana',
        note: 'Ta notatka nie powinna się pokazać',
      })
      expect(nextStepNote(payload)).toBeNull()
    })

    it('zwraca null w trybie "unknown" nawet gdy note jest ustawione', () => {
      const payload = progressPayload({
        off_pipeline: true,
        off_pipeline_type: 'Recycled',
        status: 'Obcy status',
        note: 'Ta notatka nie powinna się pokazać',
      })
      expect(nextStepNote(payload)).toBeNull()
    })

    it('zwraca null w trybie "hidden" (brak payloadu)', () => {
      expect(nextStepNote(null)).toBeNull()
      expect(nextStepNote({ steps: [] })).toBeNull()
    })
  })

  describe('offPipelineBadge', () => {
    it('zwraca null w trybie "progress"', () => {
      expect(offPipelineBadge(progressPayload())).toBeNull()
    })

    it('zwraca null w trybie "hidden"', () => {
      expect(offPipelineBadge(null)).toBeNull()
      expect(offPipelineBadge({ steps: [] })).toBeNull()
    })

    it('zwraca surowy status w trybie "lost"', () => {
      const payload = progressPayload({
        off_pipeline: true,
        off_pipeline_type: 'Lost',
        status: 'Utracona — cena',
      })
      expect(offPipelineBadge(payload)).toBe('Utracona — cena')
    })

    it('zwraca surowy status w trybie "won"', () => {
      const payload = progressPayload({
        off_pipeline: true,
        off_pipeline_type: 'Won',
        status: 'Wygrana',
      })
      expect(offPipelineBadge(payload)).toBe('Wygrana')
    })

    it('zwraca surowy status w trybie "unknown"', () => {
      const payload = progressPayload({
        off_pipeline: true,
        off_pipeline_type: 'Recycled',
        status: 'Status spoza znanych typów',
      })
      expect(offPipelineBadge(payload)).toBe('Status spoza znanych typów')
    })
  })

  describe('brak mutacji payloadu', () => {
    it('żadna funkcja nie modyfikuje przekazanego obiektu payload', () => {
      const payload = progressPayload()
      const kopia = JSON.parse(JSON.stringify(payload))

      bandMode(payload)
      nextStepNote(payload)
      offPipelineBadge(payload)
      nodeState(1, payload.current_index)
      nodeStateForMode(bandMode(payload), 1, payload.current_index)
      stepNumber(1)

      expect(payload).toEqual(kopia)
    })
  })
})
