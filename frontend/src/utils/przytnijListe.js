// Zapisana w IndexedDB odpowiedz get_data niesie page_length po wielokrotnym
// "load more" (np. 300). Przy wejsciu na liste wracamy do wybranego rozmiaru
// strony. Kanban ma data jako kolumny (nie wiersze), wiec go nie ruszamy.
export function przytnijZapisanaListe(data) {
  const n = data?.page_length_count
  if (!n || !Array.isArray(data.data) || data.view_type === 'kanban') return data
  if (data.data.length <= n && data.page_length <= n) return data
  return {
    ...data,
    data: data.data.slice(0, n),
    row_count: Math.min(data.row_count ?? n, n),
    page_length: n,
  }
}
