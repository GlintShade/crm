import json

import frappe

from crm.volteo_panel_boczny import plan_sekcji_utraty


def add_or_remove_lost_reason_section_in_sidepanel(doc):
	doctype = doc.doctype
	if doctype not in ("CRM Deal", "CRM Lead"):
		return

	status_doctype = "CRM Deal Status" if doctype == "CRM Deal" else "CRM Lead Status"

	status = None
	if getattr(doc, "status", None):
		status = frappe.db.get_value(status_doctype, doc.status, "type")
	is_lost = status and status == "Lost"

	layout_doc = frappe.get_doc("CRM Fields Layout", f"{doctype}-Side Panel")
	sections = json.loads(layout_doc.layout)

	# ops#326: gdy uklad ma wlasna sekcje z lost_reason/lost_notes, upstream nie
	# doklada drugiej karty "Lost Reason" (logika w crm/volteo_panel_boczny.py).
	nowe_sekcje = plan_sekcji_utraty(sections, bool(is_lost))
	if nowe_sekcje is not None:
		layout_doc.layout = json.dumps(nowe_sekcje)
		layout_doc.save(ignore_permissions=True)
