"""Contact document event handlers and whitelisted Contact API methods."""

import frappe
from frappe import _


def validate(doc, method):
	update_deals_email_mobile_no(doc)


def update_deals_email_mobile_no(doc):
	linked_deals = frappe.get_all(
		"CRM Contacts",
		filters={"contact": doc.name, "is_primary": 1},
		fields=["parent"],
	)

	for linked_deal in linked_deals:
		deal = frappe.db.get_values("CRM Deal", linked_deal.parent, ["email", "mobile_no"], as_dict=True)[0]
		if deal.email != doc.email_id or deal.mobile_no != doc.mobile_no:
			frappe.db.set_value(
				"CRM Deal",
				linked_deal.parent,
				{
					"email": doc.email_id,
					"mobile_no": doc.mobile_no,
				},
			)


@frappe.whitelist()
def get_linked_deals(contact: str):
	"""Get linked deals for a contact"""

	if not frappe.has_permission("Contact", "read", contact):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	deal_names = frappe.get_all(
		"CRM Contacts",
		filters={"contact": contact, "parenttype": "CRM Deal"},
		fields=["parent"],
		distinct=True,
	)

	# get deals data
	deals = []
	for d in deal_names:
		deal = frappe.get_cached_doc(
			"CRM Deal",
			d.parent,
			fields=[
				"name",
				"organization",
				"currency",
				"annual_revenue",
				"status",
				"email",
				"mobile_no",
				"deal_owner",
				"modified",
			],
		)
		deals.append(deal.as_dict())

	return deals


@frappe.whitelist()
def create_new(contact: str, field: str, value: str):
	"""Create new email or phone for a contact"""
	if not frappe.has_permission("Contact", "write", contact):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	contact = frappe.get_cached_doc("Contact", contact)

	if field == "email":
		email = {"email_id": value, "is_primary": 1 if len(contact.email_ids) == 0 else 0}
		contact.append("email_ids", email)
	elif field in ("mobile_no", "phone"):
		mobile_no = {"phone": value, "is_primary_mobile_no": 1 if len(contact.phone_nos) == 0 else 0}
		contact.append("phone_nos", mobile_no)
	else:
		frappe.throw(_("Invalid field"))

	contact.save()
	return True


@frappe.whitelist()
def set_as_primary(contact: str, field: str, value: str):
	"""Set email or phone as primary for a contact"""
	if not frappe.has_permission("Contact", "write", contact):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	contact = frappe.get_doc("Contact", contact)

	if field == "email":
		for email in contact.email_ids:
			if email.email_id == value:
				email.is_primary = 1
			else:
				email.is_primary = 0
	elif field in ("mobile_no", "phone"):
		name = "is_primary_mobile_no" if field == "mobile_no" else "is_primary_phone"
		for phone in contact.phone_nos:
			if phone.phone == value:
				phone.set(name, 1)
			else:
				phone.set(name, 0)
	else:
		frappe.throw(_("Invalid field"))

	contact.save()
	return True


@frappe.whitelist()
def search_emails(txt: str):
	doctype = "Contact"
	meta = frappe.get_meta(doctype)
	filters = [["Contact", "email_id", "is", "set"]]

	if meta.get("fields", {"fieldname": "enabled", "fieldtype": "Check"}):
		filters.append([doctype, "enabled", "=", 1])
	if meta.get("fields", {"fieldname": "disabled", "fieldtype": "Check"}):
		filters.append([doctype, "disabled", "!=", 1])

	or_filters = []
	search_fields = ["full_name", "email_id", "name"]
	if txt:
		for f in search_fields:
			or_filters.append([doctype, f.strip(), "like", f"%{txt}%"])

	results = frappe.get_list(
		doctype,
		filters=filters,
		fields=search_fields,
		or_filters=or_filters,
		limit_start=0,
		limit_page_length=20,
		order_by="email_id, full_name, name",
		ignore_permissions=False,
		as_list=True,
		strict=False,
	)

	return results


