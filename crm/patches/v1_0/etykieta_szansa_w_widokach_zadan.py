import json

import frappe

KLUCZ_KOLUMNY = "reference_docname"
NOWA_ETYKIETA = "Szansa"
# Etykiety, ktore kolumna dostala automatycznie (angielski msgid i jego polskie
# tlumaczenie). Kazda inna etykieta to reczna zmiana uzytkownika i zostaje.
STARE_ETYKIETY = ("Reference Doc", "Powiązany dokument")


def _napraw_kolumny(kolumny):
	"""Zwraca (nowe_kolumny, zmieniono): etykieta kolumny `reference_docname`
	zmieniona na "Szansa", tylko gdy jest jedna ze STARE_ETYKIETY. Nie mutuje
	wejscia."""
	if not isinstance(kolumny, list):
		return kolumny, False

	zmieniono = False
	nowe = []
	for kolumna in kolumny:
		if (
			isinstance(kolumna, dict)
			and kolumna.get("key") == KLUCZ_KOLUMNY
			and kolumna.get("label") in STARE_ETYKIETY
		):
			kolumna = {**kolumna, "label": NOWA_ETYKIETA}
			zmieniono = True
		nowe.append(kolumna)
	return nowe, zmieniono


def _wczytaj(tekst):
	if not tekst:
		return None
	try:
		return json.loads(tekst)
	except (TypeError, ValueError):
		return None


def execute():
	# Etykieta pola `reference_docname` zadania zmieniona na "Szansa" (2026-11-16):
	# zapisane widoki listy trzymaja etykiete sprzed zmiany, wiec poprawiamy tylko
	# te, ktore maja dawna etykiete automatyczna.
	widoki = frappe.get_all("CRM View Settings", filters={"dt": "CRM Task"}, fields=["name", "columns"])
	for widok in widoki:
		kolumny = _wczytaj(widok.get("columns"))
		if kolumny is None:
			continue
		nowe, zmieniono = _napraw_kolumny(kolumny)
		if zmieniono:
			frappe.db.set_value(
				"CRM View Settings", widok["name"], "columns", json.dumps(nowe), update_modified=False
			)
