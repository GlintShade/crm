import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  SPECYFIKACJA_USTALONA,
  SPECYFIKACJA_PLYWAJACA,
  kluczeZeSpecyfikacji,
  przyciskiUstalone,
  przyciskiPlywajace,
} from '@/utils/edytorPrzyciski'

// UWAGA: ten plik celowo NIE importuje niczego z 'frappe-ui' (ani barrela,
// ani żadnej podściezki) - samo `import { createEditorButton } from
// 'frappe-ui'` psuje ładowanie modułu pod vitestem tego projektu (Vitest 4
// SSR-externalizuje node_modules i wymaga jawnych rozszerzeń plików oraz
// realnego pluginu unplugin-icons na komendach z ikonami lucide, którego
// `vitest.config.js` nie ładuje - potwierdzone bezpośrednią próbą importu
// zarówno barrela jak i `frappe-ui/src/components/TextEditor/utils.js`).
// Dlatego `edytorPrzyciski.js` jest frappe-free (createEditorButton
// wstrzykiwany przez konsumenta), a ten test czyta źródła frappe-ui
// WYŁĄCZNIE jako tekst (fs.readFileSync), nigdy jako moduł JS.

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const FRAPPE_UI_TEXT_EDITOR_DIR = path.resolve(
  __dirname,
  '../../node_modules/frappe-ui/src/components/TextEditor',
)

// Czyta domyślną tablicę nazw komend wprost ze źródła frappe-ui (gałąź
// `else` w komputowanej `fixedMenuButtons`/`bubbleMenuButtons`), zamiast
// trzymać własną, zamrożoną kopię - przyszły bump frappe-ui dodający komendę
// do domyślnego paska zmieni ten zestaw i test poczerwienieje.
function domyslneKomendyZeZrodlaFrappeUI(plikVue, znacznikBlokuElse) {
  const sciezka = path.join(FRAPPE_UI_TEXT_EDITOR_DIR, 'components', plikVue)
  const zrodlo = fs.readFileSync(sciezka, 'utf8')
  const idxElse = zrodlo.indexOf(znacznikBlokuElse)
  if (idxElse === -1) {
    throw new Error(
      `Nie znaleziono bloku "${znacznikBlokuElse}" w ${plikVue} - frappe-ui zmienił strukturę pliku, sprawdzić ręcznie.`,
    )
  }
  const idxStart = zrodlo.indexOf('buttons = [', idxElse)
  const idxEnd = zrodlo.indexOf('return buttons.map(createEditorButton)', idxStart)
  if (idxStart === -1 || idxEnd === -1) {
    throw new Error(
      `Nie znaleziono tablicy domyślnych przycisków w ${plikVue} - frappe-ui zmienił strukturę pliku, sprawdzić ręcznie.`,
    )
  }
  const wycinek = zrodlo.slice(idxStart, idxEnd)
  const nazwy = [...wycinek.matchAll(/'([^']+)'/g)].map((dopasowanie) => dopasowanie[1])
  return new Set(nazwy.filter((nazwa) => nazwa !== 'Separator'))
}

// Czyta zbiór realnych kluczy komend z commands.js (obiekty top-level typu
// `Bold: {` lub `'Heading 1': {`), jako tekst - patrz uwaga u góry pliku.
function realneKluczeKomend() {
  const sciezka = path.join(FRAPPE_UI_TEXT_EDITOR_DIR, 'commands.js')
  const zrodlo = fs.readFileSync(sciezka, 'utf8')
  const idxExport = zrodlo.indexOf('export default {')
  const cialo = zrodlo.slice(idxExport)
  const dopasowania = [
    ...cialo.matchAll(/^\s{2}(?:'([^']+)'|([A-Za-z][A-Za-z0-9]*)):\s*\{/gm),
  ]
  return new Set(dopasowania.map((m) => m[1] ?? m[2]))
}

// Prosty fałszywy createEditorButton - dość wierny oryginałowi
// (frappe-ui/src/components/TextEditor/utils.js), żeby przetestować
// zachowanie zbudujTablice/przyciskiUstalone/przyciskiPlywajace bez
// dotykania prawdziwego frappe-ui (patrz uwaga u góry pliku).
function fakeCreateEditorButton(option) {
  if (Array.isArray(option)) return option.map(fakeCreateEditorButton)
  if (typeof option === 'object') return option
  if (option === 'Separator') return { type: 'separator' }
  return { label: option, icon: `icon:${option}`, action: () => option, isActive: () => false }
}

