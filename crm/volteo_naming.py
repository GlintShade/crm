# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Nazewnictwo dokumentów `CRM Deal` w formacie ``PRO/<KOD>/<RR>/<NUMER>``.

Moduł celowo nie importuje ``frappe`` — to jedyny sposób, żeby dało się go
przetestować lokalnie (na tej maszynie ``frappe`` nie jest instalowalne, więc
reszta backendu ma wyłącznie bramkę składniową). Cała logika zależna od
frameworka (pobranie kolejnego numeru z serii, złożenie nazwy dokumentu)
mieszka w ``crm.fcrm.doctype.crm_deal.crm_deal.CRMDeal.autoname``.
"""

UMOWA_CODES: dict[str, str] = {
	"Fotowoltaika": "PV",
	"Fotowoltaika + Magazyn": "PVME",
	"Magazyn energii": "ME",
	"Czyste Powietrze": "CP",
}
"""Mapowanie rodzaju umowy (wartość pola `custom_rodzaj_umowy`) na kod używany w nazwie dokumentu."""

FALLBACK_CODE = "XX"
"""Kod używany dla nieznanego, pustego albo brakującego rodzaju umowy."""

SERIES_KEY = "PRO-UMOWA-"
"""Klucz wiersza `tabSeries` — jeden, wspólny dla wszystkich rodzajów umowy."""

SERIES_DIGITS = 4
"""Liczba cyfr licznika przed uzupełnieniem zerami wiodącymi (np. 1000, po 9999 naturalnie 5 cyfr)."""


def code_for(rodzaj: str | None) -> str:
	"""Zwraca kod rodzaju umowy dla nazwy dokumentu.

	Nieznany, pusty albo brakujący rodzaj zwraca `FALLBACK_CODE`. Nie mutuje `UMOWA_CODES`.
	"""
	if not rodzaj:
		return FALLBACK_CODE
	return UMOWA_CODES.get(rodzaj, FALLBACK_CODE)


def format_deal_name(code: str, yy: str, number: str) -> str:
	"""Składa pełną nazwę dokumentu `CRM Deal` z kodu rodzaju, roku i numeru porządkowego."""
	return f"PRO/{code}/{yy}/{number}"
