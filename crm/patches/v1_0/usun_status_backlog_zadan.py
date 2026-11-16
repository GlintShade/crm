import json

import frappe


def _napraw_filtry(filtry):
	"""Zwraca (nowe_filtry, zmieniono). Obsluguje status == "Backlog" oraz [operator, [lista]]."""
	if not isinstance(filtry, dict) or "status" not in filtry:
		return filtry, False

	wartosc = filtry["status"]
	nowe = dict(filtry)

	if wartosc == "Backlog":
		nowe["status"] = "Todo"
		return nowe, True

	if (
		isinstance(wartosc, (list, tuple))
		and len(wartosc) == 2
		and isinstance(wartosc[1], (list, tuple))
		and "Backlog" in wartosc[1]
	):
		lista = [x for x in wartosc[1] if x != "Backlog"]
		if lista:
			nowe["status"] = [wartosc[0], lista]
		else:
			del nowe["status"]
		return nowe, True

	return filtry, False


def _napraw_kolumny_kanbana(kolumny):
	if not isinstance(kolumny, list):
		return kolumny, False
	nowe = [k for k in kolumny if not (isinstance(k, dict) and k.get("name") == "Backlog")]
	return nowe, len(nowe) != len(kolumny)


def _wczytaj(tekst):
	if not tekst:
		return None
	try:
		return json.loads(tekst)
	except (TypeError, ValueError):
		return None


def execute():
	# Status "Backlog" usuniety z zadan 2026-11-16: istniejace zadania i zapisane widoki przechodza na "Todo".
	frappe.db.sql("update `tabCRM Task` set status='Todo' where status='Backlog'")

	widoki = frappe.get_all(
		"CRM View Settings",
		filters={"dt": "CRM Task"},
		fields=["name", "filters", "kanban_columns"],
	)
	for widok in widoki:
		zmiany = {}

		filtry = _wczytaj(widok.get("filters"))
		if filtry is not None:
			nowe, zmieniono = _napraw_filtry(filtry)
			if zmieniono:
				zmiany["filters"] = json.dumps(nowe)

		kolumny = _wczytaj(widok.get("kanban_columns"))
		if kolumny is not None:
			nowe, zmieniono = _napraw_kolumny_kanbana(kolumny)
			if zmieniono:
				zmiany["kanban_columns"] = json.dumps(nowe)

		if zmiany:
			frappe.db.set_value("CRM View Settings", widok["name"], zmiany, update_modified=False)
