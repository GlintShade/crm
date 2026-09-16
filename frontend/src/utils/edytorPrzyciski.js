// Polskie etykiety paska narzędzi edytora tekstu (frappe-ui `TextEditor`).
//
// Gdy `fixedMenu`/`bubbleMenu` dostaje `true`, `TextEditorFixedMenu.vue` i
// `TextEditorBubbleMenu.vue` (frappe-ui) same rozwiązują tę wartość na
// wbudowaną, angielską tablicę nazw komend i mapują ją przez
// `createEditorButton()` (frappe-ui/src/components/TextEditor/utils.js) na
// obiekty przycisków z `TextEditor/commands.js` (ikona, akcja, isActive,
// label po angielsku) - patrz frappe-ui/src/components/TextEditor/
// components/TextEditorFixedMenu.vue:14-75 i TextEditorBubbleMenu.vue:27-75.
// `createEditorButton()` samo w sobie (utils.js:3-10) obsługuje trzy
// kształty wejścia: string (lookup w `commands`), tablicę (grupa - rekurencyjny
// map, renderowana jako dropdown w TextEditorMenu.vue), obiekt (zwracany bez
// zmian). Tooltip w TextEditorMenu.vue czyta `button.label || button.text`
// (components/TextEditorMenu.vue:125), więc podmiana samego `label` przy
// zachowaniu `icon`/`action`/`isActive` z oryginału wystarcza.
//
// Bez łatki frappe-ui: budujemy tu WŁASNĄ tablicę tych samych komend (też
// przez `createEditorButton()`, więc te same ikony/akcje) z nadpisanym
// polskim `label`, w dokładnie tej samej kolejności i grupowaniu co domyślne
// tablice frappe-ui, i podajemy ją do `fixedMenu`/`bubbleMenu` zamiast `true`.
//
// FRAPPE-FREE CELOWO: ten moduł NIE importuje `frappe-ui` - `createEditorButton`
// jest wstrzykiwany przez wywołującego (każdy z 9 konsumentów i tak już
// importuje `frappe-ui`). Powód nie jest stylistyczny: `frappe-ui`'s barrel
// (`src/index.ts`) i nawet jego węższe podścieżki (np.
// `TextEditor/utils.js` -> `./commands` -> `~icons/lucide/*`) nie dają się
// rozwiązać pod vitestem tego projektu (SSR-externalizacja node_modules w
// Vitest 4 wymaga jawnych rozszerzeń i realnego pluginu unplugin-icons,
// którego `vitest.config.js` nie ładuje - potwierdzone próbami: import
// samego `frappe-ui` i głębokich podścieżek psuje ładowanie modułu w
// testach, zarówno przez pole "exports" jak i przez zagnieżdżone importy
// bez rozszerzeń). Trzymanie się z dala od tego importu na poziomie modułu
// czyni ten plik w pełni testowalnym bez modyfikowania współdzielonej
// konfiguracji vitest. Por. podobny unik w `src/utils/aktualizacje.js`
// (tam z innego, ale pokrewnego powodu: unplugin-icons przez `@/utils`).

function jestGrupa(wpis) {
  return Array.isArray(wpis) && Array.isArray(wpis[0])
}

