// Uwaga 71: handlowiec (Volteo D2D Sales bez rol uprzywilejowanych) nie zmienia
// statusu CC leada. Czysta funkcja, wzorem serwerowego
// crm/volteo_leady_status.py::czy_moze_zmienic_status_cc (ta sama regula).
const ROLE_ZMIANY_STATUSU_CC = [
  'Volteo Call Center',
  'Volteo Backend',
  'Volteo Core Admin',
  'System Manager',
]

export function mozeZmieniacStatusCC(roles, isAdminUser = false) {
  if (isAdminUser) return true
  const lista = roles || []
  if (lista.some((r) => ROLE_ZMIANY_STATUSU_CC.includes(r))) return true
  return !lista.includes('Volteo D2D Sales')
}

// Zwraca NOWE sekcje, w ktorych pole `status` jest read_only. Nie mutuje
// wejscia (zasob sections jest wspoldzielony miedzy instancjami panelu).
export function sekcjeZeStatusemTylkoDoOdczytu(sections) {
  if (!sections?.length) return sections
  return sections.map((section) => {
    if (!section.columns?.length) return section
    return {
      ...section,
      columns: section.columns.map((column) => ({
        ...column,
        fields: (column.fields || []).map((field) =>
          field.fieldname === 'status' ? { ...field, read_only: 1 } : field,
        ),
      })),
    }
  })
}
