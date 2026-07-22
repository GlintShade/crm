import frappe
from frappe import _
from pypika import Criterion


@frappe.whitelist()
def get_views(doctype: str):
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	View = frappe.qb.DocType("CRM View Settings")
	query = (
		frappe.qb.from_(View)
		.select("*")
		.where(Criterion.any([View.user == "", View.user == frappe.session.user]))
	)
	if doctype:
		query = query.where(View.dt == doctype)
	views = query.run(as_dict=True)
	return views