// Domyślna tablica stałego paska (frappe-ui TextEditorFixedMenu.vue, gałąź
// else w `fixedMenuButtons`), z polskimi etykietami. 'Separator' zostaje
// jako string - createEditorButton('Separator') zwraca {type: 'separator'},
// więc nie potrzebuje etykiety.
export const SPECYFIKACJA_USTALONA = [
  ['Paragraph', 'Akapit'],
  [
    ['Heading 1', 'Nagłówek 1'],
    ['Heading 2', 'Nagłówek 2'],
    ['Heading 3', 'Nagłówek 3'],
    ['Heading 4', 'Nagłówek 4'],
    ['Heading 5', 'Nagłówek 5'],
    ['Heading 6', 'Nagłówek 6'],
  ],
  'Separator',
  ['Bold', 'Pogrubienie'],
  ['Italic', 'Kursywa'],
  ['Strikethrough', 'Przekreślenie'],
  ['Link', 'Link'],
  ['FontColor', 'Kolor czcionki'],
  'Separator',
  ['Bullet List', 'Lista punktowana'],
  ['Numbered List', 'Lista numerowana'],
  ['Task List', 'Lista zadań'],
  'Separator',
  ['Align Left', 'Wyrównaj do lewej'],
  ['Align Center', 'Wyśrodkuj'],
  ['Align Right', 'Wyrównaj do prawej'],
  'Separator',
  ['Image', 'Obraz'],
  ['Video', 'Wideo'],
  ['Blockquote', 'Cytat'],
  ['Code', 'Kod'],
  ['Iframe', 'Osadzenie'],
  'Separator',
  ['Horizontal Rule', 'Linia pozioma'],
  [
    ['InsertTable', 'Wstaw tabelę'],
    ['AddColumnBefore', 'Dodaj kolumnę przed'],
    ['AddColumnAfter', 'Dodaj kolumnę po'],
    ['DeleteColumn', 'Usuń kolumnę'],
    ['AddRowBefore', 'Dodaj wiersz przed'],
    ['AddRowAfter', 'Dodaj wiersz po'],
    ['DeleteRow', 'Usuń wiersz'],
    ['MergeCells', 'Scal komórki'],
    ['SplitCell', 'Rozdziel komórkę'],
    ['ToggleHeaderColumn', 'Kolumna nagłówkowa'],
    ['ToggleHeaderRow', 'Wiersz nagłówkowy'],
    ['ToggleHeaderCell', 'Komórka nagłówkowa'],
    ['DeleteTable', 'Usuń tabelę'],
  ],
  'Separator',
  ['TableOfContents', 'Spis treści'],
  'Separator',
  ['Undo', 'Cofnij'],
  ['Redo', 'Ponów'],
]

// Domyślna tablica paska pływającego (frappe-ui TextEditorBubbleMenu.vue,
// gałąź else w `bubbleMenuButtons`) - inny podzbiór i inna kolejność niż
// stały pasek (np. FontColor i Link zamienione miejscami, brak Undo/Redo,
// Horizontal Rule, Iframe, TableOfContents, brak nagłówków 1/4/5/6).
export const SPECYFIKACJA_PLYWAJACA = [
  ['Paragraph', 'Akapit'],
  ['Heading 2', 'Nagłówek 2'],
  ['Heading 3', 'Nagłówek 3'],
  'Separator',
  ['Bold', 'Pogrubienie'],
  ['Italic', 'Kursywa'],
  ['Strikethrough', 'Przekreślenie'],
  ['FontColor', 'Kolor czcionki'],
  ['Link', 'Link'],
  'Separator',
  ['Bullet List', 'Lista punktowana'],
  ['Numbered List', 'Lista numerowana'],
  ['Task List', 'Lista zadań'],
  'Separator',
  ['Align Left', 'Wyrównaj do lewej'],
  ['Align Center', 'Wyśrodkuj'],
  ['Align Right', 'Wyrównaj do prawej'],
  'Separator',
  ['Image', 'Obraz'],
  ['Video', 'Wideo'],
  ['Blockquote', 'Cytat'],
  ['Code', 'Kod'],
  [
    ['InsertTable', 'Wstaw tabelę'],
    ['AddColumnBefore', 'Dodaj kolumnę przed'],
    ['AddColumnAfter', 'Dodaj kolumnę po'],
    ['DeleteColumn', 'Usuń kolumnę'],
    ['AddRowBefore', 'Dodaj wiersz przed'],
    ['AddRowAfter', 'Dodaj wiersz po'],
    ['DeleteRow', 'Usuń wiersz'],
    ['MergeCells', 'Scal komórki'],
    ['SplitCell', 'Rozdziel komórkę'],
    ['ToggleHeaderColumn', 'Kolumna nagłówkowa'],
    ['ToggleHeaderRow', 'Wiersz nagłówkowy'],
    ['ToggleHeaderCell', 'Komórka nagłówkowa'],
    ['DeleteTable', 'Usuń tabelę'],
  ],
]

