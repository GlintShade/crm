// Motyw odznaki (Badge frappe-ui: gray/blue/green/amber/red/violet) dla
// koloru statusu szansy (CRM Deal Status.color, surowy string zanim
// parseColor() w stores/statuses.js zamieni go na klase !text-*). Frappe-
// free, testowalne bezposrednio przez vitest, ten sam wzorzec co
// dealPipeline.js/etapFiltr.js.
//
// Badge (frappe-ui) obsluguje 6 motywow: gray, blue, green, amber (alias
// "orange"), red, violet - mniej niz paleta kolorow dostepna w polu
// wyboru koloru statusu (patrz ops/crm-pipeline-statusy.py TARGET:
// gray/blue/cyan/purple/orange/violet/teal/yellow/amber/green/red), wiec
// czesc kolorow mapuje sie na najblizszy odpowiednik: cyan/teal -> blue
// (niebiesko-zielone), yellow/orange -> amber (Badge traktuje "orange"
// jako przestarzaly alias "amber" i tak), purple/pink -> violet
// (czerwono-fioletowe), black -> gray. Nieznany/pusty kolor -> gray.

const MAPA_MOTYWOW = {
  gray: 'gray',
  black: 'gray',
  blue: 'blue',
  cyan: 'blue',
  teal: 'blue',
  green: 'green',
  amber: 'amber',
  orange: 'amber',
  yellow: 'amber',
  red: 'red',
  violet: 'violet',
  purple: 'violet',
  pink: 'violet',
}

/**
 * @param {string|null|undefined} kolor - surowy CRM Deal Status.color
 * @returns {'gray'|'blue'|'green'|'amber'|'red'|'violet'}
 */
export function motywDlaKoloru(kolor) {
  if (!kolor) return 'gray'
  return MAPA_MOTYWOW[kolor.toLowerCase()] || 'gray'
}
