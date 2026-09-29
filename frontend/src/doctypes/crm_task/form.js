export class CRMTask {
  onRender() {
    if (this.doc.reference_doctype && this.doc.reference_docname) {
      let label =
        this.doc.reference_doctype == 'CRM Deal'
          ? __('Open Deal')
          : __('Open Lead')

      this.actions = [
        {
          name: 'Redirect Action',
          label: label,
          onClick: (close) => {
            if (!this.doc.reference_docname) return
            let name =
              this.doc.reference_doctype == 'CRM Deal' ? 'Deal' : 'Lead'
            let params = { leadId: this.doc.reference_docname }
            if (name == 'Deal') {
              params = { dealId: this.doc.reference_docname }
            }
            this.router.push({ name: name, params: params })
            close?.()
          },
        },
      ]
    }
  }
}
