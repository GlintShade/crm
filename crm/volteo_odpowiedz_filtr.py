# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Czysta (bez frappe) logika filtra odpowiedzi JSON z polami permlevel (ops#372).

Rdzen Frappe filtruje pola permlevel przy odczycie dokumentu, ale wiele
sciezek (`run_doc_method`, REST v2, kazda metoda whitelisted zwracajaca obiekt
dokumentu) serializuje dokument bez filtra. Ten modul daje jedna funkcje
dzialajaca na gotowej, zdekodowanej odpowiedzi: `odfiltruj`.
"""

from collections.abc import Callable, Collection
from typing import Any

PODSTAWA_TRESCI_JSON = "application/json"
ZNACZNIK_DOKUMENTU = b'"doctype"'


def czy_filtrowac(typ_tresci: str | None, tresc: bytes | None) -> bool:
	"""Szybka sciezka: True tylko dla odpowiedzi JSON, w ktorej w ogole wystepuje
	ciag `"doctype"`. Pozostale odpowiedzi nie sa parsowane."""
	if not typ_tresci or not tresc:
		return False
	if not typ_tresci.strip().lower().startswith(PODSTAWA_TRESCI_JSON):
		return False
	return ZNACZNIK_DOKUMENTU in tresc


def odfiltruj(
	struktura: Any,
	tajne_pola: Callable[[str, str | None], Collection[str] | None],
) -> int:
	"""Zeruje (ustawia None) pola, ktorych wywolujacy nie moze czytac, w kazdym
	slowniku z kluczem `doctype` (typu str) znalezionym w `struktura`.

	`tajne_pola(doctype, parenttype)` zwraca nazwy pol do usuniecia albo
	None/pusty zbior. Klucz zostaje w slowniku z wartoscia None (tak jak po
	`apply_fieldlevel_read_permissions()` + `as_dict()`). Wartosci 0, "" i False
	tez sa zerowane: to sa wartosci. Tabele potomne (listy slownikow z wlasnym
	`doctype` i `parenttype`) sa odwiedzane tak samo.

	Swiadomy wyjatek od zasady niemutowalnosci: struktura jest mutowana w
	miejscu, bo odpowiedz bywa duza. Przejscie jest iteracyjne (jawny stos), wiec
	gleboka struktura nie daje RecursionError. Callback jest wolany najwyzej raz
	na pare (doctype, parenttype). Zwraca liczbe wyzerowanych wartosci.
	"""
	pamiec: dict[tuple[str, str | None], Collection[str] | None] = {}
	wyzerowane = 0
	stos: list[Any] = [struktura]
	while stos:
		wezel = stos.pop()
		if isinstance(wezel, dict):
			doctype = wezel.get("doctype")
			if isinstance(doctype, str):
				parenttype = wezel.get("parenttype")
				if not isinstance(parenttype, str):
					parenttype = None
				klucz = (doctype, parenttype)
				if klucz not in pamiec:
					pamiec[klucz] = tajne_pola(doctype, parenttype)
				for pole in pamiec[klucz] or ():
					if pole in wezel and wezel[pole] is not None:
						wezel[pole] = None
						wyzerowane += 1
			stos.extend(v for v in wezel.values() if isinstance(v, (dict, list, tuple)))
		elif isinstance(wezel, (list, tuple)):
			stos.extend(v for v in wezel if isinstance(v, (dict, list, tuple)))
	return wyzerowane
