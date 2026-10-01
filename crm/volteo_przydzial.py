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

PUŁAPKA naprawiona w QA (orkiestrator, 2026-10-01): `frappe.parse_json`
NIE zwraca gołego stringa bez zmian -- w Frappe 15 to zwykłe
`json.loads(val)` na KAŻDYM stringu, więc `frappe.parse_json("mazowieckie")`
rzuca `JSONDecodeError`. Pierwsza wersja tego modułu (błędnie) zakładała, że
`frappe.parse_json` samo rozpoznaje "czy to JSON" i zostawia zwykły string
bez zmian -- to był błąd, pojedyncza nazwa województwa/powiatu wysłana
przez starsze wywołanie (zgodność wsteczna, np. przyszłe issue "Powiat z
listy wartości" na pasku szybkich filtrów) kończyłaby się HTTP 500 zamiast
normalnego działania. Dlatego dekodowanie JSON-stringa listy
(`'["mazowieckie","slaskie"]'`, kształt, w jakim `LeadyPrzydzial.vue`
wysyła wielokrotny wybór przez `JSON.stringify`) jest teraz wykonywane
TUTAJ, w tym module, przez zwykłe `json.loads`, WYŁĄCZNIE gdy string (po
`strip()`) zaczyna się od `"["` -- dokładnie tak rozpoznaje kształt JSON
listy, bez polegania na żadnym zachowaniu `frappe.parse_json`. Goły string
bez `[` na początku (zwykła nazwa województwa/powiatu) zostaje stringiem
bez zmian. Niepoprawny JSON zaczynający się od `"["` (np. `"[abc"`) rzuca
`ValueError` z czytelnym komunikatem po polsku, zamiast propagować surowy
`json.JSONDecodeError` do wołającego.
"""

from __future__ import annotations

import json


def normalizuj_wartosci_geo(wartosc: str | list | tuple | None) -> list[str]:
	"""Normalizuje wartość parametru geograficznego (województwo/powiat) do
	listy niepustych, przyciętych stringów bez duplikatów, w kolejności
	pierwszego wystąpienia.

	Przyjmuje:
	  - `None` albo pusty/biały string: pusta lista -- front wtedy pokazuje
	    niezawężoną pulę zamiast pustego selecta;
	  - pojedynczy string BEZ `[` na początku (zgodność wsteczna z API
	    sprzed wielokrotnego wyboru) -- zostaje stringiem bez zmian, NIE
	    jest przepuszczany przez `json.loads`;
	  - JSON-string listy (string zaczynający się, po `strip()`, od `"["`,
	    kształt wysyłany przez `LeadyPrzydzial.vue` przez `JSON.stringify`
	    przy wielokrotnym wyborze) -- dekodowany tutaj przez `json.loads`;
	  - już gotową listę/krotkę stringów (wywołanie z Pythona, albo POST z
	    ciałem JSON, gdzie dekodowanie zaszło wcześniej, przed wejściem do
	    tej funkcji).

	Niepoprawny JSON zaczynający się od `"["` (np. `"[abc"`), element listy,
	który nie jest stringiem, albo wejście innego typu niż
	string/lista/krotka/`None`, rzuca `ValueError` z czytelnym komunikatem
	po polsku -- wołający w `crm.api.volteo_leady` łapie to i zamienia na
	`frappe.throw`, żeby front dostał normalny błąd walidacji zamiast
	nieczytelnego 500."""
	if isinstance(wartosc, str):
		tekst = wartosc.strip()
		if tekst.startswith("["):
			try:
				wartosc = json.loads(tekst)
			except json.JSONDecodeError as exc:
				raise ValueError(
					"Niepoprawny JSON listy wartości -- oczekiwano tablicy stringów."
				) from exc
		else:
			wartosc = tekst

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
