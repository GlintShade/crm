// Slowniki statusow i priorytetow zadania (CRM Task), uzywane przez
// TaskModal.vue (issue GlintShade/proenergy-crm-ops#208, "wariant C"
// dedykowanego okna zadania). Lustro crm/fcrm/doctype/crm_task/crm_task.json
// (status: Backlog|Todo|In Progress|Done|Canceled, priority: Low|Medium|
// High) - wartosci to surowy angielski zapisywany do bazy, tlumaczenie
// etykiet przez __(wartosc) dzieje sie wylacznie u wolajacego (te same
// msgid juz istnieja w pl.po: Backlog/Todo/In Progress/Done/Canceled,
// Low/Medium/High), nigdy tutaj.
//
// Frappe-free (bez importu __, frappe-ui ani @/utils) - ten sam wzorzec co
// dataPolska.js/statusColors.js/osdDotacja.js, testowalne bezposrednio
// przez vitest.
//
// Kolor "In Progress" jest zawsze niebieski (blue), nigdy amber/zolty -
// decyzja wlasciciela 2026-09-28 (MEMORY.md "statusy-w-trakcie-niebieskie"):
// statusy "w trakcie" sa zawsze niebieskie w tej aplikacji.
//
// Tailwind JIT skanuje TYLKO literalny tekst zrodel - klasy w mapach nizej
// sa w calosci wypisane literalami (ten sam wzor co COLOR_BUTTON_CLASS_MAP w
// statusColors.js), nigdy budowane w runtime (np. `bg-${kolor}-100`).
// Rodziny rose/emerald/sky/lime NIE istnieja w presecie frappe-ui - uzywane
// sa wylacznie gray/blue/green/red/orange/yellow.

export const STATUSY_ZADANIA = ['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled']

export const PRIORYTETY_ZADANIA = ['Low', 'Medium', 'High']

const DOMYSLNY_KOLOR = 'gray'

const KOLOR_STATUSU = {
  Backlog: 'gray',
  Todo: 'orange',
  'In Progress': 'blue',
  Done: 'green',
  Canceled: 'red',
}

// Priorytet Niski jest niebieski, nie szary (decyzja wlasciciela po
// klik-tescie 2026-09-29) - szary segment w panelu wlasciwosci wygladal
// jak "wylaczony"/nieaktywny, nie jak wybrany priorytet.
const KOLOR_PRIORYTETU = {
  Low: 'blue',
  Medium: 'yellow',
  High: 'red',
}

// Tlo wybranego wiersza/segmentu w panelu wlasciwosci TaskModal.vue.
const TLO_WYBRANEGO = {
  gray: 'bg-gray-100 text-gray-800',
  blue: 'bg-blue-100 text-blue-800',
  green: 'bg-green-100 text-green-800',
  red: 'bg-red-100 text-red-800',
  orange: 'bg-orange-100 text-orange-800',
  yellow: 'bg-yellow-100 text-yellow-800',
}

// Kolor kropki wskaznika (klasa text-*, IndicatorIcon rysuje przez
// currentColor - patrz components/Icons/IndicatorIcon.vue).
const KROPKA_KOLORU = {
  gray: 'text-gray-400',
  blue: 'text-blue-500',
  green: 'text-green-500',
  red: 'text-red-500',
  orange: 'text-orange-500',
  yellow: 'text-yellow-500',
}

/**
 * Nazwa koloru (gray/blue/green/red/orange/yellow) dla surowej wartosci
 * statusu CRM Task. Nieznana wartosc -> szary (bezpieczny fallback, nigdy
 * pusty string).
 * @param {string} status
 * @returns {string}
 */
export function kolorStatusuZadania(status) {
  return KOLOR_STATUSU[status] || DOMYSLNY_KOLOR
}

/**
 * Nazwa koloru (gray/blue/green/red/orange/yellow) dla surowej wartosci
 * priorytetu CRM Task. Nieznana wartosc -> szary.
 * @param {string} priority
 * @returns {string}
 */
export function kolorPriorytetuZadania(priority) {
  return KOLOR_PRIORYTETU[priority] || DOMYSLNY_KOLOR
}

/** Literalne klasy tla dla wybranego wiersza statusu. */
export function tloWybranegoStatusu(status) {
  return TLO_WYBRANEGO[kolorStatusuZadania(status)] || TLO_WYBRANEGO[DOMYSLNY_KOLOR]
}

/** Literalne klasy tla dla wybranego segmentu priorytetu. */
export function tloWybranegoPriorytetu(priority) {
  return TLO_WYBRANEGO[kolorPriorytetuZadania(priority)] || TLO_WYBRANEGO[DOMYSLNY_KOLOR]
}

/** Literalna klasa koloru kropki wskaznika statusu. */
export function kropkaStatusu(status) {
  return KROPKA_KOLORU[kolorStatusuZadania(status)] || KROPKA_KOLORU[DOMYSLNY_KOLOR]
}

/**
 * Lista `name` uzytkownikow CRM dla filtra Link->User "Przypisano do"
 * (ops#208, TaskModal.vue) - ten sam ksztalt filtra co Field.vue buduje dla
 * kazdego pola Link->User. Przyjmuje surowa tablice `crmUsers` (z
 * `users.data?.crmUsers` w usersStore, NIGDY z destrukturyzowanego
 * `computed()` - patrz komentarz w TaskModal.vue przy `przypisanyFiltry` o
 * tym, jak Pinia rozpakowuje computed na instancji store i czemu
 * destrukturyzacja gubi reaktywnosc/.value). Brak listy albo nie-tablica ->
 * pusta lista, nigdy wyjatek.
 * @param {Array<{name: string}>|undefined|null} crmUsers
 * @returns {string[]}
 */
export function nazwyUzytkownikowDoPrzypisania(crmUsers) {
  if (!Array.isArray(crmUsers)) return []
  return crmUsers.map((u) => u.name)
}
