# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Rdzen (bez Frappe) reguly ops#412: tytul i opis istniejacego zadania
(`CRM Task`) zmienia tylko jego autor (`owner`), administratorzy tez nie maja
wyjatku. Adapter: `crm.fcrm.doctype.crm_task.crm_task.CRMTask.validate`."""

import re

POLA_TRESCI = ("title", "description")
_BIALE = re.compile(r"\s+")


def normalizuj(tekst) -> str:
	"""`None` i pusty tekst sa tym samym; biale znaki na brzegach i ich
	powtorzenia nie licza sie jako zmiana (opis to HTML z edytora)."""
	return _BIALE.sub(" ", str(tekst or "")).strip()


def czy_zmiana_tresci_dozwolona(owner, uzytkownik, przed: dict, po: dict) -> bool:
	"""Autor zmienia co chce; ktokolwiek inny moze zapisac zadanie tylko wtedy,
	gdy tytul i opis (po normalizacji) zostaja takie, jakie byly."""
	if owner and owner == uzytkownik:
		return True
	return all(normalizuj(przed.get(pole)) == normalizuj(po.get(pole)) for pole in POLA_TRESCI)


def wartosci_do_zapisu(owner, uzytkownik, przed: dict, po: dict) -> dict:
	"""Wartosci pol tresci, ktore maja zostac w dokumencie: autor zapisuje swoje,
	ktokolwiek inny dostaje zapisane wczesniej (zmiana samych bialych znakow nie
	moze tworzyc wersji historii)."""
	zrodlo = po if owner and owner == uzytkownik else przed
	return {pole: zrodlo.get(pole) for pole in POLA_TRESCI}
