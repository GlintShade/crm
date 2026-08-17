// NOTE: this must stay a function, not a module-level constant. `stores/meta.js` (via
// `utils/index.js` <- `stores/session.js` <- `router.js` <- `main.js`) sits in the EAGER
// entry chunk, which is statically imported and evaluated before `main.js` reaches
// `app.use(translationPlugin)` (the line that assigns `window.__`). A top-level `__()` call
// here throws `ReferenceError: __ is not defined` and crashes the whole bundle on load.
// Building the array inside a function defers every `__()` call to when a caller (always a
// component setup/computed, always post-mount) actually invokes it — which also means the
// labels pick up `translatedMessages` (set in App.vue's setup) instead of freezing in
// English at module-eval time.
export function getStandardFieldsMeta() {
  return [
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
}

export const noValueFieldTypes = [
  'Section Break',
  'Column Break',
  'Tab Break',
  'Table',
  'Table MultiSelect',
  'Button',
  'Image',
]
