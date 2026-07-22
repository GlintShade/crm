import frappe
from frappe import _
from pypika import Criterion


@frappe.whitelist()
def get_views(doctype: str = ""):
	View = frappe.qb.DocType("CRM View Settings")
	query = (
		frappe.qb.from_(View)
		.select("*")
		.where(Criterion.any([View.user == "", View.user == frappe.session.user]))
	)
	if doctype:
		if not frappe.has_permission(doctype, "read"):
			frappe.throw(_("Brak uprawnień"), frappe.PermissionError)
		query = query.where(View.dt == doctype)
	views = query.run(as_dict=True)
	# Only return views for doctypes the user can read (protects secret-doctype view
	# configs on the global no-doctype call); keep rows with no dt.
	return [v for v in views if not v.get("dt") or frappe.has_permission(v["dt"], "read")]
