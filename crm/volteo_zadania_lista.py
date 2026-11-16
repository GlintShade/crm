# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Czysta logika kolumny "Klient" na liscie Zadan (`CRM Task`).

Modul celowo nie importuje ``frappe``, wzorem ``crm/volteo_zadania.py`` i
``crm/volteo_pipeline.py``. Warstwe frappe-owa (zapytania o `lead_name` szans
i leadow) niesie `crm.api.doc._dolacz_klienta_zadan`.

Funkcje sa immutable: zwracaja nowe struktury, nigdy nie mutuja argumentow.
"""

KLUCZ_KLIENTA = "_klient"
"""Pseudo-pole listy: nie jest DocFieldem, dzieli klucz kolumny "Klient"
z `CRMTask.default_list_data()`. Wartosc dokleja `get_data` po zapytaniu SQL."""

DOCTYPE_SZANSY = "CRM Deal"
DOCTYPE_LEADA = "CRM Lead"


def klient_zadania(
	reference_doctype: str | None,
	reference_docname: str | None,
	klienci_szans: dict,
	klienci_leadow: dict,
) -> str:
	"""Nazwa klienta zadania: `lead_name` szansy (CRM Deal) albo leada (CRM Lead).

	Brak powiazania, nieznany doctype albo brak wpisu w mapie daje pusty string.
	"""
	if not reference_doctype or not reference_docname:
		return ""
	if reference_doctype == DOCTYPE_SZANSY:
		mapa = klienci_szans
	elif reference_doctype == DOCTYPE_LEADA:
		mapa = klienci_leadow
	else:
		return ""
	return (mapa.get(reference_docname) or "").strip()


def nazwy_powiazan(wiersze: list[dict]) -> tuple[list[str], list[str]]:
	"""Unikalne nazwy szans i leadow z wierszy listy zadan.

	Zwraca `(szanse, leady)`, kazda lista w kolejnosci pierwszego wystapienia,
	bez duplikatow i bez pustych nazw.
	"""
	szanse: list[str] = []
	leady: list[str] = []
	for wiersz in wiersze:
		doctype = wiersz.get("reference_doctype")
		nazwa = wiersz.get("reference_docname")
		if not nazwa:
			continue
		if doctype == DOCTYPE_SZANSY and nazwa not in szanse:
			szanse.append(nazwa)
		elif doctype == DOCTYPE_LEADA and nazwa not in leady:
			leady.append(nazwa)
	return szanse, leady