def _contact_has_references(contact_name):
	"""Return whether a live metadata scan finds, or cannot rule out, a reference."""
	incomplete_check = False
	link_fields = set()

	if frappe.db.table_exists("DocField"):
		for field in frappe.get_all(
			"DocField",
			filters={"fieldtype": "Link", "options": "Contact"},
			fields=["parent", "fieldname"],
		):
			if field.parent and field.fieldname:
				link_fields.add((field.parent, field.fieldname))
	else:
		incomplete_check = True

	if frappe.db.table_exists("Custom Field"):
		for field in frappe.get_all(
			"Custom Field",
			filters={"fieldtype": "Link", "options": "Contact"},
			fields=["dt", "fieldname"],
		):
			if field.dt and field.fieldname:
				link_fields.add((field.dt, field.fieldname))
	else:
		incomplete_check = True

	for doctype, fieldname in link_fields:
		if not frappe.db.table_exists(doctype):
			continue
		if frappe.get_all(doctype, filters={fieldname: contact_name}, limit=1):
			return True

	if frappe.db.table_exists("Dynamic Link"):
		if frappe.get_all(
			"Dynamic Link",
			filters={"parenttype": "Contact", "parent": contact_name},
			limit=1,
		):
			return True
		if frappe.get_all(
			"Dynamic Link",
			filters={"link_doctype": "Contact", "link_name": contact_name},
			limit=1,
		):
			return True
	else:
		incomplete_check = True

	return incomplete_check


def remove_user_shadow_contact(doc, method=None):
	"""Queue removal of an unreferenced Contact automatically created for a System User.

	This hook runs on ``Contact.after_insert`` rather than ``User.on_update`` because
	Frappe enqueues ``create_contact`` with ``enqueue_after_commit=True`` from
	``User.on_update``. At the time ``User.on_update`` runs, the Contact does not exist
	yet, whereas this hook reacts after the Contact actually exists regardless of what
	created it. The ``user_type == "System User"`` guard is equally deliberate:
	``Website User`` accounts are legitimate customers with portal access and must not
	be treated as shadow contacts merely because ``doc.user`` is set.

	The deletion itself is deferred to a background job -- mirroring exactly how Frappe
	schedules ``create_contact`` -- rather than performed inline here. ``Document.insert()``
	keeps running after ``after_insert`` returns and goes on to call
	``run_post_save_methods()``, which runs ``update_global_search()`` and ``save_version()``.
	If the Contact were deleted inline, those would execute against a row that no longer
	exists and re-insert a ``__global_search`` entry (and a ``Version`` row) pointing at a
	deleted docname -- a ghost contact that still shows up in global search but 404s when
	opened. Only the cheap guards live here, so an ordinary client contact (no ``user`` set)
	costs nothing and never reaches the queue; the expensive reference scan happens in
	``delete_shadow_contact`` instead.
	"""
	if not doc.user:
		return
	if doc.user in ("Administrator", "Guest"):
		return
	if not frappe.db.exists("User", doc.user):
		return
	user_type = frappe.db.get_value("User", doc.user, "user_type")
	if user_type != "System User":
		return

	frappe.enqueue(
		"crm.api.contact.delete_shadow_contact",
		contact=doc.name,
		now=frappe.flags.in_test or frappe.flags.in_install,
		enqueue_after_commit=True,
	)


def delete_shadow_contact(contact):
	"""Delete a shadow Contact created for a System User, re-verifying every guard.

	This is the deferred worker enqueued by ``remove_user_shadow_contact`` -- see that
	function's docstring for why the deletion must be deferred out of the ``insert()``
	transaction rather than run inline inside ``after_insert``.

	Time passes between enqueueing and execution, and the job may even run after a
	retry, so nothing about the original state can be trusted: the Contact may already
	be gone, its ``user`` may have been cleared, the User may have been deleted or had
	its ``user_type`` changed, or a reference to the Contact may have appeared since.
	Every guard is therefore re-run from scratch against current data before deleting.
	"""
	try:
		if not frappe.db.exists("Contact", contact):
			return
		user = frappe.db.get_value("Contact", contact, "user")
		if not user:
			return
		if user in ("Administrator", "Guest"):
			return
		if not frappe.db.exists("User", user):
			return
		user_type = frappe.db.get_value("User", user, "user_type")
		if user_type != "System User":
			return
		if _contact_has_references(contact):
			return
		frappe.delete_doc("Contact", contact, ignore_permissions=True, delete_permanently=True)
	except Exception:
		frappe.log_error(title="Failed to remove user shadow Contact", message=frappe.get_traceback())
