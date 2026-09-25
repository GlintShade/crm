# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Czysta logika automatycznych zadan `CRM Task` po przeslaniu audytu do weryfikacji (ops#192).

Moduł celowo nie importuje ``frappe`` na poziomie modułu, wzorem
``crm/volteo_aktywnosc.py`` i ``crm/volteo_pipeline.py``: to jedyny sposob, zeby
dało się go przetestowac lokalnie (``frappe`` nie jest instalowalne na tej maszynie).
Zero funkcji w tym pliku dotyka Frappe, warstwe frappe-owa (odczyt reguly
`Volteo Automatyzacja`, deduplikacja przez `frappe.get_all`, wstawienie
`CRM Task`) niesie `crm.api.pipeline.dispatch_task`.

Uwaga na dwa miejsca naraz: `ops/crm-audyt.py::SUBMIT_SCRIPT` to Server Script
(nie moze importowac) obslugujacy sciezke OZE i niesie BAJT W BAJT ten sam
tytul/opis/tekst sladu co ten modul, zeby handlowiec dostawal identycznie
sformulowane zadanie niezaleznie od tego, ktory audyt (OZE czy CP) je wygenerowal.
Przy kazdej zmianie tytulu, opisu albo tekstu sladu zaktualizuj OBA miejsca:
ten modul i `SUBMIT_SCRIPT` w ops.

Wszystkie funkcje sa immutable: zwracaja nowe struktury, nigdy nie mutuja
argumentow wejsciowych.
"""

from datetime import date, timedelta

RODZAJE: tuple[str, ...] = ("oze", "cp")
"""Dwa rodzaje audytu obslugiwane przez ten modul: OZE (Server Script po stronie
ops) i CP (ten modul, wolany z `crm.api.audyt_cp.volteo_audyt_cp_submit`)."""

ETYKIETA_RODZAJU: dict[str, str] = {"oze": "OZE", "cp": "CP"}
"""Etykieta rodzaju audytu do tytulu/opisu zadania."""

KLUCZ_REGULY: dict[str, str] = {
	"oze": "zadanie_audyt_przeslany",
	"cp": "zadanie_audyt_cp_przeslany",
}
"""Klucz wiersza `Volteo Automatyzacja` (typ „Zadanie”) dla kazdego rodzaju audytu."""

STATUSY_ZAMKNIETE: tuple[str, ...] = ("Done", "Canceled")
"""Statusy `CRM Task`, ktore NIE licza sie jako otwarte zadanie do deduplikacji:
ponowne przeslanie audytu, gdy stare zadanie jest juz Done/Canceled, tworzy nowe."""


def tytul_zadania(rodzaj: str, klient: str) -> str:
	"""Tytul zadania: „Zweryfikuj audyt OZE: {klient}” albo „Zweryfikuj audyt CP: {klient}”.

	Nieznany `rodzaj` daje `ValueError`.
	"""
	if rodzaj not in ETYKIETA_RODZAJU:
		raise ValueError(f"Nieznany rodzaj audytu: {rodzaj!r}")
	return f"Zweryfikuj audyt {ETYKIETA_RODZAJU[rodzaj]}: {klient}"


def opis_zadania_html(rodzaj: str, klient: str, deal: str, autor: str) -> str:
	"""Opis zadania (HTML, pole Text Editor): jedno zdanie po polsku, informujace kto,
	co i dla ktorej szansy przeslal do weryfikacji.

	Nieznany `rodzaj` daje `ValueError`.
	"""
	if rodzaj not in ETYKIETA_RODZAJU:
		raise ValueError(f"Nieznany rodzaj audytu: {rodzaj!r}")
	etykieta = ETYKIETA_RODZAJU[rodzaj]
	return (
		f"<p>Audyt {etykieta} szansy <b>{deal}</b> (klient: <b>{klient}</b>) "
		f"został przesłany do weryfikacji przez {autor}.</p>"
	)


def oblicz_termin(dzisiaj: date, termin_dni: int) -> date | None:
	"""Data terminu zadania: `dzisiaj + termin_dni` dni, albo `None`, gdy `termin_dni`
	jest 0 (albo ujemne), czyli "brak terminu".

	`termin_dni` moze przyjsc jako string (tak, jak wraca z `frappe.db.get_value` na
	polu Int gdy typ nie jest jeszcze znormalizowany) albo `None`: oba parsowane przez
	`int()`, z fallbackiem na 0, gdy parsowanie sie nie uda.
	"""
	try:
		dni = int(termin_dni)
	except (TypeError, ValueError):
		dni = 0
	if dni <= 0:
		return None
	return dzisiaj + timedelta(days=dni)


def filtr_duplikatu(deal: str, odbiorca: str, tytul: str) -> dict:
	"""Filtr `frappe.get_all("CRM Task", filters=...)` do deduplikacji: czy odbiorca
	ma juz OTWARTE (nie Done/Canceled) zadanie o tym tytule dla tej szansy.

	Zwraca zawsze NOWY dict, nigdy nie dzieli obiektu miedzy wywolaniami.
	"""
	return {
		"reference_doctype": "CRM Deal",
		"reference_docname": deal,
		"assigned_to": odbiorca,
		"title": tytul,
		"status": ["not in", list(STATUSY_ZAMKNIETE)],
	}


def dane_zadania(
	rodzaj: str,
	klient: str,
	deal: str,
	autor: str,
	odbiorca: str,
	dzisiaj: date,
	termin_dni: int,
) -> dict:
	"""Kompletny dict gotowy dla `frappe.get_doc(...)` do zalozenia jednego `CRM Task`
	dla jednego odbiorcy.

	`start_date` to `dzisiaj` (pole Date), `due_date` to `oblicz_termin(...)` (pole
	Datetime, akceptuje string daty ISO, patrz `crm/api/pipeline.py`) albo `None`, gdy
	`termin_dni` nie ustawia terminu. Nieznany `rodzaj` daje `ValueError` (przez
	`tytul_zadania`/`opis_zadania_html`).
	"""
	termin = oblicz_termin(dzisiaj, termin_dni)
	return {
		"doctype": "CRM Task",
		"title": tytul_zadania(rodzaj, klient),
		"description": opis_zadania_html(rodzaj, klient, deal, autor),
		"status": "Todo",
		"priority": "Medium",
		"start_date": dzisiaj.isoformat(),
		"due_date": termin.isoformat() if termin else None,
		"assigned_to": odbiorca,
		"reference_doctype": "CRM Deal",
		"reference_docname": deal,
	}
