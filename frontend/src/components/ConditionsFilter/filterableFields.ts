import { createResource } from 'frappe-ui'

// Ten zasob obsluguje WYLACZNIE ConditionsFilter (reguly przypisan, SLA) —
// `scope: 'conditions'` w `makeParams` wymusza pelna liste pol niezaleznie od
// tego, co przekaze wywolujacy, zeby CRM Deal (allowlista sortowania/filtrow
// listy, ops#81) nie zdegradowal tych ustawien do 14 pol widoku listy.
export const filterableFields = createResource({
  url: 'crm.api.doc.get_filterable_fields',
  makeParams: (params) => ({ ...params, scope: 'conditions' }),
  transform: (data) => {
    data = data
      .filter((field) => !field.fieldname.startsWith('_'))
      .map((field) => {
        return {
          label: field.label,
          value: field.fieldname,
          ...field,
        }
      })
    return data
  },
})
