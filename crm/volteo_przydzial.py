# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Normalizacja wartości geograficznych przy przydziale leadów (issue #216)
=========================================================================

Czysta (frappe-free) logika stojąca za `crm.api.volteo_leady.powiaty` i
`crm.api.volteo_leady.przydziel`: panel „Przydział leadów"
(`LeadyPrzydzial.vue`) od issue #216 może przydzielać leady z wielu
województw i powiatów naraz, zachowując zgodność wsteczną z pojedynczym
stringiem sprzed tej zmiany (`przydziel_cc` korzysta z tej samej listy
wartości, ale buduje z niej filtr `["in", [...]]` dla `frappe.get_list`
wprost w `crm/api/volteo_leady.py`, nie przez ten moduł -- patrz jej
docstring).

Ten moduł NIE importuje `frappe` (patrz `CLAUDE.md`/`WORKSHOP.md`: frappe
nie jest zainstalowane lokalnie, `pytest` nie działa dla przypiętego
Pythona 3.14 -- jedynym lokalnym gate dla kodu importującego frappe jest
składnia, `ruff`/`py_compile`). Ten moduł dostaje więc realny `unittest`
zamiast tego, patrz `crm/test_volteo_przydzial.py`.

Dekodowanie ewentualnego JSON-stringa listy (`'["mazowieckie","slaskie"]'`,
kształt, w jakim `LeadyPrzydzial.vue` wysyła wielokrotny wybór przez
`JSON.stringify`) robi `frappe.parse_json` W WOŁAJĄCYM
(`crm.api.volteo_leady._normalizuj_liste_lub_string`), PRZED wywołaniem
funkcji poniżej -- ten moduł dostaje już zdekodowaną wartość (string,
lista/krotka, albo `None`) i zajmuje się wyłącznie jej normalizacją do
kształtu używanego dalej w zapytaniu SQL (`IN %(...)s`) albo w filtrze
`frappe.get_list` (`["in", [...]]`).
"""

from __future__ import annotations


def normalizuj_wartosci_geo(wartosc: str | list | tuple | None) -> list[str]:
	"""Normalizuje JUŻ zdekodowaną wartość parametru geograficznego
	(województwo/powiat) do listy niepustych, przyciętych stringów bez
	duplikatów, w kolejności pierwszego wystąpienia.

	Przyjmuje:
	  - `None` albo pusty string: pusta lista -- front wtedy pokazuje
	    niezawężoną pulę zamiast pustego selecta;
	  - pojedynczy string (zgodność wsteczna z API sprzed wielokrotnego
	    wyboru);
	  - listę/krotkę stringów (wielokrotny wybór, issue #216).

	Element listy, który nie jest stringiem, albo wejście innego typu niż
	string/lista/krotka/`None`, rzuca `ValueError` z czytelnym komunikatem
	po polsku -- wołający w `crm.api.volteo_leady` łapie to i zamienia na
	`frappe.throw`, żeby front dostał normalny błąd walidacji zamiast
	nieczytelnego 500."""
	if not wartosc:
		return []

	if isinstance(wartosc, str):
		elementy = [wartosc]
	elif isinstance(wartosc, (list, tuple)):
		elementy = list(wartosc)
	else:
		raise ValueError("Nieprawidłowa wartość -- oczekiwano stringa albo listy stringów.")

	if not all(isinstance(el, str) for el in elementy):
		raise ValueError("Lista musi zawierać wyłącznie stringi.")

	wynik: list[str] = []
	widziane: set[str] = set()
	for el in elementy:
		el = el.strip()
		if el and el not in widziane:
			widziane.add(el)
			wynik.append(el)
	return wynik
