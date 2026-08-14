// Pure helpers for per-element audit verification state in AudytTab.vue.
//
// Frappe-free by design: the audit stores a sparse JSON map, while this module
// derives visible elements and progress without importing Vue or app runtime.

export const FIELD_PREFIX = 'pole:'
export const PHOTO_PREFIX = 'foto:'

export function fieldKey(fieldname) {
  return FIELD_PREFIX + fieldname
}

export function photoKey(slotKey) {
  return PHOTO_PREFIX + slotKey
}

function isPlainObject(value) {
  if (value === null || typeof value !== 'object') return false
  const prototype = Object.getPrototypeOf(value)
  return prototype === Object.prototype || prototype === null
}

function parsedMap(raw) {
  if (raw === null || raw === undefined || raw === '') return {}
  if (typeof raw === 'string') {
    try {
      raw = JSON.parse(raw)
      if (typeof raw === 'string') raw = JSON.parse(raw)
    } catch (e) {
      return {}
    }
  }
  return isPlainObject(raw) ? raw : {}
}

/** Parse and validate the sparse weryfikacja_json map. */
export function parseWeryfikacja(raw) {
  const source = parsedMap(raw)
  const result = {}
  Object.entries(source).forEach(([key, entry]) => {
    if (!isPlainObject(entry)) return
    if (entry.status !== 'accepted' && entry.status !== 'error') return
    result[key] = entry
  })
  return result
}

/** Mirror AudytTab's dependency rule: no dependency means visible. */
export function depOk(item, values) {
  const dep = item?.depends_on
  if (!dep) return true
  return values?.[dep.fieldname] === dep.value
}

/** Flatten visible matrix fields followed by visible photo slots. */
export function visibleElements(variantDef, values) {
  if (variantDef === null || variantDef === undefined) return []

  const elements = []
  ;(variantDef.sections || []).forEach((section) => {
    ;(section?.fields || []).filter((field) => depOk(field, values)).forEach((field) => {
      elements.push({
        key: fieldKey(field.fieldname),
        kind: 'field',
        label: field.label,
        fieldname: field.fieldname,
      })
    })
  })
  ;(variantDef.photo_slots || [])
    .filter((slot) => depOk(slot, values))
    .forEach((slot) => {
      elements.push({
        key: photoKey(slot.key),
        kind: 'photo',
        label: slot.label,
        slotKey: slot.key,
      })
    })
  return elements
}

export function verdictFor(map, key) {
  const entry = map?.[key]
  if (!isPlainObject(entry) || (entry.status !== 'accepted' && entry.status !== 'error')) {
    return { status: 'waiting' }
  }
  return entry
}

export function aggregate(map, elements) {
  const list = Array.isArray(elements) ? elements : []
  let accepted = 0
  let errors = 0
  list.forEach((element) => {
    const status = verdictFor(map, element.key).status
    if (status === 'accepted') accepted += 1
    if (status === 'error') errors += 1
  })
  const total = list.length
  return {
    accepted,
    errors,
    waiting: total - accepted - errors,
    total,
    allAccepted: total > 0 && accepted === total,
  }
}

export const VERDICT_META = {
  waiting: { theme: 'blue', label: 'Oczekuje', ring: 'ring-outline-blue-2' },
  accepted: { theme: 'green', label: 'Zaakceptowano', ring: 'ring-outline-green-2' },
  error: { theme: 'red', label: 'Błąd', ring: 'ring-outline-red-3' },
}
