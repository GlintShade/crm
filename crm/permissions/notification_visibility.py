# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Widocznosc dzwoneczka `CRM Notification` tylko dla adresata (ops#375).

Wczesniej DocPerm roli `Sales User` pozwalal kazdemu handlowcowi czytac przez
`frappe.client.get_list` cudze powiadomienia razem z trescia. Ten modul zawęza
liste (permission_query_conditions) i pojedyncze dokumenty (has_permission) do
wierszy, w ktorych `to_user` to biezacy uzytkownik.

Wyjatki: tylko `Administrator` i rola `System Manager`. Backoffice
(`Volteo Backend`) celowo NIE jest wyjatkiem. Logika decyzji siedzi w
`crm.volteo_powiadomienia_widocznosc` (bez frappe, z testami).

Hak `has_permission` zwraca wylacznie `False` albo `None`, nigdy `True`:
pierwszy wynik jest ostateczny, wiec `True` nadawaloby uprawnienia ponad DocPerm.
Sciezki serwerowe z `ignore_permissions=True`, `frappe.get_all` i
`frappe.db.*` nie podlegaja temu hakowi.
"""

import frappe

from crm.volteo_powiadomienia_widocznosc import czy_widzi_wszystkie, decyzja_dokumentu


def get_notification_permission_query_conditions(user=None, doctype=None) -> str:
	user = user or frappe.session.user

	if czy_widzi_wszystkie(user, frappe.get_roles(user)):
		return ""

	Notification = frappe.qb.DocType("CRM Notification")
	sql = (Notification.to_user == user).get_sql(quote_char="`", secondary_quote_char="'")

	# Fail closed: znak procenta w SQL rozbilby formatowanie zapytania.
	if "%" in sql:
		frappe.throw("Niedozwolony znak w warunku widocznosci powiadomien.", frappe.PermissionError)

	return f"({sql})"


def has_notification_permission(doc, ptype="read", user=None, debug=False):
	user = user or frappe.session.user

	if isinstance(doc, dict):
		nazwa, to_user = doc.get("name"), doc.get("to_user")
	else:
		nazwa, to_user = getattr(doc, "name", None), getattr(doc, "to_user", None)

	return decyzja_dokumentu(user, frappe.get_roles(user), ptype, nazwa, to_user)
