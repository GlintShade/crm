# import frappe
from frappe.contacts.doctype.contact.contact import Contact


class CustomContact(Contact):
	@staticmethod
	def default_list_data():
		# VOLTEO: default Klienci (Contact) list columns — Polish labels, opiekun,
		# date-only "Data dodania". Users can still customize per-user natively.
		columns = [
			{
				"label": "Imię i nazwisko",
				"type": "Data",
				"key": "full_name",
				"width": "17rem",
			},
			{
				"label": "Status",
				"type": "Select",
				"key": "status",
				"width": "10rem",
			},
			{
				"label": "Telefon",
				"type": "Data",
				"key": "mobile_no",
				"width": "11rem",
			},
			{
				"label": "Email",
				"type": "Data",
				"key": "email_id",
				"width": "14rem",
			},
			{
				"label": "Przypisany pracownik",
				"type": "Link",
				"options": "User",
				"key": "custom_opiekun",
				"width": "12rem",
			},
			{
				# Date (not Datetime) → rendered date-only ("tylko data bez godziny").
				"label": "Data dodania",
				"type": "Date",
				"key": "creation",
				"width": "9rem",
			},
		]
		rows = [
			"name",
			"full_name",
			"status",
			"mobile_no",
			"email_id",
			"custom_opiekun",
			"creation",
			"image",
		]
		return {"columns": columns, "rows": rows}
