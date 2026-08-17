export const standardFieldsMeta = [
  {
    fieldname: 'name',
    label: __('Name'),
    fieldtype: 'Data',
  },
  {
    fieldname: 'creation',
    label: __('Created On'),
    fieldtype: 'Datetime',
  },
  {
    fieldname: 'modified',
    label: __('Last Modified'),
    fieldtype: 'Datetime',
  },
  {
    fieldname: 'modified_by',
    label: __('Modified By'),
    fieldtype: 'Link',
    options: 'User',
  },
  { label: __('Assigned To'), fieldtype: 'Text', fieldname: '_assign' },
  {
    label: __('Owner'),
    fieldtype: 'Link',
    fieldname: 'owner',
    options: 'User',
  },
  { label: __('Like', null, 'field label'), fieldtype: 'Data', fieldname: '_liked_by' },
]

export const noValueFieldTypes = [
  'Section Break',
  'Column Break',
  'Tab Break',
  'Table',
  'Table MultiSelect',
  'Button',
  'Image',
]
