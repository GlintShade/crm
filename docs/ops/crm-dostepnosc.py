# Wzor skryptu ops dla grafiku dostepnosci handlowcow (b82).
#
# Doctypy Volteo powstaja skryptami w repo ops (np. ops/crm-sms-dyzury.py),
# nie w tym repo. Ten plik to gotowa tresc do przeniesienia jako
# ops/crm-dostepnosc.py; dopasuj sposob uruchomienia do reszty skryptow ops.
# Skrypt jest idempotentny: drugi przebieg nic nie zmienia.
#
# Uruchomienie (przyklad):
#   bench --site <site> console < crm-dostepnosc.py
#
# Bez tego doctype kalendarz dziala jak dotad: crm.api.kalendarz.spotkania
# zwraca `dostepnosc: None`, front nie pokazuje cieniowania ani przycisku
# "Grafik".

import frappe

DOCTYPE = "Volteo Dostepnosc"
ROLE_ZAPISU = ("System Manager", "Volteo Core Admin", "Volteo Backend")
DNI = ("Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela")

POLA = [
	{
		"fieldname": "handlowiec",
		"label": "Handlowiec",
		"fieldtype": "Link",
		"options": "User",
		"reqd": 1,
		"in_list_view": 1,
		"in_standard_filter": 1,
		"search_index": 1,
	},
	{
		"fieldname": "dzien_tygodnia",
		"label": "Dzień tygodnia",
		"fieldtype": "Select",
		"options": "\n" + "\n".join(DNI),
		"in_list_view": 1,
		"description": "Stały grafik co tydzień. Puste, gdy wiersz to zmiana na konkretną datę.",
	},
	{
		"fieldname": "data",
		"label": "Data",
		"fieldtype": "Date",
		"in_list_view": 1,
		"in_standard_filter": 1,
		"search_index": 1,
		"description": "Zmiana tylko na ten dzień, zastępuje stały grafik.",
	},
	{
		"fieldname": "wolne",
		"label": "Wolne",
		"fieldtype": "Check",
		"default": "0",
		"in_list_view": 1,
	},
	{
		"fieldname": "od",
		"label": "Od (godz.)",
		"fieldtype": "Int",
		"in_list_view": 1,
		"depends_on": "eval:!doc.wolne",
	},
	{
		"fieldname": "do",
		"label": "Do (godz.)",
		"fieldtype": "Int",
		"in_list_view": 1,
		"depends_on": "eval:!doc.wolne",
	},
	{
		"fieldname": "uwagi",
		"label": "Uwagi",
		"fieldtype": "Small Text",
	},
]


def utworz_doctype():
	if frappe.db.exists("DocType", DOCTYPE):
		print(f"{DOCTYPE}: już istnieje, bez zmian")
		return
	frappe.get_doc(
		{
			"doctype": "DocType",
			"name": DOCTYPE,
			"module": "FCRM",
			"custom": 1,
			"autoname": "hash",
			"track_changes": 1,
			"sort_field": "modified",
			"sort_order": "DESC",
			"fields": POLA,
			"permissions": [
				{"role": rola, "read": 1, "write": 1, "create": 1, "delete": 1} for rola in ROLE_ZAPISU
			],
		}
	).insert()
	frappe.db.commit()
	print(f"{DOCTYPE}: utworzony")


utworz_doctype()