// Klucze komend (bez 'Separator'), spłaszczone przez grupy - do porównania
// z rzeczywistym zestawem komend frappe-ui w teście, i do walidacji kluczy.
export function kluczeZeSpecyfikacji(specyfikacja) {
  const klucze = new Set()
  for (const wpis of specyfikacja) {
    if (wpis === 'Separator') continue
    if (jestGrupa(wpis)) {
      for (const [klucz] of wpis) klucze.add(klucz)
    } else {
      klucze.add(wpis[0])
    }
  }
  return klucze
}

function zbudujPrzycisk(createEditorButton, [klucz, etykieta]) {
  return { ...createEditorButton(klucz), label: __(etykieta) }
}

function zbudujTablice(specyfikacja, createEditorButton) {
  return specyfikacja.map((wpis) => {
    if (wpis === 'Separator') return createEditorButton('Separator')
    if (jestGrupa(wpis)) return wpis.map((para) => zbudujPrzycisk(createEditorButton, para))
    return zbudujPrzycisk(createEditorButton, wpis)
  })
}

// `createEditorButton` przekazuje wywołujący (import { createEditorButton }
// from 'frappe-ui' w komponencie .vue) - patrz uwaga "FRAPPE-FREE CELOWO"
// wyżej. `__()` jest wołane dopiero tutaj, wewnątrz ciała funkcji, więc
// wywołanie tej funkcji z <script setup>/computed konsumenta jest bezpieczne
// także w eager grafie importów (patrz CLAUDE.md → "Eager chunk a __()").
export function przyciskiUstalone(createEditorButton) {
  return zbudujTablice(SPECYFIKACJA_USTALONA, createEditorButton)
}

export function przyciskiPlywajace(createEditorButton) {
  return zbudujTablice(SPECYFIKACJA_PLYWAJACA, createEditorButton)
}

// Słownik klucz komendy -> polska etykieta, zbudowany raz z obu specyfikacji
// powyżej (SPECYFIKACJA_USTALONA jest nadzbiorem SPECYFIKACJA_PLYWAJACA co do
// zestawu komend, ale iterujemy obie na wypadek przyszłej rozbieżności).
// Służy konsumentom, którzy - jak CommentBox.vue i EmailEditor.vue - nie
// chcą pełnej listy `przyciskiUstalone`/`przyciskiPlywajace`, tylko WŁASNY,
// węższy podzbiór/kolejność komend (np. bez Strikethrough/Task List/Undo),
// ale wciąż z polskimi etykietami zamiast angielskiego literału wprost.
const SLOWNIK_ETYKIET = new Map()
for (const specyfikacja of [SPECYFIKACJA_USTALONA, SPECYFIKACJA_PLYWAJACA]) {
  for (const wpis of specyfikacja) {
    if (wpis === 'Separator') continue
    const pary = jestGrupa(wpis) ? wpis : [wpis]
    for (const [klucz, etykieta] of pary) SLOWNIK_ETYKIET.set(klucz, etykieta)
  }
}

function zbudujZeSlownika(createEditorButton, klucz) {
  const etykieta = SLOWNIK_ETYKIET.get(klucz)
  if (!etykieta) {
    // Celowo błąd, nie cichy fallback na angielski literał - zob.
    // konwencja "unknown material is an error" w CLAUDE.md.
    throw new Error(`edytorPrzyciski: brak polskiej etykiety dla komendy "${klucz}"`)
  }
  return { ...createEditorButton(klucz), label: __(etykieta) }
}

// Buduje tablicę przycisków wg WŁASNEJ listy komend konsumenta - własny
// podzbiór i własna kolejność (np. `textEditorMenuButtons` w CommentBox.vue
// i EmailEditor.vue), z polskimi etykietami wziętymi ze wspólnego słownika
// powyżej. `lista` ma inny kształt niż SPECYFIKACJA_*: same stringi komend
// zamiast par [klucz, etykieta] - string komendy, 'Separator', albo tablica
// stringów (grupa/dropdown, np. nagłówki albo podmenu tabeli).
export function przyciskiWedlugListy(lista, createEditorButton) {
  return lista.map((wpis) => {
    if (wpis === 'Separator') return createEditorButton('Separator')
    if (Array.isArray(wpis)) {
      return wpis.map((klucz) => zbudujZeSlownika(createEditorButton, klucz))
    }
    return zbudujZeSlownika(createEditorButton, wpis)
  })
}
