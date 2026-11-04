// Lista leadow w oknie "Nowe spotkanie" (b84, ops#332). Czyste funkcje bez
// Vue i frappe-ui; filtr wlasciciela i "tylko z Facebooka" liczy serwer
// (crm.api.kalendarz.leady_do_spotkania), tu tylko opcje listy i spojnosc
// wybranego leada po zmianie handlowca.

// Opcje Autocomplete z wierszy endpointu. Wybrany lead, ktorego nie ma w
// biezacym wyniku (inne wyszukiwanie), zostaje na gorze listy, zeby pole
// nadal pokazywalo jego nazwe, a nie identyfikator.
export function opcjeLeadow(wiersze, wybrany = null) {
  const opcje = (Array.isArray(wiersze) ? wiersze : [])
    .filter((w) => w && w.name)
    .map((w) => ({
      label: w.lead_name || w.name,
      value: w.name,
      description: [w.mobile_no, w.lead_name ? w.name : '']
        .filter(Boolean)
        .join(' · '),
      lead_owner: w.lead_owner || '',
    }))
  if (wybrany?.value && !opcje.some((o) => o.value === wybrany.value)) {
    return [wybrany, ...opcje]
  }
  return opcje
}

// Czy lead z wlascicielem `wlasciciel` moze zostac wybrany dla handlowca
// `handlowiec`: pusty wlasciciel albo ten sam handlowiec; brak handlowca
// ("Bez zmiany handlowca") dopuszcza kazdego leada.
export function leadDozwolony(wlasciciel, handlowiec) {
  if (!handlowiec) return true
  return !wlasciciel || wlasciciel === handlowiec
}
