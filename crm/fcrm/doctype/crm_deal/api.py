import frappe


@frappe.whitelist()
def get_deal_contacts(name: str):
	frappe.has_permission("CRM Deal", ptype="read", doc=name, throw=True)

	contacts = frappe.get_all(
		"CRM Contacts",
		filters={"parenttype": "CRM Deal", "parent": name},
		fields=["contact", "is_primary"],
		distinct=True,
	)

	contact_names = [row.contact for row in contacts if row.contact]
	if not contact_names:
		return []

	visible_contacts = {
		row.name: row
		for row in frappe.get_list(
			"Contact",
			filters={"name": ["in", contact_names]},
			fields=["name", "full_name", "email_id", "mobile_no", "image"],
		)
	}

	deal_contacts = []
	for row in contacts:
		contact = visible_contacts.get(row.contact)
		if not contact:
			continue

		deal_contacts.append(
			{
				"name": contact.name,
				"image": contact.image,
				"full_name": contact.full_name,
				"email": contact.email_id,
				"mobile_no": contact.mobile_no,
				"is_primary": row.is_primary,
			}
		)
	return deal_contacts