describe('edytorPrzyciski', () => {
  it('SPECYFIKACJA_USTALONA pokrywa dokładnie domyślne komendy stałego paska frappe-ui', () => {
    const oczekiwane = domyslneKomendyZeZrodlaFrappeUI('TextEditorFixedMenu.vue', '} else {')
    const nasze = kluczeZeSpecyfikacji(SPECYFIKACJA_USTALONA)
    expect(nasze).toEqual(oczekiwane)
  })

  it('SPECYFIKACJA_PLYWAJACA pokrywa dokładnie domyślne komendy paska pływającego frappe-ui', () => {
    const oczekiwane = domyslneKomendyZeZrodlaFrappeUI('TextEditorBubbleMenu.vue', '} else {')
    const nasze = kluczeZeSpecyfikacji(SPECYFIKACJA_PLYWAJACA)
    expect(nasze).toEqual(oczekiwane)
  })

  it('każda komenda ze specyfikacji istnieje naprawdę w commands.js frappe-ui (bez literówek w kluczach)', () => {
    const prawdziweKlucze = realneKluczeKomend()
    expect(prawdziweKlucze.size).toBeGreaterThan(20)
    const wszystkieNasze = new Set([
      ...kluczeZeSpecyfikacji(SPECYFIKACJA_USTALONA),
      ...kluczeZeSpecyfikacji(SPECYFIKACJA_PLYWAJACA),
    ])
    for (const klucz of wszystkieNasze) {
      expect(prawdziweKlucze.has(klucz), `komenda "${klucz}" nie istnieje w commands.js frappe-ui`).toBe(true)
    }
  })

  it('przyciskiUstalone() zachowuje kolejność i grupowanie ze specyfikacji', () => {
    const przyciski = przyciskiUstalone(fakeCreateEditorButton)
    expect(przyciski).toHaveLength(SPECYFIKACJA_USTALONA.length)
    // drugi wpis to grupa nagłówków (tablica przycisków), nie pojedynczy przycisk
    expect(Array.isArray(przyciski[1])).toBe(true)
    expect(przyciski[1]).toHaveLength(6)
    expect(przyciski[1][0].label).toBe('Nagłówek 1')
  })

  it('każdy zbudowany przycisk ma polską etykietę, separatory zostają bez zmian', () => {
    const splaszczone = przyciskiUstalone(fakeCreateEditorButton).flatMap((wpis) =>
      Array.isArray(wpis) ? wpis : [wpis],
    )
    const etykietyAngielskie = SPECYFIKACJA_USTALONA
    for (const przycisk of splaszczone) {
      if (przycisk.type === 'separator') continue
      expect(typeof przycisk.label).toBe('string')
      expect(przycisk.label.length).toBeGreaterThan(0)
    }
    // kontrola na krzyż: żadna polska etykieta nie jest po prostu przepisanym
    // angielskim literałem ze specyfikacji (czyli tłumaczenie faktycznie
    // zaszło) - poza 'Link', które po polsku brzmi identycznie z rozmysłem
    const angielskieLiteraly = new Set(
      [...SPECYFIKACJA_USTALONA, ...SPECYFIKACJA_PLYWAJACA]
        .flatMap((wpis) => {
          if (wpis === 'Separator') return []
          if (Array.isArray(wpis) && Array.isArray(wpis[0])) return wpis.map((p) => p[0])
          return [wpis[0]]
        })
        .filter((klucz) => klucz !== 'Link'),
    )
    for (const przycisk of splaszczone) {
      if (przycisk.type === 'separator' || przycisk.label === 'Link') continue
      expect(angielskieLiteraly.has(przycisk.label)).toBe(false)
    }
  })

  it('nadpisuje tylko label, reszta obiektu (icon/action/isActive) zostaje z oryginalnej komendy', () => {
    const przyciski = przyciskiUstalone(fakeCreateEditorButton)
    const bold = przyciski.find((p) => !Array.isArray(p) && p.label === 'Pogrubienie')
    expect(bold).toBeDefined()
    expect(bold.icon).toBe('icon:Bold')
    expect(typeof bold.action).toBe('function')
    expect(typeof bold.isActive).toBe('function')
  })

  it('przyciskiPlywajace() ma inną kolejność Font Color/Link niż stały pasek i bez Undo/Redo', () => {
    const plywajace = przyciskiPlywajace(fakeCreateEditorButton).flatMap((wpis) =>
      Array.isArray(wpis) ? wpis : [wpis],
    )
    const etykiety = plywajace.map((p) => p.label).filter(Boolean)
    expect(etykiety.indexOf('Kolor czcionki')).toBeLessThan(etykiety.indexOf('Link'))
    expect(etykiety).not.toContain('Cofnij')
    expect(etykiety).not.toContain('Ponów')
  })

  it('Separator pozostaje jako {type: "separator"}, bez etykiety', () => {
    const przyciski = przyciskiUstalone(fakeCreateEditorButton)
    const separator = przyciski.find((p) => !Array.isArray(p) && p.type === 'separator')
    expect(separator).toEqual({ type: 'separator' })
  })
})
